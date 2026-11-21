# 维护者：首次发布到 GitHub

## 发布前

1. 确认拥有源码及图标的发布权。选择许可证并确认署名，再添加完整 `LICENSE`，同步 `package.json` 和 README 的许可证说明。
2. 按 README 在干净目录运行安装和测试，记录结果。
3. 检查 `git status --short` 和待提交 diff，排除个人备份、密钥、浏览器配置、截图及本地笔记。
4. Git 提交会公开作者名称和邮箱。如需保护私人邮箱，可从 GitHub 的 **Settings → Emails** 获取自己的 noreply 邮箱，并仅在当前仓库设置提交身份。

`.gitignore` 不能移除已经提交的秘密；若未来误提交真实密钥，应先撤销密钥，再处理历史。本次初始整理时仓库没有提交历史。

## 仓库和登录

本项目已配置远程仓库 [web3olalala/FitBuddy](https://github.com/web3olalala/FitBuddy)，首次整理时它是公开空仓库。已有空仓库无需重复创建。

若另建仓库，在 [GitHub 新建仓库页](https://github.com/new) 输入名称、选择 Public；保持为空，不勾选初始化 README、许可证或 `.gitignore`，避免和本地首个提交冲突。然后把远程 URL 改为自己的仓库地址。

上传身份必须拥有目标仓库写权限。可使用 GitHub CLI 的浏览器授权流程，或已配置的 SSH 密钥。密码、验证码和访问令牌只在 GitHub 官方页面或本机工具中输入，不要写进项目或聊天。

```sh
gh auth login --hostname github.com --git-protocol https --web
```

如果已有多个账号，可以用 `gh auth switch` 切换，然后用 `gh repo view` / GitHub 网页检查目标仓库及权限。SSH 和 CLI 可能使用不同账号，应分别核实。本机若为不同账号配置了 SSH Host 别名，远程地址需要使用对应别名；仅修改 `git config user.name` 和 `user.email` 不会切换 GitHub 登录身份。

## 提交与上传

在许可证、身份及发布内容确认后：

```sh
git status --short
git add .
git diff --cached --check
git diff --cached --stat
git diff --cached
```

检查暂存内容，确认不含本地数据后再提交。`.local-notes/`、`node_modules/`、`test-results/`、个人导出和密钥文件应保持忽略。

```sh
git commit -m "Prepare FitBuddy for public release"
git push -u origin main
```

如远程已有新提交，先检查变更，不要强制覆盖远程历史。上传后，打开仓库确认 README、LICENSE、源文件与下载 ZIP 正常显示。

## 最后从公开仓库验证

在新建的空目录中执行（不要覆盖开发目录）：

```sh
git clone https://github.com/web3olalala/FitBuddy.git
cd FitBuddy
npm start
```

打开本机地址完成 README 的首次训练流程。随后停止服务，并执行：

```sh
npm ci
npx playwright install chromium
npm run check
npm test
npm run test:browser
```

验证记录需区分本地发布候选验证和上传后的公开克隆验证，不把尚未执行的步骤标为通过。GitHub 托管源码与发布可直接访问的 PWA 网站是两个独立操作。

参考：[GitHub 创建仓库指南](https://docs.github.com/en/repositories/creating-and-managing-repositories/quickstart-for-repositories)、[MIT 许可证](https://choosealicense.com/licenses/mit/)、[Apache-2.0 许可证](https://choosealicense.com/licenses/apache-2.0/)。
