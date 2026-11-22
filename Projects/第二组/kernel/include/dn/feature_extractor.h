// ============================================================================
//  dn/feature_extractor.h —— 梅尔频谱（fbank）特征提取
//
//  ★ 数值规格必须与 HuggingFace AST 完全一致，否则模型输出会失真。
//    对照实现：
//      transformers/models/audio_spectrogram_transformer/
//          feature_extraction_audio_spectrogram_transformer.py
//      torchaudio/compliance/kaldi.py
//
//    关键参数（已逐行核对源码）：
//      sample_rate      = 16000
//      window_size      = 400  (25 ms)      frame_length=25.0ms
//      window_shift     = 160  (10 ms)      frame_shift=10.0ms
//      padded_window    = 512  (next_pow2)  ← kaldi 默认 round_to_power_of_two=True
//      fft bins         = 257  (rfft(512))
//      mel bins         = 128
//      low_freq=20, high_freq=0(=nyquist 8000)
//      preemphasis      = 0.97
//      remove_dc_offset = True
//      dither           = 0.0
//      use_power=True, use_log_fbank=True, subtract_mean=False
//      窗函数: hann(400, periodic=False) = 0.5-0.5*cos(2*pi*n/399)
//      log 地板: 1.192092955078125e-07 (float32 eps)
//    处理顺序：分帧 → 去直流 → 预加重 → 加窗 → 右侧补零到 512 → rfft →
//              功率谱 → 梅尔滤波 → log → 补/截断到 1024 帧 → 归一化
//    归一化：(x - mean) / (std * 2)
//    输入波形是 [-1,1] 浮点（AST 侧那行 *2**15 被注释掉了，不要缩放！）
// ============================================================================
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace dn {

struct FeatureParams {
  int sample_rate = 16000;
  int window_size = 400;        // 25 ms
  int window_shift = 160;       // 10 ms
  int padded_window_size = 512; // next_pow2(400)
  int num_mel_bins = 128;
  int max_length = 1024;        // 模型要求的帧数
  int num_fft_bins = 257;       // rfft(512) 的输出个数
  float mean = -4.2677393f;
  float std = 4.5689974f;
  float preemphasis = 0.97f;
  float low_freq = 20.f;
  float high_freq = 0.f;  // <=0 表示取 nyquist
  float mel_floor = 1.192092955078125e-07f;
};

class FeatureExtractor {
 public:
  FeatureExtractor();

  // 设置参数并重建窗函数 / 梅尔滤波器组。
  void Configure(const FeatureParams& params);

  const FeatureParams& params() const { return params_; }

  // 输入：单声道 float 波形 [-1,1]，采样率必须等于 params_.sample_rate
  // 输出：params_.max_length * params_.num_mel_bins 个 float，行主序 [frame][mel]
  //       已完成 log、补零/截断与归一化，可以直接喂给 AST。
  // 返回 false 表示样本数不足一帧（< window_size），此时输出被清零。
  bool Extract(const std::vector<float>& samples, std::vector<float>* features) const;

  // 理论帧数（kaldi snip_edges 规则）：1 + (n - window_size) / window_shift
  static int FrameCount(int num_samples, int window_size, int window_shift);

 private:
  void BuildWindow();
  void BuildMelBank();

  FeatureParams params_;
  std::vector<float> window_;       // window_size 长度的 hann 窗
  std::vector<float> mel_bank_;     // num_mel_bins * num_fft_bins(256) 梅尔权重
  std::vector<double> fft_re_, fft_im_;  // FFT 工作区
};

}  // namespace dn
