# DSH Studio 2.0 — 一键回归测试
# 用法: powershell -ExecutionPolicy Bypass -File scripts\test.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$esbuild = Join-Path $root 'node_modules\@esbuild\win32-x64\esbuild.exe'
$tmp = Join-Path $root '.tmp'
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

if (-not (Test-Path -LiteralPath $esbuild)) { throw "esbuild not found: $esbuild" }

$coreJs = Join-Path $tmp 'core.test.mjs'
$ssrJs = Join-Path $tmp 'ssr.test.cjs'

Write-Output "== 打包测试 =="
& $esbuild (Join-Path $root 'tests\core.test.ts') --bundle --platform=node --format=esm --target=node20 `
  --outfile=$coreJs --log-level=warning
if ($LASTEXITCODE -ne 0) { throw "core bundle failed" }

& $esbuild (Join-Path $root 'tests\ssr.test.tsx') --bundle --platform=node --format=cjs --target=node20 `
  --jsx=automatic --outfile=$ssrJs --log-level=warning
if ($LASTEXITCODE -ne 0) { throw "ssr bundle failed" }

$failed = 0
Write-Output "`n== 核心链路（解析 / 作曲 / 编曲 / MIDI / 后端） =="
& node $coreJs
if ($LASTEXITCODE -ne 0) { $failed = 1 }

Write-Output "`n== 组件渲染（React SSR） =="
& node $ssrJs
if ($LASTEXITCODE -ne 0) { $failed = 1 }

if ($failed -ne 0) {
  Write-Output "`nTEST FAILED"
  exit 1
}
Write-Output "`nTEST OK"
