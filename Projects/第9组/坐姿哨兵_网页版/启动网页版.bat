@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "LOG=%~dp0启动日志.txt"
echo ==== %date% %time% ==== > "%LOG%"
echo 当前目录: %CD% >> "%LOG%"

echo ==========================================
echo   坐姿哨兵 网页版
echo ==========================================
echo.

if not exist "index.html" (
    echo [错误] 这个文件夹里没有 index.html >> "%LOG%"
    echo [错误] 这个文件夹里没有 index.html
    echo.
    echo 你很可能是在“压缩包预览”里直接双击的，或者只解压了一部分。
    echo 请把 zip 完整解压到一个普通文件夹（比如桌面），再进文件夹运行。
    echo.
    pause
    exit /b 1
)

rem 找一个能用的 Python
set "PY="
where python >nul 2>nul
if not errorlevel 1 (
    python -c "print(1)" >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "print(1)" >nul 2>nul
        if not errorlevel 1 set "PY=py -3"
    )
)

if defined PY (
    echo 使用 Python 启动本地服务... 
    echo 使用 Python: %PY% >> "%LOG%"
    %PY% "%~dp0serve.py"
    echo 服务退出，代码 %errorlevel% >> "%LOG%"
    goto :done
)

echo 没找到可用的 Python，尝试 PowerShell...
echo 没找到 Python >> "%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1"
echo PowerShell 退出，代码 %errorlevel% >> "%LOG%"

:done
echo.
echo 服务已停止。如果浏览器一直没打开，请看同目录的 启动日志.txt
pause
