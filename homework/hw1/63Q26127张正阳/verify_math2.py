from decimal import Decimal, getcontext

getcontext().prec = 60
D = Decimal


def phi(u):
    return u * u.exp()


def cond(k, x):
    return phi(k + x) + phi(k - x) - 2 * phi(k)


for k in ["-2.01", "-2.001", "-2", "-1.999", "0", "1"]:
    kk = D(k)
    worst = None
    for i in range(-40, 60):
        x = D(10) ** (D(i) / D(10))
        v = cond(kk, x)
        if worst is None or v < worst[1]:
            worst = (x, v)
    print(f"k={k:>7}  worst (x, D) = ({float(worst[0]):.3e}, {float(worst[1]):+.3e})  "
          f"holds={worst[1] > 0}")

print()
# part (2) at boundary m = 2 ln 2 : F(x) = g(x+m) - g(x) - 4m must be > 0 for x>0
m = 2 * D(2).ln()
print("m = 2ln2 =", m)


def g(t):
    return t * t.exp()


for i in range(-30, 30):
    x = D(10) ** (D(i) / D(10))
    v = g(x + m) - g(x) - 4 * m
    if v <= 0:
        print("  FAIL at x =", float(x), float(v))
        break
else:
    print("  F(x) > 4m holds for all sampled x > 0 at m = 2ln2")
