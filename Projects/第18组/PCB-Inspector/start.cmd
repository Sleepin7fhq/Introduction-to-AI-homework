@echo off
setlocal
cd /d "%~dp0"
set "PCB_PY=.venv\Scripts\python.exe"
if not exist "%PCB_PY%" set "PCB_PY=..\..\.venv\Scripts\python.exe"
if not exist "%PCB_PY%" (
  echo Please follow README.md to create the project environment.
  pause
  exit /b 1
)
"%PCB_PY%" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause

