@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PY=%~dp0runtime\python\pythonw.exe"
start "route_a_gui" "%PY%" -m route_a.gui %*
