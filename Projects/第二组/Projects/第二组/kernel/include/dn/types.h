// ============================================================================
//  dn/types.h —— 宿舍噪音识别内核的公共数据结构
//
//  设计原则（对应需求第 5/6 条）：
//    * 这里流转的全部是「结构化结果」：类别、置信度、时长、告警。
//    * 任何时候都不存在「原始音频」类型在内核对外接口上，
//      原始 PCM 只在 dn::Pipeline 内部的一个栈上缓冲里存在，
//      推理结束后立刻被 SecureZero() 擦除。
// ============================================================================
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace dn {

// ---------------------------------------------------------------------------
// 四个目标类别。顺序必须与 models/ast_labels.h 里的 ClassKey 一致，
// 也与 UI 上的展示顺序一致。
// ---------------------------------------------------------------------------
enum ClassIndex : int {
  kClassLoudTalk = 0,   // 大声喧哗
  kClassNormalVolume = 1, // 正常音量（低电平环境）
  kClassGameAudio = 2,  // 游戏外放
  kClassNormalTalk = 3, // 正常交谈
  kClassCount = 4
};

// ---------------------------------------------------------------------------
// 一个音频分段的识别结果
// ---------------------------------------------------------------------------
struct SegmentResult {
  int class_index = -1;                    // 判定类别；-1 = 低置信度/未分类
  float confidence = 0.f;                  // 判定类别的概率质量
  int top_label_id = -1;                   // AudioSet 最可能细分标签 id
  float top_label_prob = 0.f;              // 该细分标签概率
  std::string top_label_name;              // 该细分标签名称
  std::array<float, kClassCount> class_mass{};  // 四类各自的概率质量
  float other_mass = 0.f;                  // 其它 AudioSet 标签的概率质量
  double rms_dbfs = -120.0;                // 段 RMS 相对满幅电平，非 dB SPL
  double segment_sec = 0.0;                // 本分段时长（秒）
  std::int64_t segment_index = 0;          // 分段序号（从 1 开始）
  double audio_time_sec = 0.0;             // 累计已处理音频时长（秒）
};

// ---------------------------------------------------------------------------
// 超标告警事件
// ---------------------------------------------------------------------------
struct AlertEvent {
  int class_index = -1;
  double duration_sec = 0.0;   // 触发时的累计时长
  double threshold_sec = 0.0;  // 该类阈值
  std::string message;         // 已本地化好的中文提示
};

// ---------------------------------------------------------------------------
// 内核运行参数（全部可以通过 IPC 命令在运行时热更新）
// ---------------------------------------------------------------------------
struct KernelConfig {
  double segment_sec = 5.0;    // 分段长度（秒）
  double thresholds[kClassCount] = {15.0, 9999.0, 45.0, 9999.0};
  double normal_volume_dbfs = -45.0; // 段 RMS 低于此值归正常音量；非校准声压级
  double loud_dbfs = -22.0;      // 段 RMS 高于此值且语义为“说话”时，按大声喧哗处理
  float min_confidence = 0.05f;  // 低于此置信度的分段不计入时长
  int num_threads = 4;           // ONNX Runtime intra-op 线程数
  bool capture_enabled = true;   // 是否实时采集麦克风
  bool auto_alert = true;        // 超标是否主动推送告警
};

// ---------------------------------------------------------------------------
// 全局状态快照（UI 拉取状态时返回；同样只含结构化数据）
// ---------------------------------------------------------------------------
struct ClassStat {
  double duration_sec = 0.0;
  double threshold_sec = 0.0;
  bool exceeded = false;
  float last_confidence = 0.f;
  std::int64_t segment_count = 0;
};

struct StateSnapshot {
  bool kernel_alive = true;
  bool capture_running = false;
  std::string device_name;
  std::string model_path;
  KernelConfig config;
  double total_audio_sec = 0.0;  // 累计处理音频时长
  std::array<ClassStat, kClassCount> classes{};
  SegmentResult last;                       // 最近一次分段结果
  std::vector<SegmentResult> history;       // 最近 N 次分段结果（倒序）
  double infer_ms_avg = 0.0;                // 平均推理耗时（毫秒）
  std::int64_t segment_total = 0;           // 分段总数
  std::int64_t client_count = 0;            // 已连接 UI 数量
};

}  // namespace dn
