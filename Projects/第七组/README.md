# 奶蛙舞台 Nawa Studio

人工智能导论课程作品：用三维角色、房间、箱子和连线，展示 Python 代码的执行过程。

**[打开正式演示网站](https://stately-choux-aa7b11.netlify.app/)** · [本地运行指南](docs/GETTING_STARTED.md) · [GitHub 上传与部署](docs/GITHUB_UPLOAD.md) · [实现原理](docs/ARCHITECTURE.md)

![奶蛙舞台界面](docs/images/workbench-desktop.png)

## 作品能做什么

- 根据 Python 的真实执行记录展示运行过程，动画与代码、变量信息相互对应。
- 用奶蛙表示当前执行位置，用房间帮助理解函数调用，用箱子和连线展示数据关系。
- 支持播放、暂停、重播、前后单步、时间轴和倍速。
- 支持旋转、缩放三维视角，点击角色、对象或连线查看当前信息。
- 提供“认识奶蛙”页面，可查看角色模型。

## 两种使用方式

| 使用方式 | 能力 | 启动方式 |
| --- | --- | --- |
| 公开演示版 | 七段固定示例，复制粘贴后回放，不在托管主机执行访客代码 | 正式网址，或 `python tools/serve-public.py` |
| 私人电脑本地版 | 输入自己的 Python 代码，执行、记录、编译成舞台演示；提供基于内置资料的问答 | `python tools/serve.py --open` |

公开版限制输入是为了保护主机。个人部署后可使用其他代码，但可视化主要面向短小的 Python 学习示例，不保证所有语法、第三方库或复杂程序都能完整呈现。这里的本地执行程序也可理解为负责记录与编译任务的 Agent；启动本地基础功能不需要安装 Codex 或配置 API 密钥。

## 快速开始

需要 **Python 3.11 或更新版本**。基础功能只使用 Python 标准库，不需要安装第三方 Python 包。

在项目根目录打开终端：

```bash
python tools/serve.py --open
```

打开 `http://127.0.0.1:8765/`，点击“写代码”，输入短小的 Python 代码后点击“编译并演出”。Windows 也可以双击 `start.bat`。macOS/Linux 可将 `python` 换为 `python3`。

```python
def add_bonus(score):
    return score + 5

score = add_bonus(80)
```

本地服务会真实执行输入代码，仅用于自己的电脑和可信代码。默认监听 `127.0.0.1`，请保持这一设置；超时与事件数量限制用于避免卡住演示，不构成代码安全沙箱。

## 预设示例

| 示例 | 观察重点 |
| --- | --- |
| 函数调用与返回 | 进入函数、处理参数、返回结果 |
| 容器与共享引用 | 多个名字连接同一份列表和字典中的数据关系 |
| 对象、属性与方法 | 创建对象、调用方法、修改内容 |
| 闭包保留的变量 | 内部函数记住之前的数据 |
| 接住异常后继续 | 处理错误后继续执行 |
| 越界与错误停止 | 定位访问不存在位置的错误 |
| 递归与调用折叠 | 重复调用、省略展示和递归错误 |

## 构建公开演示版

仓库包含构建好的 `public-release/site/`，下载后可直接预览：

```bash
python tools/serve-public.py --port 8877
```

打开 `http://127.0.0.1:8877/`。修改示例或网页后，使用 **Node.js 22 或更新版本**重新构建；不需要 `npm install`：

```bash
python tools/build-demos.py
node tools/build-public.mjs
```

只发布 `public-release/site/`，不要把本地 Python 执行服务作为公网服务部署。仓库提供 `netlify.toml` 和手动触发的 GitHub Pages 工作流，具体步骤见[上传与部署说明](docs/GITHUB_UPLOAD.md)。

## 人工智能怎样参与

Codex 在制作阶段协助编写代码、调整界面、改善模型效果和排查问题。学生负责提出需求、选择表达方式和检查实际效果。

运行时默认使用规则把真实执行记录转换为舞台动作，不需要调用大模型。可选的 `pipeline/llm_actions.py` 支持通过兼容接口让模型协助组织动作，结果仍经过一致性检查；失败时退回规则版本。本地问答没有密钥时使用内置资料与当前帧信息作答。公开静态版不提供在线问答服务。

## 目录

```text
nawa-studio/
├── pipeline/                执行记录、动作编译、检查和问答
├── web/                     本地版网页、模型与本地 Three.js 文件
├── demos/                   七段公开示例的 Python 源码
├── fixtures/golden_cases/   保留的回归样例与原始记录
├── tests/                   Python 自动检查
├── tools/                   启动、构建和模型处理工具
├── public-release/
│   ├── recordings/          公开示例的执行与动画数据
│   └── site/                可直接部署的静态网页
├── docs/                    运行、实现、上传说明及截图
│   └── course/              课程报告和答辩文字提纲
├── .github/workflows/       自动检查及 GitHub Pages 部署
├── requirements.txt         说明基础功能无需额外 Python 包
├── package.json             常用 Node 脚本命令，无 npm 依赖
└── start.bat                Windows 本地启动入口
```

## 检查项目

```bash
python -m unittest discover -s tests -v
python tools/check-release.py
```

回归样例生成时的 Python 版本、事件数量可能与当前环境不同。`fixtures/golden_cases/` 是测试基准，不需要为普通运行重新生成。更多技术细节见 [IMPLEMENTATION.md](docs/IMPLEMENTATION.md)。

## 当前边界

- 公开版以七段预设示例回放为主，问答需要本地服务。
- 当前角色没有完整骨骼或独立五官控制，主要通过整体姿态和文字表达状态。
- 重复调用过多时会折叠部分过程，并给出说明。
- 三维画面依赖浏览器 WebGL 支持。
- `web/python-client.js`、`web/python-worker.js` 与 `pipeline/browser_bridge.py` 是尚未接入当前页面的浏览器 Python 实验源码，详见[实验状态](docs/BROWSER_RUNTIME.md)。

## 材料与许可

[课程报告](docs/course/奶蛙舞台人工智能导论课程报告.docx) · [答辩文字提纲](docs/course/答辩PPT内容提纲.md) · [第三方组件和模型说明](THIRD_PARTY_NOTICES.md)

项目尚未为自有代码和角色素材选择统一开源许可证；公开仓库本身不自动授予这些内容的再利用许可。Three.js 文件遵循其 MIT 许可证，完整文本已保留在仓库中。
