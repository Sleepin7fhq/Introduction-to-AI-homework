# uninstall.ps1 —— 卸载 DSH 共享网关（安装目录 + 快捷方式 + 卸载注册表项）
# 先关闭 DSH/网关窗口再运行；本脚本会尝试停止安装目录下的 node 进程。
$ErrorActionPreference = "Continue"
$dest = Join-Path $env:LOCALAPPDATA "DSHLanShare"

# 停止安装目录下的 node 进程（内置 Node 的路径形如 $dest\runtime\node.exe）
Get-Process node -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -and $_.Path.StartsWith($dest, [System.StringComparison]::OrdinalIgnoreCase) } |
  Stop-Process -Force -ErrorAction SilentlyContinue

# 删除快捷方式
$startMenu = [Environment]::GetFolderPath("StartMenu")
$desktop = [Environment]::GetFolderPath("Desktop")
Remove-Item (Join-Path $startMenu "DSH 局域网共享网关") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $desktop "DSH 共享网关.lnk") -Force -ErrorAction SilentlyContinue

# 删除安装目录
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue

# 删除卸载注册表项
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DSHLanShare" -Force -ErrorAction SilentlyContinue

Write-Host "已卸载 DSH 共享网关。"
