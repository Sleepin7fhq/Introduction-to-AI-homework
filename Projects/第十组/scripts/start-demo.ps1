# DSH Studio 2.0 —— 一键演示启动（前端 + ACE-Step）
# 用法：双击根目录「启动演示.bat」，或在本目录执行：
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-demo.ps1
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
# 统一控制台代码页，避免子进程（Python）的 UTF-8 输出被按 GBK 解码成乱码
try { cmd /c chcp 65001 | Out-Null } catch {}
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = Split-Path -Parent $PSScriptRoot
$venvPy = 'D:\AI\ACE-Step-1.5\.venv\Scripts\python.exe'
$aceServe = Join-Path $root '.tmp\ace\serve.py'
$distDir = Join-Path $root 'dist'
$single = Join-Path $distDir 'index.html'
$frontUrl = 'http://127.0.0.1:5173/'

function Write-Line($text = '') { Write-Host $text }

# 用 TCP 连接判断端口是否已被占用。
# 不用 Get-NetTCPConnection：在部分受限会话里它会返回空，导致误判服务没起、重复启动。
function Test-Port([int]$port) {
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne(600)) { return $false }
    $client.EndConnect($iar)
    return $true
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

Write-Line '============================================================'
Write-Line '  DSH Studio 2.0 · 一键演示启动'
Write-Line '============================================================'
Write-Line ''

if (-not (Test-Path -LiteralPath $venvPy)) {
  Write-Line '[错误] 找不到 Python 3.12：'
  Write-Line "       $venvPy"
  Write-Line "       备用：直接双击 $single"
  exit 1
}
if (-not (Test-Path -LiteralPath $aceServe)) {
  Write-Line '[错误] 找不到 ACE-Step 服务脚本：'
  Write-Line "       $aceServe"
  exit 1
}
if (-not (Test-Path -LiteralPath $single)) {
  Write-Line "[错误] 找不到前端产物：$single"
  Write-Line '       请先执行 npm run build:file'
  exit 1
}

# ---------- 1) ACE-Step 推理服务 ----------
if (Test-Port 8000) {
  Write-Line '[1/2] ACE-Step 已在运行，跳过启动'
} else {
  Write-Line '[1/2] 启动 ACE-Step 推理服务…'
  Start-Process -FilePath $venvPy -ArgumentList @($aceServe) `
    -WorkingDirectory (Join-Path $root '.tmp\ace') -WindowStyle Minimized | Out-Null
}

# ---------- 2) 前端静态服务 ----------
if (Test-Port 5173) {
  Write-Line '[2/2] 前端已在运行，跳过启动'
} else {
  Write-Line '[2/2] 启动前端静态服务…'
  Start-Process -FilePath $venvPy `
    -ArgumentList @('-m', 'http.server', '5173', '--bind', '127.0.0.1', '--directory', $distDir) `
    -WorkingDirectory $root -WindowStyle Minimized | Out-Null
}

Write-Line ''
Write-Line '等待服务就绪（模型加载约 15–20 秒，最多等 120 秒）…'
Write-Line ''
& $venvPy (Join-Path $root 'scripts\wait_ready.py') 120
if ($LASTEXITCODE -ne 0) {
  Write-Line ''
  Write-Line '------------------------------------------------------------'
  Write-Line '  [失败] 服务没有起来。备用方案（现在就能演示）：'
  Write-Line "    1. 双击 $single"
  Write-Line '    2. 页面右侧「预生成真实音频」播放两条真实 WAV'
  Write-Line '------------------------------------------------------------'
  exit 1
}

Write-Line ''
Write-Line '============================================================'
Write-Line "  就绪！浏览器打开： $frontUrl"
Write-Line '============================================================'
Write-Line ''
Write-Line '  演示四步：'
Write-Line '    1. 右上角「ACE-Step 1.5（本机）」应为绿色「可用」'
Write-Line '    2. 写描述 → 生成音乐 → 约 10 秒出 AI 音频条 → 播放'
Write-Line '    3. 引擎切「本地符号引擎」再生成 → 可编辑工程 → 导出 MIDI'
Write-Line '    4. 右侧「预生成真实音频」= 服务挂了也能放真实 AI 音频'
Write-Line ''
Write-Line '  关闭：关掉「ACE-Step 服务」「DSH Studio 前端」两个窗口'
Write-Line "  备用：双击 $single （不需要任何服务）"
Write-Line ''

if (-not $NoBrowser) {
  Start-Process $frontUrl | Out-Null
  Write-Line '  已尝试打开浏览器。'
} else {
  Write-Line "  （-NoBrowser：未自动打开浏览器，请手动访问 $frontUrl）"
}
exit 0
