// ============================================================================
//  dn/util.h —— 字符串 / 路径编码工具（header-only）
//
//  为什么需要它：
//    Windows 中文系统上，命令行参数由控制台按系统 ANSI 代码页(GBK) 传入，
//    而 JSON 是 UTF-8 协议。若把 GBK 字节直接塞进 JSON，UI 侧解析会得到乱码。
//    这里统一把"本地代码页字节"转换成 UTF-8。
//
//  隐私说明：本文件只做字符编码转换，不涉及任何音频数据。
// ============================================================================
#ifndef DN_UTIL_H_
#define DN_UTIL_H_

#include <string>

#if defined(_WIN32)
#include <windows.h>
#endif

namespace dn {

// 把本地代码页(ANSI/GBK)的字符串转换为 UTF-8。
// 若输入本身已是合法 UTF-8，则原样返回。
inline std::string LocalToUtf8(const std::string& s) {
#if defined(_WIN32)
  if (s.empty()) return s;
  // 1) 先按系统 ANSI 代码页解成宽字符
  int n = ::MultiByteToWideChar(CP_ACP, 0, s.c_str(), static_cast<int>(s.size()),
                                nullptr, 0);
  if (n <= 0) return s;
  std::wstring wide(static_cast<size_t>(n), L'\0');
  ::MultiByteToWideChar(CP_ACP, 0, s.c_str(), static_cast<int>(s.size()), &wide[0], n);
  // 2) 再转成 UTF-8
  int m = ::WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), n, nullptr, 0, nullptr, nullptr);
  if (m <= 0) return s;
  std::string out(static_cast<size_t>(m), '\0');
  ::WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), n, &out[0], m, nullptr, nullptr);
  return out;
#else
  return s;
#endif
}

// 把 UTF-8 字符串转换回本地代码页(ANSI/GBK)，用于交给 Win32 文件 API。
inline std::string Utf8ToLocal(const std::string& s) {
#if defined(_WIN32)
  if (s.empty()) return s;
  int n = ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()),
                                nullptr, 0);
  if (n <= 0) return s;
  std::wstring wide(static_cast<size_t>(n), L'\0');
  ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), &wide[0], n);
  int m = ::WideCharToMultiByte(CP_ACP, 0, wide.c_str(), n, nullptr, 0, nullptr, nullptr);
  if (m <= 0) return s;
  std::string out(static_cast<size_t>(m), '\0');
  ::WideCharToMultiByte(CP_ACP, 0, wide.c_str(), n, &out[0], m, nullptr, nullptr);
  return out;
#else
  return s;
#endif
}

// 判断字符串是否已经是合法 UTF-8（严格解码）。
inline bool IsValidUtf8(const std::string& s) {
#if defined(_WIN32)
  if (s.empty()) return true;
  int n = ::MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.c_str(),
                                static_cast<int>(s.size()), nullptr, 0);
  return n > 0;
#else
  // POSIX：这里默认系统就是 UTF-8，交给上层按需处理。
  return true;
#endif
}

// 保证输出是 UTF-8：
//   - 输入已经是合法 UTF-8（比如 miniaudio 返回的设备名）→ 原样返回
//   - 输入是本地代码页(GBK) → 先 ACP 解码再转 UTF-8
inline std::string EnsureUtf8(const std::string& s) {
  if (IsValidUtf8(s)) return s;
  return LocalToUtf8(s);
}

// 去掉 Windows 路径里的引号，方便命令行粘贴。
inline std::string StripQuotes(const std::string& s) {
  if (s.size() >= 2 && ((s.front() == '"' && s.back() == '"') ||
                         (s.front() == '\'' && s.back() == '\''))) {
    return s.substr(1, s.size() - 2);
  }
  return s;
}

// 让 Windows 控制台按 UTF-8 输出，避免中文日志在 GBK 代码页控制台里显示成乱码。
// （源文件里的中文字面量本身就是 UTF-8 字节；只要控制台代码页是 UTF-8 就能正确显示。）
inline void SetConsoleUtf8() {
#if defined(_WIN32)
  ::SetConsoleOutputCP(CP_UTF8);
  ::SetConsoleCP(CP_UTF8);
#endif
}

#if defined(_WIN32)

// 文件是否存在（宽字符路径）。
inline bool WideFileExists(const std::wstring& w) {
  if (w.empty()) return false;
  DWORD attr = ::GetFileAttributesW(w.c_str());
  return attr != INVALID_FILE_ATTRIBUTES;
}

// 把"可能是 UTF-8、也可能是本地 ANSI(GBK)"的路径字符串转成宽字符，
// 并在两种解释里挑一个真实存在的文件。
//   - UTF-8 严格解码失败 → 一定是本地代码页
//   - 两者都解码成功 → 用文件是否存在来判定
inline std::wstring ToWideFlexiblePath(const std::string& s) {
  if (s.empty()) return std::wstring();
  auto decode = [&s](UINT cp, DWORD flags) -> std::wstring {
    int n = ::MultiByteToWideChar(cp, flags, s.c_str(), static_cast<int>(s.size()),
                                  nullptr, 0);
    if (n <= 0) return std::wstring();
    std::wstring out(static_cast<size_t>(n), L'\0');
    ::MultiByteToWideChar(cp, flags, s.c_str(), static_cast<int>(s.size()), &out[0], n);
    return out;
  };
  std::wstring utf8 = decode(CP_UTF8, MB_ERR_INVALID_CHARS);
  std::wstring acp = decode(CP_ACP, 0);
  if (!utf8.empty() && WideFileExists(utf8)) return utf8;
  if (!acp.empty() && WideFileExists(acp)) return acp;
  return utf8.empty() ? acp : utf8;
}

#endif  // _WIN32

}  // namespace dn

#endif  // DN_UTIL_H_
