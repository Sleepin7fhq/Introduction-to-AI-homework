// ============================================================================
//  dn/pipeline.cpp —— 推理流水线实现
// ============================================================================
#include "dn/pipeline.h"

#include <algorithm>
#include <cmath>
#include <cstring>

// 四类中文名（自动生成的标签表）
#include "ast_labels.h"

namespace dn {

void SecureZero(void* data, size_t bytes) {
  if (data == nullptr || bytes == 0) return;
  // volatile 指针防止编译器优化掉这次写入。
  volatile unsigned char* p = static_cast<volatile unsigned char*>(data);
  while (bytes--) *p++ = 0;
}

namespace {
constexpr size_t kMaxHistory = 200;
}

Pipeline::Pipeline() { feat_.Configure(FeatureParams()); }

Pipeline::~Pipeline() {
  SecureZero(buffer_.data(), buffer_.size() * sizeof(float));
  buffer_.clear();
  buffer_.shrink_to_fit();
}

void Pipeline::UpdateConfig(const KernelConfig& cfg) {
  config_ = cfg;
  // 阈值变化时重置告警状态，避免旧的告警标志卡住。
  for (int c = 0; c < kClassCount; ++c) {
    stats_[static_cast<size_t>(c)].threshold_sec = config_.thresholds[c];
    if (stats_[static_cast<size_t>(c)].duration_sec < config_.thresholds[c]) {
      alerted_[c] = false;
    }
  }
}

bool Pipeline::ConsumeSegment(std::vector<float>* segment, bool realtime) {
  if (!classifier_ || !classifier_->loaded()) return false;
  if (segment->empty()) return false;

  std::vector<float> features;
  const bool ok = feat_.Extract(*segment, &features);
  if (!ok) {
    SecureZero(segment->data(), segment->size() * sizeof(float));
    return false;
  }

  std::vector<float> logits;
  double ms = 0.0;
  if (!classifier_->Infer(features, &logits, &ms)) {
    SecureZero(segment->data(), segment->size() * sizeof(float));
    SecureZero(features.data(), features.size() * sizeof(float));
    return false;
  }

  SegmentResult res;
  Classifier::Aggregate(logits, &res);
  // 仅在内核计算相对音量；UI 只获得 RMS 标量，不获得波形。
  double square_sum = 0.0;
  for (float v : *segment) square_sum += static_cast<double>(v) * v;
  res.rms_dbfs = 20.0 * std::log10(std::max(1e-6,
      std::sqrt(square_sum / static_cast<double>(segment->size()))));
  const bool strong_game_event =
      (res.class_index == kClassGameAudio && res.confidence >= 0.10f);
  if (res.rms_dbfs <= config_.normal_volume_dbfs && !strong_game_event) {
    // 正常音量是电平规则，不是 AST 概率；1 表示该门控规则成立。
    // 例外：枪声/爆炸/游戏音乐即使很轻（麦克风只收到 -50 dBFS 左右），
    // 只要 AST 仍给出足够强的游戏标签，就保留语义分类，不压成“正常音量”。
    res.class_index = kClassNormalVolume;
    res.confidence = 1.f;
    res.class_mass.fill(0.f);
    res.class_mass[kClassNormalVolume] = 1.f;
  } else if (res.rms_dbfs > config_.normal_volume_dbfs &&
             res.confidence < config_.min_confidence) {
    // 低于置信度门限，保持未分类。
    res.class_index = -1;
  } else if (res.class_index == kClassNormalTalk &&
             res.confidence <= res.other_mass) {
    // 只对“正常交谈”保留 other_mass 保护：音乐等非目标声音不能因
    // 残余语音概率最大而被硬判成交谈。
    // 游戏/喧哗是“事件类”标签，即使不是全场最大标签，只要有足够
    // 概率质量就应被识别（枪声、爆炸往往只占混音的一部分）。
    res.class_index = -1;
  } else if (res.class_index == kClassNormalTalk &&
             res.rms_dbfs >= config_.loud_dbfs) {
    // 语义模型常把“大声喊叫”判成 Speech（正常交谈），导致大声喧哗永远不计时。
    // 这里补一条可配置的电平规则：高于 loud_dbfs 的说话段按大声喧哗处理。
    // 只改写“正常交谈”，不把音乐/游戏/未分类硬拉进大声喧哗。
    res.class_index = kClassLoudTalk;
    res.confidence = 1.f;
    res.class_mass.fill(0.f);
    res.class_mass[kClassLoudTalk] = 1.f;
  }
  res.segment_sec = static_cast<double>(segment->size()) /
                    static_cast<double>(feat_.params().sample_rate);
  res.segment_index = ++segment_index_;
  res.audio_time_sec = total_audio_sec_;

  // 原始音频在这一刻立即销毁（隐私硬约束）。
  SecureZero(segment->data(), segment->size() * sizeof(float));
  SecureZero(features.data(), features.size() * sizeof(float));

  // 统计
  total_audio_sec_ += res.segment_sec;
  ++segment_total_;
  infer_ms_avg_ = (infer_ms_avg_ == 0.0) ? ms : infer_ms_avg_ * 0.8 + ms * 0.2;

  if (res.class_index >= 0 && res.confidence >= config_.min_confidence) {
    auto& st = stats_[static_cast<size_t>(res.class_index)];
    st.duration_sec += res.segment_sec;
    st.last_confidence = res.confidence;
    st.segment_count += 1;
    st.threshold_sec = config_.thresholds[res.class_index];
    st.exceeded = st.duration_sec >= st.threshold_sec;

    // 超标告警：每类只在首次跨越阈值时触发一次，累计超出后再提升可再次提醒
    if (config_.auto_alert && st.threshold_sec < 9000.0 &&
        st.duration_sec >= st.threshold_sec) {
      if (!alerted_[res.class_index]) {
        alerted_[res.class_index] = true;
        AlertEvent ev;
        ev.class_index = res.class_index;
        ev.duration_sec = st.duration_sec;
        ev.threshold_sec = st.threshold_sec;
        ev.message = std::string(dorm_noise::kClassZh[res.class_index]) +
                     " 已累计 " + std::to_string(static_cast<int>(st.duration_sec)) +
                     " 秒，超过阈值 " + std::to_string(static_cast<int>(st.threshold_sec)) +
                     " 秒";
        if (alert_cb_) alert_cb_(ev);
      } else if (st.duration_sec >= st.threshold_sec * 1.5) {
        // 达到 1.5 倍再提醒一次，然后复位标志以便下次继续提醒
        alerted_[res.class_index] = false;
        AlertEvent ev;
        ev.class_index = res.class_index;
        ev.duration_sec = st.duration_sec;
        ev.threshold_sec = st.threshold_sec;
        ev.message = std::string(dorm_noise::kClassZh[res.class_index]) +
                     " 仍在持续，已累计 " + std::to_string(static_cast<int>(st.duration_sec)) +
                     " 秒（阈值 " + std::to_string(static_cast<int>(st.threshold_sec)) + " 秒）";
        if (alert_cb_) alert_cb_(ev);
      }
    }
  }

  last_ = res;
  history_.insert(history_.begin(), res);
  if (history_.size() > kMaxHistory) history_.resize(kMaxHistory);
  (void)realtime;
  return true;
}

void Pipeline::PushRealtime(const float* samples, size_t count) {
  if (samples == nullptr || count == 0) return;
  const size_t sr = static_cast<size_t>(feat_.params().sample_rate);
  const size_t seg_samples =
      static_cast<size_t>(std::max(1.0, config_.segment_sec) * static_cast<double>(sr));

  size_t offset = 0;
  while (offset < count) {
    const size_t space = seg_samples - buffer_.size();
    const size_t take = std::min(space, count - offset);
    buffer_.insert(buffer_.end(), samples + offset, samples + offset + take);
    offset += take;
    buffer_sec_ = static_cast<double>(buffer_.size()) / static_cast<double>(sr);

    if (buffer_.size() >= seg_samples) {
      std::vector<float> segment;
      segment.swap(buffer_);
      buffer_sec_ = 0.0;
      ConsumeSegment(&segment, true);
      SecureZero(segment.data(), segment.size() * sizeof(float));
      segment.clear();
      segment.shrink_to_fit();
    }
  }
}

std::vector<SegmentResult> Pipeline::ProcessOffline(const std::vector<float>& samples,
                                                    double sample_rate) {
  std::vector<SegmentResult> results;
  if (samples.empty()) return results;

  const size_t sr = static_cast<size_t>(feat_.params().sample_rate);
  const size_t seg_samples =
      static_cast<size_t>(std::max(1.0, config_.segment_sec) * static_cast<double>(sr));

  // 离线输入可能不是 16kHz，用线性插值重采样到模型要求。
  std::vector<float> mono;
  if (std::abs(sample_rate - static_cast<double>(sr)) < 1.0) {
    mono = samples;
  } else {
    const double ratio = static_cast<double>(sr) / sample_rate;
    const size_t out_n = static_cast<size_t>(static_cast<double>(samples.size()) * ratio);
    mono.resize(out_n);
    for (size_t i = 0; i < out_n; ++i) {
      const double src = static_cast<double>(i) / ratio;
      const size_t i0 = static_cast<size_t>(src);
      const size_t i1 = std::min(i0 + 1, samples.size() - 1);
      const double frac = src - static_cast<double>(i0);
      mono[i] = static_cast<float>(samples[i0] * (1.0 - frac) + samples[i1] * frac);
    }
  }

  size_t offset = 0;
  while (offset < mono.size()) {
    const size_t take = std::min(seg_samples, mono.size() - offset);
    std::vector<float> segment(mono.begin() + static_cast<long>(offset),
                               mono.begin() + static_cast<long>(offset + take));
    SegmentResult snapshot_before = last_;
    (void)snapshot_before;
    const std::int64_t idx_before = segment_index_;
    if (ConsumeSegment(&segment, false)) {
      results.push_back(last_);
    } else {
      // 不足一帧时跳过，但保持 segment_index 连续性由 ConsumeSegment 负责
      (void)idx_before;
    }
    SecureZero(segment.data(), segment.size() * sizeof(float));
    segment.clear();
    segment.shrink_to_fit();
    offset += take;
  }
  return results;
}

void Pipeline::ResetStats() {
  for (int c = 0; c < kClassCount; ++c) {
    stats_[static_cast<size_t>(c)] = ClassStat{};
    stats_[static_cast<size_t>(c)].threshold_sec = config_.thresholds[c];
    alerted_[c] = false;
  }
  history_.clear();
  last_ = SegmentResult{};
  total_audio_sec_ = 0.0;
  segment_total_ = 0;
  segment_index_ = 0;
  infer_ms_avg_ = 0.0;
  SecureZero(buffer_.data(), buffer_.size() * sizeof(float));
  buffer_.clear();
  buffer_sec_ = 0.0;
}

StateSnapshot Pipeline::Snapshot() const {
  StateSnapshot s;
  s.config = config_;
  s.classes = stats_;
  s.last = last_;
  s.history = history_;
  s.total_audio_sec = total_audio_sec_;
  s.infer_ms_avg = infer_ms_avg_;
  s.segment_total = segment_total_;
  for (int c = 0; c < kClassCount; ++c) {
    s.classes[static_cast<size_t>(c)].threshold_sec = config_.thresholds[c];
  }
  return s;
}

}  // namespace dn
