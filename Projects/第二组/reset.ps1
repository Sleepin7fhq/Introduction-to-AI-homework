$ErrorActionPreference = 'Stop'
$port = 8765
$client = $null
for ($i = 0; $i -lt 10; $i++) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $port)
        break
    } catch {
        if ($client) { $client.Close(); $client = $null }
        Start-Sleep -Milliseconds 300
    }
}
if ($null -eq $client) {
    Write-Host '连不上内核：请先双击「1-启动」。' -ForegroundColor Red
    Start-Sleep -Seconds 3
    exit 1
}
$st = $client.GetStream()
$sw = New-Object System.IO.StreamWriter($st, (New-Object System.Text.UTF8Encoding($false)))
$sw.AutoFlush = $true
$sr = New-Object System.IO.StreamReader($st, (New-Object System.Text.UTF8Encoding($false)))
$sw.WriteLine('{"cmd":"reset","rid":"reset1"}')
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    $line = $sr.ReadLine()
    if ($null -eq $line) { break }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    if ($o.type -eq 'ok' -and $o.cmd -eq 'reset') { $ok = $true; break }
    if ($o.rid -eq 'reset1' -and $o.type -eq 'ok') { $ok = $true; break }
}
$client.Close()
if ($ok) {
    Write-Host '已清零：累计时长全部归 0。' -ForegroundColor Green
} else {
    Write-Host '清零失败，请重试。' -ForegroundColor Yellow
}
Start-Sleep -Seconds 2