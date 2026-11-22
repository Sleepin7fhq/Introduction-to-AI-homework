# DSH 局域网共享网关 —— 快速启动

收到这个包之后，一条命令就能跑起来。

## 0. 你需要什么

- Windows 10/11。**Node 现在可选**：可以先用系统 Node（>= 22，`node -v` 确认），
  也可以运行 `make-portable.cmd` 把便携 Node 内置到包里（推荐，之后完全不依赖系统 Node）。
  DSH 与网关的所有依赖都在包里，不需要联网安装（内置 Node 需联网下载一次）。
- 解压到一个目录（建议路径不含空格和中文，如 `C:\dsh-share\`；含中文路径也能跑，
  但 cmd 在中文路径下的行为不可控，别给自己找麻烦）。

## 0.5 可选：内置 Node（自包含）

双击 **`make-portable.cmd`**，自动下载 Node 官方便携包并解压到 `runtime\`。
完成后 `start-all` 会自动优先使用 `runtime\node.exe`，整套东西不再依赖系统 Node。

## 0.6 可选：安装成 setup.exe / 装到本机

两种方式任选：

1. **Inno Setup 打包成 setup.exe**：先跑 `make-portable.cmd` 内置 Node，再用 Inno Setup 6
   编译 `installer\setup.iss`，即可生成 `installer\DSH-Lan-Share-Setup.exe`。
   安装器会装到 `%LOCALAPPDATA%\DSHLanShare`，建开始菜单/桌面快捷方式 + 卸载项，
   装完自动启动网关。
2. **免 Inno 一键安装**（PowerShell）：
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File installer\install.ps1
   ```
   效果同上；卸载：控制面板 →「添加或删除程序」→ DSH 局域网共享网关，或
   `powershell -NoProfile -ExecutionPolicy Bypass -File installer\uninstall.ps1`。

## 1. 一键启动

双击包根目录的 **`start-all.cmd`**，或在 PowerShell 里执行：

```powershell
cd C:\dsh-share          # 换成你的解压目录
powershell -NoProfile -ExecutionPolicy Bypass -File start-all.ps1
```

脚本会自动：检查 Node 版本 → 归一化 config.json 的绝对路径（UTF-8 无 BOM）→
启动 DSH(3080) → 等待 token 出现 → 启动网关(3090) → 等待就绪 → 跑自检 → 打印登录地址。

成功标志（脚本末尾）：

```
[start-all] 启动完成！
  本机入口：http://127.0.0.1:3090/login
  局域网入口：http://192.168.x.x:3090/login
```

- **自动跳转**：启动成功（或网关已在运行）后，会自动打开默认浏览器到 `http://127.0.0.1:3090/login`，无需手输地址；用 `start-all.ps1 -NoBrowser` 可关闭自动跳转。
- **重复执行**：若网关已在运行，脚本会提示「网关已在运行」并直接退出（也会自动打开浏览器），不会崩溃。
- **停止**：运行 `stop-all.cmd`（两个进程都在后台隐藏运行，不要按 Ctrl+C 关窗口，否则上游会挂掉）。

## 2. 账号与首登

账号随包分发在 `hubhome\config.json`：

| 账号 | 初始密码 | 角色 |
|---|---|---|
| admin | AdminPass!2026 | admin |
| alice | AlicePass!2026 | member |
| bob | BobPass!2026 | member |

**所有账号首次登录都强制改密**（`mustChangePassword:true`）。真实部署务必改成强密码；
课堂演示可按提示改成同样的密码以保持文档一致。

## 3. 自检（可选）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File demo\rehearse.ps1
```

末行 `REHEARSAL: all checks PASS` = 环境健康，可以照
`report\DSH共享服务-课堂演示操作流程.docx` 演示。

## 4. 手工启动（排障用，等价于把 start-all 拆开）

```powershell
# 终端 1 —— DSH 上游（3080）
cd C:\dsh-share
cmd /c "probe\start-dsh.cmd"

# 终端 2 —— 网关（3090），等终端 1 出现 token 后再开
cd C:\dsh-share
cmd /c "probe\start-gateway.cmd"
```

> 顺序不能反：网关启动时会同步一次归属表。DSH 还没就绪就先起网关，会拿空表把
> 已有工作区当成新的重建（工作区 id 轮换，报「上游工作区已变更」）。

## 5. 用量与配额（Agent 治理）

Admin 控制台新增「用量」页：按用户记录 Agent 消息数、被拒次数，估算 token 与成本。

- 估算口径：input 按消息字符（每 4 字符 ≈ 1 token），output 按 2× 估算；成本为占位价（每百万 token 4 元）。
- 配额：每人每天 50 万 token（演示占位值，可在 `probe\hub-fix\src\usage-tracker.mjs` 修改），超额在面板标红。
- 记录文件：`hubhome\logs\usage.jsonl`；后续可接入 WS usage 帧做精确记账。

## 6. 会话转交与审计时间线

- Admin 控制台新增「时间线」页：把审计日志变成「谁在何时让 Agent 做了什么 / 被拦了什么 / 接力棒在谁手里」的故事视图。
- 会话转交：`POST /__teamhub/api/sessions/<会话id>/handoff`，body `{"holder":"成员名"}`——把接力棒交给一个有权访问该会话的成员（纯标记，不改变权限），审计记 `session.handoff`；`GET /__teamhub/api/sessions` 可看每个会话的当前 holder。

## 7. Agent 身份注入（轻量原型）

共享成员（非会话所有者）排队发消息时，网关会在纯文本最前面注入一行系统上下文：

> （系统注入：你正在为成员 X 服务，其角色是【协作成员/只读成员】；请按该角色的权限范围回答。）

- 会话所有者（原生身份）不注入；用户原文与权限守卫不变；`config.json` 里设 `"memberContextInjection": false` 可关闭。
- 注入行在模型实际运行时才会进入会话日志；队列未处理时不落日志（正常现象）。

## 常见坑速查
| 症状 | 修法 |
|---|---|
| 网关一直刷 `token unavailable` | 3080 没起来就先起了网关 → 停网关，确认 3080 LISTENING 后再启动；用 `probe\start-dsh.cmd` 启动，别用 PowerShell 重定向 |
| 网关刷 `DSH Web token exchange failed` | 手动 `node ... bin.js web` 起的 DSH 没把新 token 写进 `probe\dsh-web.log`（网关拿旧 token 交换被 401）→ 跑 `stop-all.cmd` 停干净，再 `start-all.cmd` 重新起（别手动起 DSH） |
| 别的目录/临时实例占着 3080 或 3090 | 跑 `stop-all.cmd`（会停掉任何跑 DSH/网关入口脚本的 node 进程）；仍占用就 `taskkill /F /IM node.exe` 后 `start-all.cmd` |
| 读文件报「上游工作区已变更」 | 工作区 id 轮换 → 按顺序重启两个进程 |
| 成员界面大量 403 | 只用 `probe\hub-fix` 这个网关目录，别换目录 |
| 连续登录失败被退避/锁定 | 每「账号+IP」5 次失败后指数退避（10 秒起，最长 15 分钟）；等退避结束，或换 IP |
| 刚建的会话成员进不去 | 已改为事件驱动，新建会话立即生效；若仍异常，重启网关强制同步归属表 |

## 安全边界与已知限制（照实宣讲，勿夸大）

- **权限模型两档可配置（chat / viewer）**：共享成员可被管理员设为「协作 chat」或「只读 viewer」。
  - chat（协作）：读工作区文件/会话历史 + 排队发送纯文本消息（`session/prompt` mode=queue + 纯文本）。
  - viewer（只读）：只能读文件/历史，不能发送任何消息。
  interrupt、图片/文件/引用块、重命名、设置等仍一律拒绝；更细的"审批/编辑"档未实现。
- **演示走 HTTP 明文**：登录 Cookie、密码、RPC 载荷都在局域网明文传输，任何能抓包的
  主机都可能截走会话 Cookie。仅用于教学演示，不可用于真实敏感数据。
- **安全边界在网关，3080 不可暴露**：DSH 上游只能绑定回环（不支持 0.0.0.0），且上游
  自身没有路径围栏——绕过网关直连 127.0.0.1:3080 可读到任意文件。对外只暴露 3090，
  绝不要用端口转发把 3080 暴露到局域网。
- **本工具不能替代 VPN**：它做的是「工作区级共享 + 纯文本消息」，不是加密隧道，也没有
  端到端加密。跨网段/公网访问仍需 VPN 或等效安全通道。

完整踩坑清单见 `report\使用说明.md`；设计原理与每条结论的证据，见
`report\DSH共享服务-验证报告.md`；本轮 P0/P1 修复记录见 `report\DSH共享服务-修复记录.md`。
