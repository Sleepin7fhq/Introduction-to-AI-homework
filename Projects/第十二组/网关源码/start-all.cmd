@echo off
REM One-command startup for the DSH LAN share gateway.
REM Derives its own directory via %~dp0 so CJK paths are never embedded here.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1"
exit /b %ERRORLEVEL%
