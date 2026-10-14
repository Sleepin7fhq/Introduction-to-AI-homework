#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 年新高考Ⅰ卷 数学 第18题 —— 数值验证代码
================================================
题目：椭圆 C: x²/a² + y²/b² = 1 (a > b > 0)，左焦点 F(-1, 0)，离心率 1/2。
      (1) 求 C 的方程；
      (2) O 为原点，过 F 且斜率 k > 0 的动直线 l 与 C 交于 P、Q，其中 Q 在第三象限，
          直线 PO 与 C 的另一个交点为 R。
          (i) 若 △PQR 面积是 △PFO 面积的 3 倍，求 l 的方程；
          (ii) 求 tan∠PQR 的最小值。

本脚本只用 Python 3 标准库，独立数值验证解析解：
      (1)  C: x²/4 + y²/3 = 1
      (2)(i)   l: y = (√5/2)(x+1)，即 √5·x − 2y + √5 = 0
      (2)(ii)  min tan∠PQR = 4√3，在 k = √3/2 处取得

运行： python 验证代码.py
"""

import math

# ---------------------------------------------------------------- 椭圆参数
C_COORD = 1.0                              # 半焦距 c = |OF| = 1
ECC = 0.5                                  # 离心率 e = c/a = 1/2
A = C_COORD / ECC                          # 长半轴 a = 2
B = math.sqrt(A * A - C_COORD ** 2)         # 短半轴 b = √3
F = (-C_COORD, 0.0)                        # 左焦点 F(-1, 0)
O = (0.0, 0.0)

report = []


def say(line=""):
    print(line)
    report.append(line)


def on_ellipse(x, y, tol=1e-9):
    """点是否在椭圆 x²/4 + y²/3 = 1 上"""
    return abs(x * x / (A * A) + y * y / (B * B) - 1.0) < tol


def intersections(k):
    """
    直线 l: y = k(x+1) 与椭圆的两交点。
    代入整理得 (3+4k²)x² + 8k²x + (4k²−12) = 0。
    返回 (Q, P)：Q 取较小根（第三象限），P 取较大根。
    """
    kk = k * k
    Aa = 3.0 + 4.0 * kk
    Bb = 8.0 * kk
    Cc = 4.0 * kk - 12.0
    disc = Bb * Bb - 4.0 * Aa * Cc
    if disc < 0:
        return None
    r = math.sqrt(disc)
    x_q = (-Bb - r) / (2.0 * Aa)
    x_p = (-Bb + r) / (2.0 * Aa)
    return (x_q, k * (x_q + 1.0)), (x_p, k * (x_p + 1.0))


def antipode(pt):
    """椭圆中心为原点，对径点即取负"""
    return (-pt[0], -pt[1])


def dist_point_line(pt, k):
    """点 pt 到直线 kx − y + k = 0 的距离"""
    return abs(k * pt[0] - pt[1] + k) / math.sqrt(k * k + 1.0)


def area_triangle(p1, p2, p3):
    """三角形面积（叉积法）"""
    return abs((p2[0] - p1[0]) * (p3[1] - p1[1])
               - (p3[0] - p1[0]) * (p2[1] - p1[1])) / 2.0


def area_ratio(k):
    """面积比 S(△PQR) / S(△PFO)"""
    Q, P = intersections(k)
    R = antipode(P)
    return area_triangle(P, Q, R) / area_triangle(P, F, O)


def tan_angle_PQR(k):
    """
    tan∠PQR：顶点 Q，两条射线 QP 与 QR。
    对 θ∈(0,π) 有 tanθ = |u×v| / (u·v)，其中 u=QP, v=QR。
    （叉积绝对值是 sinθ 的分子，故取绝对值；点积的符号决定角度锐钝。）
    """
    Q, P = intersections(k)
    R = antipode(P)
    ux, uy = P[0] - Q[0], P[1] - Q[1]          # QP
    vx, vy = R[0] - Q[0], R[1] - Q[1]          # QR
    cross = abs(ux * vy - uy * vx)
    dot = ux * vx + uy * vy
    if abs(dot) < 1e-15:
        return float("inf")
    return cross / dot


# ================================================================ 0. 参数
say("=" * 68)
say(" 2026 新高考Ⅰ卷 数学 第18题 · 数值验证")
say("=" * 68)
say()
say("【第0步】由 c = 1, e = 1/2 定出椭圆参数")
say(f"  a = c/e = {A:g}，b = √(a²−c²) = {B:.12f}")
say(f"  校验：b 与 √3 = {math.sqrt(3):.12f} 的偏差 = {abs(B - math.sqrt(3)):.3e}")
say(f"  F = {F}")
say()

# ================================================================ 1. 第(1)问
say("【第(1)问】求 C 的方程")
say(f"  解析解： x²/{A * A:g} + y²/{B * B:.12f} = 1   （即 x²/4 + y²/3 = 1）")
say("  用曲线上的点回代验算：")
for x in (-A, -1.0, 0.0, 1.0, A):
    y = B * math.sqrt(max(0.0, 1.0 - x * x / (A * A)))
    say(f"    ({x:5.1f}, ±{y:.6f})   在椭圆上？ {on_ellipse(x, y)} / {on_ellipse(x, -y)}")
say()

# ============================================== 2. 第(2)(i)问：求 l 的方程
say("【第(2)(i)问】面积比为 3，求直线 l 的方程")


def bisect(fn, lo, hi, iters=300):
    flo = fn(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        fm = fn(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2.0


k_sol = bisect(lambda k: area_ratio(k) - 3.0, 1e-6, 10.0)
k_ana = math.sqrt(5) / 2
say(f"  数值解 k = {k_sol:.12f}")
say(f"  解析解 k = √5/2 = {k_ana:.12f}")
say(f"  偏差 = {abs(k_sol - k_ana):.3e}")
say(f"  → 该处的面积比 = {area_ratio(k_sol):.12f}   （应为 3）")
say()
say("  面积比随 k 的抽样变化：")
for k in (0.5, 1.0, k_ana, 2.0, 3.0):
    say(f"    k = {k:8.5f}  →  S(△PQR)/S(△PFO) = {area_ratio(k):.6f}")
say()
say("  几何量核对（取 k = √5/2）：")
Q, P = intersections(k_ana)
R = antipode(P)
say(f"    Q = ({Q[0]:.6f}, {Q[1]:.6f})   Q 在第三象限？ {Q[0] < 0 and Q[1] < 0}")
say(f"    P = ({P[0]:.6f}, {P[1]:.6f})")
say(f"    R = ({R[0]:.6f}, {R[1]:.6f})   （P 的对径点）")
say(f"    P、Q 是否都在椭圆上？ {on_ellipse(*P, tol=1e-9)} / {on_ellipse(*Q, tol=1e-9)}")
say(f"    |PQ| = {math.dist(P, Q):.6f}")
say(f"    |PF| = {math.dist(P, F):.6f}")
say(f"    |PQ|/|PF| = {math.dist(P, Q) / math.dist(P, F):.12f}   （应为 3/2）")
say(f"    d(R,l)/d(O,l) = {dist_point_line(R, k_ana) / dist_point_line(O, k_ana):.12f}   （应为 2）")
say(f"    S(△PQR) = {area_triangle(P, Q, R):.6f}")
say(f"    S(△PFO) = {area_triangle(P, F, O):.6f}")
say("  解析解： l: y = (√5/2)(x+1)，即 √5·x − 2y + √5 = 0")
say()

# ========================================== 3. 第(2)(ii)问：tan∠PQR 最小值
say("【第(2)(ii)问】求 tan∠PQR 的最小值")
say("  解析解： tan∠PQR = 4k + 3/k ≥ 2√(12) = 4√3，等号在 k = √3/2 时取得")
say()
say("  逐点核对解析表达式 4k + 3/k：")
worst = 0.0
for k in (0.3, 0.5, math.sqrt(3) / 2, 1.0, k_ana, 2.0, 3.0, 5.0):
    num = tan_angle_PQR(k)
    ana = 4.0 * k + 3.0 / k
    worst = max(worst, abs(num - ana))
    say(f"    k = {k:8.5f}   数值 = {num:12.8f}   解析 = {ana:12.8f}   差 = {abs(num - ana):.3e}")
say(f"  最大偏差 = {worst:.3e}   → 解析式 tan∠PQR = 4k + 3/k 成立")
say()

say("  确认 ∠PQR 恒为锐角（点积 > 0，故 tan 取正值）：")
for k in (0.2, 0.8660254, 1.5, 4.0):
    Q, P = intersections(k)
    R = antipode(P)
    ux, uy = P[0] - Q[0], P[1] - Q[1]
    vx, vy = R[0] - Q[0], R[1] - Q[1]
    say(f"    k = {k:8.5f}   QP·QR = {ux * vx + uy * vy:12.6f}")
say()

say("  数值扫描求最小值（k ∈ (0, 5]，步长 2.5e-5）：")
best_k, best_v = None, float("inf")
for i in range(1, 200001):
    k = 5.0 * i / 200000.0
    v = tan_angle_PQR(k)
    if v < best_v:
        best_v, best_k = v, k
say(f"    扫描最小： k = {best_k:.9f}，tan∠PQR = {best_v:.9f}")
say(f"    理论值  ： k = √3/2 = {math.sqrt(3) / 2:.9f}，4√3 = {4 * math.sqrt(3):.9f}")
say(f"    偏差 = {abs(best_v - 4 * math.sqrt(3)):.3e}")
say()

lo, hi = 0.1, 3.0
for _ in range(300):
    m1 = lo + (hi - lo) / 3.0
    m2 = hi - (hi - lo) / 3.0
    if tan_angle_PQR(m1) < tan_angle_PQR(m2):
        hi = m2
    else:
        lo = m1
k_ref = (lo + hi) / 2.0
say(f"  三分法精化： k* = {k_ref:.12f}，tan∠PQR(k*) = {tan_angle_PQR(k_ref):.12f}")
say(f"  4√3 = {4 * math.sqrt(3):.12f}，偏差 = {abs(tan_angle_PQR(k_ref) - 4 * math.sqrt(3)):.3e}")
say()

say("  端点行为（说明最小值在内部取得，而非边界）：")
for k in (0.01, 0.1, 10.0, 100.0):
    say(f"    k = {k:8.2f}  →  tan∠PQR = {tan_angle_PQR(k):14.6f}")
say()

say("=" * 68)
say(" 结论")
say("=" * 68)
say("  (1)     C: x²/4 + y²/3 = 1")
say("  (2)(i)  l: y = (√5/2)(x+1)，即 √5·x − 2y + √5 = 0")
say("  (2)(ii) tan∠PQR 的最小值为 4√3，此时 l 的斜率 k = √3/2")
say("=" * 68)

with open("验证结果.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(report) + "\n")
print("\n[已保存 验证结果.txt]")
