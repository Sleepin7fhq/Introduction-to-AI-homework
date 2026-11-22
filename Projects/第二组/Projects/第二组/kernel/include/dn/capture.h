// ============================================================================
//  dn/capture.h —— 麦克风采集（miniaudio）
//
//  采集线程只负责把 PCM 帧搬运到环形队列；真正的推理在流水线线程做，
//  避免在音频回调里做重活导致爆音。
// ============================================================================
#pragma once

#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace dn {

class MicrophoneCapture {
 public:
  // sink 收到的样本是 float、单声道、16kHz、范围 [-1,1]
  using Sink = std::function<void(const float* samples, size_t count)>;

  MicrophoneCapture();
  ~MicrophoneCapture();

  bool Start(Sink sink, std::string* error);
  void Stop();
  bool running() const { return running_.load(); }
  const std::string& device_name() const { return device_name_; }
  int sample_rate() const { return sample_rate_; }

  struct Impl;  // 实现体在 capture.cpp；公开以便 C 风格音频回调访问

 private:
  std::unique_ptr<Impl> impl_;
  std::atomic<bool> running_{false};
  std::string device_name_;
  int sample_rate_ = 16000;
};

}  // namespace dn
