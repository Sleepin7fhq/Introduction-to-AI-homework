# Verify every command the demo script will print actually works, using curl.exe
# exactly as a student would type it. Prints a labelled transcript.
$ErrorActionPreference = "Continue"
$H = "http://127.0.0.1:3090"
$WS = "fcd6f438-6c45-4fb4-9dd2-b4178d12137a"
$sid = "session-5fac988a-a974-442b-a7e1-5a6d71e3d1ce"
# (run from the workspace root; no hard-coded path so the file stays ASCII-safe)

function Login($name, $pw, $jar) {
  curl.exe -s -c $jar -o NUL "$H/login"
  $code = curl.exe -s -b $jar -c $jar -o NUL -w "%{http_code}" `
    -d "next=/&username=$name&password=$pw" "$H/login"
  return $code
}

Write-Host "=== 1. login (expect 302 each) ==="
Write-Host ("  admin -> " + (Login "admin" "AdminPass!2026" "demo\admin.jar"))
Write-Host ("  alice -> " + (Login "alice" "AlicePass!2026" "demo\alice.jar"))
Write-Host ("  bob   -> " + (Login "bob" "BobPass!2026" "demo\bob.jar"))

Write-Host "`n=== 2. selftest (admin) ==="
curl.exe -s -b demo\admin.jar -H "content-type: application/json" -d "{}" "$H/__teamhub/api/selftest"

Write-Host "`n`n=== 3. alice reads bob's file WITHOUT share (expect deny) ==="
curl.exe -s -b demo\admin.jar -o NUL -H "content-type: application/json" `
  --data-binary "@demo/payloads/share-none.json" "$H/__teamhub/api/workspaces/$WS/sharing"
curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/read-secret.json" "$H/api/workspaceFiles/read"

Write-Host "`n`n=== 4. admin grants share (expect members:[alice]) ==="
curl.exe -s -b demo\admin.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/share-alice.json" "$H/__teamhub/api/workspaces/$WS/sharing"

Write-Host "`n`n=== 5. alice reads same file, now SHARED (expect plaintext) ==="
curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/read-secret.json" "$H/api/workspaceFiles/read"

Write-Host "`n`n=== 6. path escape attempts (expect 3x deny) ==="
foreach ($p in @("read-escape", "read-absolute", "read-traversal")) {
  Write-Host ("  --- " + $p)
  curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
    --data-binary "@demo/payloads/$p.json" "$H/api/workspaceFiles/read"
  Write-Host ""
}

Write-Host "`n=== 7. prompt variants ==="
foreach ($p in @("prompt-queue", "prompt-interrupt", "prompt-image", "rename-session")) {
  Write-Host ("  --- " + $p)
  curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
    --data-binary "@demo/payloads/$p.json" "$H/api/$((Get-Content "demo/payloads/$p.json" -Raw | ConvertFrom-Json).method)"
  Write-Host ""
}

Write-Host "`n=== 8. admin-only surfaces as alice (expect 403) ==="
Write-Host ("  GET /admin/            -> " + (curl.exe -s -o NUL -w "%{http_code}" -b demo\alice.jar "$H/admin/"))
Write-Host ("  GET /__teamhub/api/workspaces -> " + (curl.exe -s -b demo\alice.jar "$H/__teamhub/api/workspaces"))

Write-Host "`n=== 9. revoke share, then immediate retry (expect all deny) ==="
curl.exe -s -b demo\admin.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/share-none.json" "$H/__teamhub/api/workspaces/$WS/sharing"
Write-Host ""
curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/read-secret.json" "$H/api/workspaceFiles/read"
Write-Host ""
curl.exe -s -b demo\alice.jar -H "content-type: application/json" `
  --data-binary "@demo/payloads/prompt-queue.json" "$H/api/session/prompt"

Write-Host "`n`n=== 10. audit tail (expect policy.allowed / policy.denied / admin.workspace-shares) ==="
$audit = curl.exe -s -b demo\admin.jar "$H/__teamhub/api/audit?limit=8"
$audit | Out-File -Encoding utf8 demo\_audit-tmp.json
Get-Content demo\_audit-tmp.json -Encoding UTF8 -Raw | Write-Host

Write-Host "`n=== 11. gateway still alive after all of that ==="
curl.exe -s -b demo\admin.jar -H "content-type: application/json" -d "{}" "$H/__teamhub/api/selftest"
Write-Host ""
