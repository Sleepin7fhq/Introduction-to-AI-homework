#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo "请先按 README.md 的安装步骤创建项目环境。"
    exit 1
fi
exec .venv/bin/python -m streamlit run app.py --server.address=127.0.0.1 --server.headless=false
