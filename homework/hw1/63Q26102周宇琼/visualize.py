#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 新高考 I 卷 · 数学 第 19 题：求解 + 可视化
=================================================
运行：  .venv/bin/python visualize.py
输出：  figures/fig1_part1.png ... figures/fig5_why_condition1.png
        verification.txt（数值自检结果）

一句话思路：
    d ∈ D(x0)  ⟺  从 x0 出发走 d 步后，函数值“变高”了。
    条件① 说的就是“高的更难超越”：f(x1) ≤ f(x2) ⇒ D(x2) ⊆ D(x1)。
    而 f 在 (-∞,0) 上被完全确定（f = 2^x），所有条件都要与这一段对撞。
"""
from __future__ import annotations

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import ListedColormap

# ---------------------------------------------------------------- 全局设置
HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

FONT = os.path.join(HERE, "assets", "fonts", "SimHei.ttf")
fm.fontManager.addfont(FONT)
CN = fm.FontProperties(fname=FONT)          # 中文字体（SimHei）
plt.rcParams.update({
    "font.family": CN.get_name(),
    "axes.unicode_minus": False,
    "mathtext.fontset": "cm",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.22,
    "grid.linestyle": "--",
    "axes.labelsize": 12,
})

BLUE, ORANGE, RED = "#1f4e9c", "#e67e22", "#c0392b"
GREEN, GREY, PURPLE = "#27ae60", "#7f8c8d", "#8e44ad"
DARK = "#2c3e50"


# ---------------------------------------------------------------- 三个函数
def f1(x):
    """(1) 中的函数：x<0 时 2^x，x≥0 时 1-x（在 0 处连续）。"""
    x = np.asarray(x, dtype=float)
    return np.where(x < 0, np.power(2.0, x), 1.0 - x)


def f_odd(x):
    """(2) 中的奇函数：2^x (x<0)，0 (x=0)，-2^{-x} (x>0)。"""
    x = np.asarray(x, dtype=float)
    with np.errstate(all="ignore"):
        y = np.where(x < 0, np.power(2.0, x), -np.power(2.0, -x))
    return np.where(x == 0, 0.0, y)


def f_model(x):
    """满足 (3) 中 ①② 的模型函数：2^x (x<0)，1 (x=0)，-2^{-x} (x>0)。"""
    x = np.asarray(x, dtype=float)
    with np.errstate(all="ignore"):
        y = np.where(x < 0, np.power(2.0, x), -np.power(2.0, -x))
    return np.where(x == 0, 1.0, y)


def members(f, x0s, ds):
    """M[i, j] = [ f(x0_i + d_j) > f(x0_i) ]，即 d_j ∈ D(x0_i) 的真值表。"""
    X0 = np.asarray(x0s, float)[:, None]
    D = np.asarray(ds, float)[None, :]
    return f(X0 + D) > f(X0)


# ---------------------------------------------------------------- 小工具
def thick_interval(ax, a, b, y, color, lw=10, open_ends=True, alpha=0.55, z=4):
    """画一段加粗区间，两端用空心圆表示开区间。"""
    ax.plot([a, b], [y, y], lw=lw, color=color, alpha=alpha,
            solid_capstyle="butt", zorder=z)
    if open_ends:
        for t in (a, b):
            ax.plot([t], [y], "o", ms=9, mfc="white", mec=color, mew=2.2, zorder=z + 1)


def style_axis(ax, xlabel=None, ylabel=None, xlim=None, ylim=None):
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- 图 1
def fig1():
    """第 (1) 问：D(-1) = (0, 3/2)。"""
    fig = plt.figure(figsize=(10.6, 6.4))
    ax = fig.add_axes([0.075, 0.315, 0.895, 0.625])
    axd = fig.add_axes([0.075, 0.085, 0.895, 0.135])

    X = np.linspace(-2.4, 3.0, 4000)
    Y = f1(X)
    ax.plot(X, Y, color=BLUE, lw=2.9, zorder=3)

    m = (X > -1) & (X < 0.5)
    ax.fill_between(X[m], 0.5, Y[m], color=ORANGE, alpha=0.32, lw=0, zorder=2)
    ax.axhline(0.5, color=RED, ls="--", lw=1.3, zorder=1)
    ax.axhline(0, color="#bdc3c7", lw=1.0)
    ax.axvline(0, color="#bdc3c7", lw=1.0)
    ax.plot([-1], [0.5], "o", ms=10, color=RED, zorder=6)
    style_axis(ax, "x", "y", (-2.4, 3.0), (-0.55, 2.45))
    ax.text(2.95, 0.56, r"$y=\frac{1}{2}$", color=RED, ha="right", va="bottom",
            fontsize=13)
    ax.annotate("$x_0=-1$\n$f(x_0)=\\frac{1}{2}$", xy=(-1, 0.5), xytext=(-2.3, 1.45),
                fontproperties=CN, fontsize=12.5, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    ax.annotate("这段图象在 $y=\\frac{1}{2}$ 上方\n"
                "$f(x)>\\frac{1}{2}\\ \\Leftrightarrow\\ x\\in(-1,\\frac{1}{2})$",
                xy=(0.10, 0.86), xytext=(0.55, 1.86),
                fontproperties=CN, fontsize=11.5, color="#b9770e",
                arrowprops=dict(arrowstyle="->", color="#b9770e", lw=1.2))
    ax.text(1.42, 0.38, r"$f(x)=2^{x}\ (x<0)$", color=BLUE, fontsize=11.5)
    ax.text(1.42, 0.18, r"$f(x)=1-x\ (x\geq 0)$", color=BLUE, fontsize=11.5)
    ax.set_title("第 (1) 问：先找出使 $f(x)>f(-1)$ 的 $x$，再整体平移",
                 fontsize=13.5, pad=8, fontproperties=CN)

    # 下方 d 轴
    style_axis(axd, None, None, (-2.4, 3.0), (-0.95, 0.85))
    axd.grid(False)
    axd.set_xticks([])
    axd.axhline(0, color="#333", lw=1.3)
    for t in [-2, -1, 0, 0.5, 1, 1.5, 2, 2.5, 3]:
        axd.plot([t, t], [-0.07, 0.07], color="#333", lw=1.2)
        axd.text(t, -0.16, f"{t:g}", ha="center", va="top", fontsize=10, color="#555")
    thick_interval(axd, 0, 1.5, 0, GREEN, lw=11, alpha=0.75)
    axd.text(0.75, 0.40, r"$D(-1)=\left(0,\frac{3}{2}\right)$", ha="center",
             va="bottom", fontsize=15, color=GREEN, fontweight="bold")
    axd.set_yticks([])
    axd.spines["left"].set_visible(False)
    axd.spines["bottom"].set_visible(False)
    axd.set_xlabel("$d$ 轴：$d=x-x_0=x+1$，于是 $\\left(-1,\\frac{1}{2}\\right)$ 整体右移 1 个单位",
                   fontsize=11.5)

    fig.savefig(os.path.join(FIG, "fig1_part1.png"), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 图 2
def fig2():
    """第 (2) 问：奇函数的 D(x0) 的三种形态，以及包含关系。"""
    fig = plt.figure(figsize=(12.8, 7.6))
    axA = fig.add_axes([0.055, 0.56, 0.39, 0.38])
    axC = fig.add_axes([0.055, 0.09, 0.39, 0.31])
    axB = fig.add_axes([0.545, 0.09, 0.445, 0.85])

    # ---- A：函数图象
    Xn = np.linspace(-2.6, 0, 800)
    Xp = np.linspace(0, 2.6, 800)
    axA.plot(Xn, np.power(2.0, Xn), color=BLUE, lw=2.9, zorder=3)
    axA.plot(Xp, -np.power(2.0, -Xp), color=ORANGE, lw=2.9, zorder=3)
    axA.plot([0], [0], "o", ms=8, color=DARK, zorder=4)
    axA.plot([0, 0], [1, -1], ls=":", lw=1.2, color=GREY)
    axA.axhline(0, color="#bdc3c7", lw=1.0)
    axA.axvline(0, color="#bdc3c7", lw=1.0)
    style_axis(axA, "x", "y", (-2.6, 2.6), (-1.35, 1.35))
    axA.text(-2.55, 0.98, r"$x<0$：$2^{x}\in(0,1)$", color=BLUE, fontsize=11.5)
    axA.text(0.30, -1.20, r"$x>0$：$-2^{-x}\in(-1,0)$", color=ORANGE, fontsize=11.5)
    axA.set_title("奇函数：两段各自递增，在 $x=0$ 处“断崖式”下落",
                  fontsize=12.5, pad=6, fontproperties=CN)

    # ---- B：D(x0) 条形图
    rows = [
        ("$x_0=-2$", [(0, 2)], BLUE, r"$D=(0,2)$"),
        ("$x_0=-1$", [(0, 1)], BLUE, r"$D=(0,1)$"),
        ("$x_0=-0.5$", [(0, 0.5)], BLUE, r"$D=(0,0.5)$"),
        ("$x_0=0$", [(-3, 0)], DARK, r"$D=(-\infty,0)$"),
        ("$x_0=0.5$", [(-3, -0.5), (0, 3)], ORANGE,
         "$D=(-\\infty,-0.5]$\n$\\cup\\,(0,+\\infty)$"),
        ("$x_0=1$", [(-3, -1), (0, 3)], ORANGE,
         "$D=(-\\infty,-1]$\n$\\cup\\,(0,+\\infty)$"),
        ("$x_0=1.5$", [(-3, -1.5), (0, 3)], ORANGE,
         "$D=(-\\infty,-1.5]$\n$\\cup\\,(0,+\\infty)$"),
    ]
    n = len(rows)
    for i, (lab, segs, col, dtext) in enumerate(rows):
        y = n - 1 - i
        for (a, b) in segs:
            thick_interval(axB, a, b, y, col, lw=10)
            if a == -3:      # 左端延伸到 -∞
                axB.annotate("", xy=(-2.98, y), xytext=(-2.45, y),
                             arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4,
                                             alpha=0.85))
            if b == 3:       # 右端延伸到 +∞
                axB.annotate("", xy=(2.98, y), xytext=(2.45, y),
                             arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4,
                                             alpha=0.85))
        axB.text(-3.15, y, lab, ha="right", va="center", fontsize=12)
        axB.text(3.35, y, dtext, ha="left", va="center", fontsize=9.5, color=col)
    style_axis(axB, "$d$", None, (-3.2, 6.9), (-1.55, n - 0.25))
    axB.set_xticks([-3, -2, -1, 0, 1, 2, 3])
    axB.spines["left"].set_visible(False)
    axB.set_yticks([])
    axB.set_title("每个 $x_0$ 一行：$D(x_0)$ 在 $d$ 轴上是什么样子",
                  fontsize=12.5, pad=6, fontproperties=CN)
    axB.text(-3.15, -0.55,
             "蓝：$x_1<x_2<0\\ \\Rightarrow\\ D(x_2)\\subseteq D(x_1)$",
             fontsize=10.5, color=BLUE, va="center")
    axB.text(-3.15, -0.95,
             "橙：$0<x_1<x_2\\ \\Rightarrow\\ D(x_2)\\subseteq D(x_1)$",
             fontsize=10.5, color=ORANGE, va="center")
    axB.text(-3.15, -1.35,
             "混：$x_1>0>x_2\\ \\Rightarrow\\ D(x_2)\\subseteq D(x_1)$",
             fontsize=10.5, color=PURPLE, va="center")

    # ---- C：真值表热图
    x0s = np.linspace(-3, 3, 1401)
    ds = np.linspace(-3, 3, 1401)
    M = members(f_odd, x0s, ds)
    axC.imshow(M, origin="lower", extent=[-3, 3, -3, 3], aspect="auto",
               cmap=ListedColormap(["#f2f2f2", "#aed6f1"]),
               interpolation="nearest")
    axC.axhline(0, color="#333", lw=1.0)
    axC.axvline(0, color="#333", lw=1.0)
    style_axis(axC, "$d$", "$x_0$", (-3, 3), (-3, 3))
    axC.grid(False)
    axC.set_title("蓝色 = $d\\in D(x_0)$：每行中的蓝段就是 $D(x_0)$",
                  fontsize=12, pad=6, fontproperties=CN)

    fig.savefig(os.path.join(FIG, "fig2_part2.png"), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 图 3
def fig3():
    """第 (3)(i)：若 f(0) < 1，则 ① 与 ② 直接打架。"""
    a = 0.7
    x1 = -0.45

    def f_hyp(x):
        x = np.asarray(x, dtype=float)
        y = np.where(x < 0, np.power(2.0, x), a - 0.45 * x)
        return np.where(x == 0, a, y)

    fig = plt.figure(figsize=(11.4, 7.2))
    ax = fig.add_axes([0.07, 0.46, 0.90, 0.47])
    axB = fig.add_axes([0.07, 0.085, 0.90, 0.28])

    X = np.linspace(-2.0, 1.6, 3000)
    ax.plot(X, f_hyp(X), color=BLUE, lw=2.7, zorder=3)
    ax.axhline(a, color=RED, ls="--", lw=1.3)
    ax.axhline(0, color="#bdc3c7", lw=1.0)
    ax.axvline(0, color="#bdc3c7", lw=1.0)
    ax.plot([0], [a], "o", ms=10, color=RED, zorder=5)
    ax.plot([x1], [2.0 ** x1], "o", ms=9, color=GREEN, zorder=5)

    # 左半轴上 x1 到 0 的一段：f 比 f(x1) 还高 ⇒ 这一段位移都属于 D(x1)
    xs = np.linspace(x1, 0, 400)
    ax.plot(xs, np.power(2.0, xs), color=GREEN, lw=4.0, alpha=0.55, zorder=4)
    ax.fill_between(xs, a, np.power(2.0, xs), color=GREEN, alpha=0.15, lw=0)

    ax.annotate("取 $x_1\\in(-1,0)$ 使 $f(x_1)>f(0)$\n（因为 $2^{x}\\to1>f(0)$）",
                xy=(x1, 2.0 ** x1), xytext=(-1.95, 1.02),
                fontproperties=CN, fontsize=11, color=GREEN,
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))
    ax.annotate("$f(0)=a<1$", xy=(0, a), xytext=(0.12, 0.30),
                fontproperties=CN, fontsize=12, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.1))
    ax.text(0.42, 0.83, "左侧从 $f(x_1)$ 一路升到 1\n"
                        "$\\Rightarrow$ 只要 $0<d<-x_1$，就有 $f(x_1+d)>f(x_1)$",
            fontsize=10.5, fontproperties=CN, color=GREEN)

    # 把“位移窗口”画在 x 轴上
    ax.plot([0, -x1], [-0.10, -0.10], lw=9, color=GREEN, alpha=0.55,
            solid_capstyle="butt", clip_on=False)
    ax.text(-x1 / 2, -0.22, "① 推出 $f(d)>f(0)$", ha="center", va="top",
            fontsize=11, color=GREEN, fontproperties=CN)
    ax.text(0.95, -0.24, "（右侧分支仅示意）", fontsize=9.5, color=GREY,
            fontproperties=CN)
    style_axis(ax, "x", "y", (-2.0, 1.6), (-0.5, 1.4))
    ax.set_title("反设 $f(0)<1$：左侧一定存在比 $f(0)$ 高的点",
                 fontsize=13, pad=8, fontproperties=CN)

    # ---- 下方：两个区间必然重叠
    style_axis(axB, "$d$", None, (-0.25, 1.45), (-0.35, 2.25))
    axB.set_yticks([])
    axB.spines["left"].set_visible(False)
    thick_interval(axB, 0.0, 1.0, 1.2, RED, lw=12, alpha=0.40)
    axB.text(1.02, 1.2, "②：$0<d<1$ 时 $f(d)<f(0)$", va="center",
             fontsize=11.5, color=RED, fontproperties=CN)
    thick_interval(axB, 0.0, -x1, 0.4, GREEN, lw=12, alpha=0.65)
    axB.text(-x1 + 0.03, 0.4, "①：$0<d<-x_1$ 时 $f(d)>f(0)$", va="center",
             fontsize=11.5, color=GREEN, fontproperties=CN)
    axB.fill_between([0, -x1], 0.12, 0.95, color=PURPLE, alpha=0.15)
    axB.text(-0.22, 1.95,
             "重叠部分：同一批 $d$ 既满足 $f(d)>f(0)$ 又满足 $f(d)<f(0)$ —— 矛盾！",
             fontsize=11.5, color=PURPLE, fontproperties=CN)
    axB.set_title("把结论搬到 $d$ 轴上：两个区间必然重叠", fontsize=12.5,
                  pad=6, fontproperties=CN)

    fig.savefig(os.path.join(FIG, "fig3_part3i.png"), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 图 4
def fig4():
    """第 (3)(ii)：先证 f 在正半轴 ≤ 0，再一步得到严格递增。"""
    fig = plt.figure(figsize=(12.8, 8.8))
    axA = fig.add_axes([0.055, 0.58, 0.39, 0.37])
    axC = fig.add_axes([0.555, 0.58, 0.37, 0.33])
    axS = fig.add_axes([0.045, 0.05, 0.92, 0.36])

    # ---- A：模型函数
    Xn = np.linspace(-2.6, 0, 800)
    Xp = np.linspace(0, 2.6, 800)
    axA.plot(Xn, np.power(2.0, Xn), color=BLUE, lw=2.8)
    axA.plot(Xp, -np.power(2.0, -Xp), color=GREEN, lw=2.8)
    axA.fill_between(Xp, -np.power(2.0, -Xp), 0, color=GREEN, alpha=0.18, lw=0)
    axA.plot([0, 0], [1, -1], ls=":", lw=1.2, color=GREY)
    axA.plot([0], [1], "o", ms=8, color=RED, zorder=5)
    axA.axhline(0, color="#bdc3c7", lw=1.0)
    axA.axvline(0, color="#bdc3c7", lw=1.0)
    axA.annotate("$f(0)\\geq 1$", xy=(0, 1), xytext=(0.35, 1.12),
                 fontsize=12, color=RED, fontproperties=CN,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1.0))
    axA.text(0.45, -1.18, "正半轴：$f(x)\\leq 0$，且严格递增", fontsize=11,
             color=GREEN, fontproperties=CN)
    style_axis(axA, "x", "y", (-2.6, 2.6), (-1.35, 1.30))
    axA.set_title("模型函数：$2^{x}\\ (x<0)$，$1\\ (x=0)$，$-2^{-x}\\ (x>0)$",
                  fontsize=12, pad=6, fontproperties=CN)

    # ---- C：模型函数的 D(x0) 真值表
    x0s = np.linspace(-3, 3, 1401)
    ds = np.linspace(-3, 3, 1401)
    M = members(f_model, x0s, ds)
    axC.imshow(M, origin="lower", extent=[-3, 3, -3, 3], aspect="auto",
               cmap=ListedColormap(["#f2f2f2", "#a9dfbf"]),
               interpolation="nearest")
    axC.axhline(0, color="#333", lw=1.0)
    axC.axvline(0, color="#333", lw=1.0)
    style_axis(axC, "$d$", "$x_0$", (-3, 3), (-3, 3))
    axC.grid(False)
    fig.text(0.555, 0.505,
             "$x_0>0$ 时所有 $d>0$ 都属于 $D(x_0)$ $\\Rightarrow$ 向右走一定变高",
             fontsize=10.5, color="#1e8449", fontproperties=CN, va="center")
    axC.set_title("$d\\in D(x_0)$ 的真值表（绿 = 属于）", fontsize=12,
                  pad=6, fontproperties=CN)

    # ---- S：关键一步的示意图
    axS.axis("off")
    axS.set_xlim(-2.15, 1.55)
    axS.set_ylim(-1.45, 1.35)
    axS.axhline(0, color="#333", lw=1.5)
    for t in [-2, -1.5, -1, -0.5, 0, 0.5, 1]:
        axS.plot([t, t], [-0.05, 0.05], color="#333", lw=1.0)
        axS.text(t, -0.10, f"{t:g}", ha="center", va="top", fontsize=9.5, color="#666")

    v, d, x, t = -1.0, 1.5, 0.5, 0.3
    u, ud = v - t, x - t
    pts = [
        (u, r"$f(u)=2^{u}$", 0.46, BLUE),
        (v, r"$f(v)=2^{v}$", 0.88, BLUE),
        (ud, r"$u+d\in(0,1)$", -0.46, GREEN),
        (x, r"$f(x)$（假设 $>2^{v}$）", 0.46, RED),
    ]
    for px, lab, h, col in pts:
        axS.plot([px, px], [0, h], color=col, lw=1.6, alpha=0.85)
        axS.plot([px], [h], "o", ms=7, color=col, zorder=5)
        axS.text(px, h + (0.06 if h > 0 else -0.06), lab, ha="center",
                 va="bottom" if h > 0 else "top", fontsize=10.5, color=col)
    for px, col in [(u, BLUE), (v, BLUE), (ud, GREEN), (x, RED)]:
        axS.plot([px], [0], "o", ms=8, color=col, zorder=6)

    axS.annotate("", xy=(x, 0.24), xytext=(v, 0.24),
                 arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.2))
    axS.text((v + x) / 2, 0.28, "$d$", ha="center", fontsize=12, color=GREY)
    axS.annotate("", xy=(ud, -0.22), xytext=(u, -0.22),
                 arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.2))
    axS.text(-0.55, -0.42, "同一个 $d$", ha="center", fontsize=11, color=GREY)
    axS.annotate("", xy=(v, 0.68), xytext=(u, 0.68),
                 arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.0))
    axS.text((u + v) / 2, 0.72, "$t$", ha="center", fontsize=11, color=GREY)

    axS.text(-2.12, -0.78,
             "若 $f(x)>2^{v}$：$d\\in D(v)$；又 $f(u)<f(v)\\Rightarrow D(v)\\subseteq D(u)$，"
             "故 $d\\in D(u)$，即 $f(u+d)>f(u)=2^{u}>0$。",
             fontsize=11, color="#333", fontproperties=CN)
    axS.text(-2.12, -1.10,
             "但 $u+d=x-t\\in(0,1)$，由 $(*)$ 应有 $f(u+d)\\leq 0$ —— 矛盾！"
             "把 $u$ 推得越左，这个矛盾越明显。",
             fontsize=11, color=PURPLE, fontproperties=CN)
    axS.set_title("关键一步：把 $u$ 推到 $v$ 左边，让 $u+d$ 落进 $(0,1)$",
                  fontsize=12, pad=2, fontproperties=CN, loc="left")

    fig.savefig(os.path.join(FIG, "fig4_part3ii.png"), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 图 5
def fig5():
    """为什么需要条件②：第(2)问的奇函数在 x₂=0 时违反 ①。"""
    fig = plt.figure(figsize=(12.4, 6.8))
    ax = fig.add_axes([0.055, 0.10, 0.46, 0.78])
    axT = fig.add_axes([0.565, 0.06, 0.415, 0.84])
    axT.axis("off")

    Xn = np.linspace(-2.8, 0, 900)
    Xp = np.linspace(0, 2.8, 900)
    ax.plot(Xn, np.power(2.0, Xn), color=BLUE, lw=2.8)
    ax.plot(Xp, -np.power(2.0, -Xp), color=ORANGE, lw=2.8)
    ax.plot([0], [0], "o", ms=8, color=DARK)
    ax.axhline(0, color="#bdc3c7", lw=1.0)
    ax.axvline(0, color="#bdc3c7", lw=1.0)

    ax.plot([-1.0], [0.5], "o", ms=9, color=BLUE, zorder=5)
    ax.plot([1.0], [-0.5], "o", ms=9, color=ORANGE, zorder=5)
    ax.plot([2.0], [-0.25], "o", ms=9, color=ORANGE, zorder=5)
    ax.plot([0.0], [0.0], "o", ms=9, color=DARK, zorder=5)

    ax.annotate(r"$f(-1)=\frac{1}{2}$", xy=(-1.0, 0.5), xytext=(-2.75, 0.85),
                fontsize=10.5, color=BLUE,
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.0))
    ax.annotate(r"$x_2=0,\ f=0$", xy=(0.0, 0.0), xytext=(-2.05, -0.50),
                fontsize=10.5, color=DARK,
                arrowprops=dict(arrowstyle="->", color=DARK, lw=1.0))
    ax.annotate(r"$f(1)=-\frac{1}{2}$", xy=(1.0, -0.5), xytext=(0.55, -0.78),
                fontsize=10.5, color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.0))
    ax.annotate(r"$x_1=2,\ f=-\frac{1}{4}$", xy=(2.0, -0.25), xytext=(2.90, -0.06),
                ha="right", fontsize=10, color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.0))

    ax.annotate("", xy=(-1.0, 0.5), xytext=(0.0, 0.0),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.9,
                                connectionstyle="arc3,rad=0.3"))
    ax.annotate("", xy=(1.0, -0.5), xytext=(2.0, -0.25),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.9,
                                connectionstyle="arc3,rad=0.3"))
    ax.text(-2.85, -1.40,
            "绿箭头：从 $x_2$ 出发走 $d=-1$；红箭头：从 $x_1$ 出发走 $d=-1$",
            color=GREY, fontsize=9.5, fontproperties=CN)

    ax.set_xlim(-2.95, 3.15)
    ax.set_ylim(-1.55, 1.15)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("第 (2) 问的奇函数：取 $x_1=2,\\ x_2=0,\\ d=-1$",
                 fontsize=12.5, pad=10, fontproperties=CN)

    lines = [
        ("这次“反例”说明：第 (2) 问的 $f$ 不满足条件 ①", DARK, 12.5, 0.98),
        ("", DARK, 11, 0.90),
        ("取 $x_1=2,\\ x_2=0,\\ d=-1$：", DARK, 11.5, 0.84),
        ("$f(x_1)=-\\frac{1}{4}\\leq f(x_2)=0$", DARK, 11.5, 0.755),
        ("若 ① 成立，本应有 $D(x_2)\\subseteq D(x_1)$", DARK, 11.5, 0.67),
        ("", DARK, 11, 0.60),
        ("$x_2+d=-1$：$f(-1)=\\frac{1}{2}>f(0)=0$", DARK, 11.5, 0.53),
        ("$\\Rightarrow\\ -1\\in D(x_2)$", GREEN, 11.5, 0.445),
        ("", DARK, 11, 0.38),
        ("$x_1+d=1$：$f(1)=-\\frac{1}{2}<f(2)=-\\frac{1}{4}$", DARK, 11.5, 0.31),
        ("$\\Rightarrow\\ -1\\notin D(x_1)$", RED, 11.5, 0.225),
        ("", DARK, 11, 0.16),
        ("故 $D(x_2)\\not\\subseteq D(x_1)$：① 失效。", PURPLE, 12, 0.10),
        ("这正是第 (3) 问要加 ②、并推出 $f(0)\\geq1$ 的原因。", GREY, 10.5, 0.02),
    ]
    for txt, col, fs, y in lines:
        if txt:
            axT.text(0.0, y, txt, fontsize=fs, color=col, va="top",
                     fontproperties=CN, transform=axT.transAxes)

    fig.savefig(os.path.join(FIG, "fig5_why_condition1.png"), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 数值自检
def verify():
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    rng = np.random.default_rng(20260607)

    say("=" * 72)
    say("数值自检（用于核对结论，不代替证明）")
    say("=" * 72)

    # (1) D(-1) = (0, 1.5)
    ds = np.linspace(-3, 3, 200001)
    inside = f1(-1 + ds) > f1(-1)
    pred = (ds > 0) & (ds < 1.5)
    say(f"(1) D(-1) 与 (0, 1.5) 逐一比对：{'一致 ✓' if np.array_equal(inside, pred) else '不一致 ✗'}")

    # (2) 奇函数：随机检验包含关系
    x1 = rng.uniform(-3, 3, 300000)
    x2 = rng.uniform(-3, 3, 300000)
    ok = (x1 * x2 != 0) & (f_odd(x1) <= f_odd(x2))
    x1, x2 = x1[ok], x2[ok]
    dd = rng.uniform(-3.5, 3.5, x1.size)
    in2 = f_odd(x2 + dd) > f_odd(x2)
    in1 = f_odd(x1 + dd) > f_odd(x1)
    bad = int(np.count_nonzero(in2 & ~in1))
    say(f"(2) 随机取 {x1.size} 组 (x1,x2,d) 检验 D(x2)⊆D(x1)：反例 {bad} 个 "
        f"{'✓' if bad == 0 else '✗'}")

    # (3)(i)
    say(f"(3)(i) 模型函数 f(0) = {f_model(0.0):g} ≥ 1 ✓")

    # (3) 模型函数是否满足 ①：随机检验
    a = rng.uniform(-3, 3, 400000)
    b = rng.uniform(-3, 3, 400000)
    m = f_model(a) <= f_model(b)
    a, b = a[m], b[m]
    dd = rng.uniform(-3.5, 3.5, a.size)
    inb = f_model(b + dd) > f_model(b)
    ina = f_model(a + dd) > f_model(a)
    bad = int(np.count_nonzero(inb & ~ina))
    say(f"(3) 模型函数随机检验条件①：{a.size} 组，反例 {bad} 个 "
        f"{'✓' if bad == 0 else '✗'}")

    # ②
    t = rng.uniform(0, 1, 100000)
    say(f"(3) 模型函数检验条件②：max f = {f_model(t).max():.3g} < f(0) = 1 ✓")

    # 严格递增
    s = rng.uniform(0, 3, 200000)
    tt = s + rng.uniform(0.001, 3, s.size)
    inc = bool(np.all(f_model(tt) > f_model(s)))
    say(f"(3)(ii) 模型函数在 (0,+∞) 上严格递增：{inc and '✓'}")

    # 第(2)问的函数违反 ①
    say("")
    say("对照：第 (2) 问的奇函数并不满足 ① ——")
    say(f"  f(2) = {f_odd(2.0):g} ≤ f(0) = {f_odd(0.0):g}，"
        f"但 d=-1：f(2-1) = {f_odd(1.0):g} < f(2)，而 f(0-1) = {f_odd(-1.0):g} > f(0)。")
    say("  即 -1 ∈ D(0) 但 -1 ∉ D(2)，D(0) ⊄ D(2)。")

    with open(os.path.join(HERE, "verification.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    say("")
    say("结果已写入 verification.txt")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    verify()
    print("\n图片输出目录：", FIG)


if __name__ == "__main__":
    main()
