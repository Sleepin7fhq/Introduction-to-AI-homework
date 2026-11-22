# One-time setup on the recipient machine: rewrite machine-specific absolute
# paths in hubhome\config.json from the folder this package is extracted to.
# Run from the package root:  powershell -NoProfile -ExecutionPolicy Bypass -File demo\setup-config.ps1
$ErrorActionPreference = "Stop"
$root = (Get-Location).Path
$cfgPath = Join-Path $root "hubhome\config.json"
$cfg = Get-Content $cfgPath -Encoding UTF8 -Raw | ConvertFrom-Json
$cfg.dshWebLog     = ($root -replace '\\','/') + "/probe/dsh-web.log"   # forward slashes
$cfg.workspaceRoot = Join-Path $root "hubhome\workspaces"
$cfg.sharedRoot    = Join-Path $root "hubhome\shared"
# write back UTF-8 WITHOUT BOM (gateway reads raw utf8; BOM breaks JSON.parse on some setups)
$json = $cfg | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($cfgPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "config.json rewritten:"
Get-Content $cfgPath -Encoding UTF8 | Select-String "dshWebLog|workspaceRoot|sharedRoot" | ForEach-Object { "  " + $_.Line.Trim() }