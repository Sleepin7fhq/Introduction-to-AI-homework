@echo off
REM Nawa Stage - step 5/6 demo. Double-click to start.
REM Requires Python 3.11+ on PATH (python or py).
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  set PY=python
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set PY=py
  ) else (
    echo Python not found. Install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
  )
)

echo Starting local server at http://127.0.0.1:8765/
echo Close this window to stop the server.
%PY% tools\serve.py --port 8765 --open
if %errorlevel% neq 0 pause
endlocal
