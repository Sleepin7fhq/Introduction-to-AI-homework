@echo off
REM Stop the DSH LAN share gateway (DSH + gateway) started by start-all.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1"
exit /b %ERRORLEVEL%
