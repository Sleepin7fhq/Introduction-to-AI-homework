# 手语译窗

东南大学《人工智能通识导论》课程小组作品。网页支持 203 个国家通用手语孤立词，提供摄像头、本地单动作视频和三条公开样例。每次输出一个首选和四个候选，在浏览器本地完成骨架提取与模型推理。

## 提交到班级 GitHub

1. 解压外层 ZIP。在 `materials` 中打开 Word 报告和 PPT，把小组号、成员姓名、学号和实际分工填写完整。PDF 是与 Word 同内容的排版参考，填写后用于提交的 PDF 请从更新过的 Word 重新导出。
2. 把解压目录内的文件和文件夹上传到班级 GitHub 规定的作品目录。手机界面已经整合到原入口 `index.html`，保持它与 `assets`、`materials`、`research` 同层。每份模型文件小于 25 MiB。ZIP 用于传递材料，仓库中放解压后的文件。
3. 如果原网站已经发布，把新版覆盖到原来的发布目录即可沿用原网址。需要启用 GitHub Pages 且作品位于发布分支根目录时，在 **Settings → Pages → Deploy from a branch** 中选择该分支及 `/(root)`。按小组子目录提交时，沿用班级仓库指定路径。
4. 页面和识别资源一起托管，JS、模型、样例与 MediaPipe WASM 均从同一站点加载。老师提供国内可访问的 HTTPS 静态站点时，可把同一个目录部署到该站点。GitHub Pages 在目标网络上的可达性可以用演示当天的手机网络检查。

[GitHub Pages 配置说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [浏览器摄像头权限说明](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)

## 本地展示

在解压目录运行 `python local_preview.py`，浏览器会打开本地页面。网页文件解压后即可用本地服务演示，摄像头、模型和样例都在本机运行。手机查看线上版本时，用 Safari 或 Chrome 打开原部署地址。若安卓已安装 Termux 与 Python，可在手机上解压完整包，运行 `python local_preview.py --port 8765 --no-open`，然后用同一部手机打开 `http://127.0.0.1:8765/`。

- 摄像头模式下，点「打开摄像头」并授权，让双肩和双手入镜。点击「录一段并识别」，看到「录制中」后做一个完整手语词。录制约 1.7 秒。
- 可以点「相册视频」，选择约 2 秒的本地短视频。单张照片缺少动作轨迹。手机摄像头需要 HTTPS 或本机地址，图像处理需要浏览器支持 WebGL。
- 现场汇报可先点「试内置样例」→「跑」→「播放并识别」。从候选中选词，或展开「文字记录」添加首选词。

- **PPT** `materials/三分钟答辩.pptx`，5 页含演讲者备注。
- **报告** `materials/创意报告.docx` 与 `materials/创意报告.pdf`。
- **讲稿** `materials/三分钟讲稿.md`。
- **研究代码** `research/`。包括数据筛选、骨架提取、训练和复核。

## 评估口径

国家通用手语 203 词。训练集 7 位手语者、1421 条动作，固定测试集 3 位手语者、609 条动作。网页版本 Top‑1 为 386/609（63.38%），Top‑5 为 504/609（82.76%）。浏览器 JavaScript 核心推理在 609 条已提取骨架上复核，首选标签与对应 Python 版逐条一致。网页样例使用预先提取的骨架，摄像头和本地视频入口进行实时骨架提取。手机现场表现需另测。

所有网页资源都使用相对路径。无需 npm 构建、服务器端推理或 API 密钥。首次加载需要下载浏览器模型与运行资源。项目的词表为孤立词，建议每次识别一个完整动作。

## 资料与署名

- 样例帧与训练数据来自 Jing 等发布的 [NationalCSL-DP v3](https://doi.org/10.6084/m9.figshare.27261843.v3)，CC BY 4.0。样例来自 Participant_01、02、05，取自正面抽帧并与提取关键点配对。发布论文见 [Scientific Data](https://doi.org/10.1038/s41597-025-04986-x)。
- 手部、姿态模型及 JavaScript/WASM 运行时归 [Google AI Edge MediaPipe](https://github.com/google-ai-edge/mediapipe) 作者，使用 Apache 2.0 许可证。项目使用 Tasks Vision 0.10.32。许可证见 `assets/vision/LICENSE`。
