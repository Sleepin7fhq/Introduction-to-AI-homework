# install.ps1 —— 免 Inno 的一键安装：把包复制到 %LOCALAPPDATA%\DSHLanShare 并建快捷方式 + 卸载项
# 用法：在包根目录执行
#   powershell -NoProfile -ExecutionPolicy Bypass -File installer\install.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)   # 包根目录
$dest = Join-Path $env:LOCALAPPDATA "DSHLanShare"

Write-Host "安装到 $dest ..."
robocopy $root $dest /E /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Host "复制失败（robocopy 退出码 $LASTEXITCODE）"; exit 1 }

# 归一化 config.json 绝对路径到安装目录
Push-Location $dest
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dest "demo\setup-config.ps1")
Pop-Location

# 快捷方式（开始菜单 + 桌面）
$ws = New-Object -ComObject WScript.Shell
$startMenu = [Environment]::GetFolderPath("StartMenu")
$desktop = [Environment]::GetFolderPath("Desktop")
$group = Join-Path $startMenu "DSH 局域网共享网关"
New-Item -ItemType Directory -Path $group -Force | Out-Null

function New-Shortcut($path, $target) {
  $s = $ws.CreateShortcut($path)
  $s.TargetPath = $target
  $s.WorkingDirectory = $dest
  $s.Save()
}
New-Shortcut (Join-Path $group "启动 DSH 共享网关.lnk") (Join-Path $dest "start-all.cmd")
New-Shortcut (Join-Path $desktop "DSH 共享网关.lnk") (Join-Path $dest "start-all.cmd")

# 「添加或删除程序」卸载项
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DSHLanShare"
New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name DisplayName -Value "DSH 局域网共享网关"
Set-ItemProperty -Path $uninstallKey -Name DisplayVersion -Value "1.0.0"
Set-ItemProperty -Path $uninstallKey -Name Publisher -Value "DSH Team"
Set-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $dest
Set-ItemProperty -Path $uninstallKey -Name UninstallString -Value ("powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f (Join-Path $dest "installer\uninstall.ps1"))
Set-ItemProperty -Path $uninstallKey -Name NoModify -Value 1
Set-ItemProperty -Path $uninstallKey -Name NoRepair -Value 1

Write-Host ""
Write-Host "安装完成！启动方式："
Write-Host "  开始菜单 -> DSH 局域网共享网关 -> 启动 DSH 共享网关"
Write-Host "  或桌面快捷方式 'DSH 共享网关'"
Write-Host "卸载：控制面板 -> 添加或删除程序 -> DSH 局域网共享网关"
