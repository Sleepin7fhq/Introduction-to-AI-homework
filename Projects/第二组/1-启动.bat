@echo off
setlocal
chcp 936 >nul
title 宿舍噪音识别 - 便携版
set "PATH=%~dp0run;%~dp0dist;%PATH%"
cd /d "%~dp0run"
echo ============================================================
echo   宿舍噪音智能识别与分类提醒系统 - 便携内核
echo.
echo   首次启动会加载模型（约 2-4 秒）。
echo   看到 "IPC 服务已启动: 127.0.0.1:8765" 就说明正常运行。
echo   已启用喊叫规则：大声说话（高于 -22 dBFS）算大声喧哗。
echo   关闭本窗口即停止。
echo ============================================================
echo.
"%~dp0run\dorm_noise_kernel.exe" --model "%~dp0models\ast_audioset_int8.onnx" --port 8765 %*
set "RC=%ERRORLEVEL%"
chcp 936 >nul
echo.
echo 程序已退出（代码 %RC%）。
if "%~1"=="" pause
exit /b %RC%