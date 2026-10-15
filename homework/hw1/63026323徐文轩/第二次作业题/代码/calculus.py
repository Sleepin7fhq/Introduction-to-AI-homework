# -*- coding: utf-8 -*-
"""Q4 numeric verification: z = x^2 + y^2 - x/y + xy."""
from fractions import Fraction as F
from math import isclose


def z(x, y):
    return x**2 + y**2 - x / y + x * y


print("z(2, 0.5) =", z(2, 0.5))
print("exact via fractions:", F(2) ** 2 + F(1, 2) ** 2 - F(2) / F(1, 2) + F(2) * F(1, 2))
print("term-by-term: 4 + 0.25 - 4 + 1 =", 4 + 0.25 - 4 + 1)

dx_exact = 2 * 2 + 0.5 - 1 / 0.5
dy_exact = 2 * 0.5 + 2 + 2 / 0.5**2
print("\ndz/dx at (2,0.5) [2x + y - 1/y] =", dx_exact)
print("dz/dy at (2,0.5) [2y + x + x/y^2] =", dy_exact)

h = 1e-7
ndx = (z(2 + h, 0.5) - z(2 - h, 0.5)) / (2 * h)
ndy = (z(2, 0.5 + h) - z(2, 0.5 - h)) / (2 * h)
print(f"\nnumerical dz/dx = {ndx:.10f}  (matches: {isclose(ndx, dx_exact, rel_tol=1e-6)})")
print(f"numerical dz/dy = {ndy:.10f}  (matches: {isclose(ndy, dy_exact, rel_tol=1e-6)})")

# gradient step illustration: must use a small lr, y=0.5 is near the singular line y=0
print("\ngradient direction at (2,0.5): grad = (2.5, 11.0);  descent dir = (-2.5, -11.0)")
for lr in [0.5, 0.1, 0.01, 0.001, 0.0001]:
    nx, ny = 2 - lr * dx_exact, 0.5 - lr * dy_exact
    print(f"  lr={lr:<8} -> (x,y)=({nx:+.5f},{ny:+.5f})   z: {z(2,0.5):.6f} -> {z(nx,ny):.6f}"
          f"   decreased={z(nx, ny) < z(2, 0.5)}")
print("  NOTE: lr too large steps across y=0, where -x/y blows up; local descent only holds for small lr.")

# finite-difference confirmation of the sign of dz/dy
print("\nsign check dz/dy: z(2,0.51) - z(2,0.50) =", f"{z(2,0.51) - z(2,0.50):.6f}", "-> positive => dz/dy > 0")

# sanity: symbolic-derivative forms verified by many random points
import random
random.seed(0)
okx = oky = True
for _ in range(1000):
    a = random.uniform(0.5, 3)
    b = random.uniform(0.5, 3)
    if not isclose((z(a + h, b) - z(a - h, b)) / (2 * h), 2 * a + b - 1 / b, rel_tol=1e-5):
        okx = False
    if not isclose((z(a, b + h) - z(a, b - h)) / (2 * h), 2 * b + a + a / b**2, rel_tol=1e-5):
        oky = False
print(f"\nformula check over 1000 random points: dz/dx OK={okx}, dz/dy OK={oky}")
