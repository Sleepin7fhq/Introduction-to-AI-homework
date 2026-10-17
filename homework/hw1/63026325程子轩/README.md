# 用 DeepSeek Harness 求解一道 0/0 型极限

> 课程 Demo 实践 · 数学题求解 · 完整过程与材料

## 一、原题

求极限

$$
\lim_{x\to 0}\frac{(1+mx)^n-(1+nx)^m}{x^2},\qquad m,n\in\mathbb N_+
$$

**来源**：《高等数学》"函数与极限"一章的课后习题（第 (b) 小题），m、n 为正整数。

**答案**：

$$
L=\frac{mn(n-m)}{2}
$$

## 二、目录结构

```
demo-limit/
├── generate.mjs                 ★ 唯一的生成脚本（验证 + 数据 + 12 页排版 + 导出）
├── README.md                    本文件：题目、结构、生成流程、提交说明
├── prompt.md                    提示词记录（含迭代与自检）
├── package.json                 npm 脚本入口
├── out/
│   ├── 一道极限题-求解与验证.pptx   交付 PPT（12 页，16:9）
│   └── 一道极限题-求解与验证.pdf    PDF 版，便于在线预览
└── preview/                     12 张页面 PNG（GitHub 上可直接看）
```

## 三、生成流程（可完整复现）

所有步骤都在 `generate.mjs` 一个文件里，按顺序执行、不依赖任何中间数据文件：

```
   generate.mjs
   ├─【1/4】数值验证    公式值 vs 直接代值 → 打印对照表（含灾难性抵消的演示）
   ├─【2/4】计算数据    6 组表格 / 16 点曲线 / 8×8 相图 全部在内存里算好
   ├─【3/4】排版幻灯片  12 页逐页绘制 → out/*.pptx
   └─【4/4】导出预览    （可选 --preview）PNG × 12 + PDF，脚本内联 PowerShell
```

```bash
npm install             # 只装 pptxgenjs
node generate.mjs       # 验证 + 生成 PPT
node generate.mjs --preview   # 上面全部 + 导出 PNG 与 PDF（需 Windows + PowerPoint）
node generate.mjs --dump      # 额外把数据写成 code/series.json，便于检查
```

也可以用 npm 别名：`npm run build` / `npm run preview` / `npm run all`。

> 两个实现细节：
> 1. 内联的 PowerShell 片段故意写成纯 ASCII。Windows PowerShell 5.1 会把无 BOM 的非 ASCII
>    `.ps1` 当 ANSI 解析，中文注释会直接导致语法错误——这是调试时踩到的坑。
> 2. 需要导出预览时，脚本会把这段 PowerShell 写到系统临时目录再执行、执行完删除，
>    所以仓库里只有 `generate.mjs` 一个脚本文件。

## 四、PPT 的 12 页结构

| 页 | 内容 |
|---|---|
| 01 | 封面：题目、答案、工具链 |
| 02 | 原题与来源；三个观察（0/0、一次项抵消、只剩 x²） |
| 03 | 解法一：二项式展开（主推） |
| 04 | 解法二：二阶导数 / 二阶零点 |
| 05 | 解法三：两次洛必达，及其与展开的等价性 |
| 06 | 结果与特例：m=n、反对称性 |
| 07 | 代码（20 行）与运行输出 |
| 08 | 数值表：前三列收敛，x=1e-8 崩坏 |
| 09 | 收敛曲线：从上方逼近 15，误差约 145x |
| 10 | 全景：L(m,n) 的 8×8 反对称相图 |
| 11 | 四个易错点 |
| 12 | 小结与提交材料清单 |

## 五、提交到 GitHub

1. 在班级作业仓库中新建目录，例如 `demo/极限题-学号-姓名/`；
2. 至少包含：`out/*.pptx`、`code/limit.mjs`、`prompt.md`、`README.md`；
3. 建议把 `preview/*.png` 一并提交，README 里引用即可直接显示预览；
4. 提交信息示例：`feat: demo2 — 0/0 型极限 mn(n-m)/2 求解与验证`。

## 六、AI 使用声明

- 题目由本人提供；
- 推导、代码、PPT 由 DeepSeek Harness（dsh）辅助完成，推导经数值实验交叉验证；
- `prompt.md` 记录了完整的提示词与两次自查修正（"45x → 145x"、"易错点补充"），可复现整个过程。
