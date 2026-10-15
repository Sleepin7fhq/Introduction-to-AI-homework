# -*- coding: utf-8 -*-
"""Numerically confirm: a_1=1, a_{n+1}=a_n+1/a_n;  a_n -> oo ;  determine lim a_n^2/n."""
from decimal import Decimal, getcontext

getcontext().prec = 60

# --- high precision iteration ---
a = Decimal(1)
targets = {10, 100, 1000, 5000, 10000, 50000, 100000, 200000}
print("=" * 78)
print("HIGH-PRECISION ITERATION")
print("=" * 78)
print(f"{'n':>8} {'a_n':>18} {'a_n^2':>18} {'a_n^2/n':>14} {'a_n/sqrt(n)':>14}")
import math
for n in range(1, 200001):
    if n in targets:
        an2 = a * a
        s = an2 / Decimal(n)
        print(f"{n:>8} {str(a)[:18]:>18} {str(an2)[:18]:>18} {float(s):14.6f} {float(a)/math.sqrt(n):14.6f}")
    a = a + 1 / a

print()
print("=" * 78)
print("KEY IDENTITY CHECK   a_n^2 = 2n - 1 + sum_{k=1}^{n-1} 1/a_k^2")
print("=" * 78)
a = Decimal(1)
S = Decimal(0)          # sum of 1/a_k^2 for k=1..n-1
for n in range(1, 100001):
    if n in {10, 1000, 10000, 100000}:
        lhs = a * a
        rhs = Decimal(2 * n - 1) + S
        print(f"n={n:>7}  a_n^2={float(lhs):16.6f}   2n-1+sum={float(rhs):16.6f}   diff={float(lhs - rhs):.3e}")
    S += 1 / (a * a)
    a = a + 1 / a

print()
print("=" * 78)
print("GROWTH COMPARISON")
print("=" * 78)
a = Decimal(1)
for n in range(1, 100001):
    if n in {1000, 10000, 100000}:
        an2 = a * a
        print(f"n={n:>7}: a_n^2={float(an2):14.3f}  2n={2*n:>8}  "
              f"a_n^2/(2n)={float(an2/(2*n)):.4f}  ln(n)={math.log(n):.3f}  "
              f"(a_n^2-2n)/ln(n)={float((an2-2*n)/Decimal(math.log(n))):.4f}")
    a = a + 1 / a
