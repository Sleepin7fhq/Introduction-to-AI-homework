# 极限求解与 Python 数值验证

## 题目

求极限

\[
L=\lim_{x\to 0}\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}.
\]

---

## 一、数学推导

### 1. 通分

当 \(x\neq 0\) 且 \(\sin x\neq 0\) 时，

\[
\frac{1}{\sin x}-\frac{1}{x}
=\frac{x-\sin x}{x\sin x}.
\]

因此在 \(x=0\) 的去心邻域内，

\[
\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}
=
\frac{x-\sin x}{x\sin x}\arctan\frac{1}{x}.
\]

### 2. 对第一个因子作 Taylor 展开

由正弦函数的 Maclaurin 展开，

\[
\sin x=x-\frac{x^3}{3!}+\frac{x^5}{5!}+O(x^7)
=x-\frac{x^3}{6}+\frac{x^5}{120}+O(x^7).
\]

所以

\[
x-\sin x=\frac{x^3}{6}-\frac{x^5}{120}+O(x^7)
=\frac{x^3}{6}+O(x^5),
\]

并且

\[
x\sin x=x\left(x-\frac{x^3}{6}+O(x^5)\right)
=x^2+O(x^4).
\]

于是

\[
\frac{1}{\sin x}-\frac{1}{x}
=
\frac{\frac{x^3}{6}+O(x^5)}{x^2+O(x^4)}
=
\frac{x}{6}+O(x^3).
\]

因此

\[
\lim_{x\to 0}\left(\frac{1}{\sin x}-\frac{1}{x}\right)
=
\lim_{x\to 0}\left(\frac{x}{6}+O(x^3)\right)
=0.
\]

### 3. 处理第二个因子 \(\arctan(1/x)\)

当 \(x\to 0^+\) 时，\(\frac{1}{x}\to +\infty\)，所以

\[
\lim_{x\to 0^+}\arctan\frac{1}{x}=\frac{\pi}{2}.
\]

当 \(x\to 0^-\) 时，\(\frac{1}{x}\to -\infty\)，所以

\[
\lim_{x\to 0^-}\arctan\frac{1}{x}=-\frac{\pi}{2}.
\]

注意：\(\arctan(1/x)\) 在 \(x\to 0\) 时的双侧极限并不存在，但它是有界函数：

\[
\left|\arctan\frac{1}{x}\right|<\frac{\pi}{2}\qquad (x\neq 0).
\]

### 4. 求原极限

分别考虑左右极限：

\[
\lim_{x\to 0^+}
\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}
=
0\cdot\frac{\pi}{2}=0,
\]

\[
\lim_{x\to 0^-}
\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}
=
0\cdot\left(-\frac{\pi}{2}\right)=0.
\]

左右极限都存在且等于 \(0\)，所以原双侧极限存在，并且

\[
L=0.
\]

也可以直接使用有界性：

\[
\left|
\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}
\right|
\le
\left|\frac{1}{\sin x}-\frac{1}{x}\right|\frac{\pi}{2}
\to 0.
\]

由夹逼定理同样得到 \(L=0\)。

### 5. 更精细的渐近形态

由上面的展开，

\[
\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}
=
\left(\frac{x}{6}+O(x^3)\right)\arctan\frac{1}{x}.
\]

于是：

- 当 \(x\to 0^+\) 时，

\[
f(x)\sim \frac{x}{6}\cdot\frac{\pi}{2}=\frac{\pi x}{12},
\qquad \frac{f(x)}{x}\to \frac{\pi}{12}.
\]

- 当 \(x\to 0^-\) 时，

\[
f(x)\sim \frac{x}{6}\cdot\left(-\frac{\pi}{2}\right)
=-\frac{\pi x}{12}=\frac{\pi |x|}{12},
\qquad \frac{f(x)}{x}\to -\frac{\pi}{12}.
\]

因此两侧的函数值实际上都为正，并且都以 \(\frac{\pi |x|}{12}\) 的速度趋于 \(0\)。

---

## 二、Python 数值验证

### 1. 验证思路

直接用双精度浮点数计算 \(\sin x-x\) 时，在 \(x\) 很小时会发生严重的相消误差。例如 \(x=10^{-12}\) 时，\(\sin x\) 与 \(x\) 的双精度值可能完全相同，从而无法得到正确的差值。

下面的 Python 程序使用标准库 `decimal`，设置 90 位十进制精度，并：

1. 用 Taylor 级数计算 \(\sin x\)；
2. 用 Machin 公式计算 \(\pi\)；
3. 利用精确恒等式

\[
\arctan\frac{1}{x}=\operatorname{sgn}(x)\frac{\pi}{2}-\arctan x
\qquad (x\neq 0)
\]

计算 \(\arctan(1/x)\)，避免直接计算大自变量反正切；
4. 计算不同数量级的 \(x=\pm 10^{-k}\) 处的函数值，并观察 \(f(x)\) 和 \(f(x)/x\) 的变化趋势。

完整脚本见 [verify_limit.py](verify_limit.py)。

### 2. Python 代码

```python
"""High-precision numerical check for
    lim_{x -> 0} (1/sin(x) - 1/x) * arctan(1/x).

Only the Python standard library is used.  Decimal arithmetic avoids the
catastrophic cancellation in sin(x) - x when x is very small.
"""

from decimal import Decimal, getcontext

getcontext().prec = 90
TOL = Decimal("1e-80")


def atan_series(z: Decimal) -> Decimal:
    """arctan(z) by its Taylor series; intended for |z| <= 0.5."""
    z = Decimal(z)
    term = z
    total = z
    z2 = z * z
    n = 1
    while True:
        term *= -z2
        add = term / (2 * n + 1)
        if abs(add) < TOL:
            return total
        total += add
        n += 1


# Machin's formula: pi/4 = 4 arctan(1/5) - arctan(1/239).
PI = 16 * atan_series(Decimal(1) / 5) - 4 * atan_series(Decimal(1) / 239)


def sin_series(x: Decimal) -> Decimal:
    """sin(x) by its Taylor series; intended for small |x|."""
    x = Decimal(x)
    term = x
    total = x
    x2 = x * x
    n = 1
    while True:
        term *= -x2 / ((2 * n) * (2 * n + 1))
        if abs(term) < TOL:
            return total
        total += term
        n += 1


def arctan_reciprocal(x: Decimal) -> Decimal:
    """arctan(1/x), using the exact identity
       arctan(1/x) = sign(x)*pi/2 - arctan(x),  x != 0.
    """
    x = Decimal(x)
    sign = Decimal(1) if x > 0 else Decimal(-1)
    return sign * PI / 2 - atan_series(x)


def limit_expression(x: Decimal):
    x = Decimal(x)
    first_factor = 1 / sin_series(x) - 1 / x
    second_factor = arctan_reciprocal(x)
    return first_factor, second_factor, first_factor * second_factor


def sci(value: Decimal, digits: int = 8) -> str:
    return f"{value:.{digits}E}"


print(f"pi = {PI:.60f}")
print()
print("Numerical values of f(x) = (1/sin x - 1/x) arctan(1/x)")
print("Expected behaviour: f(x) ~ (pi/12)|x| as x -> 0 from either side;")
print("therefore f(x)/x -> +pi/12 (x>0) and -> -pi/12 (x<0).")
print()
header = (
    f"{'x':>10}  {'1/sin(x)-1/x':>17}  {'arctan(1/x)':>16}  "
    f"{'f(x)':>17}  {'f(x)/x':>15}"
)
print(header)
print("-" * len(header))

for k in (1, 2, 4, 6, 8, 10, 12):
    for sign in (1, -1):
        x = Decimal(sign) / (Decimal(10) ** k)
        a, b, f = limit_expression(x)
        print(
            f"{sci(x, 2):>10}  {sci(a, 8):>17}  {sci(b, 8):>16}  "
            f"{sci(f, 8):>17}  {sci(f / x, 8):>15}"
        )

print()
print(f"pi/12 = {PI / 12:.16f}")
print("The ratio f(x)/x approaches +pi/12 from the right and -pi/12 from the left,")
print("while |f(x)| decreases toward 0 on both sides.  Hence the limit is 0.")
```

运行命令：

```text
python verify_limit.py
```

### 3. 运行结果

```text
pi = 3.141592653589793238462643383279502884197169399375105820974945

Numerical values of f(x) = (1/sin x - 1/x) arctan(1/x)
Expected behaviour: f(x) ~ (pi/12)|x| as x -> 0 from either side;
therefore f(x)/x -> +pi/12 (x>0) and -> -pi/12 (x<0).

         x       1/sin(x)-1/x       arctan(1/x)               f(x)           f(x)/x
-----------------------------------------------------------------------------------
   1.00E-1      1.66861316E-2     1.47112767E+0      2.45474300E-2    2.45474300E-1
  -1.00E-1     -1.66861316E-2    -1.47112767E+0      2.45474300E-2   -2.45474300E-1
   1.00E-2      1.66668611E-3     1.56079666E+0      2.60135812E-3    2.60135812E-1
  -1.00E-2     -1.66668611E-3    -1.56079666E+0      2.60135812E-3   -2.60135812E-1
   1.00E-4      1.66666667E-5     1.57069633E+0      2.61782721E-5    2.61782721E-1
  -1.00E-4     -1.66666667E-5    -1.57069633E+0      2.61782721E-5   -2.61782721E-1
   1.00E-6      1.66666667E-7     1.57079533E+0      2.61799221E-7    2.61799221E-1
  -1.00E-6     -1.66666667E-7    -1.57079533E+0      2.61799221E-7   -2.61799221E-1
   1.00E-8      1.66666667E-9     1.57079632E+0      2.61799386E-9    2.61799386E-1
  -1.00E-8     -1.66666667E-9    -1.57079632E+0      2.61799386E-9   -2.61799386E-1
  1.00E-10     1.66666667E-11     1.57079633E+0     2.61799388E-11    2.61799388E-1
 -1.00E-10    -1.66666667E-11    -1.57079633E+0     2.61799388E-11   -2.61799388E-1
  1.00E-12     1.66666667E-13     1.57079633E+0     2.61799388E-13    2.61799388E-1
 -1.00E-12    -1.66666667E-13    -1.57079633E+0     2.61799388E-13   -2.61799388E-1

pi/12 = 0.2617993877991494
The ratio f(x)/x approaches +pi/12 from the right and -pi/12 from the left,
while |f(x)| decreases toward 0 on both sides.  Hence the limit is 0.
```

### 4. 结果分析

从表中可以看到：

1. 当 \(x\) 从右侧趋于 \(0\) 时，第一个因子约为 \(x/6\)，第二个因子趋于 \(\pi/2\)，函数值 \(f(x)\) 为正并且迅速减小；
2. 当 \(x\) 从左侧趋于 \(0\) 时，第一个因子为负，第二个因子趋于 \(-\pi/2\)，两者相乘仍然为正，函数值同样迅速减小；
3. 每将 \(|x|\) 缩小为原来的 \(1/100\)，\(|f(x)|\) 也大致缩小为原来的 \(1/100\)，符合 \(f(x)\sim \frac{\pi |x|}{12}\)；
4. \(f(x)/x\) 在右侧趋近于

\[
\frac{\pi}{12}\approx 0.2617993877991494,
\]

在左侧趋近于

\[
-\frac{\pi}{12}\approx -0.2617993877991494.
\]

例如 \(x=\pm 10^{-12}\) 时，

\[
|f(x)|\approx 2.61799388\times 10^{-13}
\approx \frac{\pi}{12}\times 10^{-12},
\]

与推导完全一致。

数值结果支持并验证了：

\[
L=0.
\]

---

## 三、最终答案

\[
\boxed{\displaystyle
\lim_{x\to 0}\left(\frac{1}{\sin x}-\frac{1}{x}\right)\arctan\frac{1}{x}=0
}
\]

原极限存在，且等于 \(0\)。
