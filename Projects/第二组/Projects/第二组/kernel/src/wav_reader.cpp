// ============================================================================
//  dn/wav_reader.cpp —— 轻量 WAV 解析实现
// ============================================================================
#include "dn/wav_reader.h"

#include "dn/util.h"

#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(_WIN32)
#include <windows.h>
#endif

namespace dn {
namespace {

uint32_t RdU32(const unsigned char* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
uint16_t RdU16(const unsigned char* p) {
  return static_cast<uint16_t>(static_cast<uint16_t>(p[0]) | (static_cast<uint16_t>(p[1]) << 8));
}

}  // namespace

bool ReadWavMono(const std::string& path, WavData* out, std::string* error) {
  // Windows 上路径可能是 UTF-8（来自 UI 的 JSON），也可能是本地 ANSI(GBK)
  // （来自命令行参数）；统一用 dn::ToWideFlexiblePath 解析成宽字符再开文件。
#if defined(_WIN32)
  std::FILE* f = nullptr;
  const std::wstring wpath = dn::ToWideFlexiblePath(path);
  if (!wpath.empty()) {
    _wfopen_s(&f, wpath.c_str(), L"rb");
  }
#else
  std::FILE* f = std::fopen(path.c_str(), "rb");
#endif
  if (f == nullptr) {
    if (error) *error = "无法打开文件: " + path;
    return false;
  }
  unsigned char header[12];
  if (std::fread(header, 1, 12, f) != 12 || std::memcmp(header, "RIFF", 4) != 0 ||
      std::memcmp(header + 8, "WAVE", 4) != 0) {
    std::fclose(f);
    if (error) *error = "不是合法的 RIFF/WAVE 文件";
    return false;
  }

  uint16_t audio_format = 0;
  uint16_t channels = 0;
  uint32_t sample_rate = 0;
  uint16_t bits = 0;
  bool have_fmt = false;
  std::vector<unsigned char> data;

  while (true) {
    unsigned char chunk[8];
    if (std::fread(chunk, 1, 8, f) != 8) break;
    const uint32_t size = RdU32(chunk + 4);
    const bool is_fmt = std::memcmp(chunk, "fmt ", 4) == 0;
    const bool is_data = std::memcmp(chunk, "data", 4) == 0;

    if (is_fmt) {
      std::vector<unsigned char> fmt(size);
      if (size < 16 || std::fread(fmt.data(), 1, size, f) != size) {
        std::fclose(f);
        if (error) *error = "fmt 块损坏";
        return false;
      }
      audio_format = RdU16(fmt.data());
      channels = RdU16(fmt.data() + 2);
      sample_rate = RdU32(fmt.data() + 4);
      bits = RdU16(fmt.data() + 14);
      have_fmt = true;
      if (size % 2 == 1) std::fseek(f, 1, SEEK_CUR);
    } else if (is_data) {
      data.resize(size);
      const size_t got = std::fread(data.data(), 1, size, f);
      data.resize(got);
      break;
    } else {
      std::fseek(f, static_cast<long>(size + (size % 2)), SEEK_CUR);
    }
  }
  std::fclose(f);

  if (!have_fmt) {
    if (error) *error = "WAV 缺少 fmt 块";
    return false;
  }
  if (data.empty()) {
    if (error) *error = "WAV 没有音频数据";
    return false;
  }
  if (channels == 0) {
    if (error) *error = "WAV 声道数为 0";
    return false;
  }

  const size_t bytes_per_sample = bits / 8;
  if (bytes_per_sample == 0) {
    if (error) *error = "WAV 位深非法";
    return false;
  }
  const size_t frame_bytes = bytes_per_sample * channels;
  const size_t frames = data.size() / frame_bytes;

  out->sample_rate = static_cast<int>(sample_rate);
  out->channels = channels;
  out->samples.resize(frames);
  out->duration_sec = frames > 0 ? static_cast<double>(frames) / sample_rate : 0.0;

  for (size_t i = 0; i < frames; ++i) {
    double acc = 0.0;
    for (size_t c = 0; c < channels; ++c) {
      const unsigned char* p = data.data() + i * frame_bytes + c * bytes_per_sample;
      double v = 0.0;
      if (audio_format == 3) {  // IEEE float
        if (bits == 32) {
          float fv;
          std::memcpy(&fv, p, 4);
          v = fv;
        } else if (bits == 64) {
          double dv;
          std::memcpy(&dv, p, 8);
          v = dv;
        }
      } else {  // PCM integer
        switch (bits) {
          case 8:
            v = (static_cast<int>(p[0]) - 128) / 128.0;
            break;
          case 16: {
            int16_t iv;
            std::memcpy(&iv, p, 2);
            v = iv / 32768.0;
            break;
          }
          case 24: {
            int32_t iv = (static_cast<int32_t>(p[0]) << 8) |
                         (static_cast<int32_t>(p[1]) << 16) |
                         (static_cast<int32_t>(p[2]) << 24);
            v = static_cast<double>(iv) / 2147483648.0;
            break;
          }
          case 32: {
            int32_t iv;
            std::memcpy(&iv, p, 4);
            v = static_cast<double>(iv) / 2147483648.0;
            break;
          }
          default:
            v = 0.0;
        }
      }
      acc += v;
    }
    out->samples[i] = static_cast<float>(acc / static_cast<double>(channels));
  }
  return true;
}

}  // namespace dn
