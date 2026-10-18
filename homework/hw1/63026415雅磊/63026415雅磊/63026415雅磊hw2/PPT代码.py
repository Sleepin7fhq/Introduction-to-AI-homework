# -*- coding: utf-8 -*-
"""
第19题：集合 D(x0) 的解题验算脚本

说明：
    这道题的证明主体是“反证法 + 集合包含”，不是程序自动证明出来的。
    本脚本做三件事：
    1. 复现第（1）问的区间计算；
    2. 对第（2）问的 D(x) 表达式做数值抽样检验；
    3. 复现第（3）问中用到的构造式与代数恒等式，并检查关键不等式。

依赖：无第三方库，直接 python 运行。
"""

from math import isclose, log2
from fractions import Fraction
import random


# ------------------------------------------------------------
# 两个具体函数
# ------------------------------------------------------------
def f1(x):
    """第（1）问：x<0 时 2^x；x>=0 时 1-x。"""
    return 2.0 ** x if x < 0 else 1.0 - x


def f2(x):
    """第（2）问：奇函数，负半轴为 2^x。"""
    if x < 0:
        return 2.0 ** x
    if x == 0:
        return 0.0
    return -2.0 ** (-x)


def in_D(f, x0, d):
    """按定义判断 d 是否属于 D(x0)。"""
    return f(x0 + d) > f(x0)


def section(title):
    print("\n" + "=" * 66)
    print(title)
    print("=" * 66)


# ------------------------------------------------------------
# 第（1）问
# ------------------------------------------------------------
def check_part1():
    section("第（1）问：D(-1) = (0, 3/2)")
    x0 = -1.0
    target = f1(x0)
    print(f"f(-1) = 2^(-1) = {target}")

    inside = [0.001, 0.2, 0.999999, 1.0, 1.2, 1.499999]
    outside = [-0.5, 0.0, 1.5, 1.500001, 2.0]

    for d in inside:
        assert in_D(f1, x0, d), f"d={d} 应在 D(-1) 中"
    for d in outside:
        assert not in_D(f1, x0, d), f"d={d} 不应在 D(-1) 中"

    print("区间内部抽样点均满足 f(-1+d) > f(-1)：", inside)
    print("区间外部/端点抽样点均不满足：", outside)
    print("结论：0 < d < 3/2，即 D(-1) = (0, 3/2)。")


# ------------------------------------------------------------
# 第（2）问
# ------------------------------------------------------------
def check_part2():
    section("第（2）问：奇函数时 D(x) 的表达式")
    print("x < 0 时：D(x) = (0, -x)")
    print("x > 0 时：D(x) = (-∞, -x] ∪ (0, +∞)")

    checks = [
        # (x, d, 是否应属于 D(x))
        (-0.7, -0.10, False),   # 向左移，函数值变小
        (-0.7,  0.20, True),    # 仍在负半轴，2^t 递增
        (-0.7,  0.699, True),   # 仍在负半轴
        (-0.7,  0.701, False),  # 已越过 0，函数值变成负数
        ( 0.8, -1.50, True),    # 移到负半轴，函数值 > 0
        ( 0.8, -0.80, True),    # 移到 x=0，f(0)=0 > f(0.8)
        ( 0.8, -0.50, False),   # 仍在正半轴左侧，函数值更小
        ( 0.8,  0.00, False),   # 原地，不严格变大
        ( 0.8,  0.50, True),    # 向右移，-2^(-x) 递增
    ]

    for x, d, expected in checks:
        got = in_D(f2, x, d)
        assert got == expected, (x, d, expected, got)

    print("\n数值抽样（x, d, 是否属于 D(x)）：")
    for x, d, expected in checks:
        print(f"  x={x:>5}, d={d:>7}, 属于={in_D(f2, x, d)}")

    print("\n结论：两组 D(x) 表达式与抽样结果一致；")
    print("再按 x1、x2 同负、同正、异号分类，即可证 D(x2) ⊆ D(x1)。")


# ------------------------------------------------------------
# 第（3）（i）问
# ------------------------------------------------------------
def check_part3_i():
    section("第（3）（i）问：反证法构造 d = -y/2")
    f0 = 0.6  # 任取一个 0 < f0 < 1 的例子
    y = log2((1.0 + f0) / 2.0)  # 使 2^y = (1+f0)/2 > f0
    d = -y / 2.0

    assert -1.0 < y < 0.0
    assert 0.0 < d < 1.0
    assert 2.0 ** y > f0
    assert isclose(y + d, y / 2.0)
    assert y / 2.0 > y

    print(f"取 f(0)={f0}, y=log2((1+f0)/2)={y:.6f}")
    print(f"则 2^y={2.0 ** y:.6f} > f(0)")
    print(f"d=-y/2={d:.6f} ∈ (0,1)，且 y+d=y/2")
    print("于是 y/2 > y ⇒ f(y+d)>f(y) ⇒ d∈D(y)。")
    print("又 d∈(0,1) ⇒ f(d)<f(0) ⇒ d∉D(0)。")
    print("但 f(y)>f(0) ⇒ D(y)⊆D(0)，矛盾。")
    print("结论：f(0) ≥ 1。")


# ------------------------------------------------------------
# 第（3）（ii）问
# ------------------------------------------------------------
def check_part3_ii():
    section("第（3）（ii）问：引理与最后一步的代数替换")
    print("核心引理：")
    print("  若 f(a) ≤ f(b) < f(c)，则 f(a) < f(a-b+c)。")
    print("证明要点：c-b ∈ D(b) ⊆ D(a)。")

    # 检验最后一步的代数恒等式：a=u, b=-v, c=-u
    random.seed(20260619)
    for _ in range(5):
        u = Fraction(random.randint(2, 20), 10)
        v = u + Fraction(random.randint(1, 20), 10)
        assert 0 < u < v
        assert -v < -u < 0

        a, b, c = u, -v, -u
        assert a - b + c == v
        print(f"u={u}, v={v}:  a-b+c = {a} - ({b}) + ({c}) = {a-b+c}")

    print("\n所以取 (a,b,c)=(u,-v,-u)，引理给出：")
    print("  f(u) < f(u+v-u) = f(v)。")
    print("结论：f(x) 在 (0,+∞) 上严格单调递增。")


if __name__ == "__main__":
    check_part1()
    check_part2()
    check_part3_i()
    check_part3_ii()
    print("\n全部数值/代数检查通过。")
