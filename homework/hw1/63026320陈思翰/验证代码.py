#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 2022 年高考全国甲卷·理科数学第 21 题解答的独立数值/符号检验。

题目: f(x) = e^x/x - ln x + x - a  (x>0)
 (1) 若 f(x) >= 0 恒成立, 求 a 的取值范围;
 (2) 若 f(x) 有两个零点 x1 < x2, 证明 x1*x2 < 1.

本脚本只做"检验", 不参与推导: 它用 60 位十进制精度独立重算
导数、单调性、极值、零点以及待证不等式。
"""
from decimal import Decimal, getcontext

getcontext().prec = 60

D = Decimal
E = D(1).exp()          # 自然常数 e, 60 位精度


def g(x):
    """g(x) = e^x/x - ln x + x,   f(x) = g(x) - a"""
    x = D(x)
    return x.exp() / x - x.ln() + x


def gp(x):
    """g'(x) = (e^x + x)(x-1)/x^2  (推导结果, 用有限差分独立复核)"""
    x = D(x)
    return (x.exp() + x) * (x - 1) / (x * x)


def f(x, a):
    return g(x) - D(a)


def h(x):
    """h(x) = f(x) - f(1/x) = g(x) - g(1/x)  (与 a 无关)"""
    x = D(x)
    return g(x) - g(1 / x)


def hp_formula(x):
    """解答中推出的 h'(x) = (x-1)/x^2 * [e^x + x - x*e^(1/x) - 1]"""
    x = D(x)
    m = x.exp() + x - x * (1 / x).exp() - 1
    return (x - 1) / (x * x) * m


def hp_fd(x, eps="1e-25"):
    """用中心差分独立计算 h'(x)"""
    x = D(x)
    e = D(eps)
    return (h(x + e) - h(x - e)) / (2 * e)


def m(x):
    """m(x) = e^x + x - x*e^(1/x) - 1"""
    x = D(x)
    return x.exp() + x - x * (1 / x).exp() - 1


def mp(x):
    """m'(x) = e^x + 1 + e^(1/x)*(1/x - 1)  (推导结果)"""
    x = D(x)
    return x.exp() + 1 + (1 / x).exp() * (1 / x - 1)


def bisect(func, lo, hi, iters=400):
    """在 [lo,hi] 上二分求根, 要求 func(lo) 与 func(hi) 异号"""
    flo = func(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = func(mid)
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def find_root_left(a):
    """f(1)<0, f(x)->+inf (x->0+), 先向左扩张区间再二分"""
    lo = D(1) / 2
    while f(lo, a) < 0:
        lo /= 2
    return bisect(lambda x: f(x, a), lo, D(1))


def find_root_right(a):
    """f(1)<0, f(x)->+inf (x->+inf), 先向右扩张区间再二分"""
    hi = D(2)
    while f(hi, a) < 0:
        hi = 1 + (hi - 1) * 2
        assert hi < D("1000"), "扩张区间越界"
    return bisect(lambda x: f(x, a), D(1), hi)


def ok(cond):
    return "PASS" if cond else "**FAIL**"


print("=" * 78)
print("检验 0: 常数与极值")
print("=" * 78)
print(f"e                    = {E}")
print(f"g(1) = e + 1         = {g(1)}")
print(f"e + 1 (直接计算)      = {E + 1}")
print(f"两者相等? {ok(abs(g(1) - (E + 1)) < D('1e-55'))}")
print(f"g'(1)                = {gp(1)}   (应为 0: {ok(abs(gp(1)) < D('1e-55'))})")
gmin = min(g(D(1) + D(k) / 1000) for k in range(-50, 51))
print(f"x=1 邻域扫描最小值     = {gmin}  (>= g(1): {ok(gmin >= g(1))})")

print()
print("=" * 78)
print("检验 1: g'(x) 公式正确性 (解析式 vs 中心差分)")
print("=" * 78)
worst = D(0)
for t in [D("0.05"), D("0.3"), D("0.7"), D("0.99"), D("1.01"), D("1.5"), D("3"), D("10")]:
    fd = (g(t + D("1e-25")) - g(t - D("1e-25"))) / (2 * D("1e-25"))
    rel = abs(fd - gp(t)) / max(abs(fd), D("1e-40"))
    worst = max(worst, rel)
print(f"8 个采样点上 (g'(x)_差分 - g'(x)_解析)/|.| 的最大值 = {worst:.3E}")
print(f"解析导数公式与数值差分一致 (<1e-20)? {ok(worst < D('1e-20'))}")
print(f"g' 在 (0,1) 上 <0 ? {ok(all(gp(D(k)/200) < 0 for k in range(1, 200)))}")
print(f"g' 在 (1,inf) 上 >0 ? {ok(all(gp(1 + D(k)/50) > 0 for k in range(1, 500)))}")

print()
print("=" * 78)
print("检验 2: h(x)=g(x)-g(1/x) 在 (0,1) 上恒为负 (第(2)问核心引理)")
print("=" * 78)
vals = [D(k) / 1000 for k in range(1, 1000)]
hs = [h(x) for x in vals]
print(f"x 从 0.001 到 0.999 扫描 999 点:  max h(x) = {max(hs)}")
print(f"h(x) < 0 全部成立? {ok(all(v < 0 for v in hs))}")
print(f"h(1) = {h(1)}  (应为 0: {ok(h(1) == 0)})")
worst_h = max(abs(hp_fd(x) - hp_formula(x)) for x in [D("0.1"), D("0.4"), D("0.8"), D("0.95")])
print(f"h'(x) 解析式 vs 差分 最大相对偏差 = {worst_h:.3E}")
print(f"h'(x) > 0 在 (0,1) 上成立? {ok(all(hp_formula(D(k)/1000) > 0 for k in range(1, 1000)))}")

print()
print("=" * 78)
print("检验 3: 辅助函数 m(x)=e^x+x-xe^(1/x)-1 的符号与单调性")
print("=" * 78)
print(f"m(1) = {m(1)}  (应为 0: {ok(abs(m(1)) < D('1e-55'))})")
print(f"m(x)<0 且 m'(x)>0 在 (0,1) 上? "
      f"{ok(all(m(D(k)/1000) < 0 and mp(D(k)/1000) > 0 for k in range(1, 1000)))}")
print(f"m'(x) 最小值 (0<x<1) = {min(mp(D(k)/1000) for k in range(1, 1000))}")
# 用差分复核 m'(x)
w = max(abs((m(x + D('1e-25')) - m(x - D('1e-25'))) / (2 * D('1e-25')) - mp(x))
        for x in [D("0.2"), D("0.5"), D("0.9")])
print(f"m'(x) 解析式 vs 差分 最大偏差 = {w:.3E}   {ok(w < D('1e-20'))}")

print()
print("=" * 78)
print("检验 4: 第一问 —— a 的临界值 (数值求 g 的最小值)")
print("=" * 78)
# 用三分搜索独立求 g 在 (0, 20] 上的最小值
lo, hi = D("0.01"), D("20")
for _ in range(300):
    m1 = lo + (hi - lo) / 3
    m2 = hi - (hi - lo) / 3
    if g(m1) < g(m2):
        hi = m2
    else:
        lo = m1
xstar = (lo + hi) / 2
print(f"三分搜索得到的极小值点 x* = {xstar}")
print(f"极小值 g(x*) = {g(xstar)}   (应等于 e+1 = {E+1})")
print(f"偏差 = {abs(g(xstar)-(E+1)):.3E}   {ok(abs(g(xstar)-(E+1)) < D('1e-40'))}")
print(f"a = e+1 时 f(1) = 0 且 f>=0;  a 略大时 f 取负值:")
print(f"   f(1) 在 a=e+1 处   = {f(1, E+1)}")
print(f"   f(1) 在 a=e+1+1e-9 = {f(1, E + 1 + D('1e-9'))}  (<0: "
      f"{ok(f(1, E + 1 + D('1e-9')) < 0)})")

print()
print("=" * 78)
print("检验 5: 第二问 —— 对各种 a>e+1 实际求两根并检查 x1*x2 < 1")
print("=" * 78)
print(f"{'a':>12} {'x1':>28} {'x2':>28} {'x1*x2':>26} {'<1?':>6} {'1/(x1)-x2':>14}")
rows = []
alist = [E + 1 + D(s) for s in
         ["1e-6", "1e-3", "0.01", "0.1", "0.5", "1", "2", "5", "20", "100", "1000", "100000"]]
for a in alist:
    x1 = find_root_left(a)
    x2 = find_root_right(a)
    prod = x1 * x2
    gap = 1 / x1 - x2
    rows.append((a, x1, x2, prod))
    print(f"{a:>12.6f} {x1:>28.18f} {x2:>28.18f} {prod:>26.20f} "
          f"{ok(prod < 1):>6} {gap:>14.3E}")
    assert abs(f(x1, a)) < D("1e-45") and abs(f(x2, a)) < D("1e-45"), "根不满足方程!"

print()
print(f"所有 a 的 x1*x2 都 < 1 ? {ok(all(r[3] < 1 for r in rows))}")
print("趋势: a 增大 => 两根分离越远 => 乘积远离 1 (单调递减);")
print("      反之 a -> (e+1)^+ 时乘积从下方单调递增趋于 1.")
prods = [r[3] for r in rows]
print(f"随 a 增大, 乘积严格单调递减? {ok(all(prods[i] > prods[i+1] for i in range(len(prods)-1)))}")
print(f"首项 (a 最接近 e+1) 的乘积 = {prods[0]:.25f}")
print(f"       1 - x1*x2 = {1-prods[0]:.6E}")

# 随机抽查 40 个 a, 独立复核
import random
random.seed(20220607)
print("随机抽查 40 个 a in (e+1, e+1+50):")
bad = []
for _ in range(40):
    a = E + 1 + D(str(round(random.uniform(1e-9, 50), 9)))
    X1, X2 = find_root_left(a), find_root_right(a)
    if not (X1 < 1 < X2 and X1 * X2 < 1 and abs(f(X1, a)) < D("1e-45") and abs(f(X2, a)) < D("1e-45")):
        bad.append(a)
print(f"   全部满足 x1<1<x2, f(x1)=f(x2)=0 且 x1*x2<1 ? {ok(not bad)}  反例数={len(bad)}")

print()
print("=" * 78)
print("检验 6: 极端边界与'未达'情形")
print("=" * 78)
a = E + 1 + D("1e-40")
x1 = find_root_left(a)
x2 = find_root_right(a)
print(f"a 只比 e+1 大 1e-40 时: x1-1 = {x1-1:.6E}")
print(f"                        x2-1 = {x2-1:.6E}")
print(f"                        x1*x2 = 1 - {1-x1*x2:.6E}   < 1 ? {ok(x1*x2 < 1)}")
print(f"                        (对称抛物近似: 偏差应与 a-(e+1)=1e-40 同阶)")
a = E + 1
print(f"a = e+1 时 f(x) >= 0 且只有一个零点 x=1: f(1)={f(1,a)}, "
      f"f(0.5)={f(D('0.5'),a)}, f(3)={f(3,a)}")

print()
print("=" * 78)
print("检验 7: 反向试探 —— 若结论方向反过来 (x1*x2>1) 会怎样?")
print("=" * 78)
print("对每个 a 用同一组根计算 h(x1)=f(x1)-f(1/x1):")
bad = 0
for a in alist[:8]:
    x1 = find_root_left(a)
    if not (h(x1) < 0):
        bad += 1
print(f"h(x1) < 0 全部成立 (否则 8 个中应有 {bad} 个反例)? {ok(bad == 0)}")
print(f"并且 1/x1 - x2 > 0 (即 x2 < 1/x1) 全部成立? {ok(all(1/r[1]-r[2] > 0 for r in rows))}")
print()
print("全部检验结束。")
