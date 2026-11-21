# 极简静态服务器（无需管理员权限）
# 用 TcpListener 自己回 HTTP，绕开 HttpListener 需要 URL ACL 的问题。

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

$listener = $null
$port = 0
foreach ($p in 8765..8784) {
    try {
        $t = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $p)
        $t.Start()
        $listener = $t
        $port = $p
        break
    } catch { }
}

if ($null -eq $listener) {
    Write-Host "[错误] 8765-8784 端口都被占用了。"
    Read-Host "按回车退出"
    exit 1
}

$url = "http://localhost:$port/index.html"
Write-Host "=========================================="
Write-Host "  坐姿哨兵 网页版"
Write-Host "=========================================="
Write-Host "  地址: $url"
Write-Host "  关掉这个窗口即停止服务。"
Write-Host "=========================================="
Start-Process $url

$mime = @{
    '.html' = 'text/html; charset=utf-8'
    '.js'   = 'application/javascript; charset=utf-8'
    '.mjs'  = 'application/javascript; charset=utf-8'
    '.css'  = 'text/css; charset=utf-8'
    '.wasm' = 'application/wasm'
    '.task' = 'application/octet-stream'
    '.json' = 'application/json; charset=utf-8'
    '.png'  = 'image/png'
}

try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        try {
            $stream = $client.GetStream()
            $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)
            $requestLine = $reader.ReadLine()
            if (-not $requestLine) { $client.Close(); continue }
            while (($line = $reader.ReadLine()) -ne $null -and $line -ne '') { }

            $parts = $requestLine.Split(' ')
            $rawPath = if ($parts.Length -ge 2) { $parts[1] } else { '/' }
            $rawPath = $rawPath.Split('?')[0]
            $rel = [Uri]::UnescapeDataString($rawPath).TrimStart('/')
            if ([string]::IsNullOrWhiteSpace($rel)) { $rel = 'index.html' }
            $file = Join-Path $root $rel

            if (Test-Path -LiteralPath $file -PathType Leaf) {
                $bytes = [IO.File]::ReadAllBytes($file)
                $ext = [IO.Path]::GetExtension($file).ToLower()
                $type = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'application/octet-stream' }
                $head = "HTTP/1.1 200 OK`r`nContent-Type: $type`r`nContent-Length: $($bytes.Length)`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n"
                $hb = [Text.Encoding]::ASCII.GetBytes($head)
                $stream.Write($hb, 0, $hb.Length)
                $stream.Write($bytes, 0, $bytes.Length)
            } else {
                $body = [Text.Encoding]::UTF8.GetBytes("404 $rel")
                $head = "HTTP/1.1 404 Not Found`r`nContent-Type: text/plain; charset=utf-8`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
                $hb = [Text.Encoding]::ASCII.GetBytes($head)
                $stream.Write($hb, 0, $hb.Length)
                $stream.Write($body, 0, $body.Length)
            }
            $stream.Flush()
        } catch {
            # 单个请求失败不影响后续
        } finally {
            try { $client.Close() } catch {}
        }
    }
} finally {
    $listener.Stop()
}
