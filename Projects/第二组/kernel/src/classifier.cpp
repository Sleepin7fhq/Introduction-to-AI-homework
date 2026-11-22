// ============================================================================
//  dn/classifier.cpp —— ONNX Runtime 推理 + 四类概率聚合
//
//  隐私说明：本文件只处理"已经提取好的梅尔特征"与"概率向量"，
//            任何阶段都不接触、也不保存原始音频波形。
// ============================================================================
#include "dn/classifier.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <mutex>

// ★ 关键：定义 ORT_API_MANUAL_INIT，禁止 ORT C++ API 在静态初始化阶段
//   自动执行 `OrtGetApiBase()->GetApi(...)`。ORT 的头文件里那条全局动态初始化
//   与我们 main.cpp 里的全局对象（dn::Classifier g_classifier）跨翻译单元的
//   初始化顺序是不确定的 —— 一旦我们的全局对象先构造，就会解引用空指针，
//   直接 0xC0000005。改为手动初始化 + 惰性创建 Env，彻底规避该问题。
#define ORT_API_MANUAL_INIT
#include "onnxruntime_cxx_api.h"

// 放在 ORT 头文件之后：util.h 会引入 <windows.h>，若先引入会与
// onnxruntime_c_api.h 里的 SAL 宏定义（_Check_return_ 等）冲突告警。
#include "dn/util.h"

// 自动生成的标签表（四类 id 集合 + AudioSet 全量标签名）
#include "ast_labels.h"

#if defined(_WIN32)
#include <windows.h>
#endif

namespace dn {
namespace {

// AudioSet 527 类 → 4 个目标类别的映射表（构建一次，O(1) 查表）。
struct LabelMap {
  std::array<int, dorm_noise::kNumAudioSetLabels> to_class;
  LabelMap() {
    to_class.fill(-1);
    const int* ids[dorm_noise::kNumClasses] = {
        dorm_noise::kIds_loud_talk, dorm_noise::kIds_normal_volume,
        dorm_noise::kIds_game_audio, dorm_noise::kIds_normal_talk};
    const int counts[dorm_noise::kNumClasses] = {
        dorm_noise::kCount_loud_talk, dorm_noise::kCount_normal_volume,
        dorm_noise::kCount_game_audio, dorm_noise::kCount_normal_talk};
    for (int c = 0; c < dorm_noise::kNumClasses; ++c) {
      for (int i = 0; i < counts[c]; ++i) {
        to_class[static_cast<size_t>(ids[c][i])] = c;
      }
    }
  }
};

const LabelMap& GetLabelMap() {
  static const LabelMap m;
  return m;
}

// ORTCHAR_T 在 Windows 下是 wchar_t，需要把路径转成宽字符。
// 中文 Windows 上命令行参数可能是 GBK，工作目录也可能含中文，
// 因此先按 UTF-8 严格解码，再按系统 ANSI 代码页解码，取第一个真实存在的路径。
std::wstring ToWide(const std::string& s) {
#if defined(_WIN32)
  return dn::ToWideFlexiblePath(s);
#else
  return std::wstring(s.begin(), s.end());
#endif
}

// 手动初始化 ORT C++ API：必须先注册 API 指针，再创建 Env / Session。
// 见文件头关于静态初始化顺序的说明。
void EnsureOrtApi() {
  static std::once_flag once;
  std::call_once(once, []() {
    Ort::InitApi(OrtGetApiBase()->GetApi(ORT_API_VERSION));
  });
}

}  // namespace

struct Classifier::Impl {
  // Env / MemoryInfo 都必须在 Ort::InitApi() 之后才能构造，故用惰性 unique_ptr。
  std::unique_ptr<Ort::Env> env;
  std::unique_ptr<Ort::Session> session;
  std::unique_ptr<Ort::MemoryInfo> mem_info;
};

Classifier::Classifier() : impl_(new Impl) {
  // 立刻注册 ORT C API 指针：即使模型从未加载，析构函数也要能安全调用 GetApi()。
  EnsureOrtApi();
}
Classifier::~Classifier() = default;

bool Classifier::loaded() const { return impl_ && impl_->session != nullptr; }

bool Classifier::Load(const std::string& model_path, const ClassifierOptions& opt,
                      std::string* error) {
  try {
    EnsureOrtApi();
    if (!impl_->env) {
      impl_->env.reset(new Ort::Env(ORT_LOGGING_LEVEL_WARNING, "dorm_noise"));
      impl_->mem_info.reset(new Ort::MemoryInfo(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)));
    }

    Ort::SessionOptions so;
    so.SetIntraOpNumThreads(opt.num_threads > 0 ? opt.num_threads : 1);
    so.SetInterOpNumThreads(1);
    so.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    so.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);

    const std::wstring wide_path = ToWide(model_path);
    impl_->session.reset(
        new Ort::Session(*impl_->env, wide_path.c_str(), so));

    // 读取真实输入/输出名，避免硬编码。
    Ort::AllocatorWithDefaultOptions allocator;
    input_names_.clear();
    output_names_.clear();
    for (size_t i = 0; i < impl_->session->GetInputCount(); ++i) {
      auto name = impl_->session->GetInputNameAllocated(i, allocator);
      input_names_.push_back(std::string(name.get()));
    }
    for (size_t i = 0; i < impl_->session->GetOutputCount(); ++i) {
      auto name = impl_->session->GetOutputNameAllocated(i, allocator);
      output_names_.push_back(std::string(name.get()));
    }
    if (input_names_.empty() || output_names_.empty()) {
      if (error) *error = "ONNX 模型没有输入/输出张量";
      return false;
    }
    model_path_ = model_path;
    return true;
  } catch (const Ort::Exception& e) {
    if (error) *error = std::string("ONNX 加载失败: ") + e.what();
    return false;
  } catch (const std::exception& e) {
    if (error) *error = std::string("ONNX 加载失败: ") + e.what();
    return false;
  }
}

bool Classifier::Infer(const std::vector<float>& features, std::vector<float>* logits,
                       double* elapsed_ms) {
  if (!loaded()) return false;
  const int64_t shape[3] = {1, dorm_noise::kMaxLength, dorm_noise::kNumMelBins};
  try {
    auto t0 = std::chrono::steady_clock::now();
    Ort::Value input = Ort::Value::CreateTensor<float>(
        *impl_->mem_info, const_cast<float*>(features.data()), features.size(), shape, 3);
    std::vector<const char*> in_c, out_c;
    for (const auto& n : input_names_) in_c.push_back(n.c_str());
    for (const auto& n : output_names_) out_c.push_back(n.c_str());
    auto outputs = impl_->session->Run(Ort::RunOptions{nullptr}, in_c.data(),
                                       &input, 1, out_c.data(), out_c.size());
    auto t1 = std::chrono::steady_clock::now();
    if (elapsed_ms) {
      *elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    }
    if (outputs.empty() || !outputs[0].IsTensor()) return false;
    auto info = outputs[0].GetTensorTypeAndShapeInfo();
    const size_t count = info.GetElementCount();
    const float* data = outputs[0].GetTensorData<float>();
    logits->assign(data, data + count);
    return true;
  } catch (const Ort::Exception&) {
    if (elapsed_ms) *elapsed_ms = 0.0;
    return false;
  }
}

void Classifier::Aggregate(const std::vector<float>& logits, SegmentResult* out) {
  out->class_mass.fill(0.f);
  out->other_mass = 0.f;
  out->top_label_id = -1;
  out->top_label_prob = 0.f;
  out->top_label_name.clear();
  out->class_index = -1;
  out->confidence = 0.f;
  if (logits.empty()) return;

  // softmax（数值稳定版）
  std::vector<double> prob(logits.size());
  double max_v = -1e300;
  for (size_t i = 0; i < logits.size(); ++i) max_v = std::max(max_v, static_cast<double>(logits[i]));
  double sum = 0.0;
  for (size_t i = 0; i < logits.size(); ++i) {
    prob[i] = std::exp(static_cast<double>(logits[i]) - max_v);
    sum += prob[i];
  }
  if (sum <= 0.0) sum = 1.0;

  const LabelMap& map = GetLabelMap();
  double best_p = -1.0;
  int best_id = -1;
  for (size_t i = 0; i < logits.size(); ++i) {
    prob[i] /= sum;
    if (prob[i] > best_p) {
      best_p = prob[i];
      best_id = static_cast<int>(i);
    }
    const int c = (i < map.to_class.size()) ? map.to_class[i] : -1;
    if (c >= 0 && c < kClassCount) {
      out->class_mass[static_cast<size_t>(c)] += static_cast<float>(prob[i]);
    } else {
      out->other_mass += static_cast<float>(prob[i]);
    }
  }

  out->top_label_id = best_id;
  out->top_label_prob = static_cast<float>(best_p);
  if (best_id >= 0 && best_id < dorm_noise::kNumAudioSetLabels) {
    out->top_label_name = dorm_noise::kAudioSetLabels[best_id];
  }

  // 判定类别 = 概率质量最大的类
  int best_c = -1;
  float best_mass = -1.f;
  for (int c = 0; c < kClassCount; ++c) {
    if (out->class_mass[static_cast<size_t>(c)] > best_mass) {
      best_mass = out->class_mass[static_cast<size_t>(c)];
      best_c = c;
    }
  }
  out->class_index = best_c;
  out->confidence = best_mass > 0.f ? best_mass : 0.f;
}

}  // namespace dn
