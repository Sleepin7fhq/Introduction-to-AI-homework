# DSH 局域网共享网关 ——「人工智能+开发协作」

> **一个 AI，多个身份**：DSH 负责能力，网关负责身份、权限、协作与记账。
> 小组成员：甘昊哲 / 李泊岩 / 王梓程 / 韩勖（贡献度 28% / 28% / 24% / 20%）

## 一、项目简介

DeepSeek Harness（DSH）是单用户本地 AI 编程助手，默认只监听 127.0.0.1，拿到 token 就是唯一 Host。本小组在**不修改 DSH 一行源码**的前提下，在其前面加了一层 `dsh-team-hub` 网关：

- 3080 仅回环、从不对外；3090 绑定局域网，成为**唯一安全边界**；
- 把一个 token 身份拆成 N 个账号（admin / alice / bob / carol），首登强制改密；
- 多级权限：chat（协作，可发消息、编辑队列）/ viewer（只读，仅看历史）+ 路径围栏；
- 四张牌：**身份**（Agent 知道在为谁服务）、**权限**（chat/viewer）、**协作**（会话转交接力棒 + 审计时间线）、**记账**（每人 token 用量/估成本/配额）。

一句话：**共享 ≠ 放行**——共享的是被明确授权的那一部分能力。

## 二、仓库内容说明

| 目录/文件 | 说明 |
|---|---|
| `网关源码/` | 自研网关完整源码（probe\hub-fix 的 src/bin/admin-ui）、启动脚本、demo 排练脚本与 payload、Inno Setup 打包配置 |
| `hubhome/config.json` | 账号配置示例（4 账号，密码为 scrypt 哈希，不存明文） |
| `报告/` | 详细修改报告、核心理念变更说明、三类审计报告、答辩问答预演、演示教程等 |
| `演示PPT.pptx` | 答辩演示幻灯片 |

**上游依赖**：网关需要配合 DSH Web 0.2.2-rc.1 运行（第三方依赖，不随本仓库分发）。
**一键安装包**（含 DSH 与内置 Node，约 120MB，超过 GitHub 单文件上限 100MB）：
- GitHub Release 直链：https://github.com/Sleepin7fhq/Introduction-to-AI-homework/releases/download/v1.0/DSH-Lan-Share-Setup.exe
- 百度网盘（备用）：https://pan.baidu.com/s/1n3kpPNIN5Gq_CcMr9wAGlA （提取码：4ghc）
- SHA256：BBBF62FF1B4DCA49D30727E5FDAAC334503583DA800EF9C4846CE89959E2B12A

## 三、如何运行

1. 取得 DSH 0.2.2-rc.1，放到 `alt/`（与网关脚本同级）；
2. 运行 `start-all.cmd`：自动按序启动 DSH(3080) 与网关(3090)，完成后自动打开浏览器；
3. 账号 `admin / AdminPass!2026`（首登强制改密），局域网访问 `http://<本机IP>:3090/login`；
4. `stop-all.cmd` 停止；`demo\rehearse.ps1` 跑 16 条权限断言（自带自愈）。

详细说明见 `网关源码/SETUP.md`。

## 四、测试与验证

- 权限矩阵 **32 项** 全部通过（owner/chat/viewer/管理隔离/审计）；
- 排练脚本 `rehearse.ps1` **16 条断言** 全绿；
- 安全边界：3080 仅回环（局域网实测不可达）、3090 局域网可达；
- 三轮系统化审计报告见 `报告/`（安全攻击面 / 演示与使用场景 / 功能验收）。

## 五、已知限制（诚实声明）

HTTP 明文（限可信局域网）；权限目前三档（owner/chat/viewer）；用量为字符级估算口径；安装包未签名（SmartScreen 处理见 SETUP.md）。
