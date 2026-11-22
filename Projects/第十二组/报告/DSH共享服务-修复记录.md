# DSH 共享网关 P0/P1/P2-A 修复记录

> 维护者轮次：一轮安全与性能加固（P0/P1）+ 多级权限模型（P2-A）。
> 未删除审计日志，未把 3080 暴露到 0.0.0.0，未引入明文密码日志；
> `/workspaces/<id>/sharing` 的 `members` 字段向后兼容（旧数组→chat）。

## 一、变更文件与改动摘要

| 文件 | 改动 |
|---|---|
| `probe/hub-fix/src/passwords.mjs` | `scryptSync` → 异步 `crypto.scrypt`（回调包装），登录/改密不再阻塞事件循环 |
| `probe/hub-fix/src/users.mjs` | `createUser/resetPassword/changePassword/authenticate` 异步化 |
| `probe/hub-fix/src/cli.mjs`、`admin-api.mjs` | 调用点补 `await` |
| `probe/hub-fix/src/login-throttle.mjs` | **新增**：按「账号+IP」指数退避锁定（5 次失败 → 10s 起，最长 15 分钟） |
| `probe/hub-fix/src/auth.mjs` | `resolveSession` 改为内存缓存 + mtime 判定重载（消除每请求 `readFileSync`） |
| `probe/hub-fix/src/server.mjs` | 节流接入；异步 `authenticate/changePassword`；`rpcError` 写真实原因；按需归属刷新；撤销共享断流（`memberStreams` 注册表 + `closeMemberStreamsForWorkspace`）；启动先探 DSH 就绪再同步；`lastOwnershipSyncAt` + `/ownership/refresh` 端点；`/system` 增加同步信息 |
| `probe/hub-fix/src/policy.mjs` | `session/create` 立即写 `sessionWorkspace`（事件驱动）；`guardWorkspaceFileRead` 的 `existsSync/statSync` 改异步 `fs.promises.stat`，guard 链异步化 |
| `probe/hub-fix/src/compat.mjs` | `workspace/follow` 改为复用常驻流（增量合并 baseline/upsert/remove/order/archived/pinned，socket unref，保留 5s 超时） |
| `probe/hub-fix/admin-ui/app.js` | Admin 系统页显示归属表最后同步时间 + 「立即刷新」按钮 |
| `hubhome/config.json` | 4 个随包账号 `mustChangePassword:true` |
| `probe/lib-hub.mjs`、`demo/rehearse.ps1` | 适配首登强制改密（rehearse 补 UTF-8 BOM） |
| `start-all.ps1`、`start-all.cmd` | **新增**：一键启动（查 Node → 归一化路径 → 起 DSH → 等 token → 起网关 → 等就绪 → selftest → 打印入口） |
| `SETUP.md` | 收敛为「一条命令启动」+ 增加「安全边界与已知限制」诚实说明 |
| `probe/hub-fix/src/config.mjs`、`policy.mjs`、`admin-api.mjs`、`server.mjs` | 多级权限：`workspaceShares` 改为 `{工作区:{成员:角色}}`，新增 viewer（只读）/chat（协作）；旧数组自动迁移为 chat |
| `probe/hub-fix/admin-ui/share-state.js`、`app.js` | 共享对话框成员角色下拉（协作/只读）+ 列表显示角色 |
| `demo/rehearse.ps1`、`demo/payloads/share-viewer.json` | 新增 CASE 9 viewer 只读用例 |
| `probe/hub-fix/src/usage-tracker.mjs` | **新增**：Agent 用量记账（按网关用户归因，估算 token、成本、配额） |
| `probe/hub-fix/src/server.mjs`、`admin-ui/app.js`、`admin-ui/index.html` | `session/prompt` 记账钩子（含被拒尝试）+ Admin「用量」页 |
| `probe/hub-fix/src/config.mjs`、`server.mjs` | 会话转交：`sessionHolders` 配置 + `POST /__teamhub/api/sessions/<id>/handoff` + `GET /__teamhub/api/sessions` |
| `probe/hub-fix/admin-ui/app.js`、`index.html` | Admin「时间线」页（审计的讲故事视图：登录/发送请求/被拒/转交/调整共享） |
| `probe/hub-fix/src/policy.mjs`、`server.mjs`、`config.mjs` | Agent 身份注入：共享成员发消息时注入「你正在为成员 X 服务，角色【…】」（owner 不注入，可配置关闭） |
| `probe/hub-fix/src/policy.mjs` | 会话队列接口 `session/updateQueue` 放行（owner/chat 可用、viewer 拒、edit 仅纯文本）；模型页 `llm/listConfigurableProviders`/`credentials/describe` 成员安全空响应 |
| `probe/hub-fix/src/policy.mjs` | **P0 修复**：`session/page` 守卫与上游语义对齐——`throughSeq` 改为可选且允许 -1（此前成员历史加载必被拒，admin 正常，即「bob 收不到消息」） |
| `stop-all.ps1` | 按入口脚本（bin.js web / dsh-team-hub）停掉任何实例的 DSH/网关，防手动启动残留占端口 |

---

## 二、逐项「问题 — 修复 — 验收」

### P0-1 自动化安装/启动
- **问题**：安装要手工改三个绝对路径 + 两个进程严格按顺序启动 + PowerShell 写日志会带 BOM，重复执行会因端口占用直接崩溃。
- **修复**：新增 `start-all.cmd`（调用 `start-all.ps1`）：检查 Node 版本 → 归一化 config.json 路径（UTF-8 无 BOM）→ 起 DSH → 等 token → 起网关 → 等就绪 → 跑 selftest → 打印本机/局域网入口；重复执行检测到 3090 已监听则提示并退出 0。
- **验收**：`start-all.ps1` 在网关已运行时输出「网关已在运行」并退出 0；正常路径 selftest 通过。

### P0-2 事件驱动归属更新（消除 5 分钟滞后）
- **问题**：`session/create` 回调只写 `sessionOwner` 漏写 `sessionWorkspace`（policy.mjs:777），新会话要等 5 分钟轮询才进归属表，连 owner 读自己文件都被判「无权读取」。
- **修复**：`filterMemberResponse` 的 `session/create|fork` 分支立即把新会话挂到它的工作区；另在 `handleApiPost` 里，请求引用未知归属时按需刷新一次（2s 冷却），5 分钟兜底轮询保留。
- **验收**：新建会话 `session-ab6498b8…` 后**立即**读到 `BOB SECRET: budget 42`（不重启、不等 5 分钟）；rehearse 14/14 PASS。

### P0-3 登录节流 + 异步 scrypt + 首登强制改密
- **问题**：登录无频率限制且绑 0.0.0.0 + 固定弱默认密码且不强制改；`scryptSync` 阻塞可被登录打满。
- **修复**：新增 `login-throttle.mjs`（账号+IP 计数、指数退避、锁定写审计不记明文）；`scryptSync` 改异步；`config.json` 四账号 `mustChangePassword:true`；`lib-hub.mjs`/`rehearse.ps1` 适配改密流程。
- **验收**：5 次错误登录 401 → 第 6 次 429；锁定期内正确密码也 429；其他账号正确登录 302 不受影响；审计出现 `auth.login-failed`（failures/locked）与 `auth.login-throttled`（ip/retryAfterMs）；admin 正确登录 302 → `/change-password`。

### P0-4 错误信息带真实原因
- **问题**：所有自定义拒绝码被拍平成 `internal`，`details` 恒为 `{}`，排障只能靠猜。
- **修复**：`rpcError` 把真实原因写入 `details.reason`（线上 `code` 仍为 `internal` 兼容 DSH 客户端）；上游错误映射带 `upstream:<code>`；WS 快照拒绝帧带原因。
- **验收**：未共享读文件返回 `{"code":"internal","message":"无权读取该工作区文件","details":{"reason":"forbidden: 无权读取该工作区文件"}}`。

### P1-5 撤销共享主动断开 WebSocket
- **问题**：撤销共享后数据层失效但连接保持 `readyState=1`（发现 C）。
- **修复**：新增 `context.memberStreams` 连接注册表；`setWorkspaceShares` 后计算被移除成员，`closeMemberStreamsForWorkspace` 主动关闭其 `session/follow` 流（发错误帧 + 从流表移除）。
- **验收**：alice 开着 bob 会话的 session/follow 时撤销共享，立即收到 `{"type":"error","streamId":"s1","error":{"code":"internal","message":"共享已撤销","details":{"reason":"share-revoked"}}}`；重连被 `guardRemoteClientFrame` 的 `canAccessSession` 拒绝（rehearse CASE 8 佐证）。

### P1-6 热路径性能
- **问题**：`resolveSession` 每请求 `readFileSync`；`guardWorkspaceFileRead` 同步 fs；每次刷新新开 `workspace/follow` WS；启动顺序靠人肉保证（先 DSH 后网关）。
- **修复**：会话内存缓存 + mtime 重载；guard 的 `existsSync/statSync` 改 `fs.promises.stat`（guard 链异步化）；`workspace/follow` 复用一条常驻流（增量合并 + socket unref + 5s 超时）；启动先 `cookieHeader()` 探 DSH 就绪（30s 内）再首次同步。
- **验收**：selftest 通过；CLI selftest 267ms 正常退出（常驻流 unref 后不再挂起）；`/ownership/refresh` 复用缓存（`ok:true`）；启动顺序不再依赖人肉保证。

### P1-7 Admin 控制台显示同步状态
- **问题**：5 分钟滞后是暗坑，Admin 看不到归属表同步情况。
- **修复**：`/system` 增加 `ownershipLastSync/ownershipSessions/ownershipWorkspaces`；新增 `POST /__teamhub/api/ownership/refresh`；Admin「系统」页显示最后同步时间 + 「立即刷新」按钮。
- **验收**：`/system` 返回同步时间；`/ownership/refresh` 返回 `{"ok":true,"lastSync":…,"sessions":3,"workspaces":3}`；点击按钮即时刷新并回显结果。

### P1-8 文档诚实说明
- **问题**：文档宣称权限模型「可配置多级」，与实测不符。
- **修复**：SETUP.md 增加「安全边界与已知限制」：固定单档「排队纯文本」、HTTP 明文风险、边界在网关/3080 不可暴露、不能替代 VPN。
- **验收**：文档与实测一致，不夸大。

### P2-A 多级权限模型（chat / viewer）
- **问题**：权限模型只有一档——共享成员要么「能排队发纯文本」要么「完全不能」，没有 read/write 分级（P1-8 已如实记录）。
- **修复**：`workspaceShares` 从 `{工作区:["alice"]}` 升级为 `{工作区:{"alice":"chat","carol":"viewer"}}`；`policy.mjs` 新增 `memberRole`/`canChatSession`，`session/prompt` 写路径加角色守卫（viewer 只读不能发消息，纯收紧、不削弱安全）；`admin-api.mjs` 的 `setWorkspaceShares` 兼容旧数组（自动按 chat）与新对象；admin 面板加「协作/只读」角色下拉；`config.mjs` 加载时自动迁移旧格式。
- **验收**：旧数组格式→chat（向后兼容）；chat 能读+发；viewer 能读+发消息被拒（「只读成员不能发送消息」）；撤销后拒读。端到端 5/5，rehearse 扩展为 16/16（新增 CASE 9a/9b）。

### P2-B Agent 用量配额与成本治理
- **问题**：多用户共享一台 Agent，但谁用了多少 token、花了多少钱、谁在被拒，完全没有账本——"白嫖一个 key"的叙事。
- **修复**：新增 `usage-tracker.mjs`，在 `session/prompt` 提交时按网关用户记账（input 按字符估算每 4 字符≈1 token，output 按 2× 估算，被拒尝试记 denied）；记录到 `hubhome\logs\usage.jsonl`；Admin 新增「用量」页（每人每日消息数/被拒/token/估成本/配额超额标红）；`GET /__teamhub/api/usage?days=N` 对外。
- **验收**：chat 发 2 条 + viewer 被拒 1 条 → `/usage` 返回 `{prompts:2, denied:1, inputTokens:11, outputTokens:16}`（估算与手算一致）；rehearse 16/16 不受影响。

### P2-C 会话转交与审计时间线（协作故事线）
- **问题**：共享约等于"各自排队发消息"，没有"接力"与"全局视角"——演示缺乏故事性（"登录进去聊天"）。
- **修复**：config 新增 `sessionHolders`；`POST /__teamhub/api/sessions/<id>/handoff`（body `{holder}`，校验接棒人是有权访问的已启用成员，纯标记不改变权限）；`GET /__teamhub/api/sessions` 返回每会话 owner/holder；审计记 `session.handoff`；Admin 新增「时间线」页（把审计翻译成"谁在何时让 Agent 做了什么、被拦了什么、棒交给了谁"）。
- **验收**：admin 转交给 alice → 响应 `{holder:"alice",at:…}`，`/sessions` 显示 `holder:"alice"`，审计出现 `session.handoff`；非法接棒人 400；rehearse 16/16 不受影响。

### P2-D Agent 身份注入（轻量原型）
- **问题**：共享成员用的是同一个无状态 Agent，Agent 不知道"现在在为谁服务"——多用户 AI 的身份问题没有落点。
- **修复**：`policy.mjs` 新增纯函数 `injectMemberContext`：共享成员（非 owner）的 `session/prompt` 在转发上游前，于纯文本最前面注入「（系统注入：你正在为成员 X 服务，其角色是【协作成员/只读成员】；请按该角色的权限范围回答。）」；owner 不注入；守卫与用户原文不动；`config.memberContextInjection:false` 可关闭。
- **验收**：单测 5 例全过（chat/viewer 标签正确、owner 跳过、非 prompt 跳过、非法内容跳过）；临时调试钩子实证转发内容 = `[系统注入行, 用户原文]`（已移除）；prompt 仍 `accepted:true`；rehearse 16/16。注：注入行在模型实际运行时才进入会话日志（队列未处理不落日志）。

---

## 三、测试命令与结果

```powershell
# 语法检查（全部 OK）
node --check passwords.mjs; node --check users.mjs; node --check cli.mjs
node --check admin-api.mjs; node --check server.mjs; node --check policy.mjs
node --check login-throttle.mjs; node --check auth.mjs; node --check compat.mjs

# 异步 scrypt 往返（hash 128 位、正确 true、错误 false）
node --input-type=module -e "import {hashPassword,verifyPassword} from './passwords.mjs'; ..."

# 兼容性自检（session/list + workspace/follow）
node probe\hub-fix\bin\dsh-team-hub.js selftest     # ✓ 3 sessions / 3 workspaces，267ms 退出

# 全量回归
powershell -NoProfile -ExecutionPolicy Bypass -File demo\rehearse.ps1   # 16/16 PASS
```

| 验收项 | 结果 |
|---|---|
| 语法检查（9 个 JS 文件） | ✅ 全通过 |
| 异步 scrypt 往返 | ✅ 正确/错误判定正确 |
| selftest（session/list + workspace/follow） | ✅ 通过，正常退出 |
| rehearse 16 项 | ✅ all checks PASS |
| 多级权限（chat 读+发 / viewer 读+拒发 / 旧数组→chat） | ✅ 端到端 5/5 |
| 事件驱动（新建会话立即可读） | ✅ `BOB SECRET: budget 42` |
| 登录节流（5→429、审计、无明文） | ✅ |
| 首登强制改密（302 → /change-password） | ✅ |
| 错误 details（reason 真实原因） | ✅ |
| 撤销共享断流（error 帧 share-revoked） | ✅ |
| /system + /ownership/refresh | ✅ |
| start-all 重复执行 | ✅ 提示并退出 0 |

---

## 四、未完成项与建议下一步

1. **`remote-stream-policy.mjs` 仍有 5 处流式错误帧 `details:{}`**（`session/follow`、`$events` 流内部的拒绝路径）。本次只改了 RPC 主路径，建议后续统一。
2. **`canAccessPath`/`ownerOfPath` 内的 `realpathSync` 仍为同步**：它们被 `filterMemberResponse`、`remote-stream-policy.mjs` 等多个同步调用方共享，整体异步化改动面大，本次只把 `guardWorkspaceFileRead` 的直接 `existsSync/statSync` 异步化。建议后续做一次「路径鉴权层整体异步化」。
3. **`workspace/follow` 常驻流的增量正确性**：已实现 baseline/upsert/remove/order/archived/pinned 合并，但缺少针对「流中断期间漏帧」的强一致校验（当前失败即重建 + 重拉 baseline）。建议加 seq/游标校验。
4. **docx 未更新**：`report\DSH共享服务-课堂演示操作流程.docx` 的登录/改密步骤还是旧版，需要时用 office-docx 重新生成。
5. **默认密码仍随包分发**（`AdminPass!2026` 等）：已用「首登强制改密 + 登录节流」双重缓解，但更彻底的做法是安装时随机生成。

---

## 五、保持不变的安全底座（未削弱）

- scrypt（N=16384）加盐 + `timingSafeEqual`；256-bit 会话 token + `HttpOnly; SameSite=Lax`。
- 路径围栏（`guardWorkspaceFileRead`：`path.isAbsolute` + realpath 前缀校验 + 响应路径复核）。
- 配置校验（用户名正则、upstream 仅限回环无凭据、workspaceShares 校验、原型污染防护）。
- 审计日志（登录/节流/策略拒绝/撤销断流等均记录，redact 掉 password/token 键）。
- 3080 仍只绑回环；对外仅 3090。
