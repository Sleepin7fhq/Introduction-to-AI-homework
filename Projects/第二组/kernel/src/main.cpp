// ============================================================================
//  main.cpp —— 宿舍噪音识别内核（可执行程序）
//
//  职责：
//    1) 加载 ONNX 模型（AST 音频分类）
//    2) 启动麦克风采集 → 分段 → 特征 → 推理 → 时长统计 → 阈值告警
//    3) 通过本地 socket 对 UI 提供结构化结果（JSON-lines）
//    4) 支持离线 wav 文件推理（答辩演示）
//
//  ★ 隐私：内核不写任何音频文件；内存中的音频片段在推理完成后立即擦除。
// ============================================================================
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "dn/capture.h"
#include "dn/classifier.h"
#include "dn/ipc_server.h"
#include "dn/json.h"
#include "dn/pipeline.h"
#include "dn/types.h"
#include "dn/util.h"
#include "dn/wav_reader.h"

#include "ast_labels.h"

namespace {

dn::IpcServer g_server;
dn::Pipeline g_pipeline;
dn::Classifier g_classifier;
dn::MicrophoneCapture g_capture;
std::atomic<bool> g_capture_running{false};
std::atomic<int> g_alert_seq{0};

// ---------------------------------------------------------------------------
//  状态快照 → JSON
// ---------------------------------------------------------------------------
std::string BuildStateJson() {
  dn::StateSnapshot s = g_pipeline.Snapshot();
  s.kernel_alive = true;
  s.capture_running = g_capture_running.load();
  s.device_name = g_capture.device_name();
  s.model_path = g_classifier.model_path();
  s.client_count = static_cast<std::int64_t>(g_server.client_count());

  dn::json::Writer w;
  w.BeginObject();
  w.Key("type").Str("state");
  w.Key("kernel_alive").Bool(s.kernel_alive);
  w.Key("capture_running").Bool(s.capture_running);
  w.Key("device_name").Str(dn::EnsureUtf8(s.device_name));
  w.Key("model_path").Str(dn::EnsureUtf8(s.model_path));
  w.Key("total_audio_sec").Num(s.total_audio_sec);
  w.Key("segment_total").Int(static_cast<long long>(s.segment_total));
  w.Key("infer_ms_avg").Num(s.infer_ms_avg);
  w.Key("client_count").Int(static_cast<long long>(s.client_count));

  // 配置
  w.Key("config").BeginObject();
  w.Key("segment_sec").Num(s.config.segment_sec);
  w.Key("min_confidence").Num(static_cast<double>(s.config.min_confidence));
  w.Key("auto_alert").Bool(s.config.auto_alert);
  w.Key("normal_volume_dbfs").Num(s.config.normal_volume_dbfs);
  w.Key("loud_dbfs").Num(s.config.loud_dbfs);
  w.Key("thresholds").BeginArray();
  for (int c = 0; c < dn::kClassCount; ++c) {
    w.Num(s.config.thresholds[c]);
  }
  w.EndArray();
  w.EndObject();

  // 各类时长
  w.Key("classes").BeginArray();
  for (int c = 0; c < dn::kClassCount; ++c) {
    const auto& st = s.classes[static_cast<size_t>(c)];
    w.BeginObject();
    w.Key("index").Int(c);
    w.Key("key").Str(dorm_noise::kClassKeys[c]);
    w.Key("zh").Str(dorm_noise::kClassZh[c]);
    w.Key("class_zh").Str(dorm_noise::kClassZh[c]);
    w.Key("duration_sec").Num(st.duration_sec);
    w.Key("threshold_sec").Num(st.threshold_sec);
    w.Key("exceeded").Bool(st.exceeded);
    w.Key("last_confidence").Num(static_cast<double>(st.last_confidence));
    w.Key("segment_count").Int(static_cast<long long>(st.segment_count));
    w.EndObject();
  }
  w.EndArray();

  // 最近一次识别结果
  w.Key("last").BeginObject();
  w.Key("class_index").Int(s.last.class_index);
  w.Key("class_key").Str(s.last.class_index >= 0
                             ? dorm_noise::kClassKeys[s.last.class_index]
                             : std::string());
  w.Key("class_zh").Str(s.last.class_index >= 0
                            ? dorm_noise::kClassZh[s.last.class_index]
                            : std::string());
  w.Key("confidence").Num(static_cast<double>(s.last.confidence));
  w.Key("top_label_id").Int(s.last.top_label_id);
  w.Key("top_label_name").Str(s.last.top_label_name);
  w.Key("top_label_prob").Num(static_cast<double>(s.last.top_label_prob));
  w.Key("segment_sec").Num(s.last.segment_sec);
  w.Key("rms_dbfs").Num(s.last.rms_dbfs);
  w.Key("segment_index").Int(static_cast<long long>(s.last.segment_index));
  w.Key("class_mass").BeginArray();
  for (int c = 0; c < dn::kClassCount; ++c) {
    w.Num(static_cast<double>(s.last.class_mass[static_cast<size_t>(c)]));
  }
  w.EndArray();
  w.EndObject();

  // 历史（最近若干段，供 UI 画图）
  w.Key("history").BeginArray();
  const size_t hist_n = s.history.size() > 120 ? 120 : s.history.size();
  for (size_t i = hist_n; i-- > 0;) {
    const auto& h = s.history[i];
    w.BeginObject();
    w.Key("index").Int(static_cast<long long>(h.segment_index));
    w.Key("class_index").Int(h.class_index);
    w.Key("class_zh").Str(h.class_index >= 0 ? dorm_noise::kClassZh[h.class_index]
                                           : std::string());
    w.Key("confidence").Num(static_cast<double>(h.confidence));
    w.Key("top_label_name").Str(h.top_label_name);
    w.Key("segment_sec").Num(h.segment_sec);
    w.Key("audio_time_sec").Num(h.audio_time_sec);
    w.EndObject();
  }
  w.EndArray();

  w.EndObject();
  return w.str();
}

std::string BuildAlertJson(const dn::AlertEvent& ev) {
  dn::json::Writer w;
  w.BeginObject();
  w.Key("type").Str("alert");
  w.Key("seq").Int(g_alert_seq.fetch_add(1));
  w.Key("class_index").Int(ev.class_index);
  w.Key("class_key").Str(dorm_noise::kClassZh[ev.class_index]);
  w.Key("duration_sec").Num(ev.duration_sec);
  w.Key("threshold_sec").Num(ev.threshold_sec);
  w.Key("message").Str(ev.message);
  w.EndObject();
  return w.str();
}

// ---------------------------------------------------------------------------
//  采集启动 / 停止
// ---------------------------------------------------------------------------
bool StartCapture(std::string* error) {
  if (g_capture_running.load()) return true;
  auto sink = [](const float* samples, size_t count) {
    g_pipeline.PushRealtime(samples, count);
  };
  if (!g_capture.Start(sink, error)) return false;
  g_capture_running.store(true);
  return true;
}

void StopCapture() {
  if (!g_capture_running.load()) return;
  g_capture.Stop();
  g_capture_running.store(false);
}

// ---------------------------------------------------------------------------
//  离线文件推理
// ---------------------------------------------------------------------------
std::string RunOffline(const std::string& path) {
  dn::WavData wav;
  std::string err;
  if (!dn::ReadWavMono(path, &wav, &err)) {
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("error");
    w.Key("message").Str(err);
    w.EndObject();
    return w.str();
  }

  const auto results = g_pipeline.ProcessOffline(wav.samples, wav.sample_rate);
  dn::SecureZero(wav.samples.data(), wav.samples.size() * sizeof(float));

  dn::json::Writer w;
  w.BeginObject();
  w.Key("type").Str("offline_result");
  w.Key("file").Str(dn::EnsureUtf8(path));
  w.Key("duration_sec").Num(wav.duration_sec);
  w.Key("sample_rate").Int(wav.sample_rate);
  w.Key("segments").BeginArray();
  for (const auto& r : results) {
    w.BeginObject();
    w.Key("class_index").Int(r.class_index);
    w.Key("class_key").Str(r.class_index >= 0 ? dorm_noise::kClassKeys[r.class_index]
                                           : std::string());
    w.Key("class_zh").Str(r.class_index >= 0 ? dorm_noise::kClassZh[r.class_index]
                                            : std::string());
    w.Key("confidence").Num(static_cast<double>(r.confidence));
    w.Key("top_label_name").Str(r.top_label_name);
    w.Key("top_label_prob").Num(static_cast<double>(r.top_label_prob));
    w.Key("segment_sec").Num(r.segment_sec);
    w.Key("rms_dbfs").Num(r.rms_dbfs);
    w.EndObject();
  }
  w.EndArray();
  w.EndObject();
  return w.str();
}

// ---------------------------------------------------------------------------
//  命令处理
// ---------------------------------------------------------------------------

/// 给响应 JSON 附上请求 ID（rid）。
/// UI 端每次命令都带一个短 rid，内核原样回显，UI 才能把"命令响应"和
/// 周期性 state 广播区分开 —— 否则 500ms 一次的广播会把 ok 响应挤掉。
/// 这里只接受字母数字/下划线/短横线，避免 JSON 转义问题。
std::string WithRid(std::string json, const std::string& rid) {
  if (rid.empty() || json.size() < 2 || json.back() != '}') return json;
  for (char c : rid) {
    const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                    (c >= '0' && c <= '9') || c == '_' || c == '-';
    if (!ok) return json;
  }
  json.pop_back();
  json += ",\"rid\":\"" + rid + "\"}";
  return json;
}

std::string HandleCommandInner(const std::string& line) {
  dn::json::Value req;
  std::string err;
  if (!dn::json::Value::Parse(line, &req, &err)) {
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("error");
    w.Key("message").Str("JSON 解析失败: " + err);
    w.EndObject();
    return w.str();
  }
  const dn::json::Value* cmd_v = req.find("cmd");
  const std::string cmd = cmd_v ? cmd_v->as_string() : "";

  if (cmd == "status") {
    return BuildStateJson();
  }
  if (cmd == "set_config") {
    dn::KernelConfig cfg = g_pipeline.config();
    if (const auto* v = req.find("segment_sec")) cfg.segment_sec = v->as_number(cfg.segment_sec);
    if (const auto* v = req.find("min_confidence")) {
      cfg.min_confidence = static_cast<float>(v->as_number(cfg.min_confidence));
    }
    if (const auto* v = req.find("auto_alert")) cfg.auto_alert = v->as_bool(cfg.auto_alert);
    if (const auto* v = req.find("thresholds")) {
      const auto& arr = v->as_array();
      for (size_t i = 0; i < arr.size() && i < dn::kClassCount; ++i) {
        cfg.thresholds[i] = arr[i].as_number(cfg.thresholds[i]);
      }
    }
    if (const auto* v = req.find("normal_volume_dbfs")) {
      cfg.normal_volume_dbfs = v->as_number(cfg.normal_volume_dbfs);
    }
    if (const auto* v = req.find("loud_dbfs")) {
      cfg.loud_dbfs = v->as_number(cfg.loud_dbfs);
    }
    if (!std::isfinite(cfg.normal_volume_dbfs) || cfg.normal_volume_dbfs < -100.0 ||
        cfg.normal_volume_dbfs > 0.0 || !std::isfinite(cfg.loud_dbfs) ||
        cfg.loud_dbfs < -100.0 || cfg.loud_dbfs > 0.0 ||
        cfg.loud_dbfs < cfg.normal_volume_dbfs || !std::isfinite(cfg.segment_sec) ||
        cfg.segment_sec < 1.0 || cfg.segment_sec > 10.0) {
      return "{\"type\":\"error\",\"message\":\"电平须在 -100 到 0 dBFS，且大声门限不低于正常音量门限；分段须在 1 到 10 秒\"}";
    }
    g_pipeline.UpdateConfig(cfg);
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("ok");
    w.Key("cmd").Str("set_config");
    w.EndObject();
    return w.str();
  }
  if (cmd == "start_capture") {
    std::string error;
    if (!StartCapture(&error)) {
      dn::json::Writer w;
      w.BeginObject();
      w.Key("type").Str("error");
      w.Key("message").Str(error);
      w.EndObject();
      return w.str();
    }
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("ok");
    w.Key("cmd").Str("start_capture");
    w.EndObject();
    return w.str();
  }
  if (cmd == "stop_capture") {
    StopCapture();
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("ok");
    w.Key("cmd").Str("stop_capture");
    w.EndObject();
    return w.str();
  }
  if (cmd == "reset") {
    g_pipeline.ResetStats();
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("ok");
    w.Key("cmd").Str("reset");
    w.EndObject();
    return w.str();
  }
  if (cmd == "offline_file") {
    const auto* v = req.find("path");
    return RunOffline(v ? dn::Utf8ToLocal(v->as_string()) : std::string());
  }
  if (cmd == "quit") {
    StopCapture();
    dn::json::Writer w;
    w.BeginObject();
    w.Key("type").Str("ok");
    w.Key("cmd").Str("quit");
    w.EndObject();
    return w.str();
  }

  dn::json::Writer w;
  w.BeginObject();
  w.Key("type").Str("error");
  w.Key("message").Str("未知命令: " + cmd);
  w.EndObject();
  return w.str();
}

std::string HandleCommand(const std::string& line) {
  // 解析出请求里的 rid（如果有），响应时原样回显。
  std::string rid;
  {
    const size_t k = line.find("\"rid\"");
    if (k != std::string::npos) {
      const size_t c = line.find(':', k);
      if (c != std::string::npos) {
        const size_t q1 = line.find('"', c);
        if (q1 != std::string::npos) {
          const size_t q2 = line.find('"', q1 + 1);
          if (q2 != std::string::npos) rid = line.substr(q1 + 1, q2 - q1 - 1);
        }
      }
    }
  }
  return WithRid(HandleCommandInner(line), rid);
}

// ---------------------------------------------------------------------------
//  自检模式：与 Python 黄金向量比对特征（开发/答辩前验证用）
// ---------------------------------------------------------------------------
int RunSelfTest(const std::string& golden_bin, const std::string& golden_wav) {
#if defined(_WIN32)
  std::FILE* f = nullptr;
  {
    const std::wstring wpath = dn::ToWideFlexiblePath(golden_bin);
    if (!wpath.empty()) _wfopen_s(&f, wpath.c_str(), L"rb");
  }
#else
  std::FILE* f = std::fopen(golden_bin.c_str(), "rb");
#endif
  if (f == nullptr) {
    std::cerr << "无法打开黄金特征文件: " << dn::EnsureUtf8(golden_bin) << "\n";
    return 2;
  }
  std::vector<float> golden(1024 * 128);
  const size_t got = std::fread(golden.data(), sizeof(float), golden.size(), f);
  std::fclose(f);
  if (got != golden.size()) {
    std::cerr << "黄金特征文件长度不符\n";
    return 2;
  }

  dn::WavData wav;
  std::string err;
  if (!dn::ReadWavMono(golden_wav, &wav, &err)) {
    std::cerr << "读取黄金音频失败: " << dn::EnsureUtf8(err) << "\n";
    return 2;
  }

  dn::FeatureExtractor feat;
  feat.Configure(dn::FeatureParams());
  std::vector<float> mine;
  if (!feat.Extract(wav.samples, &mine)) {
    std::cerr << "特征提取失败\n";
    return 2;
  }
  dn::SecureZero(wav.samples.data(), wav.samples.size() * sizeof(float));

  double max_diff = 0.0;
  for (size_t i = 0; i < golden.size(); ++i) {
    max_diff = std::max(max_diff, std::fabs(static_cast<double>(mine[i] - golden[i])));
  }
  std::printf("特征比对: max_abs_diff = %.9f\n", max_diff);
  if (max_diff < 0.02) {
    std::printf("[PASS] C++ 特征与 Python 黄金向量一致\n");
    return 0;
  }
  std::printf("[FAIL] 差异过大\n");
  return 1;
}

void PrintUsage() {
  std::printf(
      "宿舍噪音智能识别内核 (dorm_noise_kernel)\n"
      "用法:\n"
      "  dorm_noise_kernel --model <onnx> [--port <port>] [--threads N] [--segment-sec X]\n"
      "  dorm_noise_kernel --selftest <golden_fbank.bin> <golden.wav>\n"
      "  dorm_noise_kernel --offline <onnx> <wav> [--segment-sec X]\n"
      "\n"
      "选项:\n"
      "  --model       ONNX 模型路径 (默认 models/ast_audioset.onnx)\n"
      "  --port        IPC 端口，默认 8765；传 0 表示自动分配\n"
      "  --threads     推理线程数，默认 0 = 自动（取 CPU 逻辑核数的一半，上限 8）\n"
      "  --segment-sec 分段长度（秒），默认 5.0\n"
      "  --no-capture  启动后不自动开启麦克风采集\n");
}

// 自动挑线程数：AST 是 12 层 Transformer，单段推理是 CPU 密集型。
// 实测（i9-14900HX / 32 逻辑核）：1 线程 ≈2.7 s、4 线程 ≈1.3 s、8 线程 ≈0.95 s、
// 16 线程 ≈0.65 s、32 线程反而回退到 ≈0.95 s（超线程争抢）。
// 取"物理核数的一半"是个稳妥的默认值，既快又不会把 UI 线程饿死。
int AutoThreads() {
  unsigned hw = std::thread::hardware_concurrency();
  if (hw == 0) return 4;
  int t = static_cast<int>(hw / 2);
  if (t > 8) t = 8;
  if (t < 1) t = 1;
  return t;
}

}  // namespace

int main(int argc, char** argv) {
  dn::SetConsoleUtf8();
  std::string model_path = "models/ast_audioset.onnx";
  int port = 8765;
  int threads = 0;  // 0 = 自动
  double segment_sec = 5.0;
  bool auto_capture = true;
  std::string selftest_bin, selftest_wav, offline_wav;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    auto next = [&](const char* def) -> std::string {
      return (i + 1 < argc) ? std::string(argv[++i]) : std::string(def);
    };
    if (a == "--model") model_path = next("models/ast_audioset.onnx");
    else if (a == "--port") port = std::stoi(next("8765"));
    else if (a == "--threads") threads = std::stoi(next("0"));
    else if (a == "--segment-sec") segment_sec = std::stod(next("5.0"));
    else if (a == "--no-capture") auto_capture = false;
    else if (a == "--selftest") { selftest_bin = next(""); selftest_wav = next(""); }
    else if (a == "--offline") {
      // 兼容两种写法：--offline <wav> 与 --offline <onnx> <wav>
      std::string first = next("");
      if (first.size() > 5 && first.compare(first.size() - 5, 5, ".onnx") == 0) {
        model_path = first;
        offline_wav = next("");
      } else {
        offline_wav = first;
      }
    }
    else if (a == "--help" || a == "-h") { PrintUsage(); return 0; }
  }

  if (!selftest_bin.empty()) {
    return RunSelfTest(selftest_bin, selftest_wav);
  }

  if (threads <= 0) threads = AutoThreads();
  std::printf("推理线程数: %d\n", threads);

  // 加载模型
  dn::ClassifierOptions opts;
  opts.num_threads = threads;
  std::string err;
  if (!g_classifier.Load(model_path, opts, &err)) {
    std::cerr << "模型加载失败: " << dn::EnsureUtf8(err) << "\n";
    std::cerr << "提示：请先运行 scripts/export_ast_onnx.py 生成 ONNX 模型。\n";
    return 1;
  }
  std::printf("模型已加载: %s\n", dn::EnsureUtf8(model_path).c_str());

  dn::KernelConfig cfg = g_pipeline.config();
  cfg.segment_sec = segment_sec;
  cfg.num_threads = threads;
  g_pipeline.UpdateConfig(cfg);
  g_pipeline.SetClassifier(&g_classifier);
  g_pipeline.SetAlertCallback([](const dn::AlertEvent& ev) {
    const std::string json = BuildAlertJson(ev);
    std::printf("[ALERT] %s\n", ev.message.c_str());
    g_server.Broadcast(json);
  });

  // 离线模式：处理一个文件后直接退出（答辩演示用）
  if (!offline_wav.empty()) {
    const std::string json = RunOffline(offline_wav);
    std::printf("%s\n", json.c_str());
    return 0;
  }

  // IPC 服务
  g_server.SetStateProvider([]() { return BuildStateJson(); });
  g_server.SetCommandHandler(HandleCommand);
  std::string ipc_err;
  if (!g_server.Start(port, &ipc_err)) {
    std::cerr << "IPC 服务启动失败: " << dn::EnsureUtf8(ipc_err) << "\n";
    return 1;
  }
  std::printf("IPC 服务已启动: 127.0.0.1:%d\n", g_server.port());
  std::printf("等待 UI 连接...\n");

  if (auto_capture) {
    std::string cap_err;
    if (StartCapture(&cap_err)) {
      std::printf("麦克风已启动: %s\n", dn::EnsureUtf8(g_capture.device_name()).c_str());
    } else {
      std::cerr << "麦克风启动失败: " << dn::EnsureUtf8(cap_err) << "\n";
      std::cerr << "可稍后通过 UI 的「开始采集」按钮重试。\n";
    }
  }

  // 主线程：定期广播状态
  while (true) {
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    if (g_server.client_count() > 0) {
      g_server.Broadcast(BuildStateJson());
    }
  }
}
