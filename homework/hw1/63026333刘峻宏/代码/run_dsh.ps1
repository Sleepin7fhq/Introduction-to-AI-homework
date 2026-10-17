# run_dsh.ps1
# ---------------------------------------------------------------
# 用 DeepSeek Harness (dsh) headless 模式求解 2024 新课标 I 卷第 19 题
# 运行前提：
#   1) 已安装 @deepseek-ai/dsh（npm install @deepseek-ai/dsh）
#   2) 已配置 ~/.dsh/.credentials.yaml 中的 DEEPSEEK_API_KEY
#   3) 在空目录 workspace 中运行，dsh 会在其中生成
#      solution.md / verify.py / analysis.md
# ---------------------------------------------------------------

$cli   = "<dsh安装路径>\node_modules\@deepseek-ai\dsh\lib\bin.js"
$node  = "node"          # 或 node.exe 的绝对路径
$proj  = $PSScriptRoot

# 从 dsh 凭据库读取 API Key（也可直接 $env:DEEPSEEK_API_KEY = "sk-..."）
$cred = Get-Content "$env:USERPROFILE\.dsh\.credentials.yaml" -Raw
$env:DEEPSEEK_API_KEY = [regex]::Match($cred, 'DEEPSEEK_API_KEY:\s*"?([^"\r\n]+)"?').Groups[1].Value.Trim()

$prompt = Get-Content -Raw -Encoding UTF8 "$proj\prompt_for_dsh.txt"

Push-Location "$proj\workspace"
$sw = [Diagnostics.Stopwatch]::StartNew()
$out  = & $node $cli --profile headless $prompt 2>&1 | ForEach-Object { $_.ToString() }
$code = $LASTEXITCODE
$sw.Stop()
Pop-Location

("EXIT={0}  SECONDS={1}" -f $code, [math]::Round($sw.Elapsed.TotalSeconds, 1)) |
    Out-File "$proj\dsh_run.log" -Encoding utf8
$out | Out-File "$proj\dsh_run.log" -Append -Encoding utf8
