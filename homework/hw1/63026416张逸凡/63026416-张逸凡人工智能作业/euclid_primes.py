# -*- coding: utf-8 -*-
"""
质数有无穷多个 —— 欧几里得构造性证明的计算机验证
Euclid, 《几何原本》第九卷 命题 20 (Elements, Book IX, Prop. 20)

核心思想：
    设已找到质数 p1, p2, ..., pn。
    构造 N = p1 * p2 * ... * pn + 1。
    则 N 除以其中任何一个 pi 都余 1，故 pi 都不是 N 的因子。
    而 N > 1，必有质因子 q（算术基本定理 / 良序原理）。
    于是 q 是一个不在 p1..pn 中的新质数。
    重复此过程可无限进行 —— 质数无穷多。
"""

import sys
from math import isqrt, log

# 保证在 Windows 控制台（默认 GBK）下也能正确输出中文与符号
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:      # pragma: no cover
    pass


def primes_up_to(limit: int) -> list[int]:
    """埃拉托斯特尼筛法：返回不超过 limit 的全部质数。"""
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, isqrt(limit) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(range(i * i, limit + 1, i)))
    return [i for i in range(2, limit + 1) if sieve[i]]


def smallest_prime_factor(n: int) -> int:
    """返回 n (>1) 的最小质因子 —— 即欧几里得证明中那个『新质数』的可计算版本。"""
    if n % 2 == 0:
        return 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return d
        d += 2
    return n          # n 本身是质数


def euclid_construction(known: list[int]) -> tuple[int, int]:
    """给定已知质数表，执行一次欧几里得构造。

    返回 (N, q)：N = ∏known + 1，q 是 N 的一个质因子，且保证 q ∉ known。
    """
    N = 1
    for p in known:
        N *= p
    N += 1
    return N, smallest_prime_factor(N)


def main() -> None:
    print("=" * 78)
    print("欧几里得构造性证明：逐轮生成新质数")
    print("=" * 78)
    print(f"{'轮次':<4}{'已知质数个数':<14}{'N = ∏pi + 1':<26}{'N 的最小质因子 q':<18}{'q 是否为新质数'}")
    print("-" * 78)

    known = [2]                     # 从第一个质数出发
    for step in range(1, 8):
        N, q = euclid_construction(known)
        is_new = q not in known
        print(f"{step:<5}{len(known):<15}{N:<27}{q:<19}{'是 (NEW)' if is_new else '否'}")
        assert is_new, "构造失败：q 已存在于已知质数表中"
        known.append(q)

    print("-" * 78)
    print(f"经 7 轮构造得到 {len(known)} 个互不相同的质数：")
    print("   ", known)
    print()

    # 反证法的数值印证：前 6 个质数的乘积加 1，其质因子全部是新质数
    base = [2, 3, 5, 7, 11, 13]
    N, q = euclid_construction(base)
    print(f"示例：N = 2·3·5·7·11·13 + 1 = {N}，最小质因子 = {q}")
    print(f"      验证 N mod p = 1，对每个 p ∈ {base}：",
          [N % p for p in base])
    print()

    # 素数计数函数 π(x)：质数个数随 x 无限增长（经验证据，非证明）
    print("素数计数函数 π(x) 的增长（经验数据）：")
    print(f"{'x':>10}{'π(x)':>10}{'x/ln x':>14}{'π(x)/(x/ln x)':>16}")
    for k in range(1, 7):
        x = 10 ** k
        pi_x = len(primes_up_to(x))
        approx = x / log(x)
        print(f"{x:>10}{pi_x:>10}{approx:>14.1f}{pi_x / approx:>16.4f}")
    print()
    print("结论：构造过程可无限重复 → 质数有无限多个。 ∎")


if __name__ == "__main__":
    main()
