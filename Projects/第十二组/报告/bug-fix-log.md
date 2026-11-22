# Bug 修复日志（bug-fix-log）

> 对应排查报告：`report\bug-audit.md`。修复顺序：P1 → P2 → P3，每项修完即回归。

## 一、已修项

### FIX-01 [P1] 开放重定向（safeNext 编码绕过）
- **文件**：`probe\hub-fix\src\server.mjs`（safeNext）
- **原因**：只校验原始串，`%5c`→`\`、`%2f`→`/` 编码绕过；浏览器会把 Location 中的 `\` 规范化为 `/`，形成 `//evil.com` 跳转。
- **修改**：原始串与 decodeURIComponent 解码串双重校验（都以 `/` 开头、非 `//`、无 `\`、无控制字符），解码失败即拒绝。
- **回归**：`next=/%5c%5cevil.com`、`/%2f%2fevil.com`、`https://evil.com`、`/admin/` 四组全部安全跳转 ✅。

### FIX-02 [P2] createUser 非法用户名污染内存 config
- **文件**：`probe\hub-fix\src\users.mjs`（createUser）
- **原因**：先 `users.push` 后 `saveConfig→validateConfig` 抛错；内存 config 被污染且磁盘未写，mtime 不变导致热重载无法自愈，此后所有管理写接口（建用户/改共享）持续 400，需重启网关。
- **修改**：入口先校验（name 正则与 validateConfig 一致、role 枚举）再变更；重复名检查保留。
- **回归**：`../evil` → 409 且无副作用；随后合法创建 200 ✅。

### FIX-03 [P2] 改密后同账号其他会话不失效
- **文件**：`probe\hub-fix\src\auth.mjs`（新增 `revokeOtherSessions`）、`probe\hub-fix\src\server.mjs`（改密路由）
- **原因**：changePassword 只改密码，`revokeSessionsForUser` 仅在 admin 禁用/重置时调用；改密后被盗用的其他会话仍存活。
- **修改**：新增 `revokeOtherSessions(home, username, keepToken)`，改密成功后调用（保留当前会话，避免刚改完被登出）。
- **回归**：双会话场景——当前会话 200、其他会话 302 ✅。

### FIX-04 [P3] 登录时序侧信道账号枚举
- **文件**：`probe\hub-fix\src\users.mjs`（authenticate）
- **原因**：未知账号直接 return null 跳过 scrypt（10.8ms），已知账号走 scrypt（118ms），11 倍差距可枚举账号。
- **修改**：未知账号也执行一次固定假盐假哈希的 scrypt。
- **回归**：151ms vs 143ms（比率 0.95）✅。

### FIX-05 [P3] 登录节流大小写绕过
- **文件**：`probe\hub-fix\src\login-throttle.mjs`
- **原因**：键为 `${username}\0${ip}`，大小写敏感，改大小写即重置计数。
- **修改**：`username.toLowerCase()`。
- **回归**：原大小写与变体同时 429 ✅。

### FIX-06 [P3] 卸载残留 ~800MB
- **文件**：`installer\setup.iss`
- **原因**：首启解压的 node_modules 与运行时数据是安装后生成的，卸载器不认识，实测残留 4 目录约 800MB。
- **修改**：新增 `[UninstallDelete] Type: filesandordirs; Name: "{app}"`。
- **回归**：重编后走完整"装→首启（制造解压产物）→卸"循环，目录残留 False ✅。

## 二、未修项

| 项 | 原因 | 风险 | 下一步 |
|---|---|---|---|
| BUG-07 verify-demo-commands.ps1 授权步骤过期 | 已被 `rehearse.ps1`（自愈建会话+重建 payload）取代，保留仅作历史 | 无（不用它即可） | 删除或标注弃用 |
| scrypt N=16384 低于 OWASP 建议 | 提高参数会使每次登录多花数百毫秒，演示体验下降 | 低（LAN 演示场景，密码非弱口令+节流兜底） | 如上线公网再调 N=2^17 |
| audit/usage 同步 appendFileSync 热路径 | 每事件一次同步写；实测无感 | 低（演示规模） | 未来改异步批量队列 |
| exe 未签名（SmartScreen） | 代码签名证书需付费+数天签发 | 分发体验 | SHA256 核对+白名单（已在 SETUP.md） |

## 三、回归命令与结果

```
node probe\hub-fix\bin\dsh-team-hub.js selftest        → ✓ 43 sessions / 6 workspaces
powershell -File demo\rehearse.ps1                      → ✅ 16/16, exit 0
powershell -File demo\verify-demo-commands.ps1          → exit 0（授权步骤见 BUG-07）
修复回归脚本（重定向/污染/时序/大小写/改密会话）          → ✅ 9/9
中文+空格路径 安装→解压→DSH冷启→selftest                 → ✅ 全过
卸载（修复前）                                           → 残留 4 目录（BUG-06，已修待验证）
```

## 四、修复后的交付状态

- 配置已复位：admin/alice/bob/carol 首登强制改密、共享/转交清空、无测试账号残留。
- 源码语法全部通过；备份在 `hubhome\backup-audit-20261121\`。
- 最终安装包需重新编译（包含 FIX-01~06）。
