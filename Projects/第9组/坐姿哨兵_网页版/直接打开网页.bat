@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "index.html" (
    echo [错误] 找不到 index.html
    echo 请先把 zip 完整解压到一个文件夹，再进来双击。
    pause
    exit /b 1
)

echo 正在用默认浏览器打开 page...
start "" "%~dp0index.html"
echo.
echo 如果浏览器问“是否允许使用摄像头”，点允许。
echo 如果这一步拿不到摄像头，请改用「启动网页版.bat」。
echo.
pause
