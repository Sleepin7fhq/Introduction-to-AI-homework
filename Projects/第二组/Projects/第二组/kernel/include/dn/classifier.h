// ============================================================================
//  dn/classifier.h —— AST 音频分类模型推理（ONNX Runtime）
//
//  模型：MIT/ast-finetuned-audioset-10-10-0.4593 导出的 ONNX
//        输入 input_values: [batch, 1024, 128] float
//        输出 logits:       [batch, 527]      float
//
//  ★ 隐私约束：推理完成后，logits 只是概率向量；内核不保存任何音频。
// ============================================================================
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "dn/types.h"

namespace dn {

struct ClassifierOptions {
  int num_threads = 4;
  std::string provider = "CPUExecutionProvider";
};

class Classifier {
 public:
  Classifier();
  ~Classifier();

  // 加载 ONNX 模型。失败返回 false，错误信息写入 error。
  bool Load(const std::string& model_path, const ClassifierOptions& opt, std::string* error);

  bool loaded() const;
  const std::string& model_path() const { return model_path_; }

  // 推理。features 是 [1024*128] 行主序的归一化梅尔特征。
  // 输出 logits（长度 527）与耗时（毫秒）。
  bool Infer(const std::vector<float>& features, std::vector<float>* logits, double* elapsed_ms);

  // 把 527 维 logits 聚合到 4 个目标类别（概率质量 + 最可能细分标签）。
  static void Aggregate(const std::vector<float>& logits, SegmentResult* out);

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
  std::string model_path_;
  // 输入/输出张量名（自己持有字符串，避免指向 ORT 临时分配区）
  std::vector<std::string> input_names_;
  std::vector<std::string> output_names_;
};

}  // namespace dn
