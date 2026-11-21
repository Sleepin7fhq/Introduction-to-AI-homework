#!/usr/bin/env bash
# 课堂模式：同一 Wi-Fi 下的手机、平板、别的电脑都能打开
cd "$(dirname "$0")" || exit 1
export DSH_DEMO_HOST=0.0.0.0
export DSH_DEMO_PORT="${DSH_DEMO_PORT:-8770}"
export DSH_DEMO_OPEN=1
exec python3 server.py
