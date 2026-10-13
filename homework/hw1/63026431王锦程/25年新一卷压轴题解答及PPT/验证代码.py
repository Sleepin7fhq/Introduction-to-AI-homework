#!/usr/bin/env python3
"""2025 年高考新课标 I 卷数学第 19 题的辅助验证。
仅使用 Python 3 标准库。运行：python3 验证代码.py
数值实验不替代严格证明；完整证明见 PPT 和解答文件。
"""
import json
import math
from pathlib import Path

PI = math.pi
TARGET = 3 * math.sqrt(3)

def f(x, phi=0.0):
    return 5 * math.cos(x) - math.cos(5 * x + phi)

def period_max(phi):
    """枚举一周期所有驻点及端点，避免只依赖离散 x 网格。
    f'=5[sin(5x+phi)-sin x]=0 给出两个驻点族：
    x=(2k*pi-phi)/4 或 x=((2k+1)*pi-phi)/6。
    相位归一化到 [0,2pi)，k=-1,...,7 覆盖所需驻点。
    返回浮点计算的最大值及一个取到最大值的 x。
    """
    phi %= 2 * PI
    candidates = [0.0, 2 * PI]
    for k in range(-1, 8):
        for x in ((2*k*PI-phi)/4, ((2*k+1)*PI-phi)/6):
            if 0 <= x <= 2*PI:
                candidates.append(x)
    x = max(candidates, key=lambda t: f(t, phi))
    return f(x, phi), x

def lemma_witness(a, theta):
    """构造第二问的 y；theta 必须在 (0,pi)。"""
    if not 0 < theta < PI:
        raise ValueError('theta must be in (0, pi)')
    k = math.floor((a + PI)/(2*PI))
    t = a - 2*k*PI  # [-pi, pi)
    if abs(t) >= theta:
        return a
    return 2*k*PI + (theta if t >= 0 else -theta)

def main():
    tol = 1e-10
    # (1) 驻点、两端点与导数符号抽样
    part1 = [(x, f(x)) for x in (0, PI/6, PI/4)]
    assert abs(max(v for _, v in part1) - TARGET) < tol
    for j in range(1, 1000):
        x = (PI/4)*j/1000
        derivative = 10*math.cos(3*x)*math.sin(2*x)
        assert derivative*(PI/6-x) >= -tol
    # (2) 构造法抽样，包括大 theta 与远离原点的区间
    count = 0
    for j in range(1, 100):
        theta = PI*j/100
        for k in range(-100, 101):
            a = k*PI/13
            y = lemma_witness(a, theta)
            assert a-theta-tol <= y <= a+theta+tol
            assert math.cos(y) <= math.cos(theta)+tol
            count += 1
    # (3) 验证五倍角多项式及任意相位的构造下界
    for j in range(2001):
        x = -PI + 2*PI*j/2000
        t = math.cos(x)
        assert abs(f(x) - (20*t**3 - 16*t**5)) < tol
    phase_results = []
    for j in range(721):
        phi = 2*PI*j/720
        y = lemma_witness(phi, 5*PI/6)
        x = (y-phi)/5
        assert abs(x) <= PI/6+tol
        assert f(x, phi) >= TARGET-tol
        maximum, argmax = period_max(phi)
        assert maximum >= TARGET-tol
        phase_results.append({'phi':phi, 'maximum':maximum, 'argmax':argmax})
    m0, x0 = period_max(0)
    assert abs(m0-TARGET) < tol
    # 多项式端点和全部驻点：-1,-sqrt(3)/2,0,sqrt(3)/2,1
    critical = [-1, -math.sqrt(3)/2, 0, math.sqrt(3)/2, 1]
    polynomial_max = max(20*t**3-16*t**5 for t in critical)
    assert abs(polynomial_max-TARGET) < tol
    result = {
        'method':'stationary-point enumeration; floating-point verification',
        'exact_answer':'3*sqrt(3)', 'decimal_answer':TARGET,
        'part1_candidates':[{'x':x,'f':v} for x,v in part1],
        'lemma_cases_passed':count,
        'phase_samples':len(phase_results),
        'phase_sample_minimum':min(r['maximum'] for r in phase_results),
        'phase_zero_maximum':m0, 'phase_zero_argmax':x0,
        'polynomial_critical_maximum':polynomial_max,
        'note':'Finite samples do not prove a universal statement. See the analytic proof.',
        'phase_curve':phase_results
    }
    path = Path(__file__).with_name('验证结果.json')
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='phase_curve'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
