# ============================================================================
#  宿舍噪音智能识别内核 —— CMake 构建脚本
#
#  依赖:
#    - ONNX Runtime C++ (通过 ORT_ROOT 指定, 需包含 include/ 与 lib/onnxruntime.lib)
#    - miniaudio.h (third_party/miniaudio.h, 单文件库)
#    - ast_labels.h (由 scripts/export_ast_onnx.py 生成到 models/)
#
#  Windows(MinGW) 编译示例:
#    cmake -S kernel -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release ^
#          -DORT_ROOT="C:/path/to/.deps/onnxruntime-win-x64-1.22.0" ^
#          -DMODELS_DIR="C:/path/to/models"
#    cmake --build build/cmake --parallel 4
#
#  注意: 生成器请用 Ninja (MinGW Makefiles 与 CMake 4.x 不兼容)。
# ============================================================================
cmake_minimum_required(VERSION 3.16)
project(dorm_noise_kernel LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ---------------------------------------------------------------------------
#  路径参数
# ---------------------------------------------------------------------------
get_filename_component(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

set(ORT_ROOT "" CACHE PATH "ONNX Runtime SDK 根目录 (含 include/ 与 lib/)")
set(MODELS_DIR "${REPO_ROOT}/models" CACHE PATH "模型目录 (含 ast_audioset.onnx 与 ast_labels.h)")
set(THIRD_PARTY_DIR "${REPO_ROOT}/third_party" CACHE PATH "third_party 目录 (miniaudio.h)")

if(NOT EXISTS "${ORT_ROOT}/include/onnxruntime_cxx_api.h")
  message(FATAL_ERROR
    "找不到 ONNX Runtime 头文件: ${ORT_ROOT}/include/onnxruntime_cxx_api.h\n"
    "请用 -DORT_ROOT=<onnxruntime 根目录> 指定。")
endif()
if(NOT EXISTS "${THIRD_PARTY_DIR}/miniaudio.h")
  message(FATAL_ERROR "找不到 third_party/miniaudio.h")
endif()
if(NOT EXISTS "${MODELS_DIR}/ast_labels.h")
  message(FATAL_ERROR
    "找不到 ${MODELS_DIR}/ast_labels.h\n"
    "请先运行: python scripts/export_ast_onnx.py")
endif()

# ---------------------------------------------------------------------------
#  可执行目标
# ---------------------------------------------------------------------------
add_executable(dorm_noise_kernel
  src/main.cpp
  src/feature_extractor.cpp
  src/classifier.cpp
  src/pipeline.cpp
  src/capture.cpp
  src/ipc_server.cpp
  src/wav_reader.cpp
)

target_include_directories(dorm_noise_kernel PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${THIRD_PARTY_DIR}
  ${MODELS_DIR}
  ${ORT_ROOT}/include
)

# ---- ONNX Runtime 链接 ----
if(WIN32)
  find_library(ORT_LIB
    NAMES onnxruntime
    PATHS "${ORT_ROOT}/lib"
    NO_DEFAULT_PATH)
  if(NOT ORT_LIB)
    message(FATAL_ERROR "找不到 onnxruntime.lib (搜索目录: ${ORT_ROOT}/lib)")
  endif()
  target_link_libraries(dorm_noise_kernel PRIVATE "${ORT_LIB}")

  # 把 onnxruntime.dll 复制到可执行文件旁边，便于直接运行
  add_custom_command(TARGET dorm_noise_kernel POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${ORT_ROOT}/lib/onnxruntime.dll" "$<TARGET_FILE_DIR:dorm_noise_kernel>/onnxruntime.dll"
    VERBATIM)
else()
  target_link_libraries(dorm_noise_kernel PRIVATE "${ORT_ROOT}/lib/libonnxruntime.so")
endif()

# Windows 需要 ws2_32 (Winsock) 与 winmm
if(WIN32)
  target_link_libraries(dorm_noise_kernel PRIVATE ws2_32 winmm)
endif()

# MinGW 下需要显式链接静态库与 C++ 标准库
if(MINGW)
  target_link_options(dorm_noise_kernel PRIVATE -static-libgcc -static-libstdc++)
endif()

target_compile_options(dorm_noise_kernel PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -O2>
  $<$<CXX_COMPILER_ID:MSVC>:/O2 /utf-8>
)

# ★ MinGW/GCC 下必须把 _stdcall 覆盖成空。
#   onnxruntime_c_api.h 在 _WIN32 分支里把 ORT_API_CALL 定义成 MSVC 的 _stdcall，
#   而 GCC 不接受该关键字出现在函数指针声明的位置（`void*(_stdcall* Alloc)(...)`），
#   会把整个 OrtApi 函数指针表解析坏掉，表现为
#   "OrtApi has no member named CreateValue / GetVersionString" 之类
#   大量看似"头文件版本不匹配"的假报错（真实原因只有这一条）。
#
#   注意：MinGW 的 GCC 自己预定义了 _stdcall = __attribute__((__stdcall__))，
#   直接 -D_stdcall= 会触发 "'_stdcall' redefined" 警告。
#   GCC 按命令行出现顺序处理 -D / -U，所以先 -U 掉内置定义，再 -D 成空宏，
#   既干净又不会告警。
if(MINGW OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  target_compile_options(dorm_noise_kernel PRIVATE -U_stdcall -D_stdcall=)
endif()

# 运行时需要能找到模型
set_target_properties(dorm_noise_kernel PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${REPO_ROOT}/build/bin")
