@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=%~dp0runtime\python\python.exe"
"%PY%" -m route_a.cli %*
if errorlevel 1 goto :end
if /i not "%NO_PAUSE%"=="1" pause
exit /b 0
:end
if /i not "%NO_PAUSE%"=="1" pause
exit /b 1
