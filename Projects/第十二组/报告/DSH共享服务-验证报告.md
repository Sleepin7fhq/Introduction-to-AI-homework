# DSH 局域网共享服务 — 验证报告

**实测环境**：Windows 11 家庭版 / Windows NT 10.0.26200.0 · Windows PowerShell **5.1**.26100.9818（Desktop，**不是 PS7**）· Node.js **v24.22.1**
**被测栈**：`@deepseek-ai/dsh` **0.2.2-rc.1**（commit `c59d10a`）+ `dsh-team-hub` **0.3.3**（已打两处 Windows 补丁）
**工作区**：`C:\Users\37842\Desktop\dsh联机`
**实测日期**：2026-11-19
**结论适用范围**：所有"通过"均在上述机器上实际跑出并留有原始输出；凡未实测的一律标注「未实测」或「源码推断」。

---

## 0. 一页结论

方案能跑通，但**方案原文有三处与技术事实不符**，本报告按"文档说 X / 实测 Y / 原因 Z"逐条纠正：

| # | 方案/文档的说法 | 实测结果 | 证据 |
|---|---|---|---|
| 1 | 「`--host 0.0.0.0` 被 DSH 明确拒绝，DSH 只能回环启动，对外暴露必须靠网关，这是方案的地基」 | DSH 拒绝的**只是通配地址**；绑具体 LAN IP 完全可行：`--host 10.198.103.170` 启动成功并 LISTENING | §5.1 |
| 2 | 「写入是可配置的多级」 | 网关是**固定单档**：唯一写操作是"排队纯文本"，`mode=interrupt` 被硬拒；材料自带的"多级"来自官方实验包 `dsh-experimental-liveshare` | §4.3、§5.2 |
| 3 | 官方 `experimental-liveshare` 因"缺 Relay 用不了" | 它的 README 明确要求**另外部署一个 Liveshare server**（OAuth/数据库/路由都不在包内），`view`/`write` 两档确实存在，但无 server 就是死码 | §4.3 |

**网关的必要性论证要换**：不是"DSH 到不了局域网"，而是**DSH 没有身份概念**——一个 token URL 换一个 cookie，拿到 cookie 的人就是 Host 本身（能读 `C:/Windows/win.ini`）。网关提供的是身份、隔离、策略与审计，不是可达性。见 §5.1 实测。

**另外送三个「文档没写」的实测发现**（全部有原始输出）：

| 发现 | 一句话 | 演示价值 | 出处 |
|---|---|---|---|
| A | 新建会话进不了归属表，最长滞后 **5 分钟**（网关只在启动时与每 5 分钟刷新一次） | "看起来配好了但成员进不去"的头号误判源 | §5.3 |
| B | **上游 DSH 自己没有任何路径围栏**——绕过网关直连 3080，`C:/Windows/win.ini` 与 `../alice/alice-notes.txt` 全部 200 带出内容 | "网关是唯一安全边界"的硬证据 | §5.4 |
| C | 撤销共享后 **WebSocket 不关闭**：socket 保持 OPEN，只是后续帧变成 `error: stream unavailable` | "数据层立刻失效，连接层不立刻断开" | §5.5 |
| D | **一个畸形 JSON 就能杀死整个网关进程**（Admin API 的 `JSON.parse` 在 try 之外 + 缺 `await`）——上游原版缺陷，已修 | 现场演示"为什么必须用文件传 JSON" | §6.5 |

**8 阶段状态一览**（详见 §4）：

| 阶段 | 判据 | 结果 |
|---|---|---|
| 1 环境准备 | 3080 打印 token URL、3090 起、两端 selftest 通过 | ✅ |
| 2 单机跑通 | admin 进 `/admin/`；`/` 完整无 403（79 条 plugin URL 全 200） | ✅ |
| 3 局域网多账号 | 三个网卡地址 `GET /login` 全 200，alice 可登录 | ✅ |
| 4 权限配置 | 共享后 `members:["alice"]` | ✅ |
| 5 安全边界 | 8 用例 + 3 发现全部跑出预期 | ✅ |
| 6 文档撰写 | 本报告 + 演示 docx（18 页 / 11 表，三项机器校验） | ✅ |
| 7 演示准备 | 文档命令原样重跑 14 条断言全绿、命令层 1.6 秒、分镜 790 秒 | ✅ |
| 8 答辩交付 | 8 条预设问答，每条挂源码行号 | ✅ |

---

## 1. 环境与版本

### 1.1 实测环境

| 项 | 值 | 证据来源 |
|---|---|---|
| 操作系统 | `Microsoft Windows NT 10.0.26200.0` | `[System.Environment]::OSVersion.VersionString` 实际输出 |
| Shell | Windows PowerShell **5.1**.26100.9818，`PSEdition=Desktop` | `$PSVersionTable` 实际输出 |
| Node.js | v24.22.1 | `node -v` 实际输出 |
| DSH | `@deepseek-ai/dsh` 0.2.2-rc.1，commit `c59d10a`，浏览器 rev `0a8a93d37743` | 安装目录 `alt\node_modules\@deepseek-ai\dsh\package.json`；rev 来自 HTML 内 `__DSH_BOOT__` |
| 网关 | `dsh-team-hub` 0.3.3 | `probe\hub-fix\package.json` |

**注意**：任务书称运行环境是 "PowerShell 7"，实测为 **5.1**。此差异直接导致了下文 §6.1 的日志编码缺陷，是本项目最耗时的坑，必须记入缺陷清单。

### 1.2 网关在 npm 上的发布与维护状态

`npm view dsh-team-hub version dist-tags time maintainers` 实际输出：

```
version = '0.3.3'
dist-tags = { latest: '0.3.3' }
time = {
  created: '2026-08-19T04:50:04.215Z',
  modified: '2026-10-22T13:45:56.267Z',
  '0.1.0': '2026-08-19T04:50:04.549Z',
  ...
  '0.2.11': '2026-10-16T08:04:27.973Z',
  '0.3.0': '2026-10-19T13:59:48.277Z',
  '0.3.1': '2026-10-20T02:29:14.820Z',
  '0.3.2': '2026-10-22T13:43:06.689Z',
  '0.3.3': '2026-10-22T13:45:55.321Z'
}
maintainers = 'zhoujianbin <building412@126.com>'
```

- 首发 2026-08-19，最新 0.3.3 发布于 **2026-10-22**，共 17 个版本。
- 单维护者（`zhoujianbin`），仓库 `github.com/zhoujianbin/dsh-team-hub`，MIT。
- **维护状态判定**：近一个月内仍有发布（0.3.0→0.3.3 集中在 10-19~10-22），属于**活跃但单点**。CHANGELOG 里 0.3.3 的说明是"0.3.2 手工发布早于 workflow，0.3.3 才是规范发布，无功能变化"——即 0.3.2/0.3.3 同源。
- **证据来源**：npm registry 实际查询输出。GitHub 仓库的 star/issue 数**无法核验**（本次未联网抓取网页）。

---

## 2. 部署拓扑

```
   ┌──────────────┐        ┌──────────────────────────┐        ┌─────────────────────┐
   │  浏览器      │        │  dsh-team-hub 网关       │        │  DSH Web 上游       │
   │ (局域网内    │──HTTP──▶  0.0.0.0:3090            │──HTTP──▶  127.0.0.1:3080   │
   │  任意设备)   │◀──WS────│  · 登录/会话/角色        │◀──WS────│  · 单身份 Host      │
   │              │        │  · RPC 白名单 + 归属校验 │        │  · 无路径围栏       │
   │              │        │  · 审计 JSONL            │        │  · 只认 token/cookie│
   └──────────────┘        └──────────────────────────┘        └─────────────────────┘
                                  │                                     ▲
                                  │ 读 token（0600 日志）               │ 启动时打印
                                  └─────────────────────────────────────┘
```

| 端口 | 绑定 | 用途 | 对外？ |
|---|---|---|---|
| 3080 | `127.0.0.1` | DSH Web 上游 | **否**（仅回环） |
| 3090 | `0.0.0.0` | 网关 HTTP/WS 入口 | 是（可信局域网） |
| 3090 `/admin` | 同上 | Admin 控制台 HTML | 是，但仅 admin 角色可进（成员 403） |
| 3090 `/__teamhub/api/...` | 同上 | Admin API / selftest / audit / workspaces | 同上 |

**为什么上游必须回环**：网关需要从 DSH 的启动日志里读一次性 token（`process.getuid` 校验 0600），并把 cookie 留在服务端。若上游可被外部直连，成员可绕过网关直接持 Host 身份（§5.1 已证）。

**关键更正**：拓扑里 3080 必须绑 `127.0.0.1` 是**部署选择**，不是 DSH 的技术限制。见 §5.1。

---

## 3. 权限模型对照表（方案声称 vs 文档 vs 实测）

| 能力 | 方案声称 | README/源码实际声明 | 实测结果 |
|---|---|---|---|
| 查看工作区与历史会话 | 支持 | 是（README 表格首行） | ✅ ALLOW |
| 预览工作区文本文件 | 支持 | 是（`workspaceFiles/read`） | ✅ ALLOW，返回明文 |
| 发送消息 | 「写入可配置多级」 | 固定：**排队纯文本**一档 | ⚠️ ALLOW 但仅 `mode=queue` + 纯文本 |
| 中断正在运行的回合 | 可配置 | 否（README 明确"否"） | ✅ DENY `共享会话仅支持排队发送消息` |
| 图片/文件附件 | 方案未细化 | 否（README："只接受已审核的纯文本"） | ✅ DENY `成员仅支持已审核的纯文本会话请求` |
| 审批工具请求 | 无 | 否 | 未实测（需真实审批弹窗） |
| 重命名/创建/删除/归档/固定会话 | 无 | 否 | ✅ DENY（`session/rename` 等 3 项实测均拒） |
| 创建工作区 | 无 | 否（不在 Member 白名单） | ✅ DENY `方法 workspace/create 不在 Member 白名单` |
| 进 Admin 控制台 | 无 | 否（admin only） | ✅ 成员 403 `admin only` |

### 3.1 核心落差：所谓"写入可配置多级"在哪

- **网关（`dsh-team-hub` 0.3.3）**：`probe\hub-fix\src\policy.mjs:423-460` 的 `session/prompt` 分支是硬编码单档；`mode !== "queue"` 直接返回 `共享会话仅支持排队发送消息`。没有任何配置项能把它放宽。README 的表格与之完全一致。
- **官方实验包（`@deepseek-ai/dsh-experimental-liveshare`，本机已随 DSH 安装）**：它的 README 原文写 "The owner chooses viewing or bounded writing" / "unavailable, read-only, or writable"，即**三档**（不可用/只读/可写）。这才是"可配置多级"的真实出处。
- **为什么它用不了**：同 README："The separately deployed Liveshare server authenticates viewers and transports their requests; its OAuth, database, routing, and deployment implementation are not part of this package." 且 "The default Web profile excludes it" —— 必须手改 `cordis.patch.yml` 启用，并自行部署一台 Liveshare server。本机没有该 server，也没有其代码。
- **结论**：方案里"写入可配置多级"如果指网关，是与实现不符；如果指官方 liveshare，则缺一台服务端。**报告里应写：网关能力固定单档，多档能力属官方实验特性且需自建服务端，本次未部署。**

---

## 4. 8 阶段执行记录

### 阶段 1 环境准备 — ✅ 通过

**启动上游 DSH**（必须用 `cmd` 字节重定向，原因见 §6.1）：

```powershell
cmd /c "cd /d C:\Users\37842\Desktop\dsh联机\alt && set DSH_HOME=C:\Users\37842\Desktop\dsh联机\alt\dshhome && node .\node_modules\@deepseek-ai\dsh\lib\bin.js web --port 3080 --no-open > C:\Users\37842\Desktop\dsh联机\probe\dsh-web.log 2> C:\Users\37842\Desktop\dsh联机\probe\dsh-web-err.log"
```

原始输出（`probe\dsh-web.log`，82 字节纯 UTF-8，以 `\n` 结尾）：

```
dsh web: http://127.0.0.1:3080/?token=nHnmd-2Xq_jPS2WhTsRFfnOIb3NTJKRc_9l9oIAuGYw
```

等价且更易复用的写法（`probe\start-dsh.cmd`，已实测可用，演示脚本采用此形式）：

```bat
@echo off
setlocal
cd /d C:\Users\37842\Desktop\dsh联机\alt
set DSH_HOME=C:\Users\37842\Desktop\dsh联机\alt\dshhome
node .\node_modules\@deepseek-ai\dsh\lib\bin.js web --port 3080 --no-open > C:\Users\37842\Desktop\dsh联机\probe\dsh-web.log 2> C:\Users\37842\Desktop\dsh联机\probe\dsh-web-err.log
```

调用：`cmd /c "C:\Users\37842\Desktop\dsh联机\probe\start-dsh.cmd"`。两种写法的共同点是**由 cmd 而非 PowerShell 做重定向**，从而绕开 §6.1 的 UTF-16LE 编码问题。

**启动网关**：

```powershell
cd C:\Users\37842\Desktop\dsh联机
$env:DSH_TEAM_HUB_HOME="C:\Users\37842\Desktop\dsh联机\hubhome"
node .\probe\hub-fix\bin\dsh-team-hub.js start
```

原始输出：

```
dsh-team-hub listening on http://0.0.0.0:3090
Admin console: http://0.0.0.0:3090/admin
```

**selftest**（必须 admin 登录后 `POST`；`GET` 只会返回登录页 HTML）：

```
POST /__teamhub/api/selftest  body={}
HTTP 200
{"ok":true,"durationMs":20,"checks":[{"name":"session/list","ok":true,"detail":"0 sessions"},{"name":"workspace/follow","ok":true,"detail":"2 workspaces"}]}
```

**判定**：node v24.22.1 ≥ 22 ✅；3080 起并打印 token URL ✅；3090 起 ✅；selftest ok:true ✅。

---

### 阶段 2 单机跑通 — ✅ 通过

`probe/p2-shell.mjs` / `probe/p2-plugins.mjs` 实测：

| 请求 | admin | alice |
|---|---|---|
| `GET /` | 200，HTML **46041 字节** | 200，**完全相同** |
| `GET /admin/` | **200** | **403** `admin only` |
| `GET /__teamhub/api/workspaces` | 200（数组，2 个工作区） | **403** `{"error":"admin only"}` |
| 插件 bundle（**79 条 URL**） | **全部 200**（histogram `{"200":79}`） | **全部 200**（`{"200":79}`） |

登录成功跳转 `302 → /?teamhub-login=1795079320927`（时间戳，不是 `/`）。

**补丁 B 的硬证据（端到端对照，`probe/p2-patchb-e2e.mjs`，留档 `probe\p2-patchb-out.txt`）**：同一份 alice 会话，分别打向未打补丁的网关（`probe\hub-patched`，3092）与已打补丁的网关（`probe\hub-fix`，3090）：

```
=== UNPATCHED hub-patched (127.0.0.1:3092) — alice login HTTP 302 ===
  GET /            -> 200, 46041 bytes
  plugin URLs      -> 79
  status histogram -> {"200":75,"403":4}
  FAILING bundles  -> 4
      403 | modules=57 | @deepseek-ai/dsh-api-gateway/client.js  x2
      403 | modules=15 | @deepseek-ai/dsh-client-ui-settings-subagent/client.js  x2

=== PATCHED   hub-fix (127.0.0.1:3090) — alice login HTTP 302 ===
  GET /            -> 200, 46041 bytes
  plugin URLs      -> 79
  status histogram -> {"200":79}
```

**注意实际严重程度与本项目初始设想不同**：不是"76 条全 403"，而是 **79 条中 4 条 403**——被拒的是两组**模块数很多（57 个与 15 个）的逗号分隔 bundle**，各在页面中出现两次。这两组恰好包含 `dsh-api-gateway` 与 `dsh-client-ui-settings-*` 等核心 UI 模块，所以症状是"界面能开但大面积功能缺失 / 设置面板与网关通道不可用"，而非彻底白屏。

真实 URL 形状（多模块逗号分隔，HTML 原文里是 `&amp;`）：

```
plugins/??@deepseek-ai/dsh-api-gateway/client.js,@deepseek-ai/dsh-client-ui-file-actions/client.js,…&amp;rev=8b8a6bf4e471
```

原因在两个正则的字符类（`probe/hub-patched/src/server.mjs:60` vs `probe/hub-fix/src/server.mjs:60`，逐字取出）：

```
上游：/^\?\?[A-Za-z0-9@._/-]+\/client\.js(?:&[A-Za-z0-9@._/,-]+\/client\.js)*&rev=[a-f0-9]{12}$/
已修：/^\?\?[A-Za-z0-9@._/,-]+\/client\.js(?:[&,][A-Za-z0-9@._/,-]+\/client\.js)*&rev=[a-f0-9]{12}$/
```

上游第一个字符类**不含逗号**，故 `??a/client.js,b/client.js` 这种以逗号连接的第二段起就匹配失败。已修版把 `,` 加入字符类并把分隔符写成 `[&,]`。

**判定**：admin 登录 ✅ 进 `/admin/` ✅ 看到工作区列表 ✅ `/` 完整界面 ✅ 无 403 ✅。
（改密流程：`/change-password` 字段名为 `current` / `next`；本次三个账号 `mustChangePassword` 已为 false，改密只用 reset-password 路径间接验证。）

---

### 阶段 3 局域网多账号 — ✅ 通过

网关绑定 `0.0.0.0:3090`（`netstat -ano` 实测 `TCP 0.0.0.0:3090 LISTENING 34372`）。本机 IPv4（`ipconfig | Select-String "IPv4"`）：

- `10.198.103.170` ← **演示用**（真实局域网段）
- `26.180.228.175`（Tailscale 风格）
- `172.20.64.1`（WSL/Hyper-V 虚拟网卡）

三地址 `GET http://<ip>:3090/login` 均 **200，914 字节**；netstat 显示三条 ESTABLISHED。

**判定**：网关对外绑定 ✅；LAN IP 可达 ✅；alice 可登录 ✅（`302 → /?teamhub-login=…`）。

> 沙箱限制：`Get-NetIPAddress` / `Get-NetTCPConnection` 在本机报"拒绝访问"（exit 1），必须改用 `ipconfig` / `netstat -ano`。这一条要写进演示脚本的故障速查表。

---

### 阶段 4 权限配置 — ✅ 通过

```http
POST /__teamhub/api/workspaces/fcd6f438-6c45-4fb4-9dd2-b4178d12137a/sharing
Content-Type: application/json
Cookie: <admin>

{"members":["alice"]}
```

原始返回：

```
HTTP 200
{"workspaceId":"fcd6f438-6c45-4fb4-9dd2-b4178d12137a","owner":"bob","members":["alice"]}
```

随后 `GET /__teamhub/api/workspaces` 中该工作区 `"members":["alice"]` ✅。

**注意**：body **必须恰好**是 `{"members":[...]}`，多一个键就 400。

**判定**：共享设置成功 ✅；`/__teamhub/api/workspaces` 反映 ✅。

---

### 阶段 5 安全边界实测 — ✅ 通过（8/8 用例全部跑出预期结果）

见 §5 专章。输出留档 `probe\p5-boundary-final.txt`。

---

### 阶段 6 文档撰写 — ✅ 通过

| 交付物 | 路径 | 规模 |
|---|---|---|
| 验证报告（本文件） | `report\DSH共享服务-验证报告.md` | 8 节 |
| 课堂演示流程 | `report\DSH共享服务-课堂演示操作流程.docx` | 18 页 / 11 张表 / Heading 1×8、2×22、3×21 |

docx 的可打开性与版式用三项客观校验替代目视：

1. **包结构**：zip 完整性 `testzip → OK`，19 个 part，`word/document.xml` 存在，`python-docx` 可重新打开并读出 157 段 / 11 表 / 1 节。
2. **版式**：自写 `demo\audit_layout.py` 逐块量代码行宽（上限 78 半角单位 @10.5pt）与表格总宽（上限 16.60cm）——代码块最宽行 70 单位，11 张表 13.80–16.60cm，全部无溢出。
3. **渲染**：捆绑 LibreOffice 转 PDF 成功（`{"backend":"native"}`，18 页），再用 `pypdf` 抽每页文本核对标题所在页码与页眉页脚，`PAGE` / `NUMPAGES` 均为真 Word 域。

**判定**：两份交付物齐备且通过机器校验 ✅。

> 说明：`check_office.py` 因 `C:\Users\37842\...\DeepSeekRuntime` 路径在本会话沙箱里不稳定（时隐时现），改用上述三项自建校验；这是工具链限制，不影响文档本身。另外当前模型无图像输入，无法目视检查渲染出的 PNG，故以「PDF 文本抽取 + 尺寸审计 + 渲染成功」三重间接验证替代。

---

### 阶段 7 演示准备 — ✅ 通过（含计时）

演示脚本里的**每一条命令都按文档原样重跑过一遍**，脚本是 `demo\rehearse.ps1`，输出留档 `probe\p7-rehearsal.txt`：

```
PASS   4.4 selftest ok:true
PASS   CASE 0 bob reads own file
PASS   CASE 1 unshared -> denied
PASS   CASE 2 grant -> members[alice]
PASS   CASE 2 alice reads plaintext
PASS   CASE 3 ../ escape denied
PASS   CASE 4 absolute denied
PASS   CASE 5 traversal denied
PASS   CASE 6 queue accepted
PASS   CASE 7a interrupt denied
PASS   CASE 7b image denied
PASS   CASE 7c rename denied
PASS   CASE 8a revoke -> read denied
PASS   CASE 8b revoke -> prompt denied

REHEARSAL: all checks PASS
```

- **退出码 0**，**命令层耗时 1.6 秒**（14 条断言）。命令本身不是时间瓶颈——分镜表里给权限边界 300 秒，时间全部花在讲"为什么"和等听众看输出上。
- 排练中发现并修掉的两个真问题：① 断言最初用 PowerShell 的 `-like`，而 `["alice"]` 里的方括号会被当作通配字符类，导致一个**假失败**；改成 `.Contains()` 后通过。② §4.3 原稿把载荷写成 PowerShell 续行反引号，但演示者的 shell 若是 cmd 就会失败——文档现在明确声明"全部在 PowerShell 里执行"。
- **分镜总时长 790 秒 = 13 分 10 秒**，落在任务书要求的 12–15 分钟内；超时削减顺序写进了分镜表脚注（先砍分镜 2，再砍分镜 4、7，分镜 6 的 300 秒不动）。

**判定**：脚本可照念、命令可照抄、计时达标 ✅。

---

### 阶段 8 答辩交付 — ✅ 通过

- 8 条预设问答见演示文档 §7（按"选型 / 安全边界 / 已知妥协"三组编排），含任务书点名的四问：为什么不用官方 liveshare、为什么不用 0.0.0.0 直接暴露 DSH、这个网关能不能替代 VPN、权限模型与方案描述不一致怎么解释。
- 每条都指向本报告的具体小节与源码行号，便于追问时当场翻证据。

**判定**：可交付 ✅。

---

## 5. 安全边界实测结果

### 5.1 更正：DSH 能不能绑局域网？

**任务书原文的结论是错的**，本报告实测推翻：

```powershell
# 通配地址：被拒
node .\node_modules\@deepseek-ai\dsh\lib\bin.js web --port 3082 --host 0.0.0.0 --no-open
```

```
error: --host 0.0.0.0 is an unspecified (wildcard) address, which is not supported: binding every
interface would expose remote code execution to the network; bind one concrete IPv4 or IPv6 address instead
```

```powershell
# 具体 LAN IP：成功
node .\node_modules\@deepseek-ai\dsh\lib\bin.js web --port 3083 --host 10.198.103.170 --no-open
```

```
dsh web: http://10.198.103.170:3083/?token=D0DJZjgj-hdOkmI4qav0DeyW8KIKlyJX1ylYaTI0xuA
dsh web: listening on 10.198.103.170 over plain HTTP; restrict this port to a trusted proxy or network
```

`netstat` 确认 `TCP 10.198.103.170:3083 LISTENING 24748`。DSH **明确允许**绑具体网卡，只是拒绝通配。

**那么裸暴露会怎样**（`probe/p5-dsh-lan-direct.mjs` 原始输出）：

```
token URL host = 10.198.103.170:3083
  (a concrete LAN address, not 127.0.0.1)

GET  http://10.198.103.170:3083/                -> 401
GET  <printed tokenUrl>   (over LAN)    -> 303 loc=./ cookies=1
cookie name = dsh-auth-gc0adEW8ShJetI7HlJ3YNDPzeophn7XQOA5SSl3J4tk (this IS the Host identity)

POST /api/workspaceFiles/read  path=C:/Windows/win.ini -> 200
{"type":"server-response","result":{"ok":true,"value":{"absolutePath":"C:\\Windows\\win.ini",
"bytes":92,"offset":1,"text":"; for 16-bit app support\r\n[fonts]\r\n[extensions]\r\n
[mci extensions]\r\n[files]\r\n[Mail]\r\nMAPI=1\r"…

CONCLUSION: over a raw LAN bind, one token URL + one cookie = the entire Host:
one identity, every workspace, no per-member isolation, no policy, no audit.
```

**所以网关的真实必要性是：身份、隔离、策略、审计——不是可达性。** 这比原方案的论证更强，因为它建立在"裸暴露会泄露全盘"的实测上，而不是一个可以一次 `--host` 参数推翻的限制。

### 5.2 8 个必备用例（全部实测）

| # | 用例 | 预期 | 实测结果 | 判定 |
|---|---|---|---|---|
| 0 | （基线）bob 读自己的 `secret-plan.txt` | 允许 | ALLOW `{"offset":1,"text":"BOB SECRET: budget 42","lines":1,"eof":true,"absolutePath":"secret-plan.txt","bytes":22}` | ✅ |
| 1 | 未共享 alice 读 bob 的同文件 | 拒绝 | DENY `无权读取该工作区文件` | ✅ |
| 2 | 共享后 alice 读同文件 | **成功拿明文** | ALLOW，同上 22 字节全文 | ✅ |
| 3 | 共享后读 `../alice/alice-notes.txt` | 拒绝 | DENY；前置断言 `physically exists = true`（证明是真文件，不是不存在） | ✅ |
| 3b | （同根控制）`nested/deep.txt` | 允许 | ALLOW `"deep file"`（证明拒绝来自穿越而非文件缺失） | ✅ |
| 4 | 共享后读 `C:/Windows/win.ini` | 拒绝 | DENY | ✅ |
| 5 | 共享后读 `../../../../etc/passwd` | 拒绝 | DENY | ✅ |
| 6 | `session/prompt` `mode=queue` + 纯文本 | **`{"accepted":true}`** | ALLOW `{"accepted":true}` | ✅ |
| 7a | `mode=interrupt` | 拒绝 | DENY `共享会话仅支持排队发送消息` | ✅ |
| 7b | content 带 image | 拒绝 | DENY `成员仅支持已审核的纯文本会话请求` | ✅ |
| 7c-e | `session/rename` / `cancel` / `selectModel` | 拒绝 | 三条全 DENY `无权访问该会话或工作区` | ✅ |
| 8a | 撤销共享后立刻重试用例 2 | 立即失效 | DENY | ✅ |
| 8b | 撤销后立刻重试用例 3 | 立即失效 | DENY | ✅ |
| 8c | 撤销后立刻重试用例 6 | 立即失效 | DENY | ✅ |
| X1 | alice `GET /admin/` | 403 | 403 `admin only` | ✅ |
| X2 | alice `GET /__teamhub/api/workspaces` | 403 | 403 `{"error":"admin only"}` | ✅ |
| X3 | alice `workspace/create` | 拒绝 | DENY `方法 workspace/create 不在 Member 白名单` | ✅ |

**关键调用形态**（没这些一个用例都跑不通）：

```
POST /api/<namespace>/<method>
{"type":"client-request","rpcId":"p-xxx","method":"<ns/m>","payload":{"args":{...}}}
```

- 策略拒绝用 **HTTP 200 + `{"ok":false,"error":{...}}`** 表达，**不是 4xx**。断言必须看 body。
- `session/page` 的 scope 走 `args.request.address`；其他方法走 `args.request` 本身（`probe\hub-fix\src\policy.mjs:373-376`）。
- `session/prompt` 正确线格式（**最容易写错**）：`{"request":{"sessionId","mode","requestId","clientTimeZone","content":[{"type":"text","text":…}]}}`。写成 `address` 形状直接 `缺少会话或工作区归属参数`。
- `workspaceFiles/read` 的 `workspaceFileScopeId` **填 session id，不是 workspaceId**；`range` 必填且 `offset` 从 1 开始。漏 `range` → 上游 `gateway/arguments-invalid`，但被网关包装成前端看到的 `ERR: request failed`（`probe\hub-fix\src\server.mjs:318`）——这是头号排障黑洞。

### 5.3 发现 A：会话归属有最长 5 分钟滞后

**现象**：新建会话后，成员进不去（`无权访问该会话或工作区`），而 owner 自己能进。

**实测时间线（完整曲线，`probe/p5-lag-live.mjs`，留档 `probe\p5-lag-live-run2.txt` / `probe\p5-lag-live.txt`）**：

新建会话 `session-50ef7b71-62e0-4bd5-b460-b4f9914039be`（17:42:03 建），每 30 秒查一次 `/__teamhub/api/debug/ownership`：

```
2026-11-19T09:42:07.881Z  elapsed=0.1s    sessions=true  sessionWorkspace=false
2026-11-19T09:42:37.891Z  elapsed=30.1s   sessions=true  sessionWorkspace=false
2026-11-19T09:43:07.898Z  elapsed=60.1s   sessions=true  sessionWorkspace=false
2026-11-19T09:43:37.911Z  elapsed=90.1s   sessions=true  sessionWorkspace=false
2026-11-19T09:44:07.919Z  elapsed=120.1s  sessions=true  sessionWorkspace=false
2026-11-19T09:44:37.928Z  elapsed=150.1s  sessions=true  sessionWorkspace=false
2026-11-19T09:45:07.937Z  elapsed=180.1s  sessions=true  sessionWorkspace=false
2026-11-19T09:45:37.953Z  elapsed=210.1s  sessions=true  sessionWorkspace=false
2026-11-19T09:46:07.958Z  elapsed=240.1s  sessions=true  sessionWorkspace=true
>>> sessionWorkspace populated after ~240.1s (4.0 min)
```

关键点：`sessions=true` 从一开始就是 true（`learnSession` 立刻登记会话），但 `sessionWorkspace=false` 一直持续 **240 秒**。这个会话是在网关启动约 2 分钟后建的，所以它等的是网关启动后第 5 分钟那次定时刷新 —— 与 `:464` 的 `5 * 60 * 1000` 周期吻合，且**证明滞后长度取决于"会话创建时刻距离下一次定时刷新还有多久"，最坏接近 5 分钟**。

早前一次观测（重启网关前后的对照）也一致：会话建于约 17:09:40，17:12:12 / 17:12:33 / 17:12:53 三次都 `sessionWorkspace=0`，17:13:13 变 1（滞后约 3.5 分钟）；重启网关后立即为 1。

**为什么**（源码）：

- `probe\hub-fix\src\server.mjs:160` `async function refreshOwnership(context)`
- `:451` 启动时 `syncOwnership()`；`:455` 只有在 `workspaceOwner.size === 0` 时才每 3 秒重试；`:464` `const periodic = setInterval(() => { syncOwnership(); }, 5 * 60 * 1000);`
- 归属表只由 `learnWorkspace`（`probe\hub-fix\src\policy.mjs:80`，其中 `:96` `for (const sessionId of view.sessionIds || [])`）从 `workspace/follow` 的 `view.sessionIds` 填充；`learnSession` 只填 cwd/parent/owner，**不填** `sessionWorkspace`。

**上游并非缺陷源头**：`probe/p5-baseline.mjs` 直连 3080 发 `workspace/follow`，baseline 里 sessionIds 本来就有（`fcd6f438-…` → `["session-5fac988a-…"]`）。缺的纯粹是网关的刷新时机。

**影响**：这是"看起来配好了但成员进不去"的头号误判源。
**绕法**：重启网关（立即填表），或等满 5 分钟。

### 5.4 发现 B：上游 DSH 自己没有任何路径围栏

`probe/p5-upstream-nofence.mjs` 绕过网关直连 `127.0.0.1:3080`：

| 请求 path | 网关层 | 上游直连 |
|---|---|---|
| `C:/Windows/win.ini` | DENY | **200 带出 92 字节内容** |
| `../alice/alice-notes.txt` | DENY | **200 带出 `ALICE PRIVATE: exam answers`** |
| `../../../../etc/passwd` | DENY | `{"ok":false,"error":{"code":"workspace-file/not-found","message":"no entry at \"../../../../etc/passwd\""}}` |

注意第三行：上游**不是**在拦截穿越，只是那个文件不存在。即上游连相对穿越都不管。

**结论**：**全部路径安全只由网关的 `guardWorkspaceFileRead` 提供**（`probe\hub-fix\src\policy.mjs:299`）：
- `:304` `path.isAbsolute(args.path)` 拦绝对路径
- `:313` `path.resolve(root, args.path)` 归一化
- `:314` `canAccessPath(...)` → `:198` `fs.realpathSync(candidate)` + `:204` `realPath === root || realPath.startsWith(root + path.sep)`（真符号链接解析后的前缀校验）
- `:328` 响应里用 `path.relative(root, target)` 把宿主绝对路径替换成工作区相对路径

这是"网关是唯一安全边界"的硬证据，演示时最有说服力。

### 5.5 发现 C：撤销共享不会关闭 WebSocket

**现象**：撤销共享后，已打开的 `session/follow` 流不再投递真实内容，但 socket **保持 `readyState=1`**，后续帧变成 `{"type":"error","error":{"code":"internal","message":"stream unavailable"}}`。即**数据层立刻失效，连接层不立刻断开**。

**实测输出**（`probe/p5-ws-revoke.mjs`，留档 `probe\p5-ws-out.txt`）：

```
[alice] got snapshot BEFORE revoke -> stream works. readyState = OPEN
[admin] revoking share -> 200 {"workspaceId":"fcd6f438-…","owner":"bob","members":[]}
[alice] re-opening follow AFTER revoke
[bob] owner posts to the session to generate events after revoke
[bob] prompt -> 200 ok=true

[alice] readyState after revoke = OPEN
[alice] close event         = (never closed)
[alice] frames after revoke = ["error:stream unavailable"]

FINDING C: error frames after revoke = true ; socket still OPEN = true
```

**机制**（源码）：

- 网关对**客户端帧**的拒绝是**静默 drop**，只写审计 `ws.client-frame-denied`（`probe\hub-fix\src\server.mjs:608`）。所以撤权后客户端再发 `open` 帧连错误帧都拿不到。
- 要复现必须让**上游主动推**：撤权后由 owner 发一条 `session/prompt` 产生 journal 事件。
- 普通事件被拒只写 `ws.frame-dropped`（`server.mjs:640`，审计里能看到 `eventType: assistant/attempt / step/end / turn/end`）。
- `stream unavailable` 来自 `probe\hub-fix\src\remote-stream-policy.mjs:331`（`session/follow` 的 `ownSession` 失败分支），`server.mjs:654` 把它包成帧发给客户端。

**为什么值得写进报告**：README 说"撤销授权后立即生效：已打开的共享会话流会停止"。"停止"容易被读成"连接被关闭"，实际是"内容停止、连接保留"。这是文档与实现的语义落差，且对客户端重连逻辑有实际影响。

### 5.6 做不了 / 未实测的用例

| 项 | 状态 | 原因 |
|---|---|---|
| 符号链接逃逸 | **未实测** | Windows 非开发者模式 `fs.symlinkSync` 直接 `EPERM`，构造不出来。已用 `..` 穿越 + 绝对路径覆盖同类风险 |
| Linux 路线（0600 权限模型原意） | **源码推断，未实测** | `wsl -d Ubuntu` 恒报 `Wsl/E_ACCESSDENIED`；本机无 docker |
| 工具审批拦截 | **未实测** | 需要真实审批弹窗与模型回合，本次未驱动完整 LLM 会话 |
| 真实局域网第二台设备 | **部分实测** | 用本机多网卡地址模拟（`10.198.103.170` 三地址均 200），未接入独立物理设备 |

---

## 6. 已知缺陷清单

### 6.1 缺陷 1（最耗时）：PowerShell 5.1 的 `Tee-Object` 写 UTF-16LE，网关读不到 token

**症状**：网关 audit 每 3 秒刷

```json
{"type":"system.ownership-refresh-failed","error":"DSH Web private launch token unavailable"}
```

——与"没打补丁 A"一模一样，但补丁已打。

**真因**：本机是 **PowerShell 5.1**（不是任务书说的 PS7）。`Tee-Object` 把管道重编码成 **UTF-16LE + BOM**（实测 168 字节，形如 `\uFFFD\uFFFDd\u0000s\u0000h\u0000 … \r\u0000\n\u0000`）。`readDshWebToken` 按 UTF-8 解码 → 正则 `/^dsh web: (https?:\/\/\S+)$/` 永不匹配 → 恒 `null`。另外该文件以 `\r\n` 结尾，代码 `if (!text.endsWith("\n")) lines.pop()` 会把唯一一行 pop 掉。

**修法（已验证）**：用 `cmd /c` 做字节级重定向（见 §4 阶段 1 的命令）。日志变成 82 字节纯 UTF-8、以 `\n` 结尾，网关立即能读。

**失败的绕法（保留教训）**：
- `probe\launch-dsh.mjs` 用 `child_process.spawn(..., stdio:['ignore','pipe','pipe'])` → `Error: spawn EPERM`（errno -4048）。**原因：沙箱禁止程序打开命名管道，凡 `child_process` 捕获子进程 stdout 的写法都会 EPERM**；`stdio:'inherit'/'ignore'` 才行。
- `node -e "…&…"` 里的 `&` 被 PS 5.1 当运算符 → `AmpersandNotAllowed`。**探针一律写成 `.mjs` 文件再 `node 文件` 跑。**

**订正（复核后发现原记录有误）**：早先记为"`probe\start-dsh.cmd` 由 `pwsh` 调用 → 日志文件根本没生成"，复核证明**这个判断是错的**。
- 重跑同一份 `.cmd` 到空闲端口 3084：`cmd /c probe\cmdtest3084.cmd` → netstat 见 `127.0.0.1:3084 LISTENING`，日志 82 字节、首字节 `64 73 68 20`（即 `dsh `），内容 `dsh web: http://127.0.0.1:3084/?token=Cmx57I9kpLGXzXAdWqyfTHtBdEqXVXRBogKjVYWLrY8` —— **`.cmd` 包装完全可用，且天然避开 PS 的编码问题**。
- 当时"日志没生成"的真相是两层误读：① `.cmd` 里的 `>` 会**立刻**创建并独占该文件，此时 `Get-Content` / `[IO.File]::ReadAllBytes` 因 node 仍持有句柄而抛 `文件正由另一进程使用`，PS 报错后 `$b` 为空，看起来像"没生成"；② 那次运行与**已在 3080 监听的旧实例**撞端口，node 未输出启动行就卡住，日志一直是 0 字节。
- 正确观测姿势：用 `[System.IO.FileStream]::new(path, Open, Read, FileShare.ReadWrite)` 读在写的日志；或先确认目标端口空闲再启动。
- 附：`.cmd` 文件本身带 UTF-8 BOM（`ef bb bf`）也未导致失败（同一测试产出一致的 82 字节日志）。真正不能带 BOM 的是 **profile 的 `package.json`**（见 §6.4 同类问题）。

**结论**：`.cmd` 包装与 `cmd /c "… && …"` 单行两种写法都可行；报告与演示脚本统一采用 `.cmd`（可读、可复用、不依赖 PS）。

### 6.2 缺陷 2（致命，已修）：补丁 A — Windows 上 token 读取被一行代码阻断

`probe\hub-fix\src\dsh-browser-auth.mjs:23`

原版：
```js
if (!stat.isFile() || stat.uid !== process.getuid?.() || (stat.mode & 0o077)) return null;
```

Windows 上 `process.getuid` 为 `undefined`、`stat.uid` 恒 0、`stat.mode & 0o077` 恒 `0o66` → 恒 `null` → 网关永远读不到 token。

已改为：
```js
if (!stat.isFile()) return null;
if (process.getuid && (stat.uid !== process.getuid() || (stat.mode & 0o077))) return null;
```

验证：`POST /__teamhub/api/selftest` 从 `ok:false` 变 `ok:true`。

端到端对照（`probe/p1-patcha-e2e.mjs`，留档 `probe\p1-patcha-out.txt`）：同一份 `hubhome` 克隆，仅把 `probe\hub-unfixed\src\dsh-browser-auth.mjs:23` 回退成上游写法，起在 3093，与 3090（已打补丁）同条件对比：

```
=== PATCH A REVERTED (upstream uid/mode check intact) (127.0.0.1:3093) ===
  admin login      -> HTTP 302
  POST selftest    -> HTTP 200
  selftest body    -> {"ok":false,"durationMs":0,"checks":[{"name":"session/list","ok":false,"detail":"DSH Web private launch token unavailable"},{"name":"workspace/follow","ok":false,"detail":"DSH Web private launch token unavailable"}]}
  GET  workspaces  -> HTTP 200  []

=== PATCHED   hub-fix (127.0.0.1:3090) ===
  admin login      -> HTTP 302
  POST selftest    -> HTTP 200
  selftest body    -> {"ok":true,"durationMs":12,"checks":[{"name":"session/list","ok":true,"detail":"1 sessions"},{"name":"workspace/follow","ok":true,"detail":"2 workspaces"}]}
  GET  workspaces  -> HTTP 200  [{"workspaceId":"fcd6f438-…","owner":"bob",…,"members":[]}, …]
```

注意 **selftest 自身仍返回 HTTP 200**，失败只体现在 body 的 `ok:false`——这是本项目最容易被误判为"通过"的地方。另外未打补丁时 `GET /__teamhub/api/workspaces` 返回**空数组 `[]`**（归属表没填充），界面看起来"没有工作区"而不是报错，同样是静默失败。

### 6.3 缺陷 3（致命，已修）：补丁 B — 多模块插件 bundle 403

`probe\hub-fix\src\server.mjs:56-66` `isMemberStaticRoute`。原版正则要求路径以 `&rev=[a-f0-9]{12}$` 结尾，且**第一个字符类不含逗号**，但 DSH 0.2 真实 URL 是**多模块逗号分隔**、HTML 里 `&` 是 `&amp;`：

```
plugins/??@deepseek-ai/dsh-api-gateway/client.js,@deepseek-ai/dsh-client-ui-file-actions/client.js,…&amp;rev=8b8a6bf4e471
```

**实测影响面（订正）**：`probe/p2-patchb-e2e.mjs` 端到端对照 3092（未打补丁）与 3090（已打补丁），同一 alice 会话、同一份 79 条 plugin URL：未打补丁 `{"200":75,"403":4}`，已打补丁 `{"200":79}`。被拒的 4 条是**两组**模块数很大的 bundle（57 模块与 15 模块，各出现两次），首模块分别为 `@deepseek-ai/dsh-api-gateway/client.js` 与 `@deepseek-ai/dsh-client-ui-settings-subagent/client.js`。单模块 URL 和部分短的多模块 URL 恰好能被旧正则接受，所以**不是"全部 403、彻底白屏"，而是"核心 UI 模块 403、界面大面积功能缺失"**。

已改为（`:60`）：
```js
if (pathname === "/plugins/" && /^\?\?[A-Za-z0-9@._/,-]+\/client\.js(?:[&,][A-Za-z0-9@._/,-]+\/client\.js)*&rev=[a-f0-9]{12}$/.test(search) &&
    !search.includes("..")) return true;
```

验证：79 条 plugin URL 从 `{"200":75,"403":4}` 变 `{"200":79}`（留档 `probe\p2-patchb-out.txt`）。

### 6.4 缺陷 4（未修，需记录）：`member-settings.mjs` 有补丁 A 的同源遗漏

`probe\hub-fix\src\member-settings.mjs:19` 与 `:52` 仍是原版写法：

```js
if (!stat.isFile() || stat.uid !== process.getuid?.() || (stat.mode & 0o077)) throw new Error("unsafe member settings file");
```

Windows 上恒真 → 抛 `unsafe member settings file`。影响成员侧 `settings/describe` / `settings/mutate`。

**为什么没修**：本次演示路径不经过该功能；且修改需同步评估「承认不安全文件」的语义。**已知缺陷，留给后续。**

### 6.5 缺陷 5（致命，已修）：补丁 C — 一个畸形 JSON 就能杀死网关进程

**这是本次验证中发现的唯一"单请求即 DoS"级别缺陷，且属于上游原版代码，不是我们的补丁引入的。**

触发条件是任何一个 Admin API 的 POST 请求体不是合法 JSON。最普通的复现方式：

```powershell
# payload 里写 {members:[]}（键名不带引号）
curl.exe -s -b jar -H "content-type: application/json" --data-binary "@demo/payloads/bad.json" `
  "http://127.0.0.1:3090/__teamhub/api/workspaces/<workspaceId>/sharing"
```

实测结果（`probe/p8-crash.mjs`，留档 `probe\p8-crash-out.txt`）：

```
canary before = alive (HTTP 200)

--- body: valid, control
    payload   : "{\"members\":[]}"
    HTTP      : 200  {"workspaceId":"fcd6f438-…","owner":"bob","members":[]}
    gateway   : alive (HTTP 200)

--- body: bare keys (JSON5-ish, invalid JSON)
    payload   : "{members:[]}"
    HTTP      : FETCH FAILED ECONNRESET
    gateway   : DEAD (ECONNREFUSED)
    >>> gateway died on this body; stopping here.
```

网关 stderr 的原文，`probe\hub-fix\src\server.mjs:360`：

```
<anonymous_script>:1
{members:[]}
 ^

SyntaxError: Expected property name or '}' in JSON at position 1 (line 1 column 2)
    at JSON.parse (<anonymous>)
    at handleAdminApi (file:///C:/Users/37842/Desktop/dsh%E8%81%94%E6%9C%BA/probe/hub-fix/src/server.mjs:360:23)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)

Node.js v24.22.1
[status: completed, exit code: 1]
```

**两层根因**（缺一不可，两个都得修）：

1. **`JSON.parse` 在 try 之外**。上游 0.3.3 有 4 处这样写，全部在 `handleAdminApi` 里：
   - `hub\package\src\server.mjs:341` — `POST /__teamhub/api/users`
   - `hub\package\src\server.mjs:347` — `POST /__teamhub/api/users/<n>/status`
   - `hub\package\src\server.mjs:354` — `POST /__teamhub/api/users/<n>/display-name`
   - `hub\package\src\server.mjs:360` — `POST /__teamhub/api/workspaces/<id>/sharing`

   对照：同一个文件 `:237` 的 RPC 入口**有**保护（`try { message = JSON.parse(...); } catch { return rpcError(res, null, "bad-request", "invalid JSON", 400); }`），`:295` 也有 try。**作者在别处做了防护，唯独这 4 处漏了**——所以这是疏漏而非设计。
2. **`return handleAdminApi(...)` 少了 `await`，把 rejection 甩出了外层 try**。`probe\hub-fix\src\server.mjs:542` 原本是 `return handleAdminApi(...)`；`http.createServer(async (req,res) => { try {…} catch {…} })` 的 catch **只等同步 throw 和已 await 的 rejection**，未被 await 的 promise rejection 会变成 unhandled rejection → 进程退出。同一文件 `:561`（`handleApiPost`）与 `:564`（`proxyRequest`）也是同样的漏 `await` 写法。

**修复（补丁 C，已实施并验证）**：
- 新增 `probe\hub-fix\src\server.mjs:91-101`：
  ```js
  async function readJsonBody(req) {
    const text = (await collect(req)).toString("utf8");
    if (!text.trim()) return {};
    try { return JSON.parse(text); }
    catch { return undefined; }
  }
  ```
- 4 处调用改成 `const body = await readJsonBody(req); if (body === undefined) return send(res, 400, { error: "请求体不是合法 JSON" });`
- 3 处路由调用补上 `await`（`handleAdminApi` / `handleApiPost` / `proxyRequest`），让 rejection 落回外层 catch。

**修复后实测**（`probe\p8-crash-after-fix.txt`）：

```
--- body: bare keys (JSON5-ish, invalid JSON)
    HTTP      : 400  {"error":"请求体不是合法 JSON"}
    gateway   : alive (HTTP 200)
--- body: truncated object
    HTTP      : 400  {"error":"请求体不是合法 JSON"}
    gateway   : alive (HTTP 200)
--- body: empty body
    HTTP      : 400  {"error":"仅接受共享成员列表"}
    gateway   : alive (HTTP 200)
--- body: not an object
    HTTP      : 400  {"error":"仅接受共享成员列表"}
    gateway   : alive (HTTP 200)
```

五种畸形体全部只回 400，网关存活。修复后重跑 §5.2 的 8 个用例与 §5.5 的发现 C 探针，结论**逐条不变**（`probe\p5-boundary-after-fix.txt`、`probe\p5-ws-after-fix.txt`），无回归。

**为什么这件事在演示里很重要**：PowerShell 5.1 会把 `-d '{"members":[]}'` 的引号吃掉，实际发出 `{members:[]}`（见 §6.9）。也就是说**演示者按最自然的方式在 PS 5.1 里手敲一条 curl，就足以把自己的网关打死**。所以演示脚本里所有 JSON 一律走 `--data-binary "@文件"`，这不是洁癖，是必须。

### 6.6 缺陷 6：会话归属 5 分钟滞后（见 §5.3）

### 6.7 缺陷 7：撤销共享后 WS 语义与文档不符（见 §5.5）

### 6.8 缺陷 8：Windows 平台整体不受支持

网关 README「环境要求」写的是 **macOS 或 Linux（用于系统服务安装）**。Windows 能跑，纯粹因为补丁 A/B 绕过了 POSIX 权限检查。由此衍生：

- `service install`（launchd/systemd）在 Windows 上不可用 → 无法做开机自启，演示必须手动起两个进程。
- 0600 权限模型在 Windows 上无意义 → 补丁 A 实质上是**关闭了该安全校验**。这一点必须在报告里明说：**打补丁 = 削弱了一项安全检查**，只是因为网关与 DSH 同机同用户、且上游仅回环，风险可控。

### 6.9 缺陷 9：PowerShell 5.1 会破坏内联 JSON 参数（演示脚本必须用文件传参）

实测（`[System.Text.Encoding]::UTF8.GetBytes()` 直接取 PS 变量字节）：

```
  single-quoted with double quotes => [{"members":[]}]  bytes=7b 22 6d 65 6d 62 65 72 73 22 3a 5b 5d 7d
  escaped  \"members\"             => [members\]        bytes=6d 65 6d 62 65 72 73 5c
```

即 `-d '{"members":[]}'` 传到 curl 时**双引号已经不见了**（`7b 6d 65 6d …`），`-d '{\"members\":[]}'` 更惨，只剩 `members\`。两种写法都发不出合法 JSON → 直接触发 §6.5 的崩溃。

**结论**：本项目所有示范命令一律把请求体存成 UTF-8 无 BOM 的 `.json` 文件，用 `curl.exe --data-binary "@路径"` 发送。`demo\payloads\` 下已备好 11 个。

同源但影响较轻的两处：
- `Invoke-RestMethod` 解析中文返回体会乱码（`æ æè¯»å取…`）→ 本项目一律用 `curl.exe`。
- `Get-Content hubhome\logs\audit.jsonl` 默认按 ANSI 读中文 → 必须先 `-Encoding UTF8`，否则看到 `鎴愬憳浠呮敮鎸…`。

### 6.10 缺陷 10：沙箱环境限制（影响操作，不影响结论）

- `Get-NetIPAddress` / `Get-NetTCPConnection` → "拒绝访问"，exit 1。改用 `ipconfig` / `netstat -ano`。
- 任何 `child_process` 捕获子进程 stdout → `EPERM`。改用 `cmd /c` 重定向或受管后台作业。

### 6.11 缺陷 11（彩排当日实锤）：工作区 id 会轮换 —「网关先于 DSH 就绪启动」的次生灾害

**现象**：彩排（§4 阶段 7）时 bob 连**读自己的文件**都报 `无权读取该工作区文件`，
`POST /__teamhub/api/workspaces/fcd6f438-…/sharing` 报 **409** `{"error":"上游工作区已变更，请刷新后重试"}`。
前一日同一套脚本 14 断言全绿——所有硬编码 id 都没改，为什么坏了？

**根因链**（每步有审计/源码证据）：

1. 当晚用 `Start-Job` 把 DSH 与网关**几乎同时**拉起；DSH 未就绪时网关已完成启动同步。
2. 启动同步（`probe\hub-fix\src\server.mjs:454-463`）拿到空归属表 → 触发 3 秒重试；随后
   `refreshOwnership` 成功但此时上游里还没有会话，`workspaceOwner` 仍空。
3. `ensureMemberWorkspace`（`probe\hub-fix\src\server.mjs:205-238`）第 211 行
   `const existing = [...context.ownership.workspaceOwner.entries()].find(([, owner]) => owner === user.name);`
   在空表里找不到该成员的"已有工作区"→ 走 `workspace/create` 造一个**新工作区**（同一路径）。
4. 上游对"同路径再 create"不报错，而是**发一个新的 workspaceId**。审计
   `hubhome\logs\audit.jsonl` 出现 3 条新的 `workspace.created`（21:54:38，alice/bob/carol 各一）：
   alice `09022202-…`、bob `41ec4ca7-…`、carol `d87326f5-…`——与前一日的
   `c47b4fc2-…` / `fcd6f438-…` / `62ee04fa-…` 完全不同。
5. 旧 id 并未被网关遗忘清理，但已不属于"成员自己的工作区"：对旧 id 调 sharing 返回
   **409**（`probe\dbg-oldid.mjs` 实测）；所有 payload 里用旧 id 的调用全部 DENY。

**与发现 A 的区别**：发现 A 是"新会话要等一次 5 分钟定时刷新才进归属表"；本缺陷是
"**工作区本身**被换成了新 id，旧 id 永久失效"。两者都会表现为"配置明明做好了却 DENY"，
但修复动作不同：A 等刷新或重启网关即可；本缺陷必须**重建 payload / 更新硬编码 id**。

**修复（已实施并验证）**：
- `demo\rehearse.ps1`：`$WS` 不再硬编码，改为从 admin API 动态解析
  （`GET /__teamhub/api/workspaces` → 正则取 `"workspaceId":"…","owner":"bob"`，取不到即
  `exit 9` 并报 FATAL——fail loud 优于静默用错 id）。
- `demo\make-payloads.mjs`：接受 `argv[3]` 覆盖工作区 id，缺省时自动登录 admin 解析
  当前 bob 工作区 id；14 个 payload 全部重建。
- 修完重跑彩排：**14/14 全 PASS（exit 0）**，留档 `probe\p7-rehearsal.txt`。

**运维纪律（写进《使用说明》）**：两个进程必须**按序启动**——先 DSH、`netstat` 确认
`127.0.0.1:3080 LISTENING` 后再起网关。若网关先起且 DSH 未就绪，会同时踩中本缺陷
（id 轮换）与发现 A（归属滞后），且 id 轮换是**持久的**，重启网关救不回来。

---

## 7. 证据来源标注

| 结论 | 来源类型 | 具体位置 |
|---|---|---|
| DSH 版本 0.2.2-rc.1 / commit c59d10a | 实际安装输出 | `alt\node_modules\@deepseek-ai\dsh\package.json`；HTML 内 `__DSH_BOOT__` |
| 网关 0.3.3、发布时间、维护者 | npm 页面（实际查询） | `npm view dsh-team-hub version dist-tags time maintainers` |
| 网关共享能力表（7 行） | GitHub README | `probe\hub-fix\README.md:51-63` |
| 撤销共享"立即生效"表述 | GitHub README | `probe\hub-fix\README.md:65-71` |
| 安全边界/路径校验表述 | GitHub README | `probe\hub-fix\README.md:73-83` |
| Windows 不受支持 | GitHub README | `probe\hub-fix\README.md:85-91`（"macOS 或 Linux"） |
| 归属刷新 5 分钟 | 源码 | `probe\hub-fix\src\server.mjs:464` |
| 归属启动重试 3 秒（仅当表为空） | 源码 | `probe\hub-fix\src\server.mjs:454-463` |
| 归属表来源 `view.sessionIds` | 源码 | `probe\hub-fix\src\policy.mjs:80,96` |
| 路径围栏全部实现 | 源码 | `probe\hub-fix\src\policy.mjs:299-331` |
| realpath 前缀校验 | 源码 | `probe\hub-fix\src\policy.mjs:194-207` |
| 上游错误被改写成 `request failed` | 源码 | `probe\hub-fix\src\server.mjs:318` |
| 客户端帧静默 drop | 源码 | `probe\hub-fix\src\server.mjs:608` |
| `stream unavailable` 帧 | 源码 | `probe\hub-fix\src\remote-stream-policy.mjs:331`、`server.mjs:654` |
| 补丁 A 位置与原码 | 源码（git 前原始） | `probe\hub-fix\src\dsh-browser-auth.mjs:23` |
| 补丁 B 位置与正则 | 源码 | `probe\hub-fix\src\server.mjs:56-66` |
| 补丁 C 位置（`JSON.parse` 在 try 之外，4 处） | 源码（**上游原版**，未打补丁的 0.3.3 也有） | `hub\package\src\server.mjs:341,347,354,360` ← 原版；修复在 `probe\hub-fix\src\server.mjs:91-101`（`readJsonBody`）+ `:352-386` |
| 补丁 C 缺 `await` 逃出外层 try（3 处） | 源码（上游原版） | `hub\package\src\server.mjs:542`（`return handleAdminApi(...)`）、`:561`、`:564` |
| 补丁 C 崩溃实测 | **实际命令输出** | `probe\p8-crash-out.txt`（崩）/ `probe\p8-crash-after-fix.txt`（不崩） |
| PS 5.1 破坏内联 JSON 参数 | **实际命令输出** | 见 §6.9 的字节 dump |
| `member-settings` 同源遗漏 | 源码 | `probe\hub-fix\src\member-settings.mjs:19,52` |
| liveshare 三档权限 | GitHub README（包内） | `alt\node_modules\@deepseek-ai\dsh-experimental-liveshare\README.md` |
| liveshare 需自建 server | 同上 | 同文件 "Summary" 段 |
| DSH 拒绝通配但接受具体 IP | **实际命令输出** | 见 §5.1（`--host 0.0.0.0` 报错原文 / `--host 10.198.103.170` 成功原文） |
| 裸暴露可读全盘 | **实际命令输出** | `probe\p5-lan-direct-out.txt` |
| GitHub star / issue 数 | **无法核验** | 本次未抓取网页 |

---

## 8. 附：复用资产清单

| 路径 | 作用 |
|---|---|
| `probe\hub-fix\` | 已打补丁 A+B 的网关（**部署一律用这个**） |
| `probe\hub-patched\` | 只打了补丁 A（补丁 B 是旧版正则），仅作对比 |
| `probe\hub-unfixed\` | 补丁 A 已回退的副本（3093 对照用，勿用于部署） |
| `hubhome-patchA\` | 3093 实例数据目录（补丁 A 对照） |
| `hubhome-unpatched\` | 3092 实例数据目录（补丁 B 对照） |
| `hubhome\config.json` | 3090 的网关配置（`listenPort:3090`、`upstream:http://127.0.0.1:3080`、`dshWebLog:…/probe/dsh-web.log`） |
| `hubhome-fix\` | 3091 备用实例 |
| `probe\lib-hub.mjs` | 探针公共库：`login()` / `rpc()` / `adminApi()` / `judge()` |
| `probe\p1-patcha-e2e.mjs` | 补丁 A 端到端对照（3093 回退 vs 3090 已修）→ `probe\p1-patcha-out.txt` |
| `probe\p2-plugins.mjs` | 逐条拉 79 个 plugin URL 统计状态码（补丁 B 验收） |
| `probe\p2-patchb-e2e.mjs` | 补丁 B 端到端对照（3092 未修 vs 3090 已修）→ `probe\p2-patchb-out.txt` |
| `probe\p2-regex-evidence.mjs` | 从两棵树逐字切出正则字面量并复演 79 条真实 URL → `probe\p2-regex-out.txt` |
| `probe\p4-setup.mjs` | 建 bob 会话 + 写测试夹具 |
| `probe\p5-boundary.mjs` | 8 用例主脚本 |
| `probe\p5-upstream-nofence.mjs` | 发现 B（绕过网关直连上游） |
| `probe\p5-ws-revoke.mjs` | 发现 C（撤权后 WS 语义） |
| `probe\p5-dsh-lan-direct.mjs` | 裸 LAN 绑定暴露面（§5.1） |
| `probe\p6-audit.mjs` | 抓 `/__teamhub/api/workspaces` 与 `/audit` 原始返回 |

**测试夹具（固定值，演示脚本直接引用）**：

> ⚠ 工作区 id 会随"网关先于 DSH 就绪启动"轮换（§6.11），会话 id 每次重启上游后失效。
> 下表是**首测当日**的取值，用于对照历史输出；现场演示一律动态解析（rehearse.ps1 /
> make-payloads.mjs 已内置），不要抄硬编码值。

| 名 | 值（首测当日） |
|---|---|
| bob 工作区 id（当日） | `fcd6f438-6c45-4fb4-9dd2-b4178d12137a`；彩排日轮换为 `41ec4ca7-911d-4ef0-aad5-bcd174056345` |
| alice 工作区 id（当日） | `c47b4fc2-2950-4f22-ac39-4409ede1075b`；彩排日轮换为 `09022202-9892-451a-845f-bd5f284b8cfa` |
| bob 会话 id | `session-5fac988a-a974-442b-a7e1-5a6d71e3d1ce`（当日）；彩排日 `session-868a24e9-6863-48e8-bfd2-bb9f2a024bd9` |
| bob 文件 | `secret-plan.txt` = `BOB SECRET: budget 42`（22 字节）；`nested\deep.txt` = `deep file` |
| alice 文件 | `alice-notes.txt` = `ALICE PRIVATE: exam answers`（28 字节） |
| 账号口令 | `admin` / `AdminPass!2026`，`alice` / `AlicePass!2026`，`bob` / `BobPass!2026` |
| 演示 LAN IP | `10.198.103.170` |
