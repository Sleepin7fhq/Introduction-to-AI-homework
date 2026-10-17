#!/usr/bin/env bash
# pptx -> pdf 预览（需要 LibreOffice）；用法：bash preview_math.sh [文件名]
set -e
SRC="${1:-加性唯一性条件下指数和的范数估计.pptx}"
OUT="${2:-预览}"
mkdir -p "$OUT"

if command -v soffice >/dev/null 2>&1; then
  LO=soffice
elif [ -x "$HOME/tools/squashfs-root/opt/libreoffice25.8/program/soffice" ]; then
  LO="$HOME/tools/squashfs-root/opt/libreoffice25.8/program/soffice"
  export LD_LIBRARY_PATH="$HOME/tools/extra/usr/lib/x86_64-linux-gnu"
else
  echo "未找到 LibreOffice：请安装 libreoffice-impress，或手动导出 PDF。" >&2
  exit 1
fi

"$LO" --headless --norestore \
  -env:UserInstallation=file:///tmp/louser_preview \
  --convert-to pdf --outdir "$OUT" "$SRC" >/dev/null 2>&1
echo "已输出：$OUT/${SRC%.pptx}.pdf"
