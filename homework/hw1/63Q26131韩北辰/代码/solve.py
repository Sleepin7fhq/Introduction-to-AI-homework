# -*- coding: utf-8 -*-
"""
2026 年普通高等学校招生全国统一考试（新课标 II 卷）数学 第 17 题
—— 完整解答 + 高精度数值验证

题目
    在 △ABC 中，已知 cos B = 3/4，cos²(A+C) + sin A sin C = 1。
    (1) 证明：△ABC 为钝角三角形；
    (2) 若 △ABC 的面积为 √7/4，求 △ABC 的周长。

参考答案：钝角三角形；周长 3 + √2。
本脚本用 Decimal（40 位有效数字）独立复核每一步结论。
"""
from decimal import Decimal as D, getcontext
import math

getcontext().prec = 40

ok = []


def check(name, got, want, tol=D("1e-30")):
    good = abs(D(got) - D(want)) <= tol
    ok.append(good)
    print("  %-34s = %-28s %s" % (name, str(got)[:28], "✓" if good else "✗ 期望 " + str(want)[:20]))
    return good


# ============================================================
# 0. 已知量
# ============================================================
cosB = D(3) / D(4)
sinB = (D(1) - cosB * cosB).sqrt()          # B 为锐角 ⇒ 取正
print("cos B =", cosB, "   sin B =", sinB)

# ============================================================
# 1. 第 (1) 问：证明钝角三角形
#    A + C = π − B  ⇒  cos(A+C) = −cos B
#    cos²(A+C) + sinA sinC = 1  ⇒  sinA sinC = 1 − 9/16 = 7/16
#    cos(A+C) = cosA cosC − sinA sinC  ⇒  cosA cosC = −3/4 + 7/16 = −5/16
#    故 cosA、cosC 异号 ⇒ A、C 中恰有一个钝角
# ============================================================
print("\n第 (1) 问")
cosAC_sum = -cosB
check("cos(A+C) = −cos B", cosAC_sum, D(-3) / D(4))
sinA_sinC = D(1) - cosAC_sum ** 2
check("sinA·sinC = 1 − cos²(A+C)", sinA_sinC, D(7) / D(16))
cosA_cosC = cosAC_sum + sinA_sinC
check("cosA·cosC = cos(A+C) + sinA·sinC", cosA_cosC, D(-5) / D(16))
print("  cosA·cosC = −5/16 < 0，且 cos B = 3/4 > 0 ⇒ A、C 中必有一个钝角 ⇒ △ABC 为钝角三角形")

# 余弦定理的直接核对：由两边一角反求角
cosAC_diff = cosA_cosC + sinA_sinC           # cos(A−C)
check("cos(A−C) = cosA cosC + sinA sinC", cosAC_diff, D(1) / D(8))

# 由和差化积还原 A、C（弧度）
A_plus_C = math.acos(float(cosAC_sum))       # ∈ (0, π)
A_minus_C = math.acos(float(cosAC_diff))     # |A−C| ∈ (0, π/2)
A = math.degrees((A_plus_C + A_minus_C) / 2)
C = math.degrees((A_plus_C - A_minus_C) / 2)
B = math.degrees(math.acos(float(cosB)))
print("  A ≈ %.4f°，B ≈ %.4f°，C ≈ %.4f°（A + B + C = %.6f°）" % (A, B, C, A + B + C))
print("  A 为钝角（%.2f° > 90°）⇒ 结论成立" % A)

# ============================================================
# 2. 第 (2) 问：面积 → ac；正弦定理 → b；余弦定理 → a+c
# ============================================================
print("\n第 (2) 问")
S = (D(7).sqrt()) / D(4)
check("面积 S = √7/4", S, D(7).sqrt() / 4)

# 面积公式 S = (1/2)·a·c·sinB
ac = 2 * S / sinB
check("a·c = 2S / sin B", ac, D(2))

# 正弦定理：a = 2R sinA，c = 2R sinC  ⇒  ac = 4R² sinA sinC
R2 = ac / (4 * sinA_sinC)
check("R² = ac / (4 sinA sinC)", R2, D(8) / D(7))

b = 2 * R2.sqrt() * sinB
check("b = 2R sin B", b, D(2).sqrt())

# 余弦定理：b² = a² + c² − 2ac·cosB
a2_plus_c2 = b * b + 2 * ac * cosB
check("a² + c² = b² + 2ac cos B", a2_plus_c2, D(5))

ac_sum = (a2_plus_c2 + 2 * ac).sqrt()
check("a + c = √(a²+c²+2ac)", ac_sum, D(3))
check("周长 a + b + c", ac_sum + b, D(3) + D(2).sqrt())

# a、c 是 t² − (a+c)t + ac = 0 即 t² − 3t + 2 = 0 的两根 ⇒ 1 与 2
disc = ac_sum * ac_sum - 4 * ac
root_lo = (ac_sum - disc.sqrt()) / 2
root_hi = (ac_sum + disc.sqrt()) / 2
check("a·c = 2 与 a+c = 3 ⇒ 两根为 1、2", root_hi, D(2))
check("a·c = 2 与 a+c = 3 ⇒ 两根为 1、2", root_lo, D(1))
print("\n  边长：{a, c} = {%s, %s}（即 1 与 2），b = √2 ≈ %s"
      % (str(root_lo)[:10], str(root_hi)[:10], str(b)[:12]))
print("  周长 = 1 + 2 + √2 = 3 + √2 ≈", str(ac_sum + b)[:12])

# ============================================================
# 3. 反向校验：用边长 (1, √2, 2) 重建三角形，检查所有已知条件
# ============================================================
print("\n反向校验（边长 a=2, b=√2, c=1）")
a, bb, cc = D(2), D(2).sqrt(), D(1)
check("三角不等式 a < b + c", (a < bb + cc) * 1, 1)
check("面积 = (1/2)ac sinB", D(1) / 2 * a * cc * sinB, S, D("1e-30"))
check("余弦定理求 cos B", (a * a + cc * cc - bb * bb) / (2 * a * cc), cosB)
cosA = (bb * bb + cc * cc - a * a) / (2 * bb * cc)
print("  cos A = %.6f < 0 ⇒ A 为钝角（与 (1) 一致）" % float(cosA))
check("周长 = 3 + √2", a + bb + cc, D(3) + D(2).sqrt())

print("\n全部 %d 项校验：%s" % (len(ok), "全部通过 ✓" if all(ok) else "存在失败项 ✗"))
