@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo   需要管理员权限，正在重新启动...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)
echo.
echo   给 8770 端口开一个防火墙入站规则
echo   这样同一个 Wi-Fi 下的手机、别的电脑才能访问
echo.
netsh advfirewall firewall delete rule name="梦见月瑞习Demo" >nul 2>&1
netsh advfirewall firewall add rule name="梦见月瑞习Demo" dir=in action=allow protocol=TCP localport=8770
echo.
echo   完成。按任意键关闭。
pause >nul
