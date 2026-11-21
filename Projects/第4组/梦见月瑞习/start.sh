#!/usr/bin/env bash
# 梦见月瑞习 Demo 启动脚本
cd "$(dirname "$0")" || exit 1
export DSH_DEMO_PORT="${DSH_DEMO_PORT:-8770}"
echo "打开浏览器访问: http://127.0.0.1:${DSH_DEMO_PORT}"
exec python3 server.py
