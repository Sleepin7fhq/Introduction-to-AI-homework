import math

def f(x):
    return x * math.exp(x) - 3 * x + 1

# (1) tangent at 0 must be y = -2x + 1
h = 1e-6
fp0 = (f(h) - f(-h)) / (2 * h)
print("f(0) =", f(0), " f'(0) ~", round(fp0, 6), " -> a =", round(fp0 - 1, 6), " b =", f(0))
print("tangent check: f(0)=", f(0), "slope=", round(fp0, 4))

# (2) check claim m >= 2 ln2
def cond2(m, xs):
    return all(f(x + m) - f(x) > m for x in xs)

xs = [10 ** (-6 + i * 0.02) for i in range(0, 400)] + [0.5, 1, 2, 5, 10, 30]
boundary = 2 * math.log(2)
print("\n2ln2 =", boundary)
for m in [boundary - 0.01, boundary - 1e-9, boundary, boundary + 1e-9, boundary + 0.5,
          -0.001, 0, 0.5, 1.0]:
    print(f"  m={m:+.6f} holds={cond2(m, xs)}")

# (3) check claim min k = -2
def cond3(k, xs):
    return all(f(k + x) + f(k - x) > 2 * f(k) for x in xs)

print()
for k in [-2.5, -2.01, -2.001, -2.0, -1.999, -1.5, 0.0, 1.0, 3.0]:
    print(f"  k={k:+.4f} holds={cond3(k, xs)}")

# explicit h(x) = x sinh x /(cosh x -1) asymptotic check
def hh(x):
    return x * math.sinh(x) / (math.cosh(x) - 1)
print("\nh(x) samples:", [(x, round(hh(x), 6)) for x in [0.001, 0.01, 0.1, 0.5, 1, 3, 10]])
print("min approx:", min(hh(x) for x in [10 ** (-6 + i * 0.01) for i in range(0, 700)]))
