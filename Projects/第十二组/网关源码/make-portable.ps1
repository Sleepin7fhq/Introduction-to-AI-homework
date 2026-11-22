# make-portable.ps1 —— 内置便携 Node，让整个包自包含（不再依赖系统 Node）
# 用法：双击 make-portable.cmd，或：
#   powershell -NoProfile -ExecutionPolicy Bypass -File make-portable.ps1 [-NodeVersion v24.16.0]
# 注意：DSH 0.2.2-rc.1 的 engines 要求 node >= 24.9.0，内置版本不能低于它。
param([string]$NodeVersion = "v24.16.0")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtime = Join-Path $root "runtime"
$nodeExe = Join-Path $runtime "node.exe"

# DSH 最低版本要求（alt\node_modules\@deepseek-ai\dsh\package.json 的 engines.node = ">=24.9.0"）
$MinMajor = 24
$MinMinor = 9
function Test-MinVersion([string]$ver) {
  $clean = ($ver -replace '^v','').Trim()
  $parts = $clean -split '\.'
  if ($parts.Count -lt 2 -or $parts[0] -notmatch '^\d+$') { return $false }
  $maj = [int]$parts[0]; $min = [int]$parts[1]
  return ($maj -gt $MinMajor) -or ($maj -eq $MinMajor -and $min -ge $MinMinor)
}

if (Test-Path $nodeExe) {
  $v = (& $nodeExe -v).Trim()
  if (Test-MinVersion $v) {
    Write-Host "已内置 Node $v（满足 >= $MinMajor.$MinMinor），跳过下载。"
    exit 0
  }
  Write-Host "现有内置 Node $v 低于 DSH 要求（>= $MinMajor.$MinMinor），重新下载 $NodeVersion ..."
  Remove-Item $runtime -Recurse -Force -ErrorAction SilentlyContinue
}

$zipUrl = "https://nodejs.org/dist/$NodeVersion/node-$NodeVersion-win-x64.zip"
$zipPath = Join-Path $env:TEMP "node-$NodeVersion-win-x64.zip"
$extractDir = Join-Path $env:TEMP "node-portable-extract"

Write-Host "下载 $zipUrl"
curl.exe -L --fail -o $zipPath $zipUrl
if ($LASTEXITCODE -ne 0) {
  Write-Host "下载失败（版本号可能不存在，可换 -NodeVersion 重试）。"
  exit 1
}

if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
Write-Host "解压到 runtime\ ..."
tar -xf $zipPath -C $extractDir
if ($LASTEXITCODE -ne 0) { Write-Host "解压失败（tar 不可用？）"; exit 1 }

$inner = Join-Path $extractDir "node-$NodeVersion-win-x64"
if (-not (Test-Path (Join-Path $inner "node.exe"))) {
  $found = Get-ChildItem $extractDir -Recurse -Filter node.exe | Select-Object -First 1
  if (-not $found) { Write-Host "解压后找不到 node.exe"; exit 1 }
  $inner = $found.DirectoryName
}

New-Item -ItemType Directory -Path $runtime -Force | Out-Null
Copy-Item (Join-Path $inner "*") -Destination $runtime -Recurse -Force

Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

$v = (& $nodeExe -v).Trim()
if (-not (Test-MinVersion $v)) {
  Write-Host "错误：下载到的 $v 仍低于 DSH 要求（>= $MinMajor.$MinMinor）。"
  exit 1
}
Write-Host "内置 Node 完成：$v  ->  $runtime"
Write-Host "现在 start-all 会自动使用内置 Node，不再依赖系统 Node。"
