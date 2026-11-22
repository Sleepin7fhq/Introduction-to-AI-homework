@echo off
title 梦见月瑞习 Demo
cd /d "%~dp0"
echo.
echo   梦见月瑞习 Demo
echo   浏览器打开: http://127.0.0.1:8770
echo   这个窗口不要关，关了服务就停。
echo.
python server.py
echo.
pause
