@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=%~dp0runtime\python\python.exe"
echo === unit tests ===
"%PY%" tests\test_route_a.py
if errorlevel 1 goto :fail
echo.
echo === 11-song regression ===
"%PY%" tests\run_regression.py
if errorlevel 1 goto :fail
echo.
echo ALL PASSED
if /i not "%NO_PAUSE%"=="1" pause
exit /b 0
:fail
echo.
echo FAILED
if /i not "%NO_PAUSE%"=="1" pause
exit /b 1
