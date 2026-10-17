# -*- coding: utf-8 -*-
"""为《2026 新课标 II 卷第 17 题》演示文稿绘制全部插图（Pillow）

坐标约定：三角形先用数学坐标（y 向上）计算，再统一映射到屏幕（y 向下）。
角弧取最短方向，即三角形内角本身。
"""
import math
import os

import drawlib
from drawlib import (Canvas, INK, MUTED, RED, GOLD, TEAL, BLUE, WHITE, LINE,
                     CREAM, PAPER, NAVY)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "图表"))
os.makedirs(OUT, exist_ok=True)
drawlib.ASSETS = OUT

# ---------------- 题目数据 ----------------
cosB = 3 / 4
sinB = math.sqrt(1 - cosB ** 2)          # √7/4
cos_sum = -cosB                          # cos(A+C) = −3/4
sinA_sinC = 1 - cos_sum ** 2             # 7/16
cosA_cosC = cos_sum + sinA_sinC          # −5/16
cos_diff = cosA_cosC + sinA_sinC         # cos(A−C) = 1/8

Adeg = math.degrees((math.acos(cos_sum) + math.acos(cos_diff)) / 2)
Cdeg = math.degrees((math.acos(cos_sum) - math.acos(cos_diff)) / 2)
Bdeg = math.degrees(math.acos(cosB))

# 边长：a = 2（对 A），b = √2（对 B），c = 1（对 C）
SA, SB, SC = 2.0, math.sqrt(2.0), 1.0

Ax, Ay = 0.0, 0.0
Bx, By = SC, 0.0
Cx = (SB ** 2 + SC ** 2 - SA ** 2) / (2 * SC)      # −0.5
Cy = math.sqrt(max(SB ** 2 - Cx ** 2, 0.0))        # ≈ 1.3229
assert Cx < 0, "A 为钝角，C 的横坐标应为负"


# ---------------- 工具 ----------------
def arrow(cv, p0, p1, color=INK, width=1.6, head=9):
    cv.line([p0, p1], color, width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (+1, -1):
        a2 = ang + math.pi - s * 0.42
        cv.line([p1, (p1[0] + head * math.cos(a2), p1[1] + head * math.sin(a2))], color, width)


def arc_math(cv, center_px, radius, a0, a1, color=TEAL, width=1.8, n=72):
    cx, cy = center_px
    pts = [(cx + radius * math.cos(a0 + (a1 - a0) * i / n),
            cy - radius * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    cv.line(pts, color, width)


def inner_angle(V, P, Q):
    a1 = math.atan2(P[1] - V[1], P[0] - V[0])
    a2 = math.atan2(Q[1] - V[1], Q[0] - V[0])
    d = a2 - a1
    while d <= -math.pi:
        d += 2 * math.pi
    while d > math.pi:
        d -= 2 * math.pi
    return a1, a1 + d, a1 + d / 2


def dashed(cv, p0, p1, color=MUTED, width=1.2, dash=7, gap=5):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 0.5:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        cv.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], color, width)
        s = e + gap


def tri_arc_labels(cv, T, rA=56, rB=48, rC=48, fs=20):
    for V, P, Q, r, col, lab, off in (
            ((Ax, Ay), (Bx, By), (Cx, Cy), rA, RED, "$A$", 26),
            ((Bx, By), (Cx, Cy), (Ax, Ay), rB, TEAL, "$B$", 26),
            ((Cx, Cy), (Ax, Ay), (Bx, By), rC, GOLD, "$C$", 26)):
        a0, a1, mid = inner_angle(V, P, Q)
        Vp = T(V[0], V[1])
        arc_math(cv, Vp, r, a0, a1, col, 1.9)
        cv.m((Vp[0] + (r + off) * math.cos(mid), Vp[1] - (r + off) * math.sin(mid)),
             lab, fs, col, anchor="ms")


# ============================================================
# 图 1：按比例绘制的三角形（A 为钝角）
# ============================================================
def fig1():
    cv = Canvas(880, 640, bg=PAPER)
    S = 246.0
    ox, oy = 430.0, 548.0

    def T(x, y):
        return (ox + x * S, oy - y * S)

    A2, B2, C2 = T(Ax, Ay), T(Bx, By), T(Cx, Cy)
    cv.poly([A2, B2, C2], fill=(238, 245, 250), outline=INK)
    cv.line([A2, B2, C2, A2], INK, 2.6)

    for pt, name, dx, dy, anc in ((A2, "$A$", -16, 30, "rs"), (B2, "$B$", 18, 30, "ls"),
                                  (C2, "$C$", -16, -14, "rs")):
        cv.dot(pt, NAVY, 6)
        cv.m((pt[0] + dx, pt[1] + dy), name, 27, NAVY, anchor=anc)

    tri_arc_labels(cv, T, rA=62, rB=46, rC=44)

    cv.m(((A2[0] + B2[0]) / 2, (A2[1] + B2[1]) / 2 + 34), "$c=1$", 23, TEAL, anchor="ms")
    mx, my = (A2[0] + C2[0]) / 2, (A2[1] + C2[1]) / 2
    cv.m((mx - 18, my), "$b=\\sqrt{2}$", 23, GOLD, anchor="rs")
    mx, my = (B2[0] + C2[0]) / 2, (B2[1] + C2[1]) / 2
    cv.m((mx + 22, my), "$a=2$", 23, RED, anchor="ls")
    cv.save("fig1_triangle.png")


# ============================================================
# 图 2：单位圆 —— A+C 与 B 互补
# ============================================================
def fig2():
    cv = Canvas(920, 620, bg=PAPER)
    cx, cy, R = 458.0, 322.0, 250.0

    cv.line([(cx - R - 56, cy), (cx + R + 46, cy)], MUTED, 1.4)
    cv.line([(cx, cy + R + 44), (cx, cy - R - 44)], MUTED, 1.4)
    cv.m((cx + R + 52, cy - 16), "$x$", 19, MUTED, anchor="ls")
    cv.m((cx + 10, cy - R - 54), "$y$", 19, MUTED, anchor="ls")
    cv.m((cx - 12, cy + 28), "$O$", 17, MUTED, anchor="rs")
    cv.ellipse((cx - R, cy - R, cx + R, cy + R), outline=INK, width=2.3)

    thB = math.acos(cosB)
    thS = math.pi - thB

    def pt(t):
        return (cx + R * math.cos(t), cy - R * math.sin(t))

    pB, pS = pt(thB), pt(thS)
    cv.line([(cx, cy), pB], TEAL, 2.5)
    cv.line([(cx, cy), pS], RED, 2.5)
    cv.dot(pB, TEAL, 7)
    cv.dot(pS, RED, 7)

    for p, col in ((pB, TEAL), (pS, RED)):
        dashed(cv, p, (p[0], cy), col, 1.3)
        cv.line([(p[0], cy - 7), (p[0], cy + 7)], col, 2.2)

    cv.m((pB[0], cy + 44), "$\\cos B=\\dfrac{3}{4}$", 21, TEAL, anchor="ms")
    cv.m((pS[0], cy + 44), "$\\cos(A+C)=-\\dfrac{3}{4}$", 21, RED, anchor="ms")

    arc_math(cv, (cx, cy), 96, 0, thB, TEAL, 1.9)
    arc_math(cv, (cx, cy), 122, thB, thS, GOLD, 1.9)
    cv.m((cx + 122, cy - 34), "$B$", 21, TEAL, anchor="ls")
    cv.m((cx - 70, cy - 140), "$A+C$", 21, GOLD, anchor="ms")
    cv.save("fig2_supplement.png")


# ============================================================
# 图 3：外接圆与正弦定理
# ============================================================
def fig3():
    cv = Canvas(900, 640, bg=PAPER)
    S = 188.0
    ox, oy = 430.0, 540.0

    def T(x, y):
        return (ox + x * S, oy - y * S)

    A2, B2, C2 = T(Ax, Ay), T(Bx, By), T(Cx, Cy)
    Rr = SB / (2 * sinB)
    Ox, Oy = SC / 2.0, math.sqrt(max(Rr ** 2 - (SC / 2.0) ** 2, 0))
    O2 = T(Ox, Oy)

    cv.ellipse((O2[0] - Rr * S, O2[1] - Rr * S, O2[0] + Rr * S, O2[1] + Rr * S),
               outline=(150, 172, 202), width=2.0)
    cv.poly([A2, B2, C2], fill=(238, 245, 250), outline=INK)
    cv.line([A2, B2, C2, A2], INK, 2.4)

    for p in (A2, B2, C2):
        dashed(cv, O2, p, (152, 152, 162), 1.2)
    cv.dot(O2, (140, 140, 152), 5)
    cv.m((O2[0] + 10, O2[1] + 22), "$O$", 18, MUTED, anchor="ls")

    for pt, name, dx, dy, anc in ((A2, "$A$", -16, 28, "rs"), (B2, "$B$", 18, 28, "ls"),
                                  (C2, "$C$", -16, -14, "rs")):
        cv.dot(pt, NAVY, 6)
        cv.m((pt[0] + dx, pt[1] + dy), name, 25, NAVY, anchor=anc)

    mx, my = (O2[0] + A2[0]) / 2, (O2[1] + A2[1]) / 2
    cv.m((mx + 24, my + 26), "$R$", 20, (120, 130, 150), anchor="ls")

    a0, a1, mid = inner_angle((Bx, By), (Cx, Cy), (Ax, Ay))
    arc_math(cv, B2, 54, a0, a1, TEAL, 1.9)
    cv.m((B2[0] + 78 * math.cos(mid), B2[1] - 78 * math.sin(mid)), "$B$", 19, TEAL, anchor="ms")

    cv.line([A2, C2], GOLD, 3.6)
    cv.m(((A2[0] + C2[0]) / 2 - 18, (A2[1] + C2[1]) / 2 + 8), "$b$", 24, GOLD, anchor="rs")
    cv.save("fig3_circumcircle.png")


# ============================================================
# 图 4：第 (2) 问推导链
# ============================================================
def fig4():
    cv = Canvas(1200, 440, bg=PAPER)
    steps = [
        ("面积公式", "$S=\\dfrac{1}{2}ac\\sin B$", "$ac=2$", TEAL),
        ("正弦定理", "$ac=4R^{2}\\sin A\\sin C$", "$R^{2}=\\dfrac{8}{7}$", GOLD),
        ("正弦定理", "$b=2R\\sin B$", "$b=\\sqrt{2}$", BLUE),
        ("余弦定理", "$b^{2}=a^{2}+c^{2}-2ac\\cos B$", "$a^{2}+c^{2}=5$", RED),
        ("配方", "$(a+c)^{2}=a^{2}+c^{2}+2ac$", "$a+c=3$", TEAL),
        ("求和", "$a+b+c$", "$3+\\sqrt{2}$", NAVY),
    ]
    bw, bh, gap = 168, 124, 34
    x0, y0 = 26, 150
    for i, (tag, f, res, col) in enumerate(steps):
        x = x0 + i * (bw + gap)
        cv.rect((x, y0, x + bw, y0 + bh), fill=WHITE, outline=LINE, width=1.4)
        cv.rect((x, y0, x + bw, y0 + 24), fill=col)
        cv.c((x + bw / 2, y0 + 16), tag, 12.5, WHITE, bold=True, anchor="ms")
        cv.m((x + bw / 2, y0 + 58), f, 12, INK, anchor="ms")
        cv.m((x + bw / 2, y0 + 101), res, 20, col, anchor="ms")
        if i < len(steps) - 1:
            arrow(cv, (x + bw + 5, y0 + bh / 2), (x + bw + gap - 6, y0 + bh / 2), MUTED, 1.8, 8)
    cv.m((26, 42), "第 (2) 问：从面积出发，五次代换得到周长", 22, NAVY, anchor="ls")
    cv.m((26, 80), "每步只用一条公式，并反复使用第 (1) 问的 $\\sin A\\sin C=\\dfrac{7}{16}$", 15, MUTED, anchor="ls")
    cv.m((26, 336), "关键：把 $a+c$ 而非单独的 $a,c$ 当作未知量 —— 一次配方即可求出。", 16, RED, anchor="ls")
    cv.m((26, 372), "（$a,c$ 是 $t^{2}-3t+2=0$ 的两根 1 与 2，但求周长无需分开解。）", 15, MUTED, anchor="ls")
    cv.save("fig4_chain.png")


# ============================================================
# 图 5：答案自洽校验
# ============================================================
def fig5():
    W, H = 980, 470
    cv = Canvas(W, H, bg=PAPER)
    cv.rect((30, 24, W - 30, H - 24), fill=(250, 252, 250), outline=(196, 214, 200), width=1.4)
    cv.m((60, 74), "验算：边长 $(1,\\ \\sqrt{2},\\ 2)$ 满足全部条件", 20, NAVY, anchor="ls")
    rows = [
        ("三角不等式", "$1+\\sqrt{2}=2.414>2$", "成立", 128),
        ("余弦定理求 $\\cos B$", "$\\dfrac{2^{2}+1^{2}-2}{2\\cdot 2\\cdot 1}=\\dfrac{3}{4}$", "成立", 182),
        ("余弦定理求 $\\cos A$", "$\\dfrac{2+1-4}{2\\sqrt{2}}=-0.3536<0$", "$A$ 为钝角", 236),
        ("面积", "$\\dfrac{1}{2}\\cdot 2\\cdot 1\\cdot\\dfrac{\\sqrt{7}}{4}=\\dfrac{\\sqrt{7}}{4}$", "成立", 290),
        ("周长", "$1+\\sqrt{2}+2=3+\\sqrt{2}\\approx 4.4142$", "答案", 344),
    ]
    for name, expr, verdict, y in rows:
        cv.line([(60, y + 36), (W - 60, y + 36)], (232, 238, 232), 1.0)
        cv.m((64, y), name, 16.5, INK, anchor="ls")
        cv.m((330, y), expr, 17.5, TEAL, anchor="ls")
        cv.m((W - 64, y), verdict, 16.5, RED, anchor="rs")
    cv.c((W / 2, H - 40), "五条全部成立，答案 3 + √2 完全自洽", 17, (40, 110, 60), bold=True, anchor="ms")
    cv.save("fig5_check.png")




def trim(name, pad=28):
    """裁掉图片四周的空白边距"""
    from PIL import Image, ImageChops
    path = os.path.join(OUT, name)
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, PAPER)
    diff = ImageChops.difference(im, bg)
    box = diff.getbbox()
    if not box:
        return
    l, t, r, b = box
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(im.width, r + pad); b = min(im.height, b + pad)
    im.crop((l, t, r, b)).save(path)
    print("  trimmed", name, (r - l, b - t))


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print("figures ->", OUT)
    for f in ("fig1_triangle.png", "fig2_supplement.png", "fig3_circumcircle.png",
              "fig4_chain.png", "fig5_check.png"):
        trim(f)
    for f in sorted(os.listdir(OUT)):
        if f.endswith(".png"):
            print("  ", f)
