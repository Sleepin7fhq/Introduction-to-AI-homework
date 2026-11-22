// ============================================================================
//  dn/feature_extractor.cpp —— 梅尔频谱特征提取实现
//
//  与 transformers/torchaudio 的 kaldi fbank 逐位对齐（见头文件注释）。
//  实现要点：
//   1) 分帧：snip_edges=True，帧数 m = 1 + (n - 400) / 160（整除）
//   2) 每帧减均值（remove_dc_offset）
//   3) 预加重 0.97，首元素用 replicate 填充
//   4) 乘 hann(400, periodic=False)
//   5) 右侧补零到 512
//   6) 实数 FFT（radix-2, 512 点）→ 功率谱 257 bin
//   7) 梅尔滤波组（128 bin, fft_bin_width=31.25）→ log(max(x, eps))
//   8) 补零/截断到 1024 帧 → 归一化 (x-mean)/(std*2)
// ============================================================================
#include "dn/feature_extractor.h"

#include <algorithm>
#include <cmath>

namespace dn {
namespace {

constexpr double kPi = 3.14159265358979323846;

// 迭代式 radix-2 复数 FFT（就地运算，位反转重排）。
// n 必须是 2 的幂；本工程固定 n=512。
void Radix2FFT(std::vector<double>* re, std::vector<double>* im) {
  const int n = static_cast<int>(re->size());
  // 位反转置换
  for (int i = 1, j = 0; i < n; ++i) {
    int bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      std::swap((*re)[i], (*re)[j]);
      std::swap((*im)[i], (*im)[j]);
    }
  }
  for (int len = 2; len <= n; len <<= 1) {
    const double ang = -2.0 * kPi / static_cast<double>(len);
    const double w_re = std::cos(ang);
    const double w_im = std::sin(ang);
    for (int i = 0; i < n; i += len) {
      double cur_re = 1.0, cur_im = 0.0;
      const int half = len >> 1;
      for (int k = 0; k < half; ++k) {
        const double u_re = (*re)[i + k];
        const double u_im = (*im)[i + k];
        const double v_re = (*re)[i + k + half] * cur_re - (*im)[i + k + half] * cur_im;
        const double v_im = (*re)[i + k + half] * cur_im + (*im)[i + k + half] * cur_re;
        (*re)[i + k] = u_re + v_re;
        (*im)[i + k] = u_im + v_im;
        (*re)[i + k + half] = u_re - v_re;
        (*im)[i + k + half] = u_im - v_im;
        const double next_re = cur_re * w_re - cur_im * w_im;
        cur_im = cur_re * w_im + cur_im * w_re;
        cur_re = next_re;
      }
    }
  }
}

inline double MelScale(double freq) { return 1127.0 * std::log(1.0 + freq / 700.0); }

}  // namespace

FeatureExtractor::FeatureExtractor() {
  Configure(params_);
}

void FeatureExtractor::Configure(const FeatureParams& params) {
  params_ = params;
  // kaldi: padded = next_pow2(window_size)，rfft(padded) → padded/2+1 个 bin
  int padded = 1;
  while (padded < params_.window_size) padded <<= 1;
  params_.padded_window_size = padded;
  params_.num_fft_bins = padded / 2 + 1;
  BuildWindow();
  BuildMelBank();
}

void FeatureExtractor::BuildWindow() {
  // torch.hann_window(N, periodic=False) = 0.5 - 0.5*cos(2*pi*n/(N-1))
  window_.assign(static_cast<size_t>(params_.window_size), 0.f);
  const int n = params_.window_size;
  for (int i = 0; i < n; ++i) {
    const double c = std::cos(2.0 * kPi * i / static_cast<double>(n - 1));
    window_[static_cast<size_t>(i)] = static_cast<float>(0.5 - 0.5 * c);
  }
}

void FeatureExtractor::BuildMelBank() {
  // 完全对应 torchaudio compliance/kaldi.py 的 get_mel_banks()
  const int num_bins = params_.num_mel_bins;
  const int padded = params_.padded_window_size;
  const int num_fft_bins = padded / 2;  // 256，矩阵右侧另外补一列 0 -> 257

  const double sr = static_cast<double>(params_.sample_rate);
  const double nyquist = 0.5 * sr;
  double high_freq = params_.high_freq;
  if (high_freq <= 0.0) high_freq += nyquist;
  const double low_freq = params_.low_freq;

  const double fft_bin_width = sr / static_cast<double>(padded);  // 31.25
  const double mel_low = MelScale(low_freq);
  const double mel_high = MelScale(high_freq);
  const double mel_freq_delta = (mel_high - mel_low) / (num_bins + 1);

  mel_bank_.assign(static_cast<size_t>(num_bins) * static_cast<size_t>(num_fft_bins), 0.f);
  for (int bin = 0; bin < num_bins; ++bin) {
    const double left_mel = mel_low + bin * mel_freq_delta;
    const double center_mel = mel_low + (bin + 1.0) * mel_freq_delta;
    const double right_mel = mel_low + (bin + 2.0) * mel_freq_delta;
    for (int k = 0; k < num_fft_bins; ++k) {
      const double mel = MelScale(fft_bin_width * static_cast<double>(k));
      const double up_slope = (mel - left_mel) / (center_mel - left_mel);
      const double down_slope = (right_mel - mel) / (right_mel - center_mel);
      double v = std::min(up_slope, down_slope);
      if (v < 0.0) v = 0.0;
      mel_bank_[static_cast<size_t>(bin) * num_fft_bins + k] = static_cast<float>(v);
    }
  }
  fft_re_.assign(static_cast<size_t>(padded), 0.0);
  fft_im_.assign(static_cast<size_t>(padded), 0.0);
}

int FeatureExtractor::FrameCount(int num_samples, int window_size, int window_shift) {
  if (num_samples < window_size) return 0;
  return 1 + (num_samples - window_size) / window_shift;
}

bool FeatureExtractor::Extract(const std::vector<float>& samples,
                               std::vector<float>* features) const {
  const int W = params_.window_size;
  const int H = params_.window_shift;
  const int P = params_.padded_window_size;
  const int num_bins = params_.num_mel_bins;
  const int max_len = params_.max_length;
  const int fft_bins = params_.num_fft_bins;   // 257
  const int mel_cols = P / 2;                 // 256（矩阵本体，不含补的 0 列）

  features->assign(static_cast<size_t>(max_len) * static_cast<size_t>(num_bins), 0.f);
  const int n = static_cast<int>(samples.size());
  const int num_frames = FrameCount(n, W, H);
  if (num_frames <= 0) return false;

  std::vector<double> re(static_cast<size_t>(P));
  std::vector<double> im(static_cast<size_t>(P));
  const int out_frames = std::min(num_frames, max_len);

  for (int f = 0; f < out_frames; ++f) {
    const float* frame = samples.data() + static_cast<size_t>(f) * H;

    // (1) remove_dc_offset：每帧减均值
    double mean = 0.0;
    for (int i = 0; i < W; ++i) mean += frame[i];
    mean /= static_cast<double>(W);

    // (2) preemphasis 0.97，首元素用 replicate(x0)
    double prev = frame[0] - mean;  // replicate 填充的 x[0]
    for (int i = 0; i < W; ++i) {
      const double x = static_cast<double>(frame[i]) - mean;
      const double y = x - params_.preemphasis * prev;
      prev = x;
      // (3) 加窗
      re[static_cast<size_t>(i)] = y * window_[static_cast<size_t>(i)];
      im[static_cast<size_t>(i)] = 0.0;
    }
    // (4) 右侧补零到 P
    for (int i = W; i < P; ++i) {
      re[static_cast<size_t>(i)] = 0.0;
      im[static_cast<size_t>(i)] = 0.0;
    }

    // (5) rfft -> 功率谱
    Radix2FFT(&re, &im);
    std::vector<double> power(static_cast<size_t>(fft_bins));
    for (int k = 0; k < fft_bins; ++k) {
      power[static_cast<size_t>(k)] =
          re[static_cast<size_t>(k)] * re[static_cast<size_t>(k)] +
          im[static_cast<size_t>(k)] * im[static_cast<size_t>(k)];
    }

    // (6) 梅尔滤波 + log
    float* dst = features->data() + static_cast<size_t>(f) * num_bins;
    for (int b = 0; b < num_bins; ++b) {
      const float* mel_row = mel_bank_.data() + static_cast<size_t>(b) * mel_cols;
      double acc = 0.0;
      for (int k = 0; k < mel_cols; ++k) acc += mel_row[k] * power[static_cast<size_t>(k)];
      if (acc < params_.mel_floor) acc = params_.mel_floor;
      dst[b] = static_cast<float>(std::log(acc));
    }
  }

  // (7) 归一化：(x - mean) / (std * 2)
  const float scale = params_.std * 2.f;
  for (int f = 0; f < out_frames; ++f) {
    float* dst = features->data() + static_cast<size_t>(f) * num_bins;
    for (int b = 0; b < num_bins; ++b) dst[b] = (dst[b] - params_.mean) / scale;
  }
  // 不足 max_len 的部分保持 0 —— 与 transformers 的 ZeroPad2d 行为一致。
  // 注意：transformers 是「先补零、再归一化」，因此补零帧在归一化后
  //       变成 (0-mean)/(std*2) 的常数；这里为保持数值一致，
  //       直接对整块（含补零帧）做归一化。
  if (out_frames < max_len) {
    const float pad_value = (0.f - params_.mean) / scale;
    for (int f = out_frames; f < max_len; ++f) {
      float* dst = features->data() + static_cast<size_t>(f) * num_bins;
      for (int b = 0; b < num_bins; ++b) dst[b] = pad_value;
    }
  }
  return true;
}

}  // namespace dn
