// ============================================================================
//  dn/ipc_server.cpp —— 本地 socket IPC 服务端实现（Windows Winsock + POSIX 兼容）
//
//  ★ 安全边界：只监听 127.0.0.1，不对外暴露；协议里只有结构化统计结果。
// ============================================================================
#include "dn/ipc_server.h"

#include <algorithm>
#include <cstring>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#define DN_INVALID_SOCKET INVALID_SOCKET
#define DN_CLOSE_SOCKET closesocket
#define DN_SOCKET_ERROR SOCKET_ERROR
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <unistd.h>
#define DN_INVALID_SOCKET (-1)
#define DN_CLOSE_SOCKET ::close
#define DN_SOCKET_ERROR (-1)
#endif

namespace dn {
namespace {

#ifdef _WIN32
inline SocketHandle ToHandle(SOCKET s) { return static_cast<SocketHandle>(s); }
inline SOCKET ToSocket(SocketHandle h) { return static_cast<SOCKET>(h); }
#else
inline SocketHandle ToHandle(int s) { return static_cast<SocketHandle>(s); }
inline int ToSocket(SocketHandle h) { return static_cast<int>(h); }
#endif

constexpr char kHost[] = "127.0.0.1";

// 发送全部字节（Windows 的 send 不保证一次发完）
bool SendAll(SocketHandle h, const char* data, size_t len) {
  size_t sent = 0;
  while (sent < len) {
    const int n = ::send(ToSocket(h), data + sent, static_cast<int>(len - sent), 0);
    if (n <= 0) return false;
    sent += static_cast<size_t>(n);
  }
  return true;
}
}  // namespace

IpcServer::IpcServer() = default;

IpcServer::~IpcServer() { Stop(); }

bool IpcServer::Start(int port, std::string* error) {
#ifdef _WIN32
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
    if (error) *error = "Winsock 初始化失败";
    return false;
  }
#endif
  listen_fd_ = ToHandle(::socket(AF_INET, SOCK_STREAM, 0));
  if (listen_fd_ == ToHandle(DN_INVALID_SOCKET)) {
    if (error) *error = "创建 socket 失败";
    return false;
  }

  int reuse = 1;
  ::setsockopt(ToSocket(listen_fd_), SOL_SOCKET, SO_REUSEADDR,
               reinterpret_cast<const char*>(&reuse), sizeof(reuse));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(static_cast<unsigned short>(port));
  addr.sin_addr.s_addr = inet_addr(kHost);

  if (::bind(ToSocket(listen_fd_), reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) ==
      DN_SOCKET_ERROR) {
    if (error) *error = "端口绑定失败（可能已被占用）";
    DN_CLOSE_SOCKET(ToSocket(listen_fd_));
    listen_fd_ = ToHandle(DN_INVALID_SOCKET);
    return false;
  }
  if (::listen(ToSocket(listen_fd_), 8) == DN_SOCKET_ERROR) {
    if (error) *error = "listen 失败";
    DN_CLOSE_SOCKET(ToSocket(listen_fd_));
    listen_fd_ = ToHandle(DN_INVALID_SOCKET);
    return false;
  }

  sockaddr_in bound{};
  socklen_t len = sizeof(bound);
  ::getsockname(ToSocket(listen_fd_), reinterpret_cast<sockaddr*>(&bound), &len);
  port_.store(ntohs(bound.sin_port));

  running_.store(true);
  accept_thread_ = std::thread([this]() { AcceptLoop(); });
  return true;
}

void IpcServer::Stop() {
  if (!running_.exchange(false)) return;
  if (listen_fd_ != ToHandle(DN_INVALID_SOCKET)) {
    DN_CLOSE_SOCKET(ToSocket(listen_fd_));
    listen_fd_ = ToHandle(DN_INVALID_SOCKET);
  }
  if (accept_thread_.joinable()) accept_thread_.join();

  std::lock_guard<std::mutex> lock(clients_mtx_);
  for (SocketHandle fd : client_fds_) DN_CLOSE_SOCKET(ToSocket(fd));
  client_fds_.clear();
}

void IpcServer::AcceptLoop() {
  while (running_.load()) {
    sockaddr_in peer{};
    socklen_t len = sizeof(peer);
    SocketHandle fd = ToHandle(::accept(ToSocket(listen_fd_), reinterpret_cast<sockaddr*>(&peer), &len));
    if (fd == ToHandle(DN_INVALID_SOCKET)) {
      if (!running_.load()) break;
      continue;
    }
    {
      std::lock_guard<std::mutex> lock(clients_mtx_);
      client_fds_.push_back(fd);
    }
    clients_.fetch_add(1);
    std::thread([this, fd]() { ClientLoop(fd); }).detach();
  }
}

void IpcServer::PushStateTo(SocketHandle fd) {
  if (!state_provider_) return;
  const std::string payload = state_provider_();
  if (payload.empty()) return;
  const std::string line = payload + "\n";
  SendAll(fd, line.c_str(), line.size());
}

void IpcServer::ClientLoop(SocketHandle fd) {
  std::string buffer;
  char chunk[4096];

  while (running_.load()) {
    const int n = ::recv(ToSocket(fd), chunk, sizeof(chunk), 0);
    if (n <= 0) break;
    buffer.append(chunk, static_cast<size_t>(n));

    size_t pos;
    while ((pos = buffer.find('\n')) != std::string::npos) {
      std::string line = buffer.substr(0, pos);
      buffer.erase(0, pos + 1);
      if (line.empty()) continue;

      std::string response;
      if (command_handler_) response = command_handler_(line);
      if (!response.empty()) {
        const std::string out = response + "\n";
        SendAll(fd, out.c_str(), out.size());
      }
    }
  }

  {
    std::lock_guard<std::mutex> lock(clients_mtx_);
    client_fds_.erase(std::remove(client_fds_.begin(), client_fds_.end(), fd),
                      client_fds_.end());
  }
  DN_CLOSE_SOCKET(ToSocket(fd));
  clients_.fetch_sub(1);
}

void IpcServer::Broadcast(const std::string& json) {
  const std::string line = json + "\n";
  std::lock_guard<std::mutex> lock(clients_mtx_);
  for (SocketHandle fd : client_fds_) {
    SendAll(fd, line.c_str(), line.size());
  }
}

}  // namespace dn
