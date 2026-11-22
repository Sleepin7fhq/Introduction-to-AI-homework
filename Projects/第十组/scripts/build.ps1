# DSH Studio 2.0 — 单文件构建（绕过 vite 的 node 子进程，直接用 esbuild CLI）
# 用法: powershell -ExecutionPolicy Bypass -File scripts\build.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$esbuild = Join-Path $root 'node_modules\@esbuild\win32-x64\esbuild.exe'
$tmp = Join-Path $root '.tmp\build'
$dist = Join-Path $root 'dist'

if (-not (Test-Path -LiteralPath $esbuild)) { throw "esbuild not found: $esbuild" }
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
New-Item -ItemType Directory -Path $dist -Force | Out-Null
$jsOut = Join-Path $tmp 'bundle.js'
$cssOut = Join-Path $tmp 'bundle.css'

& $esbuild (Join-Path $root 'src\main.tsx') --bundle --format=iife --target=es2020 --jsx=automatic `
  --charset=utf8 --minify --outfile=$jsOut --log-level=warning
if ($LASTEXITCODE -ne 0) { throw "js bundle failed ($LASTEXITCODE)" }

& $esbuild (Join-Path $root 'src\styles.css') --bundle --charset=utf8 --minify `
  --outfile=$cssOut --log-level=warning
if ($LASTEXITCODE -ne 0) { throw "css bundle failed ($LASTEXITCODE)" }

$js = [System.IO.File]::ReadAllText((Join-Path $tmp 'bundle.js'), [System.Text.Encoding]::UTF8)
$css = [System.IO.File]::ReadAllText((Join-Path $tmp 'bundle.css'), [System.Text.Encoding]::UTF8)
# 内联时不能出现裸的 </script，转义后仍是合法 JS
$js = $js -replace '</script', '<\/script'

$bootGuard = @'
    <script>
      // 启动期兜底：如果主 bundle 在 React 挂载前就抛错，至少把原因钉在页面上，
      // 而不是留给现场一个白屏。
      window.__bootErrors = [];
      function showBootError(msg, extra) {
        window.__bootErrors.push(msg);
        var pre = document.createElement('pre');
        pre.id = 'boot-error';
        pre.style.cssText =
          'position:fixed;inset:0;margin:0;padding:16px;background:#180a0d;color:#fca5a5;' +
          'font:12px/1.6 ui-monospace,Consolas,monospace;white-space:pre-wrap;z-index:99999;overflow:auto';
        pre.textContent = 'DSH Studio 启动失败\n\n' + msg + (extra ? '\n\n' + extra : '');
        document.documentElement.appendChild(pre);
      }
      window.addEventListener('error', function (e) {
        showBootError(e.message || 'unknown error', (e.filename || '') + ':' + (e.lineno || 0));
      });
      window.addEventListener('unhandledrejection', function (e) {
        showBootError('unhandled rejection: ' + (e.reason && e.reason.message ? e.reason.message : String(e.reason)));
      });
    </script>
'@

$html = @"
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230a0e13'/%3E%3Ccircle cx='16' cy='16' r='6' fill='none' stroke='%235eead4' stroke-width='2.5'/%3E%3Ccircle cx='16' cy='16' r='2' fill='%2338bdf8'/%3E%3C/svg%3E" />
    <title>DSH Studio 2.0 · AI 音乐工作站</title>
    <style>
$css
    </style>
  </head>
  <body>
$bootGuard
    <div id="root"></div>
    <script>
$js
    </script>
  </body>
</html>
"@

$out = Join-Path $dist 'index.html'
[System.IO.File]::WriteAllText($out, $html, (New-Object System.Text.UTF8Encoding($false)))

# 预生成的真实 AI 音频（ACE-Step 产出）随产物一起发布，供服务不可用时演示
$demoSrc = Join-Path $root 'demo'
$demoDst = Join-Path $dist 'demo'
if (Test-Path -LiteralPath $demoSrc) {
  New-Item -ItemType Directory -Path $demoDst -Force | Out-Null
  Get-ChildItem -LiteralPath $demoSrc -Filter *.wav -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $demoDst $_.Name) -Force
  }
  $n = (Get-ChildItem -LiteralPath $demoDst -Filter *.wav -File).Count
  Write-Output ("DEMO AUDIO  {0} 个 WAV 已复制到 dist\demo" -f $n)
}

# 采样库：public/samples -> dist/samples
$pubSrc = Join-Path $root 'public\samples'
$pubDst = Join-Path $dist 'samples'
if (Test-Path -LiteralPath $pubSrc) {
  if (Test-Path -LiteralPath $pubDst) { Remove-Item -LiteralPath $pubDst -Recurse -Force }
  New-Item -ItemType Directory -Path $pubDst -Force | Out-Null
  Copy-Item -Path (Join-Path $pubSrc '*') -Destination $pubDst -Recurse -Force
  $n = (Get-ChildItem -LiteralPath $pubDst -Recurse -Filter *.wav -File).Count
  Write-Output ("SAMPLES    {0} 个 WAV 已复制到 dist\samples" -f $n)
}

$size = (Get-Item -LiteralPath $out).Length
Write-Output ("BUILD OK  {0}  {1:N0} bytes ({2:N0} KB)" -f $out, $size, ($size / 1KB))
