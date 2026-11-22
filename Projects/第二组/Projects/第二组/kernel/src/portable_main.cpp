// ============================================================================
//  portable_main.cpp —— 便携版启动器（自解压）
//
//  目标：产出一个「双击即用」的独立 exe，不依赖外部 onnxruntime.dll 与模型文件。
//
//  原理：
//    内核二进制 (dorm_noise_kernel.exe)、onnxruntime.dll、
//    onnxruntime_providers_shared.dll、AST int8 模型 (ast_audioset_int8.onnx)
//    全部以二进制资源的形式链接进本 exe。启动时：
//      1) 把这些资源释放到 %LOCALAPPDATA%\DormNoise\runtime\（首次释放，之后复用）；
//      2) 以继承式句柄启动真正的内核进程，并把参数原样透传；
//      3) 内核从同目录加载 DLL 与模型，因此完全离线、无外部依赖。
//
//  ★ 为什么用「外层自解压 + 内层内核」而不是把 DLL 直接链接进同一个 exe：
//     onnxruntime.dll 是通过导入库 (onnxruntime.lib) 静态依赖的，Windows 在
//     进程创建时就要解析导入表 —— 那时 DLL 还没被释放到磁盘，必然加载失败。
//     解压出真实内核 + 真实 DLL 后再启动，导入表就能正常解析。
//
//  ★ 隐私：释放到磁盘的只有「模型 + 运行时 DLL + 内核 exe」，**没有任何音频**。
// ============================================================================
#include <windows.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <cwctype>
#include <string>
#include <vector>

namespace {

// ---------------------------------------------------------------------------
//  内嵌二进制资源符号（由 ld -b binary 生成，名字与链接时的文件名一一对应）
// ---------------------------------------------------------------------------
extern "C" {
extern const unsigned char _binary_dorm_noise_kernel_exe_start[];
extern const unsigned char _binary_dorm_noise_kernel_exe_end[];
extern const unsigned char _binary_onnxruntime_dll_start[];
extern const unsigned char _binary_onnxruntime_dll_end[];
extern const unsigned char _binary_onnxruntime_providers_shared_dll_start[];
extern const unsigned char _binary_onnxruntime_providers_shared_dll_end[];
extern const unsigned char _binary_ast_audioset_int8_onnx_start[];
extern const unsigned char _binary_ast_audioset_int8_onnx_end[];
}

struct Asset {
  const char* name;        // 释放后的文件名
  const unsigned char* begin;
  const unsigned char* end;
};

const Asset kAssets[] = {
    {"dorm_noise_kernel.exe", _binary_dorm_noise_kernel_exe_start,
     _binary_dorm_noise_kernel_exe_end},
    {"onnxruntime.dll", _binary_onnxruntime_dll_start, _binary_onnxruntime_dll_end},
    {"onnxruntime_providers_shared.dll", _binary_onnxruntime_providers_shared_dll_start,
     _binary_onnxruntime_providers_shared_dll_end},
    {"ast_audioset_int8.onnx", _binary_ast_audioset_int8_onnx_start,
     _binary_ast_audioset_int8_onnx_end},
};

// ---------------------------------------------------------------------------
//  工具函数
// ---------------------------------------------------------------------------

std::wstring Utf8ToWide(const std::string& s) {
  if (s.empty()) return std::wstring();
  int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), nullptr, 0);
  std::wstring w(static_cast<size_t>(n), L'\0');
  MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), &w[0], n);
  return w;
}

std::string WideToUtf8(const std::wstring& w) {
  if (w.empty()) return std::string();
  int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), nullptr, 0,
                              nullptr, nullptr);
  std::string s(static_cast<size_t>(n), '\0');
  WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), &s[0], n, nullptr,
                      nullptr);
  return s;
}

// 递归创建目录
bool EnsureDirectory(const std::wstring& dir) {
  if (dir.empty()) return false;
  DWORD attr = GetFileAttributesW(dir.c_str());
  if (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY)) return true;
  size_t pos = dir.find_last_of(L'\\');
  if (pos != std::wstring::npos && pos > 0) {
    if (!EnsureDirectory(dir.substr(0, pos))) return false;
  }
  return CreateDirectoryW(dir.c_str(), nullptr) != 0 ||
         GetLastError() == ERROR_ALREADY_EXISTS;
}

// 原子写文件：先写 .tmp 再改名，避免半截文件被当成有效资源
bool WriteFileAtomic(const std::wstring& path, const unsigned char* data, size_t size) {
  std::wstring tmp = path + L".tmp";
  HANDLE h = CreateFileW(tmp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                         FILE_ATTRIBUTE_NORMAL, nullptr);
  if (h == INVALID_HANDLE_VALUE) return false;
  const size_t kChunk = 4u * 1024u * 1024u;
  size_t off = 0;
  bool ok = true;
  while (off < size) {
    DWORD want = static_cast<DWORD>(std::min<size_t>(kChunk, size - off));
    DWORD written = 0;
    if (!WriteFile(h, data + off, want, &written, nullptr) || written == 0) {
      ok = false;
      break;
    }
    off += written;
  }
  CloseHandle(h);
  if (!ok) {
    DeleteFileW(tmp.c_str());
    return false;
  }
  if (!MoveFileExW(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING)) {
    DeleteFileW(tmp.c_str());
    return false;
  }
  return true;
}

bool FileExistsWithSize(const std::wstring& path, size_t expect) {
  WIN32_FILE_ATTRIBUTE_DATA fd;
  if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &fd)) return false;
  return (static_cast<size_t>(fd.nFileSizeHigh) << 32 | fd.nFileSizeLow) == expect;
}

// 取 %LOCALAPPDATA%，失败则退回 %TEMP%
std::wstring BaseDataDir() {
  wchar_t buf[MAX_PATH] = {0};
  DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH);
  if (n > 0 && n < MAX_PATH) {
    std::wstring p(buf);
    while (!p.empty() && (p.back() == L'\\' || p.back() == L'/')) p.pop_back();
    return p;
  }
  n = GetEnvironmentVariableW(L"TEMP", buf, MAX_PATH);
  if (n > 0 && n < MAX_PATH) {
    std::wstring p(buf);
    while (!p.empty() && (p.back() == L'\\' || p.back() == L'/')) p.pop_back();
    return p;
  }
  return L".";
}

std::wstring ExeDir() {
  wchar_t buf[MAX_PATH] = {0};
  DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
  std::wstring p(buf, n);
  size_t pos = p.find_last_of(L'\\');
  return (pos == std::wstring::npos) ? std::wstring(L".") : p.substr(0, pos);
}

// 取命令行中 argv[0] 之后的全部参数（保留原始 UTF-16，中文路径不丢）
std::wstring CommandLineTail() {
  std::wstring cmd = GetCommandLineW();
  size_t i = 0;
  if (cmd.size() >= 2 && cmd[0] == L'"') {
    i = cmd.find(L'"', 1);
    if (i == std::wstring::npos) {
      i = cmd.size();
    } else {
      ++i;
    }
  } else {
    while (i < cmd.size() && cmd[i] != L' ') ++i;
  }
  while (i < cmd.size() && cmd[i] == L' ') ++i;
  return cmd.substr(i);
}

// 判断参数里是否已经显式给了 --model
bool HasModelFlag(const std::wstring& tail) {
  std::wstring lowered = tail;
  for (auto& c : lowered) c = static_cast<wchar_t>(::towlower(c));
  return lowered.find(L"--model") != std::wstring::npos;
}

// 是否含某个独立单词（避免 "--no-capture" 里误命中 "--capture"）
bool HasWord(const std::wstring& tail, const wchar_t* word) {
  std::wstring lowered = tail;
  for (auto& c : lowered) c = static_cast<wchar_t>(::towlower(c));
  std::wstring needle = word;
  size_t pos = 0;
  while ((pos = lowered.find(needle, pos)) != std::wstring::npos) {
    bool left_ok = (pos == 0) || lowered[pos - 1] == L' ' || lowered[pos - 1] == L'"' ||
                    lowered[pos - 1] == L'\t';
    size_t end = pos + needle.size();
    bool right_ok = (end >= lowered.size()) || lowered[end] == L' ' || lowered[end] == L'"' ||
                     lowered[end] == L'\t';
    if (left_ok && right_ok) return true;
    pos = end;
  }
  return false;
}

bool HasFlag(const std::wstring& tail, const wchar_t* flag) {
  return HasWord(tail, flag);
}

// 依次尝试若干候选目录，返回第一个能成功创建并写入的。
// 某些受限环境（沙箱 / 组策略）可能不允许写 %LOCALAPPDATA%，
// 这时退回 exe 同目录，再退回 %TEMP%，保证「双击即用」总能成功。
std::wstring PickRuntimeDir() {
  std::vector<std::wstring> candidates;
  candidates.push_back(BaseDataDir() + L"\\DormNoise\\runtime");
  candidates.push_back(ExeDir() + L"\\DormNoiseRuntime");
  wchar_t tmp[MAX_PATH] = {0};
  DWORD n = GetEnvironmentVariableW(L"TEMP", tmp, MAX_PATH);
  if (n > 0 && n < MAX_PATH) {
    std::wstring p(tmp);
    while (!p.empty() && (p.back() == L'\\' || p.back() == L'/')) p.pop_back();
    candidates.push_back(p + L"\\DormNoiseRuntime");
  }
  for (const std::wstring& c : candidates) {
    if (!EnsureDirectory(c)) continue;
    // 目录建好还要能真正写文件，才算真正可用
    std::wstring probe = c + L"\\_write_test.tmp";
    HANDLE h = CreateFileW(probe.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h != INVALID_HANDLE_VALUE) {
      CloseHandle(h);
      DeleteFileW(probe.c_str());
      return c;
    }
  }
  return std::wstring();
}

void PrintPortableUsage() {
  std::printf(
      "宿舍噪音智能识别内核 · 便携版 (dorm_noise_standalone)\n"
      "\n"
      "本 exe 已内嵌 AST 音频分类模型与 ONNX Runtime 运行时，\n"
      "双击即可运行，无需任何外部文件、无需联网。\n"
      "\n"
      "用法:\n"
      "  dorm_noise_standalone.exe [选项]\n"
      "  dorm_noise_standalone.exe --offline <wav>        对本地 wav 做离线推理\n"
      "  dorm_noise_standalone.exe --extract-only <目录>  只释放内置资源，不启动内核\n"
      "\n"
      "选项（与内核一致）:\n"
      "  --model <onnx>   指定模型（默认使用内嵌的 int8 模型）\n"
      "  --port <port>    IPC 端口，默认 8765；传 0 表示自动分配\n"
      "  --threads N      推理线程数，默认 0 = 自动（CPU 逻辑核数一半，上限 8）\n"
      "  --segment-sec X  分段长度（秒），默认 5.0\n"
      "  --no-capture     启动后不自动开启麦克风采集\n"
      "\n"
      "释放目录: %%LOCALAPPDATA%%\\DormNoise\\runtime\n");
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  (void)argc;
  (void)argv;
  SetConsoleOutputCP(CP_UTF8);

  std::wstring tail = CommandLineTail();

  // ---- --extract-only：只释放资源 ----
  if (HasFlag(tail, L"--extract-only")) {
    size_t pos = tail.find(L"--extract-only");
    size_t start = pos + std::wstring(L"--extract-only").size();
    while (start < tail.size() && tail[start] == L' ') ++start;
    size_t end = tail.find(L' ', start);
    std::wstring target = (end == std::wstring::npos) ? tail.substr(start)
                                                      : tail.substr(start, end - start);
    if (target.empty()) target = ExeDir();
    if (!EnsureDirectory(target)) {
      std::fprintf(stderr, "无法创建目录: %s\n", WideToUtf8(target).c_str());
      return 1;
    }
    for (const Asset& a : kAssets) {
      std::wstring out = target + L"\\" + Utf8ToWide(a.name);
      size_t size = static_cast<size_t>(a.end - a.begin);
      if (!FileExistsWithSize(out, size) && !WriteFileAtomic(out, a.begin, size)) {
        std::fprintf(stderr, "释放失败: %s\n", a.name);
        return 1;
      }
      std::printf("已释放: %s (%zu 字节)\n", a.name, size);
    }
    return 0;
  }

  if (HasFlag(tail, L"--help") || HasFlag(tail, L"-h")) {
    PrintPortableUsage();
    return 0;
  }

  // ---- 释放内置资源 ----
  std::wstring runtime_dir = PickRuntimeDir();
  if (runtime_dir.empty()) {
    std::fprintf(stderr, "无法创建可写的运行时目录（已尝试 %%LOCALAPPDATA%% / exe 同目录 / %%TEMP%%）\n");
    return 1;
  }

  std::wstring kernel_exe = runtime_dir + L"\\dorm_noise_kernel.exe";
  std::wstring model_path = runtime_dir + L"\\ast_audioset_int8.onnx";

  for (const Asset& a : kAssets) {
    std::wstring out = runtime_dir + L"\\" + Utf8ToWide(a.name);
    size_t size = static_cast<size_t>(a.end - a.begin);
    if (FileExistsWithSize(out, size)) continue;  // 已释放且大小一致 → 复用
    std::printf("正在释放 %s (%.1f MB) ...\n", a.name, size / 1048576.0);
    if (!WriteFileAtomic(out, a.begin, size)) {
      std::fprintf(stderr, "释放失败: %s（请检查目录权限）\n", a.name);
      return 1;
    }
  }

  // ---- 组装子进程命令行 ----
  std::wstring cmdline = L"\"" + kernel_exe + L"\"";
  if (!HasModelFlag(tail)) {
    cmdline += L" --model \"" + model_path + L"\"";
  }
  if (!tail.empty()) cmdline += L" " + tail;

  std::printf("运行目录: %s\n", WideToUtf8(runtime_dir).c_str());
  std::printf("正在启动内核...\n\n");
  fflush(stdout);

  // ---- 启动真正的内核（继承标准句柄，控制台输出直接可见）----
  STARTUPINFOW si;
  PROCESS_INFORMATION pi;
  ZeroMemory(&si, sizeof(si));
  ZeroMemory(&pi, sizeof(pi));
  si.cb = sizeof(si);

  std::vector<wchar_t> cmdbuf(cmdline.begin(), cmdline.end());
  cmdbuf.push_back(L'\0');

  if (!CreateProcessW(kernel_exe.c_str(), cmdbuf.data(), nullptr, nullptr, TRUE, 0, nullptr,
                      runtime_dir.c_str(), &si, &pi)) {
    std::fprintf(stderr, "启动内核失败 (Win32 错误 %lu)\n", GetLastError());
    return 1;
  }

  WaitForSingleObject(pi.hProcess, INFINITE);
  DWORD code = 1;
  GetExitCodeProcess(pi.hProcess, &code);
  CloseHandle(pi.hThread);
  CloseHandle(pi.hProcess);
  return static_cast<int>(code);
}
