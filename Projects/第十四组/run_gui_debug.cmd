@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PY=%~dp0runtime\python\python.exe"
"%PY%" -m route_a.gui %*
if errorlevel 1 pause
