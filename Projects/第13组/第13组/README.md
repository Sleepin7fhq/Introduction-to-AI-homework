# FitBuddy · 今天练了吗

一个手机优先的健身记录 App：安排训练、逐组记录、查看进步。使用原生 HTML、CSS 和 JavaScript 编写，可安装为 PWA（添加到手机主屏幕后像 App 一样打开）。

**无需注册、无需 API 密钥、无需数据库服务。** 训练数据保存在当前浏览器的 IndexedDB 中，不自动上传或跨设备同步。

## 可以做什么

- **每周计划**：设置训练部位、动作和休息日，支持移动、互换和清除安排；首页显示从今天起的七天。
- **边练边记**：训练前确认动作，记录每组重量和次数、逐组打卡；自动保存草稿，可关闭后继续。
- **训练历史**：按月查看、补录、编辑和删除，支持自定义动作。
- **进步与成就**：查看训练频率、动作表现和体重趋势，解锁训练次数与重量突破徽章。
- **身体指标**：记录体重、体脂率、腰围，设置每周训练次数和目标体重。
- **离线与备份**：首次加载后离线使用，导出 JSON 备份，在另一设备手动恢复。

## 先在电脑上运行

### 1. 安装运行环境

安装 [Node.js](https://nodejs.org/) **22 或更新的受支持 LTS 版本**（附带 npm）。项目提供 `.nvmrc`，使用 nvm 的开发者可运行 `nvm install` 和 `nvm use`。

安装后重新打开终端，检查：

```sh
node --version
npm --version
```

本项目无运行时第三方依赖，也没有编译步骤。使用现代 Chrome、Edge、Firefox 或 Safari；浏览器须允许网站本地存储。浏览器测试环境要求见 [Playwright 官方说明](https://playwright.dev/docs/intro#system-requirements)。

### 2. 下载项目

**没有 Git 也可以：** 在 [GitHub 仓库](https://github.com/web3olalala/FitBuddy) 点击 **Code → Download ZIP**，解压。在解压后的文件夹中打开终端，确保能看到 `package.json`。

或者，已安装 [Git](https://git-scm.com/downloads) 时运行：

```sh
git clone https://github.com/web3olalala/FitBuddy.git
cd FitBuddy
```

### 3. 启动

```sh
npm start
```

看到地址后，在**同一台电脑**打开 [http://localhost:4173](http://localhost:4173)。终端保持开启；停止按 `Ctrl+C`，下次继续使用时再运行 `npm start`。

仅使用 App 不需要 `npm install` 或 `npm ci`。不要双击 `public/index.html`，JavaScript 模块和离线功能需要通过 HTTP 服务加载。默认服务器只监听本机。

### 4. 试着记录一次

1. 在「计划」编辑今天的安排，添加动作并保存。
2. 进入「记录」，确认训练清单，开始训练。
3. 输入每组重量和次数并打卡，等待「已保存」。
4. 完成训练，在「记录」和「进步」中查看结果。
5. 在「我的 → 导出备份」保存自己的数据。

首次打开没有训练记录；代码里的测试样例不会自动出现在 App 中。

## 数据、离线与手机使用

- 数据属于当前设备、浏览器和网址。`localhost`、`127.0.0.1`、不同端口或域名的数据各自独立。
- 请固定同一入口使用。清除网站数据、重置设备或浏览器回收存储可能导致记录丢失，**定期导出备份**。
- 「我的 → 选择文件」先检查备份并显示摘要；「确认替换并恢复」会**完整替换**当前数据，不是合并。新备份为版本 2，支持导入旧版版本 1。
- 备份含训练和身体指标，未加密。请保存在项目目录之外，不要提交到 GitHub。
- 首次联网加载，在「我的」看到「离线已就绪」后再断网。离线缓存不能代替数据备份。
- 手机不能访问电脑的 `localhost`。手机使用需要将 `public/` 部署到 HTTPS 静态网站，再添加到主屏幕，详见 [手机与部署指南](./MOBILE_SETUP.md)。

项目没有账号系统、云同步或原生安装包；有氧动作目前仍按组和次数记录，没有距离、配速等专用字段。

## 二次开发

### 安装测试依赖

在项目根目录运行：

```sh
npm ci
npx playwright install chromium
```

`npm ci` 按 `package-lock.json` 安装固定依赖。Playwright 仅用于测试，不进入 App。Chromium 下载需要联网；Linux 上缺少浏览器系统库时，使用 `npx playwright install --with-deps chromium`，安装系统库可能需要管理员权限。

### 修改代码

1. 如要向本项目贡献，先在 GitHub **Fork** 到自己账号，再克隆自己的仓库。
2. 创建工作分支，例如 `git switch -c feat/my-feature`。
3. 运行 `npm start`，编辑 `public/` 下的文件。
4. 页面没有自动热更新，需刷新；若旧 Service Worker 缓存仍生效，可在**专用开发浏览器配置**中启用 DevTools 的 “Bypass for network”。不要用清除网站数据的方式更新日常记录环境。
5. 修改任何静态资源后，递增 `public/sw.js` 中的 `CACHE` 版本。发布后已有用户通过「更新应用」加载新版；不要删除 IndexedDB。
6. 执行下面的检查，查看 diff 后提交，再向原仓库发 Pull Request。

修改数据结构时，同步检查 `model.js` 的校验、旧版迁移、备份恢复和测试，避免已有用户无法读取记录。产品规则见 [PRD](./docs/PRD.md)。

### 运行检查

```sh
npm run check
npm test
npm run test:browser
```

| 命令 | 用途 |
| --- | --- |
| `npm start` | 启动本地静态服务器，默认端口 4173 |
| `npm run check` | 检查应用与服务器 JavaScript 语法 |
| `npm test` | 运行数据规则、统计、备份等单元测试 |
| `npm run test:browser` | 运行真实 Chromium 中的交互、保存、离线与恢复测试 |
| `npm run test:deployment -- https://你的域名` | 可选：验证自己部署的静态资源与本地一致，并验证线上流程 |

浏览器测试自动启动随机端口的本地服务器，使用独立临时浏览器，不需要先运行 `npm start`，不使用日常训练数据库。输出截图在被 Git 忽略的 `test-results/` 中。部署测试也使用隔离浏览器，但会访问指定网站；只对自己部署的站点执行。

如果已经安装 Chrome，也可以省略 Chromium 下载，显式指定浏览器来测试。例如 macOS 默认安装位置：

```sh
PLAYWRIGHT_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run test:browser
```

Windows PowerShell 示例（Chrome 若安装在其他位置，请修改路径）：

```powershell
$env:PLAYWRIGHT_EXECUTABLE_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
npm run test:browser
```

环境变量只用于指定测试浏览器；测试仍创建独立配置，不读取个人 Chrome 配置或训练数据。已安装 Chrome 的版本可能与 Playwright 自带版本不同，如遇兼容问题，改用匹配的 Chromium。测试不依赖原作者机器目录或 AI 工具运行时。

本项目没有 `npm run build`；部署时直接使用 `public/`。提交 `package-lock.json`，不要提交 `node_modules/`、个人导出、环境密钥或测试输出。`package.json` 的 `private: true` 仅防止误发布到 npm，不影响 GitHub 上的源码分享。

## 项目结构

```text
FitBuddy/
├── public/
│   ├── index.html           # 页面入口
│   ├── app.js               # 页面、表单、导航与交互
│   ├── model.js             # 训练规则、统计、备份校验
│   ├── store.js             # IndexedDB 读写与事务
│   ├── styles.css           # 手机与桌面样式
│   ├── sw.js                # 离线资源缓存与更新
│   ├── manifest.webmanifest # PWA 名称、图标和安装配置
│   └── icon-*.png           # 应用图标
├── tests/                   # 单元与浏览器测试、合成测试样例
├── docs/                    # 产品规则、验证与发布说明
├── server.mjs               # 仅服务 public/ 的本地服务器
├── package.json             # 命令与开发依赖
└── package-lock.json        # 固定依赖版本
```

## 常见问题

**提示 `ERR_UNKNOWN_BUILTIN_MODULE` 或不支持的 Node 版本？** 检查 `node --version`，切换到 Node.js 22 或更新的受支持 LTS；机器上同时安装多个版本时，每个新终端都需要确认当前版本。

**提示找不到 node 或 npm？** 安装 Node.js 后重开终端，再执行版本检查。Windows PowerShell 若拦截 `npm.ps1`，可在命令提示符中运行，或使用 `npm.cmd` / `npx.cmd`。

**端口被占用（EADDRINUSE）？** 检查是否已有本项目服务运行，可直接打开原地址。开发时可以指定其他端口，但新端口不会显示原端口的数据：

```sh
# macOS / Linux
PORT=4174 npm start
```

```powershell
# Windows PowerShell
$env:PORT=4174
npm start
```

**修改后仍显示旧页面？** 检查离线缓存，开发时使用上面的 DevTools 设置；正常发布应递增缓存版本，并通过 App 的「更新应用」更新。

**测试提示找不到浏览器？** 先执行 `npm ci`，再执行 `npx playwright install chromium`。下载失败时先检查网络，不能仅凭单元测试通过就认定浏览器测试也通过。

**换设备后数据为空？** 从原来的设备、浏览器和网址导出备份，再到新入口恢复。

## 验证与许可证

本次验证范围和结果见 [验证记录](./docs/VERIFICATION.md)，维护者发布步骤见 [GitHub 发布指南](./docs/GITHUB_RELEASE.md)。Chromium 自动化不代表已经通过 iPhone、安卓或 Safari 真机验收。

本项目采用 [MIT 许可证](./LICENSE)，Copyright (c) 2026 web3olalala。允许使用、修改、分发和商用，请保留版权及许可声明。
