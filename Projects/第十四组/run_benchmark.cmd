@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0runtime\python\python.exe"
if not exist "%PY%" set "PY=python"
echo === Chorales ===
"%PY%" "%~dp0tests\benchmark_chorales.py" 20
echo === ASAP ===
"%PY%" "%~dp0tests\benchmark_asap.py" 20
if not "%NO_PAUSE%"=="1" pause
