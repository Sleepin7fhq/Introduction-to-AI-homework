# Rehearsal: run the EXACT commands printed in the docx §5.2, top to bottom.
# Any deviation in the document shows up here as a failing assertion.
$ErrorActionPreference = "Continue"
$fail = 0
function Check($label, $text, $want) {
  $text = "$text"                # curl failure returns $null -> stringify
  $ok = -not [string]::IsNullOrEmpty($text) -and $text.Contains($want)
  if (-not $ok) { $script:fail++ }
  Write-Host ("{0,-6} {1}" -f ($(if ($ok) {"PASS"} else {"FAIL"})), $label)
  if (-not $ok) { Write-Host ("       got: " + $text) }
}

# --- §4.3 login (doc-verbatim) ---
# 账号现在首登强制改密（mustChangePassword:true）。演示账号用同一密码完成
# 改密，保持 docx 里记录的密码不变；真实部署务必改成新的强密码。
$H = "http://127.0.0.1:3090"
curl.exe -s -c demo\admin.jar -o NUL "$H/login"
curl.exe -s -b demo\admin.jar -c demo\admin.jar -o NUL `
  -d "next=/&username=admin&password=AdminPass!2026" "$H/login"
curl.exe -s -b demo\admin.jar -c demo\admin.jar -o NUL `
  -d "current=AdminPass!2026&next=AdminPass!2026" "$H/change-password"
curl.exe -s -c demo\alice.jar -o NUL "$H/login"
curl.exe -s -b demo\alice.jar -c demo\alice.jar -o NUL `
  -d "next=/&username=alice&password=AlicePass!2026" "$H/login"
curl.exe -s -b demo\alice.jar -c demo\alice.jar -o NUL `
  -d "current=AlicePass!2026&next=AlicePass!2026" "$H/change-password"
curl.exe -s -c demo\bob.jar -o NUL "$H/login"
curl.exe -s -b demo\bob.jar -c demo\bob.jar -o NUL `
  -d "next=/&username=bob&password=BobPass!2026" "$H/login"
curl.exe -s -b demo\bob.jar -c demo\bob.jar -o NUL `
  -d "current=BobPass!2026&next=BobPass!2026" "$H/change-password"
curl.exe -s -c demo\carol.jar -o NUL "$H/login"
curl.exe -s -b demo\carol.jar -c demo\carol.jar -o NUL `
  -d "next=/&username=carol&password=CarolPass!2026" "$H/login"
curl.exe -s -b demo\carol.jar -c demo\carol.jar -o NUL `
  -d "current=CarolPass!2026&next=CarolPass!2026" "$H/change-password"

# --- 自愈准备：会话 id 不随包分发（全新安装没有旧会话），
# 先新建一个 bob 会话并按新 id 重建 payload，演示无需任何手工步骤。 ---
$pkgRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$nodeExe = Join-Path $pkgRoot "runtime\node.exe"
if (-not (Test-Path $nodeExe)) { $nodeExe = "node" }   # 回退系统 node
$nsRaw = & $nodeExe (Join-Path $pkgRoot "probe\dbg-newsession2.mjs") 2>&1
$SID = ([regex]::Match(($nsRaw -join "`n"), 'NEW_SID=(\S+)')).Groups[1].Value
if (-not $SID) { Write-Host "FATAL: 无法新建 bob 会话（请确认 DSH/网关正在运行）"; exit 9 }
& $nodeExe (Join-Path $pkgRoot "demo\make-payloads.mjs") $SID | Out-Null
Write-Host "自愈准备完成：已新建会话并重建 payload（$SID）"

# --- §4.4 selftest (doc-verbatim) ---
$st = curl.exe -s -b demo\admin.jar -H "content-type: application/json" -d "{}" `
  "$H/__teamhub/api/selftest"
Check "4.4 selftest ok:true" $st '"ok":true'

# --- §5.2 helper (doc-verbatim) ---
$wl = curl.exe -s -b demo\admin.jar "$H/__teamhub/api/workspaces"
$WS = [regex]::Match(($wl -join ''), '"workspaceId":"([0-9a-f-]{36})","owner":"bob"').Groups[1].Value
if (-not $WS) { Write-Host "FATAL: cannot resolve bob workspace id"; exit 9 }
function Post($jar, $payload, $api) {
  curl.exe -s -b "demo\$jar.jar" -H "content-type: application/json" `
    --data-binary "@demo/payloads/$payload.json" "$H$api"
}

# CASE 0
Check "CASE 0 bob reads own file" (Post bob read-secret /api/workspaceFiles/read) 'BOB SECRET: budget 42'
# CASE 1
Post admin share-none "/__teamhub/api/workspaces/$WS/sharing" | Out-Null
Check "CASE 1 unshared -> denied" (Post alice read-secret /api/workspaceFiles/read) '无权读取该工作区文件'
# CASE 2
Check "CASE 2 grant -> members[alice]" (Post admin share-alice "/__teamhub/api/workspaces/$WS/sharing") '"alice":"chat"'
Check "CASE 2 alice reads plaintext" (Post alice read-secret /api/workspaceFiles/read) 'BOB SECRET: budget 42'
# CASE 3-5
Check "CASE 3 ../ escape denied" (Post alice read-escape /api/workspaceFiles/read) '无权读取该工作区文件'
Check "CASE 4 absolute denied"   (Post alice read-absolute /api/workspaceFiles/read) '无权读取该工作区文件'
Check "CASE 5 traversal denied"  (Post alice read-traversal /api/workspaceFiles/read) '无权读取该工作区文件'
# CASE 6-7
Check "CASE 6 queue accepted"    (Post alice prompt-queue /api/session/prompt) '{"accepted":true}'
Check "CASE 7a interrupt denied" (Post alice prompt-interrupt /api/session/prompt) '共享会话仅支持排队发送消息'
Check "CASE 7b image denied"     (Post alice prompt-image /api/session/prompt) '成员仅支持已审核的纯文本会话请求'
Check "CASE 7c rename denied"    (Post alice rename-session /api/session/rename) '无权访问该会话或工作区'
# CASE 8
Post admin share-none "/__teamhub/api/workspaces/$WS/sharing" | Out-Null
Check "CASE 8a revoke -> read denied" (Post alice read-secret /api/workspaceFiles/read) '无权读取该工作区文件'
Check "CASE 8b revoke -> prompt denied" (Post alice prompt-queue /api/session/prompt) '无权访问该会话或工作区'
# CASE 9（多级权限：viewer 只读）
Post admin share-viewer "/__teamhub/api/workspaces/$WS/sharing" | Out-Null
Check "CASE 9a viewer reads file" (Post carol read-secret /api/workspaceFiles/read) 'BOB SECRET: budget 42'
Check "CASE 9b viewer prompt denied" (Post carol prompt-queue /api/session/prompt) '只读成员不能发送消息'
Post admin share-none "/__teamhub/api/workspaces/$WS/sharing" | Out-Null

Write-Host ""
if ($fail -eq 0) { Write-Host "REHEARSAL: all checks PASS" } else { Write-Host "REHEARSAL: $fail FAILED" }
exit $fail
