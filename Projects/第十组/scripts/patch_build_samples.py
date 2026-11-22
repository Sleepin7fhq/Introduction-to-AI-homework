# -*- coding: utf-8 -*-
"""构建时把 public/samples 复制到 dist/samples。"""
import io

P = r'D:\AI\aihw\scripts\build.ps1'
s = io.open(P, encoding='utf-8-sig').read()

if 'SAMPLES' in s:
    print('already patched')
else:
    anchor = '$size = (Get-Item -LiteralPath $out).Length'
    block = '''# 采样库：public/samples -> dist/samples
$pubSrc = Join-Path $root 'public\\samples'
$pubDst = Join-Path $dist 'samples'
if (Test-Path -LiteralPath $pubSrc) {
  if (Test-Path -LiteralPath $pubDst) { Remove-Item -LiteralPath $pubDst -Recurse -Force }
  New-Item -ItemType Directory -Path $pubDst -Force | Out-Null
  Copy-Item -Path (Join-Path $pubSrc '*') -Destination $pubDst -Recurse -Force
  $n = (Get-ChildItem -LiteralPath $pubDst -Recurse -Filter *.wav -File).Count
  Write-Output ("SAMPLES    {0} 个 WAV 已复制到 dist\\samples" -f $n)
}

'''
    assert anchor in s
    s = s.replace(anchor, block + anchor, 1)
    io.open(P, 'w', encoding='utf-8-sig', newline='\r\n').write(s)
    print('build.ps1 patched')
