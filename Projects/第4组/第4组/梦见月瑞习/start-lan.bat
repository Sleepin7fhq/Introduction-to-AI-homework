@echo off
title 梦见月瑞习 · 课堂模式
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo   没有找到 Python，请先安装 https://www.python.org/downloads/
  pause
  exit /b
)
netstat -ano | findstr ":8770" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo   服务已经在运行，直接打开页面...
  start "" http://127.0.0.1:8770/classroom
  timeout /t 2 >nul
  exit /b
)
echo.
echo   正在启动梦见月瑞习课堂模式
echo   窗口不要关，关了服务就停。
echo.
python server.py --lan --open --port=8770
echo.
pause
