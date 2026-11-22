// ============================================================================
//  dn/capture.cpp —— miniaudio 麦克风采集实现
//
//  ★ 隐私说明：这里只把 PCM 帧在内存里搬运，不写文件、不做录音。
//    采集到的样本交给 Pipeline 后由 Pipeline 立即擦除。
// ============================================================================
#include "dn/capture.h"

#include <cstring>
#include <deque>
#include <mutex>
#include <thread>

#define MA_IMPLEMENTATION
#include "miniaudio.h"

#include "dn/util.h"

namespace dn {

struct MicrophoneCapture::Impl {
  ma_device device{};
  ma_context context{};
  bool context_ready = false;
  bool device_ready = false;

  std::mutex mtx;
  std::deque<float> ring;          // 待处理的 PCM 队列
  std::thread worker;              // 把队列数据搬到 sink
  std::atomic<bool> worker_run{false};
  Sink sink;
};

namespace {

constexpr size_t kRingMaxSamples = 16000 * 30;  // 最多缓存 30 秒，防止 UI 卡住导致无限增长

void DataCallback(ma_device* device, void* /*pOutput*/, const void* pInput,
                  ma_uint32 frameCount) {
  auto* impl = static_cast<MicrophoneCapture::Impl*>(device->pUserData);
  if (impl == nullptr || pInput == nullptr) return;

  const float* input = static_cast<const float*>(pInput);
  {
    std::lock_guard<std::mutex> lock(impl->mtx);
    if (impl->ring.size() + frameCount > kRingMaxSamples) {
      // 丢弃最旧的样本，保证实时性（内存不会无限增长）
      size_t overflow = impl->ring.size() + frameCount - kRingMaxSamples;
      if (overflow >= impl->ring.size()) {
        impl->ring.clear();
      } else {
        impl->ring.erase(impl->ring.begin(), impl->ring.begin() + static_cast<long>(overflow));
      }
    }
    impl->ring.insert(impl->ring.end(), input, input + frameCount);
  }
}

}  // namespace

MicrophoneCapture::MicrophoneCapture() : impl_(new Impl) {}

MicrophoneCapture::~MicrophoneCapture() { Stop(); }

bool MicrophoneCapture::Start(Sink sink, std::string* error) {
  if (running_.load()) return true;

  impl_->sink = std::move(sink);
  impl_->worker_run.store(true);

  // 初始化后端：传 NULL 让 miniaudio 使用默认优先级列表
  // (Windows: WASAPI > DirectSound > WinMM；Linux: ALSA > PulseAudio > JACK ...)
  ma_context_config ctx_config = ma_context_config_init();
  ma_result r = ma_context_init(nullptr, 0, &ctx_config, &impl_->context);
  if (r != MA_SUCCESS) {
    if (error) *error = std::string("音频后端初始化失败: ") + ma_result_description(r);
    impl_->worker_run.store(false);
    return false;
  }
  impl_->context_ready = true;

  ma_device_config config = ma_device_config_init(ma_device_type_capture);
  config.capture.format = ma_format_f32;
  config.capture.channels = 1;
  config.sampleRate = static_cast<ma_uint32>(sample_rate_);
  config.periodSizeInFrames = 1024;
  config.periods = 3;
  config.dataCallback = DataCallback;
  config.pUserData = impl_.get();

  r = ma_device_init(&impl_->context, &config, &impl_->device);
  if (r != MA_SUCCESS) {
    if (error) *error = std::string("麦克风初始化失败: ") + ma_result_description(r);
    ma_context_uninit(&impl_->context);
    impl_->context_ready = false;
    impl_->worker_run.store(false);
    return false;
  }
  impl_->device_ready = true;

  ma_device_info info{};
  if (ma_device_get_info(&impl_->device, ma_device_type_capture, &info) == MA_SUCCESS) {
    // miniaudio 返回的是 UTF-8 设备名；这里统一再确认一次，避免把本地代码页字节当成 UTF-8。
    device_name_ = dn::EnsureUtf8(info.name);
  } else {
    device_name_ = "默认麦克风";
  }

  r = ma_device_start(&impl_->device);
  if (r != MA_SUCCESS) {
    if (error) *error = std::string("麦克风启动失败: ") + ma_result_description(r);
    ma_device_uninit(&impl_->device);
    ma_context_uninit(&impl_->context);
    impl_->device_ready = false;
    impl_->context_ready = false;
    impl_->worker_run.store(false);
    return false;
  }

  // 工作线程：把队列里的样本批量交给 sink（推理在 sink 里做）
  impl_->worker = std::thread([this]() {
    std::vector<float> batch;
    batch.reserve(4096);
    while (impl_->worker_run.load()) {
      {
        std::lock_guard<std::mutex> lock(impl_->mtx);
        if (impl_->ring.empty()) {
          batch.clear();
        } else {
          size_t take = std::min<size_t>(impl_->ring.size(), 4096);
          batch.assign(impl_->ring.begin(), impl_->ring.begin() + static_cast<long>(take));
          impl_->ring.erase(impl_->ring.begin(), impl_->ring.begin() + static_cast<long>(take));
        }
      }
      if (!batch.empty() && impl_->sink) {
        impl_->sink(batch.data(), batch.size());
      } else {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      }
    }
  });

  running_.store(true);
  return true;
}

void MicrophoneCapture::Stop() {
  if (impl_->worker_run.exchange(false)) {
    if (impl_->worker.joinable()) impl_->worker.join();
  }
  if (impl_->device_ready) {
    ma_device_stop(&impl_->device);
    ma_device_uninit(&impl_->device);
    impl_->device_ready = false;
  }
  if (impl_->context_ready) {
    ma_context_uninit(&impl_->context);
    impl_->context_ready = false;
  }
  {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    impl_->ring.clear();
  }
  running_.store(false);
}

}  // namespace dn
