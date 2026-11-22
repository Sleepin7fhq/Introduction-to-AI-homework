# 第三方组件与素材说明

## Three.js

本项目保留 Three.js r160 的本地副本与配套文件，包括：

- `web/vendor/three.module.js`
- `web/vendor/OrbitControls.js`
- `web/vendor/loaders/GLTFLoader.js`
- `web/vendor/utils/BufferGeometryUtils.js`

公开构建会把相同组件复制到 `public-release/site/vendor/`。版权标识为 Copyright 2010–2023 Three.js Authors，许可为 MIT，完整文本见 [licenses/threejs-MIT.txt](licenses/threejs-MIT.txt)。项目地址：https://github.com/mrdoob/three.js 。

## 角色模型和图片

角色原始模型与参考图来自本课程项目中提供的素材。整理时保留原始模型、当前显示模型与处理纹理，以支持运行和再生成。现有目录没有提供这些素材的独立授权文件，因此本说明不替素材提供者授予再分发或商业使用许可。

## 自有代码与课程材料

尚未为自有代码、课程报告和角色素材选择统一开源许可证。上传 GitHub 与授予开源使用权是两回事，后续可由作者根据素材权利决定。课程制作中使用 Codex 协助编写、修改与排查，演示过程以真实执行记录为依据。

## 未纳入的实验运行包

原工作目录中尚未接入主页面的 Pyodide 二进制运行包没有纳入本整理版，实验源码与当前状态见 [docs/BROWSER_RUNTIME.md](docs/BROWSER_RUNTIME.md)。本项目基础运行不需要安装它。
