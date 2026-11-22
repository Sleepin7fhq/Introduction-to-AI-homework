# stop-all.ps1 —— 停止 DSH 与网关进程。
# 命中两类进程：① 本包 runtime\node.exe 启动的；② 命令行指向 DSH/网关入口脚本的
# （无论用哪个 node 启动、装在哪个目录，只要跑的是这两条入口就停——防止手动启动
# 或其它目录实例占着 3080/3090 导致新实例起不来）。
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = [System.IO.Path]::GetFullPath((Join-Path $root "runtime\node.exe"))
$killed = 0
Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
  $hit = $false
  try {
    if ($_.ExecutablePath -and [System.IO.Path]::GetFullPath($_.ExecutablePath) -eq $target) { $hit = $true }
    if ($_.CommandLine -match 'dsh\\lib\\bin\.js|dsh-team-hub\.js') { $hit = $true }
  } catch {}
  if ($hit) { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $killed++ }
}
Write-Host "已停止 $killed 个 node 进程（DSH/网关）。"
