# DSH 多人共享网关系统化 Bug 排查报告（bug-audit）

> 日期：2026-11-21 ｜ 环境：Windows 11、Node v24.16.0（内置）、DSH 0.2.2-rc.1、网关 probe\hub-fix ｜ 服务：源码实例（3080/3090）
> 方法：先读源码列攻击面 → 独立测试账号（audit9/audit2）与临时目录动态测试 → 按 A/B/C 分类 → P0→P3 修复与回归。

## 一、排查范围与方法

- **范围**：认证与会话、权限与路径、归属同步与并发、WebSocket、节流与 DoS、错误与信息泄露、安装与启动、配置与前端、selftest/doctor/rehearse。
- **方法**：每个攻击面先读实现（server.mjs / policy.mjs / users.mjs / auth.mjs / passwords.mjs / login-throttle.mjs / config.mjs / admin-api.mjs / dsh-browser-auth.mjs / remote-stream-policy.mjs / setup.iss / start-all.ps1），再写独立脚本动态验证；修复前后各跑一次回归。
- **备份**：修复前备份 `hubhome\config.json`、`sessions.json` → `hubhome\backup-audit-20261121\`。

## 二、真实模型 API 调用记录

| # | 目的 | 次数 | 结果 |
|---|---|---|---|
| 1 | 验证"成员 LLM 消息链路"（session/page 修复轮，上一轮排查） | 1（最短消息「回个好」） | 确认成员 WS 流收到完整回复帧、修复后历史可见 |
| 2-∞ | 本轮审计 | **0** | 全部用本地 mock/测试账号/临时目录/临时端口验证，未再调用 |

**总调用：1 次**（本轮 0 次）。所有权限/安全断言均不依赖模型。

## 三、Bug 清单（去重）

| ID | 级别 | 类别 | 位置 | A/B/C | 状态 |
|---|---|---|---|---|---|
| BUG-01 | P1 | 开放重定向 | server.mjs `safeNext` | A 复现 | ✅ 已修 |
| BUG-02 | P2 | 配置污染 | users.mjs `createUser`（先 push 后校验） | A 复现 | ✅ 已修 |
| BUG-03 | P2 | 会话失效 | 改密路由未撤销同账号其他会话 | A 复现 | ✅ 已修 |
| BUG-04 | P3 | 账号枚举 | users.mjs `authenticate` 未知账号跳过 scrypt | A 复现 | ✅ 已修 |
| BUG-05 | P3 | 节流绕过 | login-throttle.mjs 键大小写敏感 | A 复现 | ✅ 已修 |
| BUG-06 | P3 | 卸载残留 | setup.iss 无 [UninstallDelete]，残留 ~800MB | A 复现 | ✅ 已修（待重编后回归） |
| BUG-07 | P3 | 遗留测试脚本 | verify-demo-commands.ps1 用旧 payload 不自愈 | A 复现 | 未修（被 rehearse 取代） |

### BUG-01 [P1] 开放重定向（已修）
- **复现**：登录 `next=/%5c%5cevil.com` 或 `next=/%2f%2fevil.com` → Location 原样回显；浏览器会把解码后的 `\` 规范化为 `/`，跳转到 `//evil.com`。
- **证据**：`Location: /%5c%5cevil.com`（HTTP 302 实测）。
- **修复**：safeNext 对原始串与 decodeURIComponent 解码串双重校验。
- **回归**：4 组 next 全部安全（PASS）。

### BUG-02 [P2] 非法用户名污染内存 config（已修）
- **复现**：admin 创建用户 `name:"../evil"` → 409；此后**所有**管理写接口（建用户、改共享）持续 400「非法用户名：../evil」，直到重启网关。
- **根因**：`createUser` 先 `users.push` 再 `saveConfig` 校验，抛错后内存 config 已污染且磁盘未写（mtime 未变，热重载救不回）。
- **修复**：createUser 入口先校验（与 validateConfig 同 regex）再变更。
- **回归**：`../evil` 409 且无副作用，随后合法创建 200（PASS）。

### BUG-03 [P2] 改密后旧会话不失效（已修）
- **复现**：同一账号开两个会话，会话 A 改密后，会话 B 的 cookie 仍可访问。
- **修复**：auth.mjs 新增 `revokeOtherSessions(home, user, keepToken)`，改密路由调用（保留当前会话）。
- **回归**：当前会话 200、其他会话 302（PASS）。

### BUG-04 [P3] 登录时序侧信道枚举（已修）
- **复现**：未知账号均值 10.8ms vs 已知账号 118.2ms（11 倍差距）。
- **修复**：未知账号也执行一次固定假盐假哈希的 scrypt。
- **回归**：151ms vs 143ms（比率 0.95，PASS）。

### BUG-05 [P3] 节流大小写绕过（已修）
- **复现**：`AuditCase1` 连错 5 次锁 429，改 `auditcase1` 立刻恢复 401。
- **修复**：节流键 `username.toLowerCase()`。
- **回归**：原大小写与变体同时 429（PASS）。

### BUG-06 [P3] 卸载残留 ~800MB（已修，待安装包回归）
- **复现**：卸载后残留 `alt\node_modules`（首启解压）、`hubhome`、`probe`、`runtime` 四目录。
- **修复**：setup.iss 增加 `[UninstallDelete] Type: filesandordirs; Name: "{app}"`。
- **状态**：需重编译后走一轮装→卸验证（本轮未重装验证，未验证）。

### BUG-07 [P3] verify-demo-commands.ps1 授权步骤过期（未修）
- **复现**：脚本内"授权→读文件"步骤因 payload 会话 id 过期报「上游工作区已变更」，后续断言全变成"拒绝但原因不符"。
- **处理**：该脚本已被 `rehearse.ps1`（自愈建会话+重建 payload）取代，保留仅作历史；不建议再使用，不修。

## 四、C 类（已检查未发现问题）清单

| 面 | 结论 |
|---|---|
| 路径围栏：`../`、编码 `%2e%2e`、反斜杠、UNC、盘符绝对路径、中文+空格文件名 | 全部正确拒绝/放行（实测） |
| 符号链接指向外部 | B 类（创建 symlink 需管理员权限未复现）；代码层 `canAccessPath` 以 realpath 围栏兜底 |
| 原型污染：`__proto__`/`constructor` 共享键 | 静默丢弃或拒绝，config.json 无污染（实测） |
| CSRF：admin API 跨源 POST | 403「cross-origin admin request denied」（实测） |
| Cookie：HttpOnly、SameSite=Lax、Path=/ | 实测 Set-Cookie 三属性齐全 |
| 登出失效 | 登出后旧 cookie 302（实测） |
| XFF 伪造绕节流 | 无效，按 socket IP 计数（实测 6 次变 IP 仍 429） |
| token 熵 | `crypto.randomBytes(32)` base64url（256 位） |
| 密码校验 | scrypt N=16384/r=8/p=1 异步 + timingSafeEqual |
| 首登改密 current/next、新密码 ≥8 | 实测（17/17 账号流程） |
| 3080 仅回环 | 实测 127.0.0.1:3080，LAN 访问 000 |
| 上游响应重定向消毒 | proxyRequest 拦截跨域/带 token 的 Location |
| 静态资源 /admin 路径穿越 | 403（实测） |
| 并发 session/create ×8、并发登录 ×10 | 全部成功，sessions.json 完整可解析（实测） |
| 事件驱动归属 | 新会话立即读（实测） |
| WS 撤销主动关闭 + 重连拒绝 | share-revoked 错误帧实测；重连无流（静默拒绝） |
| 畸形 JSON/未知路由错误响应 | 无堆栈、无路径泄露（实测） |
| 中文+空格安装路径 | 安装→解压→DSH 冷启→selftest 全过（实测） |
| 端口占用/重复启动 | 「网关已在运行」提示（实测） |

## 五、B 类（静态审计可疑但未动态复现）

| 项 | 疑点 | 为何未复现 |
|---|---|---|
| 符号链接越界 | 需验证 realpath 围栏 | 创建符号链接需管理员权限，沙箱内失败；静态确认 `canAccessPath` 对 candidate 做 `realpathSync` 后与 workspacePath 比对，可兜底 |
| audit/usage 热路径同步写 IO | appendFileSync 每事件一次 | 代码级审查确认；实测登录/断言无卡顿，未做吞吐量化 |
| 多机并发 | WS 上限 50、HTTP 无显式限流 | 无第二台机器；单机并发（8 会话/10 登录）通过 |
| SmartScreen 实弹 | 未签名 exe 被拦 | 本地产物无 MOTW 不触发；下载场景的处理已写 SETUP.md（SHA256 核对+白名单） |
| scrypt 参数 N=16384 | 略低于 OWASP 交互式建议 2^17 | 异步不阻塞事件循环（已确认）；升级参数会使登录变慢，演示权衡，暂不改 |

## 六、无法验证项及缺什么条件

- SmartScreen 真实弹窗：需带 MOTW 的下载渠道 + 云端判读。
- 符号链接攻击：需管理员权限建链。
- 多机并发/网络级攻击：需第二台物理机。
- 卸载残留修复（BUG-06）：需重编译安装包后走完整装→卸循环。
- 真实模型下的 Agent 行为全链路：已用 1 次最小调用验证关键链路（成员收消息+历史），其余场景为省 key 未再调用。

## 七、测试命令汇总与统计

| 命令/脚本 | 结果 |
|---|---|
| `node probe\hub-fix\bin\dsh-team-hub.js selftest` | ✓ 43 sessions / 6 workspaces |
| `demo\rehearse.ps1`（16 断言） | ✅ 16/16，exit 0 |
| `demo\verify-demo-commands.ps1` | exit 0（授权步骤因旧 payload 报"上游工作区已变更"，见 BUG-07） |
| 审计批次1（重定向/枚举/节流/登出/Cookie/CSRF/错误泄露） | PASS 8 / 发现 4 |
| 审计批次2（路径/污染/用户名校验） | PASS 6 / 发现 1（BUG-02） |
| 审计批次3（并发/WS） | PASS 4；WS 两项因 BUG-02 污染失败，修复后重测 PASS |
| 修复回归（5 项 + 补测） | ✅ 9/9 |
| 中文+空格路径安装/启动/卸载 | 安装✓ 启动✓ 卸载残留（BUG-06） |

**总计**：A 类复现 7 个（P1×1、P2×2、P3×4），已修 6 个、遗留脚本 1 个不修；C 类 25 组；B 类 5 项。
