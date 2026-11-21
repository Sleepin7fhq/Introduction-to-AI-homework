# 发布验证记录

日期：2026-10-19。已完成本地候选检查、GitHub 上传及公开克隆 / ZIP 下载复验。仓库：[web3olalala/FitBuddy](https://github.com/web3olalala/FitBuddy)，许可证：MIT。

## 源码与隐私检查

- 检查 Git 待发布清单、源码、文档、依赖锁文件及图标；整理前仓库没有提交历史。
- 未发现私人训练导出、数据库文件、密码、常见服务访问令牌、私钥、私人邮箱或原机器绝对路径。
- 初始数据中的训练、身体指标和自定义动作均为空。测试中的数字和训练记录由测试代码构造，不是个人导出。
- 应用代码没有业务数据上传接口、外部字体、第三方分析或运行时 CDN；Service Worker 请求自身应用资源，记录存入 IndexedDB。
- 两个 PNG 图标仅含 IHDR、IDAT、IEND 数据块，没有文本或 EXIF 元数据。
- 旧开发计划、旧验收报告、设计过程记录和重复入门文档移入 `.local-notes/` 并忽略，保留本地参考。公开文档不再引用原机器目录、旧标签或未附带的部署 ZIP。
- `.gitignore` 排除个人导出、数据库、环境配置、密钥、依赖、测试截图、压缩包、浏览器配置和本地笔记；已验证代表性路径确实被忽略。

这些结论是本次文件检查结果，不是对未来新增文件的保证，也不包含未提供的外部素材授权证明。

## 可移植性修复

- 测试直接使用项目内 Playwright，移除原开发机器与 AI 工具的隐式依赖。
- 线上验证脚本必须显式传入自己的 HTTPS 部署地址，不再默认访问原站点；输出目录自动创建。
- 本地服务器使用当前操作系统的路径分隔符，修正 Windows 上公开目录资源被错误拒绝的问题。
- 声明 Node.js >=22，提供 `.nvmrc`，保留依赖锁文件；无需运行时第三方依赖或构建步骤。
- 新增服务器测试：主页、资源 MIME、目录外文件拒绝、路径穿越拒绝。

## 安装与运行验证

将 Git 待发布文件复制到新的临时目录，排除 `.git`、本地笔记、依赖、浏览器配置和个人数据。按 README 的启动与开发流程验证。

环境：macOS，Node.js 22.20.0，npm 10.9.3，Playwright 1.62.1，本机 Google Chrome 155.0.8059.84。临时目录最初命中了机器旧 Node 12，按 README 的要求切换到 Node 22 后启动正常，未修改全局 Node 配置。

| 项目 | 结果 |
| --- | --- |
| 安装依赖前 `npm start` | 通过，首页 HTTP 200；随后用隔离 Chrome 验证空库、首次训练、刷新保留及完成训练，无页面异常 |
| 项目文件隔离 | `/package.json` HTTP 404，服务器仅公开 public/ |
| `npm run check` | 通过 |
| `npm test` | 18/18 通过，无失败或跳过 |
| 从公共 npm 安装锁定依赖 | 通过，干净缓存安装 3 个开发依赖包；npm audit 报告 0 个已知漏洞 |
| `npm run test:browser`（显式指定本机 Chrome） | 32/32 通过，无失败或跳过；约 84 秒 |

安装验证使用新的 npm 缓存，并使用本机网络所需的代理参数；代理地址没有写入项目。README 的通常安装命令仍为 `npm ci`。

Chromium 下载较慢，经维护者要求改用本机已安装 Chrome，停止额外下载。实际执行：

```sh
PLAYWRIGHT_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run test:browser
```

测试仍使用新建的隔离浏览器环境。已通过训练、历史、计划、成就、统计、跨浏览器重开、离线、备份恢复、失败事务和资源更新场景。默认 `npx playwright install chromium` 的完整下载流程本次未验证完成；不能据此宣称所有系统或浏览器均已通过。

## 从 GitHub 下载后的复验

验证的源码提交：[d0e183d](https://github.com/web3olalala/FitBuddy/commit/d0e183d2e6dd364c9748d2c2fccc231fadad036a)。本记录随后单独更新，应用源码未变更。

- 使用公开 HTTPS URL 克隆，不使用 Git 凭据；另外下载 GitHub 的 main 分支 ZIP。
- 解压并逐文件比较，50 个发布文件与公开克隆内容完全一致，不含本地笔记、个人数据或依赖目录。
- ZIP 解压后、未安装依赖时执行 `npm start`：首页 HTTP 200；隔离 Chrome 验证初始空库、首次训练、刷新保留及完成训练，无页面异常。
- 在公开克隆目录执行 `npm ci`：成功，安装 3 个开发依赖包，npm audit 报告 0 个已知漏洞。此次复用此前的 npm 下载缓存，不复制 node_modules；锁文件未被修改。
- `npm run check`：通过。
- `npm test`：18/18 通过，0 失败、0 跳过。
- 使用本机 Chrome 执行 `npm run test:browser`：32/32 通过，0 失败、0 跳过，约 79 秒。
- GitHub API 确认仓库公开、默认分支 main、识别许可证 MIT。提交采用 GitHub noreply 邮箱，未公开本机配置的私人邮箱。
- 验证环境仍为本机 nvm Node.js 22.20.0 和已安装的 Chrome，未下载额外浏览器。

## 尚未完成的验收

- Windows、Linux 原生环境、Safari、iPhone / 安卓真机安装与系统键盘：本次未执行，不能由 macOS Chromium 结果推断通过。
- 实际线上部署验证：本次不发布网站，不将旧报告的成功记录计入本次验证。
