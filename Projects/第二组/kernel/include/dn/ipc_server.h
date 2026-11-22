// ============================================================================
//  dn/ipc_server.h —— 内核 IPC 服务端（本地 socket，JSON-lines 协议）
//
//  ★ 协议内容约束：只会下发「类别 / 置信度 / 各类累计时长 / 告警 / 配置」等
//    结构化结果，绝不下发任何原始音频数据。
//
//  协议：每行一个 JSON 对象，以 '\n' 结尾。
//    客户端 → 内核：
//      {"cmd":"status"}
//      {"cmd":"set_config","segment_sec":5.0,"thresholds":[30,60,45,9999],"min_confidence":0.05}
//      {"cmd":"start_capture"} / {"cmd":"stop_capture"} / {"cmd":"reset"}
//      {"cmd":"offline_file","path":"C:/x/demo.wav"}
//      {"cmd":"quit"}
//    内核 → 客户端：
//      {"type":"state", ...}
//      {"type":"alert", ...}
//      {"type":"offline_result", ...}
//      {"type":"ok","cmd":"..."} / {"type":"error","message":"..."}
// ============================================================================
#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace dn {

// 套接字句柄。用 intptr_t 表示，避免在头文件里引入 winsock2.h
// （那会和 <thread>/<mutex> 拉进来的 windows.h 冲突）。
using SocketHandle = std::intptr_t;

class IpcServer {
 public:
  // 事件回调（在服务端线程里被调用）
  using StateProvider = std::function<std::string()>;   // 返回 state JSON 字符串
  using AlertHandler = std::function<void(const std::string& json)>;
  using CommandHandler = std::function<std::string(const std::string& cmd_json)>;

  IpcServer();
  ~IpcServer();

  // 启动监听。port=0 表示自动分配端口（实际端口通过 port() 查询）。
  bool Start(int port, std::string* error);
  void Stop();

  int port() const { return port_.load(); }
  bool running() const { return running_.load(); }
  std::size_t client_count() const { return clients_.load(); }

  void SetStateProvider(StateProvider p) { state_provider_ = std::move(p); }
  void SetAlertHandler(AlertHandler h) { alert_handler_ = std::move(h); }
  // 命令处理器返回空字符串表示"由内置逻辑处理"，否则视为最终响应 JSON。
  void SetCommandHandler(CommandHandler h) { command_handler_ = std::move(h); }

  // 主动向所有客户端推送一条 JSON 消息（内部自动补 '\n'）。
  void Broadcast(const std::string& json);

 private:
  void AcceptLoop();
  void ClientLoop(SocketHandle fd);
  void PushStateTo(SocketHandle fd);

  SocketHandle listen_fd_ = static_cast<SocketHandle>(-1);
  std::atomic<int> port_{0};
  std::atomic<bool> running_{false};
  std::atomic<std::size_t> clients_{0};
  std::thread accept_thread_;

  StateProvider state_provider_;
  AlertHandler alert_handler_;
  CommandHandler command_handler_;

  std::mutex clients_mtx_;
  std::vector<SocketHandle> client_fds_;
};

}  // namespace dn
