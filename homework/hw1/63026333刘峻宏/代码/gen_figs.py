# -*- coding: utf-8 -*-
"""gen_figs.py —— 生成 PPT 用的示意图（全部由本文件重新生成，可复现）

运行： python gen_figs.py
输出： figures/*.png （300 dpi，白底或透明底）
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.font_manager import FontProperties

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# ---------- 统一视觉 ----------
INK = "#16233A"
BODY = "#3C4A63"
MUTED = "#8A94A6"
LINE = "#D8DEE9"
BLUE = "#2F5FD0"
ORANGE = "#E8833A"
TEAL = "#1E9E8F"
PURPLE = "#7B5BD6"
RED = "#D64545"
BG = "#FFFFFF"

CN = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
CNB = FontProperties(fname=r"C:\Windows\Fonts\msyhbd.ttc")

plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["axes.unicode_minus"] = False


def save(fig, name, transparent=False):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.06,
                transparent=transparent, facecolor="white" if not transparent else "none")
    plt.close(fig)
    print("saved", name)


# ============================================================
# 1. 引理：仿射映射把等距变成等距
# ============================================================
def fig_lemma():
    fig, ax = plt.subplots(figsize=(9.6, 3.1))
    ax.set_xlim(-0.4, 10.6)
    ax.set_ylim(-0.3, 3.4)
    ax.axis("off")

    xs = [1.2, 3.0, 4.8, 6.6, 8.4]
    ax.set_ylim(-0.4, 3.7)
    # 下标轴
    ax.plot([1.0, 8.6], [2.55, 2.55], color=LINE, lw=2, zorder=1)
    for k, x in enumerate(xs):
        ax.plot(x, 2.55, "o", ms=9, color=BLUE, zorder=3)
        ax.text(x, 2.85, f"{k+1}", ha="center", va="bottom",
                fontproperties=CNB, fontsize=13, color=INK)
    ax.text(0.55, 2.55, "下标", ha="right", va="center", fontproperties=CNB,
            fontsize=14, color=INK)

    # 值轴（等差，等距）
    ax.plot([1.0, 8.6], [0.75, 0.75], color=LINE, lw=2, zorder=1)
    for k, x in enumerate(xs):
        ax.plot(x, 0.75, "o", ms=9, color=ORANGE, zorder=3)
        ax.text(x, 0.42, f"a{k+1}", ha="center", va="top",
                fontproperties=FontProperties(fname=r"C:\Windows\Fonts\times.ttf",
                                              style="italic"), fontsize=14, color=INK)
    ax.text(0.55, 0.75, "数列", ha="right", va="center", fontproperties=CNB,
            fontsize=14, color=INK)

    for x in xs:
        ax.annotate("", xy=(x, 0.95), xytext=(x, 2.35),
                    arrowprops=dict(arrowstyle="-|>", color="#B9C3D4", lw=1.1,
                                    shrinkA=2, shrinkB=2))

    ax.text(9.45, 2.55, "等距", ha="left", va="center", fontproperties=CNB,
            fontsize=12.5, color=BLUE)
    ax.text(9.45, 0.75, "等距 × d", ha="left", va="center", fontproperties=CNB,
            fontsize=12.5, color=ORANGE)
    ax.annotate("", xy=(9.35, 1.62), xytext=(9.35, 1.62))
    ax.text(9.3, 1.65, "d ≠ 0", ha="left", va="center", fontproperties=CNB,
            fontsize=13, color=INK)
    ax.text(1.0, 3.45, "公差 d ≠ 0 的等差数列是一条仿射对应：下标等距，项值也等距",
            ha="left", va="center", fontproperties=CNB, fontsize=13.5, color=BODY)
    save(fig, "fig_lemma.png")


# ============================================================
# 2. 第(1)问：三种删法
# ============================================================
def fig_q1():
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.set_xlim(-0.2, 9.6)
    ax.set_ylim(-0.5, 3.3)
    ax.axis("off")

    rows = [
        ((5, 6), [1, 2, 3, 4], BLUE, "(5, 6) 删去 → 剩下的 1,2,3,4 成等差"),
        ((1, 6), [2, 3, 4, 5], ORANGE, "(1, 6) 删去 → 剩下的 2,3,4,5 成等差"),
        ((1, 2), [3, 4, 5, 6], TEAL, "(1, 2) 删去 → 剩下的 3,4,5,6 成等差"),
    ]
    w, h = 0.72, 0.46
    for r, (dele, keep, col, label) in enumerate(rows):
        y = 2.15 - r * 1.05
        for k in range(1, 7):
            x = 1.0 + (k - 1) * 0.86
            del_this = k in dele
            face = "#F2F4F8" if del_this else col
            rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.09",
                                  linewidth=0, facecolor=face, alpha=0.18 if not del_this else 1.0)
            ax.add_patch(rect)
            ax.text(x + w / 2, y + h / 2, str(k), ha="center", va="center",
                    fontproperties=CNB, fontsize=12,
                    color=MUTED if del_this else col)
            if del_this:
                ax.plot([x + 0.12, x + w - 0.12], [y + 0.08, y + h - 0.08],
                        color=RED, lw=1.4, alpha=0.35)
        ax.text(0.4, y + h / 2, ["①", "②", "③"][r], ha="center", va="center",
                fontproperties=CNB, fontsize=13, color=MUTED)
        ax.text(6.6, y + h / 2, label, ha="left", va="center",
                fontproperties=CN, fontsize=11.5, color=BODY)
    ax.text(1.0, 3.0, "把 1…6 摆成一排，划掉两个，剩下四个必须等距", ha="left", va="center",
            fontproperties=CNB, fontsize=13, color=INK)
    save(fig, "fig_q1.png")


# ============================================================
# 3. 第(2)问：(2,13) 的三组 + 尾部
# ============================================================
def fig_q2():
    fig, ax = plt.subplots(figsize=(9.8, 2.9))
    ax.set_xlim(-0.3, 14.9)
    ax.set_ylim(-1.0, 2.5)
    ax.axis("off")

    groups = {
        1: BLUE, 4: BLUE, 7: BLUE, 10: BLUE,
        3: ORANGE, 6: ORANGE, 9: ORANGE, 12: ORANGE,
        5: TEAL, 8: TEAL, 11: TEAL, 14: TEAL,
    }
    w, h = 0.78, 0.52
    y0 = 1.05
    for k in range(1, 15):
        x = 0.55 + (k - 1) * 0.92
        if k in (2, 13):
            rect = FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                  linewidth=0.9, edgecolor=RED, facecolor="#FBEAEA")
            ax.add_patch(rect)
            ax.text(x + w / 2, y0 + h / 2, str(k), ha="center", va="center",
                    fontproperties=CNB, fontsize=12, color=RED)
            ax.plot([x + 0.16, x + w - 0.16], [y0 + 0.12, y0 + h - 0.12],
                    color=RED, lw=1.5, alpha=0.35)
            ax.plot([x + 0.16, x + w - 0.16], [y0 + h - 0.12, y0 + 0.12],
                    color=RED, lw=1.5, alpha=0.35)
        else:
            c = groups[k]
            rect = FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                  linewidth=0, facecolor=c, alpha=0.16)
            ax.add_patch(rect)
            ax.text(x + w / 2, y0 + h / 2, str(k), ha="center", va="center",
                    fontproperties=CNB, fontsize=12, color=c)

    # 尾部
    x_tail = 0.55 + 14 * 0.92
    ax.add_patch(Rectangle((x_tail, y0), 2.5, h, linewidth=0, facecolor="#EEF1F7"))
    ax.text(x_tail + 1.25, y0 + h / 2, "15 … 4m+2", ha="center", va="center",
            fontproperties=CNB, fontsize=11.5, color=MUTED)
    ax.text(x_tail + 1.25, y0 + h + 0.42, "每 4 个一组", ha="center", va="center",
            fontproperties=CN, fontsize=10.5, color=MUTED)

    # 图例
    ax.text(0.55, 0.28, "● {1,4,7,10}", ha="left", va="center", fontproperties=CN,
            fontsize=11, color=BLUE)
    ax.text(2.9, 0.28, "● {3,6,9,12}", ha="left", va="center", fontproperties=CN,
            fontsize=11, color=ORANGE)
    ax.text(5.25, 0.28, "● {5,8,11,14}", ha="left", va="center", fontproperties=CN,
            fontsize=11, color=TEAL)
    ax.text(7.9, 0.28, "× 被删去的 2 与 13", ha="left", va="center", fontproperties=CN,
            fontsize=11, color=RED)
    ax.text(0.4, 2.25, "m = 3 时：3 组公差 3 + 尾部 0 组；m > 3 时尾部再加 m−3 个连续四元组",
            ha="left", va="center", fontproperties=CNB, fontsize=12.5, color=INK)
    save(fig, "fig_q2.png")


# ============================================================
# 4. 模 3 的三层（为什么是 2 和 13）
# ============================================================
def fig_mod3():
    fig, ax = plt.subplots(figsize=(7.6, 2.9))
    ax.set_xlim(-0.3, 8.3)
    ax.set_ylim(-0.4, 2.9)
    ax.axis("off")

    rows = [[1, 4, 7, 10, 13], [2, 5, 8, 11, 14], [3, 6, 9, 12]]
    cols = [BLUE, ORANGE, TEAL]
    w, h = 0.62, 0.5
    for r, row in enumerate(rows):
        y = 1.75 - r * 0.72
        ax.text(0.12, y + h / 2, f"余 {r+1}", ha="left", va="center",
                fontproperties=CNB, fontsize=10.5, color=cols[r])
        for c, val in enumerate(row):
            x = 1.05 + c * 0.72
            deleted = val in (2, 13)
            if deleted:
                ax.add_patch(FancyBboxPatch((x, y), w, h,
                                            boxstyle="round,pad=0.02,rounding_size=0.08",
                                            linewidth=0.9, edgecolor=RED, facecolor="#FBEAEA"))
                ax.text(x + w / 2, y + h / 2, str(val), ha="center", va="center",
                        fontproperties=CNB, fontsize=10.5, color=RED)
                ax.plot([x + 0.1, x + w - 0.1], [y + h - 0.1, y + 0.1],
                        color=RED, lw=1.3)
            else:
                ax.add_patch(FancyBboxPatch((x, y), w, h,
                                            boxstyle="round,pad=0.02,rounding_size=0.08",
                                            linewidth=0, facecolor=cols[r], alpha=0.15))
                ax.text(x + w / 2, y + h / 2, str(val), ha="center", va="center",
                        fontproperties=CNB, fontsize=10.5, color=cols[r])
    ax.text(1.05, 2.75, "1…14 按 mod 3 分三层：每层 4 或 5 个；13 与 2 正好各删掉一个多出来的",
            ha="left", va="center", fontproperties=CNB, fontsize=11.5, color=INK)
    ax.text(1.05, 0.02, "每行剩下的 4 个数仍等距（公差 3）→ 一行就是一组",
            ha="left", va="center", fontproperties=CN, fontsize=11, color=MUTED)
    save(fig, "fig_mod3.png")


# ============================================================
# 5. 模 4：三段长度都是 4 的倍数
# ============================================================
def fig_mod4():
    fig, ax = plt.subplots(figsize=(9.6, 2.8))
    ax.set_xlim(-0.3, 12.4)
    ax.set_ylim(-0.9, 1.9)
    ax.axis("off")

    y = 0.55
    segs = [(0.6, 2.4, BLUE, "4r 项"), (3.15, 2.9, ORANGE, "4(s−r) 项"), (6.2, 4.6, TEAL, "4(m−s) 项")]
    for x, wdt, c, lab in segs:
        ax.add_patch(Rectangle((x, y), wdt, 0.42, linewidth=0, facecolor=c, alpha=0.18))
        ax.text(x + wdt / 2, y + 0.21, lab, ha="center", va="center",
                fontproperties=CNB, fontsize=10.5, color=c)

    ax.text(3.0, y + 0.62, "i", ha="center", va="bottom", fontproperties=CNB, fontsize=11, color=RED)
    ax.text(6.05, y + 0.62, "j", ha="center", va="bottom", fontproperties=CNB, fontsize=11, color=RED)
    for xx in (3.0, 6.05):
        ax.plot([xx, xx], [y - 0.12, y + 0.52], color=RED, lw=1.2, ls=(0, (2, 2)))
    ax.text(3.0, y - 0.34, "i ≡ 1 (mod 4)", ha="center", va="center",
            fontproperties=CN, fontsize=10, color=RED)
    ax.text(6.05, y - 0.34, "j ≡ 2 (mod 4)", ha="center", va="center",
            fontproperties=CN, fontsize=10, color=RED)

    ax.text(0.6, 1.62, "只要三段都是 4 的倍数，段内「连续四项一组」就自动是等差数列",
            ha="left", va="center", fontproperties=CNB, fontsize=12, color=INK)
    ax.text(0.6, -0.72, "由 i−1≡0、j−i−1≡0、4m+2−j≡0 同时成立，解出唯一的模 4 组合（1, 2）",
            ha="left", va="center", fontproperties=CN, fontsize=10.5, color=MUTED)
    ax.set_ylim(-0.95, 1.95)
    save(fig, "fig_mod4.png")


# ============================================================
# 6. 第一族不够：比例曲线
# ============================================================
def fig_fail():
    ms = list(range(1, 9))
    total = [(4 * m + 2) * (4 * m + 1) // 2 for m in ms]
    fam_a = [(m + 1) * (m + 2) // 2 for m in ms]
    two = [m * m + m + 1 for m in ms]
    r1 = [a / t for a, t in zip(fam_a, total)]
    r2 = [b / t for b, t in zip(two, total)]

    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    ax.plot(ms, r2, "-o", color=BLUE, lw=2, ms=5, label="两族合计 m²+m+1")
    ax.plot(ms, r1, "-s", color=ORANGE, lw=2, ms=4.5, label="只用第一族 (m+1)(m+2)/2")
    ax.axhline(1 / 8, color=RED, lw=1.4, ls=(0, (4, 3)))
    ax.text(7.9, 1 / 8 + 0.0016, "1/8", ha="right", va="bottom", fontproperties=CNB,
            fontsize=11, color=RED)
    ax.plot([3], [r1[2]], "o", ms=11, mfc="none", mec=RED, mew=1.6)
    ax.annotate("m=3：10/91 ≈ 0.110 < 1/8", xy=(3, r1[2]), xytext=(3.3, 0.118),
                fontproperties=CN, fontsize=9.5, color=RED,
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
    ax.set_xlabel("m", fontproperties=CN, fontsize=11, color=BODY)
    ax.set_ylabel("可分数列的概率下界", fontproperties=CN, fontsize=11, color=BODY)
    ax.set_xticks(ms)
    ax.set_ylim(0.115, 0.215)
    ax.grid(axis="y", color=LINE, lw=0.7, alpha=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    leg = ax.legend(prop=CN, fontsize=9.5, frameon=False, loc="upper right")
    for t in leg.get_texts():
        t.set_color(BODY)
    save(fig, "fig_fail.png")


# ============================================================
# 7. 第二族：四带错位构造
# ============================================================
def fig_band():
    d = 4
    n = 4 * d + 2  # 18 -> 用 d=4 做示意
    fig, ax = plt.subplots(figsize=(9.8, 3.0))
    ax.set_xlim(-0.3, 19.0)
    ax.set_ylim(-1.5, 2.35)
    ax.axis("off")

    colors = {1: BLUE, 2: ORANGE, 3: TEAL, 4: PURPLE}
    w, h = 0.82, 0.5
    y0 = 0.75
    deleted = {2, 4 * d + 1}

    for q in range(1, n + 1):
        x = 0.5 + (q - 1) * 0.9
        if q in deleted:
            ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.09",
                                        linewidth=0.9, edgecolor=RED, facecolor="#FBEAEA"))
            ax.text(x + w / 2, y0 + h / 2, "×", ha="center", va="center",
                    fontproperties=CNB, fontsize=11, color=RED)
        else:
            if q == 1 or (q - 1) % d == 0:
                c = colors[1]
            elif q % d == 2:
                c = colors[2]
            elif q % d == 3:
                c = colors[3]
            else:
                c = colors[4]
            ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.09",
                                        linewidth=0, facecolor=c, alpha=0.18))
            ax.text(x + w / 2, y0 + h / 2, str(q), ha="center", va="center",
                    fontproperties=CNB, fontsize=9.5, color=c)

    # 分带
    for b in range(1, 4):
        xx = 0.5 + b * d * 0.9 - 0.04
        ax.plot([xx, xx], [y0 - 0.12, y0 + h + 0.12], color=LINE, lw=1, ls=(0, (2, 2)))
    ax.text(0.5 + 0.9 * d / 2, y0 + h + 0.3, "带 1", ha="center", va="center",
            fontproperties=CN, fontsize=9.5, color=MUTED)
    ax.text(0.5 + 0.9 * (d * 1.5), y0 + h + 0.3, "带 2", ha="center", va="center",
            fontproperties=CN, fontsize=9.5, color=MUTED)
    ax.text(0.5 + 0.9 * (d * 2.5), y0 + h + 0.3, "带 3", ha="center", va="center",
            fontproperties=CN, fontsize=9.5, color=MUTED)
    ax.text(0.5 + 0.9 * (d * 3 + 1), y0 + h + 0.3, "带 4（多出 2 个）", ha="center", va="center",
            fontproperties=CN, fontsize=9.5, color=MUTED)

    ax.text(0.5, y0 - 0.42,
            "第 1 组、第 3 组、第 4 组：同一条竖线上各取一个 → 公差 d；第 2 组：因 4b+2 被删而错位一格，末尾补 4b+4d+2",
            ha="left", va="center", fontproperties=CN, fontsize=9.5, color=BODY)
    ax.text(0.5, y0 - 0.78, "示意图取 d = 4，格中数字为相对位置 4b+q 的 q",
            ha="left", va="center", fontproperties=CN, fontsize=8.5, color=MUTED)
    ax.text(0.5, 2.15, "中间段 [4b+1, 4a+2] 共 4d+2 个数，删掉 2 个后剩 4d 个：切成 4 带，每带的第 p 个位置属同一组",
            ha="left", va="center", fontproperties=CNB, fontsize=11.5, color=INK)
    save(fig, "fig_band.png")


# ============================================================
# 8. 数据：穷举 vs 公式
# ============================================================
def fig_data():
    ms = [1, 2, 3, 4, 5]
    valid = [3, 7, 13, 21, 31]
    formula = [m * m + m + 1 for m in ms]
    total = [(4 * m + 2) * (4 * m + 1) // 2 for m in ms]

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    xs = range(len(ms))
    ax.bar([x - 0.19 for x in xs], total, width=0.36, color="#E6EAF2", label="总对数 (2m+1)(4m+1)")
    ax.bar([x + 0.19 for x in xs], valid, width=0.36, color=BLUE, alpha=0.85,
           label="可分的对数（穷举）")
    for x, (v, f) in enumerate(zip(valid, formula)):
        ax.text(x + 0.19, v + 4, str(v), ha="center", va="bottom", fontproperties=CNB,
                fontsize=10, color=BLUE)
        ax.text(x - 0.19, total[x] + 4, str(total[x]), ha="center", va="bottom",
                fontproperties=CN, fontsize=9, color=MUTED)
    ax.plot([x + 0.19 for x in xs], formula, "o", ms=7, mfc="none", mec=ORANGE, mew=1.8,
            label="m²+m+1（与实验完全吻合）", zorder=5)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"m={m}" for m in ms], fontproperties=CN, fontsize=10, color=BODY)
    ax.set_ylim(0, 265)
    ax.grid(axis="y", color=LINE, lw=0.7, alpha=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    leg = ax.legend(prop=CN, fontsize=9, frameon=False, loc="upper left")
    for t in leg.get_texts():
        t.set_color(BODY)
    save(fig, "fig_data.png")


if __name__ == "__main__":
    fig_lemma()
    fig_q1()
    fig_q2()
    fig_mod3()
    fig_mod4()
    fig_fail()
    fig_band()
    fig_data()
    print("ALL FIGURES DONE")
