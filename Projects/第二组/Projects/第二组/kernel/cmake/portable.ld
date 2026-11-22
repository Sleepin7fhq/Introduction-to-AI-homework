# ============================================================================
#  portable.ld —— 便携版链接脚本
#
#  把「内核 exe + onnxruntime.dll + providers_shared.dll + int8 模型」
#  以二进制资源形式链接进便携启动器，产出单文件 exe。
#
#  用法（在 build/portable/ 目录下执行）：
#     ld.exe -r -b binary -o dorm_noise_kernel.exe.o dorm_noise_kernel.exe
#     ld.exe -r -b binary -o onnxruntime.dll.o onnxruntime.dll
#     ld.exe -r -b binary -o onnxruntime_providers_shared.dll.o onnxruntime_providers_shared.dll
#     ld.exe -r -b binary -o ast_audioset_int8.onnx.o ast_audioset_int8.onnx
#     g++.exe -o dorm_noise_standalone.exe portable_main.cpp *.o -lws2_32 -lwinmm
#
#  ★ 必须用「相对路径」执行 ld —— 绝对路径会把路径分隔符变成下划线，
#    符号名会变成 _binary_C__Users_... 之类，无法和 portable_main.cpp 对上。
# ============================================================================

/* 输出文件名由链接命令 -o 指定，这里只声明输入段。 */
INPUT(portable_main.o
       dorm_noise_kernel.exe.o
       onnxruntime.dll.o
       onnxruntime_providers_shared.dll.o
       ast_audioset_int8.onnx.o)
