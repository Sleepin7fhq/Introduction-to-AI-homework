$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = '宿舍噪音识别 - 实时结果'
$port = 8765

Write-Host '============================================================'
Write-Host '  宿舍噪音识别 - 实时结果'
Write-Host '  先双击「1-启动」，等黑框出现 IPC 服务已启动，再打开本窗口'
Write-Host '  累计时长从内核启动那一刻算；想归零就双击「3-清零」。'
Write-Host '  枪声/爆炸标签 → 游戏外放；喊叫（音量 ≥ -22 dBFS）→ 大声喧哗。'
Write-Host '============================================================'
Write-Host ''

$client = $null
for ($i = 0; $i -lt 30; $i++) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $port)
        break
    } catch {
        if ($client) { $client.Close(); $client = $null }
        Start-Sleep -Milliseconds 500
    }
}
if ($null -eq $client) {
    Write-Host '连不上内核（127.0.0.1:8765）。' -ForegroundColor Red
    Write-Host '请先双击「1-启动」，看到 IPC 服务已启动 后再双击本文件。' -ForegroundColor Yellow
    Write-Host ''
    Read-Host '按回车关闭'
    exit 1
}

$stream = $client.GetStream()
$reader = New-Object System.IO.StreamReader($stream, (New-Object System.Text.UTF8Encoding($false)))
$writer = New-Object System.IO.StreamWriter($stream, (New-Object System.Text.UTF8Encoding($false)))
$writer.AutoFlush = $true
$writer.WriteLine('{"cmd":"status","rid":"viewer"}')

$lastIndex = -1
$lastTotal = -1.0
$printedHeader = $false

while ($true) {
    $line = $reader.ReadLine()
    if ($null -eq $line) { break }
    if ($line.Trim().Length -eq 0) { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }

    if ($o.type -eq 'alert') {
        $msg = $o.message
        if (-not $msg) { $msg = '收到一条超标提醒' }
        Write-Host ''
        Write-Host ("[提醒] {0}" -f $msg) -ForegroundColor Red
        continue
    }
    if ($o.type -ne 'state') { continue }

    if (-not $printedHeader) {
        $printedHeader = $true
        Write-Host ("麦克风: {0}" -f $o.device_name) -ForegroundColor DarkGray
        Write-Host ("模型:   {0}" -f $o.model_path) -ForegroundColor DarkGray
        Write-Host ''
        Write-Host '每 5 秒一段，下面实时显示（Ctrl+C 退出）' -ForegroundColor DarkGray
        Write-Host ''
    }

    $total = [double]$o.total_audio_sec
    if ($total + 0.001 -lt $lastTotal) {
        $lastIndex = -1
        Write-Host '（检测到清零，从 0 重新开始显示）' -ForegroundColor Yellow
    }
    $lastTotal = $total

    if ($null -ne $o.last -and $o.last.segment_index -gt 0 -and $o.last.segment_index -gt $lastIndex -and $o.last.segment_index -le $o.segment_total) {
        $lastIndex = $o.last.segment_index
        $cls = $o.last.class_zh
        if (-not $cls) { $cls = '（无）' }
        $conf = [double]$o.last.confidence
        $rms = [double]$o.last.rms_dbfs
        $top = $o.last.top_label_name
        $t = (Get-Date).ToString('HH:mm:ss')
        Write-Host ("[{0}] 第 {1} 段: {2}   置信度 {3:N3}   音量 {5:N1} dBFS   细分标签: {4}" -f $t, $lastIndex, $cls, $conf, $top, $rms) -ForegroundColor Green
        $parts = @()
        foreach ($c in $o.classes) {
            $parts += ("{0} {1:N0}s" -f $c.zh, [double]$c.duration_sec)
        }
        Write-Host ("           累计: " + ($parts -join ' | ')) -ForegroundColor Gray
    }
}

Write-Host ''
Write-Host '内核已断开。' -ForegroundColor Yellow
Read-Host '按回车关闭'