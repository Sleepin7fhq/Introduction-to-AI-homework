#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建「双击即用」的独立便携 exe。

把以下四样东西以二进制资源形式链接进一个启动器，产出**单个 exe**：

    dorm_noise_kernel.exe               内核本体（C++）
    onnxruntime.dll                     ONNX Runtime 运行时
    onnxruntime_providers_shared.dll    ONNX Runtime 共享依赖
    ast_audioset_int8.onnx              AST 音频分类模型（int8，91 MB）

启动器运行时会把这四样释放到 %LOCALAPPDATA%\\DormNoise\\runtime\\，
然后以子进程方式拉起真正的内核（内核自带 UI 可用的 IPC 服务）。

为什么不用「把 DLL 链进同一个 exe」的做法？
    onnxruntime.dll 通过导入库静态依赖，Windows 在**进程创建时**就要解析导入表，
    那时 DLL 还没落盘 → 必然加载失败。所以必须先解压真实文件再启动。

用法：
    python scripts\\build_portable.py
    python scripts\\build_portable.py --fp32        # 用 330 MB 的 fp32 模型（更准但更大）

产物：
    build/portable/dorm_noise_standalone.exe
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUILD = REPO / "build"
BIN = BUILD / "bin"
OUT = BUILD / "portable"
WORK = OUT / "obj"

# MinGW 工具链位置（可用环境变量或参数覆盖）
MINGW_BIN = Path(
    r"C:\Users\qtc91\mingw\x86_64-16.1.0-release-posix-seh-ucrt-rt_v14-rev1\mingw64\bin"
)


def find_tool(name: str, extra: Path | None = None) -> Path:
    """在 PATH、MinGW 目录、extra 里找可执行文件。"""
    if extra:
        cand = extra / (name + ".exe")
        if cand.exists():
            return cand
    found = shutil.which(name)
    if found:
        return Path(found)
    cand = MINGW_BIN / (name + ".exe")
    if cand.exists():
        return cand
    raise SystemExit(f"[X] 找不到 {name}（需要 MinGW-w64 工具链）")


def run(cmd: list[str], cwd: Path | None = None, quiet: bool = False) -> None:
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    dt = time.time() - t0
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(f"[X] 命令失败 ({proc.returncode}): {' '.join(cmd)}")
    if not quiet and proc.stdout.strip():
        print(proc.stdout.strip())
    print(f"    ok ({dt:.1f}s)")


def make_icon(icon_path: Path) -> None:
    """生成一个鲸鱼主题的 .ico（没有图标资源也能跑，有则更体面）。"""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        print("    (无 PIL，跳过图标)")
        return

    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 深蓝圆形底
    d.ellipse((6, 6, S - 6, S - 6), fill=(18, 62, 122, 255))
    # 身体
    d.ellipse((44, 84, 214, 186), fill=(46, 132, 214, 255))
    # 尾巴
    d.polygon([(196, 104), (238, 74), (228, 118), (238, 160)], fill=(46, 132, 214, 255))
    # 腹部
    d.ellipse((72, 138, 188, 190), fill=(236, 244, 255, 255))
    # 眼睛
    d.ellipse((84, 112, 98, 126), fill=(12, 32, 58, 255))
    # 喷水
    d.polygon([(90, 88), (78, 40), (104, 74)], fill=(150, 214, 255, 235))
    d.ellipse((70, 26, 92, 46), fill=(200, 236, 255, 220))

    icon_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(icon_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"    图标: {icon_path.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="构建单文件便携 exe")
    ap.add_argument("--fp32", action="store_true", help="使用 fp32 模型（330 MB）而不是 int8")
    ap.add_argument("--threads", type=int, default=0, help="编译并行度")
    ap.add_argument("--out-name", default="dorm_noise_standalone.exe",
                    help="输出 exe 文件名（可用中文，如 宿舍噪音识别.exe）")
    args = ap.parse_args()

    gpp = find_tool("g++")
    ld = find_tool("ld")
    windres = None
    try:
        windres = find_tool("windres")
    except SystemExit:
        pass

    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) 确认内核已经编译好
    # ------------------------------------------------------------------
    kernel_exe = BIN / "dorm_noise_kernel.exe"
    if not kernel_exe.exists():
        raise SystemExit(
            "[X] 还没编译内核。请先执行：\n"
            "    cmake -S kernel -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "
            f"-DORT_ROOT=\"{REPO / '.deps/onnxruntime-win-x64-1.22.0'}\" "
            f"-DMODELS_DIR=\"{REPO / 'models'}\"\n"
            "    cmake --build build/cmake --parallel 4"
        )

    model_name = "ast_audioset.onnx" if args.fp32 else "ast_audioset_int8.onnx"
    model_src = REPO / "models" / model_name
    if not model_src.exists():
        raise SystemExit(f"[X] 找不到模型 {model_src}")

    print("[1/6] 准备资源")
    resources = [
        (kernel_exe, "dorm_noise_kernel.exe"),
        (BIN / "onnxruntime.dll", "onnxruntime.dll"),
        (BIN / "onnxruntime_providers_shared.dll", "onnxruntime_providers_shared.dll"),
        (model_src, model_name),
    ]
    for src, _ in resources:
        if not src.exists():
            raise SystemExit(f"[X] 缺少资源文件: {src}")
        print(f"    {src.name:<40} {src.stat().st_size/1048576:8.1f} MB")

    # ------------------------------------------------------------------
    # 2) 复制到工作目录（ld 需要相对路径才能得到干净符号名）
    # ------------------------------------------------------------------
    print("[2/6] 生成二进制资源对象")
    for src, name in resources:
        shutil.copy2(src, WORK / name)

    obj_files = []
    for _, name in resources:
        stem = Path(name).stem
        obj = WORK / f"{stem}.o"
        run([str(ld), "-r", "-b", "binary", "-o", str(obj), name], cwd=WORK, quiet=True)
        obj_files.append(obj)
        print(f"    {obj.name:<44} {obj.stat().st_size/1048576:8.1f} MB")

    # ------------------------------------------------------------------
    # 3) 编译启动器
    # ------------------------------------------------------------------
    print("[3/6] 编译启动器 portable_main.cpp")
    port_obj = WORK / "portable_main.o"
    run(
        [
            str(gpp), "-std=c++17", "-O2", "-Wall", "-Wextra",
            "-DUNICODE", "-D_UNICODE",
            "-municode",              # 让 wmain 作为入口
            "-c", str(REPO / "kernel/src/portable_main.cpp"),
            "-o", str(port_obj),
        ],
        quiet=True,
    )
    obj_files.append(port_obj)
    print(f"    {port_obj.name:<44} {port_obj.stat().st_size/1048576:8.1f} MB")

    # ------------------------------------------------------------------
    # 4) 图标资源（可选）
    # ------------------------------------------------------------------
    res_obj = None
    if windres is not None:
        print("[4/6] 生成图标资源")
        ico = WORK / "icon.ico"
        make_icon(ico)
        if ico.exists():
            rc = WORK / "portable.rc"
            # windres 默认按本地 ACP(GBK) 解读 .rc 里的字符串 → 中文会变乱码。
            # 用 `#pragma code_page(65001)` 明确声明源文件是 UTF-8，windres 会正确转成 UTF-16。
            rc.write_text(
                '#pragma code_page(65001)\n'
                '1 ICON "icon.ico"\n'
                '1 VERSIONINFO\n'
                'FILEVERSION 1,0,0,0\n'
                'PRODUCTVERSION 1,0,0,0\n'
                'BEGIN\n'
                '  BLOCK "StringFileInfo"\n'
                '  BEGIN\n'
                '    BLOCK "080404B0"\n'
                '    BEGIN\n'
                '      VALUE "FileDescription", "宿舍噪音智能识别与分类提醒系统 (便携版)"\n'
                '      VALUE "FileVersion", "1.0.0.0"\n'
                '      VALUE "ProductName", "DormNoise Standalone"\n'
                '      VALUE "CompanyName", "DormNoise Project"\n'
                '      VALUE "LegalCopyright", "Local-only academic demo. No telemetry."\n'
                '    END\n'
                '  END\n'
                '  BLOCK "VarFileInfo"\n'
                '  BEGIN\n'
                '    VALUE "Translation", 0x0804, 1200\n'
                '  END\n'
                'END\n',
                encoding="utf-8",
            )
            res_obj = WORK / "portable_res.o"
            run([str(windres), str(rc), "-O", "coff", "-o", str(res_obj)], cwd=WORK, quiet=True)
            obj_files.append(res_obj)
            print("    图标已嵌入")
        else:
            print("    (无图标，继续)")
    else:
        print("[4/6] 跳过图标（无 windres）")

    # ------------------------------------------------------------------
    # 5) 链接
    # ------------------------------------------------------------------
    print("[5/6] 链接便携 exe")
    exe_out = OUT / args.out_name
    link_cmd = [
        str(gpp),
        "-std=c++17", "-O2",
        "-static-libgcc", "-static-libstdc++",
        "-municode",
        "-o", str(exe_out),
        str(port_obj),
    ]
    for obj in obj_files:
        if obj != port_obj:
            link_cmd.append(str(obj))
    link_cmd += ["-lws2_32", "-lwinmm"]
    run(link_cmd, quiet=True)
    print(f"    {exe_out.name:<44} {exe_out.stat().st_size/1048576:8.1f} MB")

    # ------------------------------------------------------------------
    # 6) 冒烟测试
    # ------------------------------------------------------------------
    print("[6/6] 冒烟测试")
    proc = subprocess.run([str(exe_out), "--help"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0 or "便携版" not in proc.stdout:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit("[X] 便携 exe 冒烟测试失败")
    print("    --help 正常")

    print()
    print("=" * 60)
    print(f"  完成: {exe_out}")
    print(f"  大小: {exe_out.stat().st_size/1048576:.1f} MB")
    print("  双击即可运行；模型与运行时自动释放到")
    print("  %LOCALAPPDATA%\\DormNoise\\runtime")
    print("=" * 60)


if __name__ == "__main__":
    main()
