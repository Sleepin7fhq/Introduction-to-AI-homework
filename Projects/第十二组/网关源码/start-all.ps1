# start-all.ps1 —— 一键启动 DSH(3080) + 网关(3090)
# 入口：双击 start-all.cmd，或在包根目录执行：
#   powershell -NoProfile -ExecutionPolicy Bypass -File start-all.ps1
# 兼容 Windows PowerShell 5.1。
# 启动成功后自动打开默认浏览器到登录页；加 -NoBrowser 参数可关闭自动跳转。
param([switch]$NoBrowser)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# 优先使用内置 Node（runtime\node.exe），使包自包含；没有则回退到系统 Node。
$runtimeDir = Join-Path $root "runtime"
if (Test-Path (Join-Path $runtimeDir "node.exe")) {
  $env:Path = "$runtimeDir;$env:Path"
}

function Write-Step($msg) { Write-Host ("[start-all] " + $msg) }

# 首次启动：解压 node_modules tar（安装器只放了大文件，这里一次性展开，约 1-2 分钟）
$bundles = @(
  @{ Tar = "alt\node_modules.tar"; Dir = "alt\node_modules" },
  @{ Tar = "probe\hub-fix\node_modules.tar"; Dir = "probe\hub-fix\node_modules" },
  @{ Tar = "runtime\node_modules.tar"; Dir = "runtime\node_modules" }
)
foreach ($b in $bundles) {
  $tarPath = Join-Path $root $b.Tar
  $dirPath = Join-Path $root $b.Dir
  if ((Test-Path $tarPath) -and -not (Test-Path $dirPath)) {
    Write-Step ("首次启动：解压 " + $b.Tar + "（约 1-2 分钟）…")
    tar -xf $tarPath -C (Split-Path $dirPath)
    if ($LASTEXITCODE -eq 0) {
      Remove-Item $tarPath -Force -ErrorAction SilentlyContinue
      Write-Step ("解压完成：" + $b.Dir)
    } else {
      Write-Host ("[start-all] 错误：解压 " + $b.Tar + " 失败")
      exit 1
    }
  }
}

# ---- 1. 检查 Node 版本 ----
function Get-NodeMajor {
  try {
    $v = & node -v 2>$null
    if ($v) {
      $clean = (($v | Select-Object -First 1) -replace '[^0-9.]','').Trim('.')
      $parts = $clean -split '\.'
      if ($parts.Count -ge 1 -and $parts[0] -match '^\d+$') { return [int]$parts[0] }
    }
  } catch {}
  return 0
}
$nodeMajor = Get-NodeMajor
if ($nodeMajor -eq 0) {
  Write-Host "[start-all] 错误：未找到 node。请先运行 make-portable.cmd 内置 Node，或安装 Node.js 22+（https://nodejs.org）。"
  exit 1
}
if ($nodeMajor -lt 22) {
  Write-Host ("[start-all] 错误：Node 主版本 " + $nodeMajor + " < 22，请升级。")
  exit 1
}
Write-Step ("Node 主版本 " + $nodeMajor + " OK")
if (Test-Path (Join-Path $runtimeDir "node.exe")) {
  Write-Step "使用内置 Node（runtime\node.exe）"
} else {
  Write-Step "使用系统 Node（建议先运行 make-portable.cmd 内置 Node，实现自包含）"
}

# ---- 2. 归一化 config.json 绝对路径（幂等，UTF-8 无 BOM）----
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "demo\setup-config.ps1")
Write-Step "配置路径已归一化"

# ---- 3. 端口占用检查 ----
function Test-Port([int]$Port) {
  try {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    return [bool]$c
  } catch {
    $line = netstat -ano | Select-String (":" + $Port + "\s")
    return [bool]($line -match "LISTENING")
  }
}

$gwUp = Test-Port 3090
if ($gwUp) {
  Write-Host ""
  Write-Host "[start-all] 网关已在运行（端口 3090），无需重复启动。"
  Write-Host "  本机入口：http://127.0.0.1:3090/login"
  Write-Host "  如需重启，请先运行 stop-all.cmd 停止现有进程（或 taskkill /F /IM node.exe）。"
  if (-not $NoBrowser) { Start-Process "http://127.0.0.1:3090/login" }
  exit 0
}

$dsUp = Test-Port 3080

# ---- 4. 启动 DSH 上游 ----
# 后台隐藏窗口运行：避免用户误关/误按 Ctrl+C 导致上游挂掉（日志都在 probe\*.log）。
if (-not $dsUp) {
  Write-Step "启动 DSH 上游（3080，后台运行）…"
  Start-Process -FilePath "cmd.exe" -ArgumentList '/c probe\start-dsh.cmd' -WorkingDirectory $root -WindowStyle Hidden
} else {
  Write-Step "DSH 已在运行（3080），复用"
}

# ---- 5. 等待 DSH token 出现 ----
# DSH 冷启动：源码热启动约 38 秒，全新安装首次启动实测约 2 分钟（要重建 profile），
# 慢磁盘可能更久。给足 6 分钟并周期性提示，避免首次安装被误判超时。
$dshLog = Join-Path $root "probe\dsh-web.log"
$ready = $false
for ($i = 0; $i -lt 720; $i++) {
  Start-Sleep -Milliseconds 500
  if (($i % 60) -eq 0 -and $i -gt 0) { Write-Host ("[start-all] 仍在等待 DSH 就绪…（已 {0} 秒，首次启动较慢属正常）" -f ($i / 2)) }
  $hasToken = $false
  if (Test-Path $dshLog) {
    $hasToken = [bool](Select-String -Path $dshLog -Pattern 'token=' -Quiet)
  }
  if ($hasToken -and (Test-Port 3080)) { $ready = $true; break }
}
if (-not $ready) {
  Write-Host "[start-all] 错误：等待 DSH 就绪超时（6 分钟）。请检查 probe\dsh-web-err.log 与 3080 端口占用。"
  exit 1
}
Write-Step "DSH 就绪（3080）"

# ---- 6. 启动网关 ----
Write-Step "启动网关（3090，后台运行）…"
Start-Process -FilePath "cmd.exe" -ArgumentList '/c probe\start-gateway.cmd' -WorkingDirectory $root -WindowStyle Hidden

# ---- 7. 等待网关就绪 ----
$gwReady = $false
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Milliseconds 500
  if (Test-Port 3090) { $gwReady = $true; break }
}
if (-not $gwReady) {
  Write-Host "[start-all] 错误：网关未在 3090 监听。请查看网关窗口输出与 hubhome\logs\audit.jsonl。"
  exit 1
}

# ---- 8. selftest（校验 DSH 上游 session/list + workspace/follow）----
$env:DSH_TEAM_HUB_HOME = Join-Path $root "hubhome"
Write-Step "运行兼容性自检…"
& node (Join-Path $root "probe\hub-fix\bin\dsh-team-hub.js") selftest
if ($LASTEXITCODE -ne 0) {
  Write-Host "[start-all] 警告：selftest 未全部通过（见上）。请按「常见坑」排查。"
} else {
  Write-Step "selftest 通过"
}

# ---- 9. 打印入口 ----
Write-Host ""
Write-Host "[start-all] 启动完成！"
Write-Host "  本机入口：http://127.0.0.1:3090/login"
try {
  $lanIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -ExpandProperty IPAddress
  foreach ($ip in $lanIps) {
    Write-Host ("  局域网入口：http://" + $ip + ":3090/login")
  }
} catch {}
Write-Host "  账号：admin/AdminPass!2026（首次登录需改密）"
Write-Host "  停止：运行 stop-all.cmd（两个进程都在后台运行，不要按 Ctrl+C 关窗口）"

# ---- 10. 自动打开浏览器 ----
if (-not $NoBrowser) {
  Write-Step "正在打开浏览器（http://127.0.0.1:3090/login）…"
  Start-Process "http://127.0.0.1:3090/login"
}
