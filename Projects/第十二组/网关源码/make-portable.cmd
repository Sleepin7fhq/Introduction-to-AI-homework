@echo off
REM Bundle a portable Node into runtime\ so the whole package is self-contained.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make-portable.ps1" %*
exit /b %ERRORLEVEL%
