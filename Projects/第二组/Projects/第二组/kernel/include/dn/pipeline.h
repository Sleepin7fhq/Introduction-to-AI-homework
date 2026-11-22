// ============================================================================
//  dn/pipeline.h —— 推理流水线：分段 → 特征 → 推理 → 时长统计 → 阈值告警
//
//  ★ 隐私约束（需求第 5 条）在这一层落实：
//    - 原始 PCM 只存在于 SegmentBuffer 的内存缓冲中；
//    - 一旦切出分段并完成推理，缓冲区立即被 SecureZero() 擦除；
//    - 全程不写任何文件、不做任何录音、不做语音识别。
// ============================================================================
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include "dn/classifier.h"
#include "dn/feature_extractor.h"
#include "dn/types.h"

namespace dn {

// 内存擦除工具：把缓冲区覆盖为 0，避免原始音频残留在内存里。
void SecureZero(void* data, size_t bytes);

class Pipeline {
 public:
  using AlertCallback = std::function<void(const AlertEvent&)>;

  Pipeline();
  ~Pipeline();

  void SetClassifier(Classifier* classifier) { classifier_ = classifier; }
  void SetAlertCallback(AlertCallback cb) { alert_cb_ = std::move(cb); }

  const KernelConfig& config() const { return config_; }
  void UpdateConfig(const KernelConfig& cfg);

  // 追加一段实时采集到的 PCM（float, [-1,1], 单声道, 16kHz）。
  // 累积到 segment_sec 时自动切段并推理。
  void PushRealtime(const float* samples, size_t count);

  // 离线推理：读入整个 wav 的单声道 float 波形，按 segment_sec 逐段推理。
  // 返回分段结果列表。
  std::vector<SegmentResult> ProcessOffline(const std::vector<float>& samples, double sample_rate);

  // 取当前状态快照（不含任何音频内容）。
  StateSnapshot Snapshot() const;

  // 复位统计。
  void ResetStats();

 private:
  // 把缓冲区里已经攒够的一段 PCM 切出来做推理。
  bool ConsumeSegment(std::vector<float>* segment, bool realtime);

  Classifier* classifier_ = nullptr;
  FeatureExtractor feat_;
  KernelConfig config_;
  AlertCallback alert_cb_;

  // 实时采集缓冲（原始 PCM，仅存在于内存）
  std::vector<float> buffer_;
  double buffer_sec_ = 0.0;

  // 统计
  std::array<ClassStat, kClassCount> stats_{};
  SegmentResult last_;
  std::vector<SegmentResult> history_;
  double total_audio_sec_ = 0.0;
  double infer_ms_avg_ = 0.0;
  std::int64_t segment_total_ = 0;
  std::int64_t segment_index_ = 0;
  bool alerted_[kClassCount] = {false, false, false, false};
};

}  // namespace dn
