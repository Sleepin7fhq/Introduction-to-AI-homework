// ============================================================================
//  dn/wav_reader.h —— 轻量 WAV 读取（仅用于离线演示）
//
//  ★ 只读取用户主动指定的本地文件用于离线推理；内核不会把读到的内容写回磁盘。
//    支持：PCM 8/16/24/32-bit 整数、32/64-bit 浮点，单声道或多声道（自动混合为单声道）。
// ============================================================================
#pragma once

#include <string>
#include <vector>

namespace dn {

struct WavData {
  std::vector<float> samples;  // 单声道 float，[-1,1]
  int sample_rate = 0;
  int channels = 0;
  double duration_sec = 0.0;
};

// 失败时 error 里写入中文原因。
bool ReadWavMono(const std::string& path, WavData* out, std::string* error);

}  // namespace dn
