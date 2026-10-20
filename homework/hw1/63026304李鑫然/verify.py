"""2025 年全国一卷数学第 19 题：可复现的数值核验。

只使用 Python 标准库。数值实验用于检查推导，不替代对连续区间的证明。
运行：python verify.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

PI = math.pi
TAU = 2 * PI
ANSWER = 3 * math.sqrt(3)


def f(x: float) -> float:
    return 5 * math.cos(x) - math.cos(5 * x)


def g(x: float, phase: float) -> float:
    return 5 * math.cos(x) - math.cos(5 * x + phase)


def lemma_witness(a: float, theta: float) -> float:
    """构造 y∈[a-theta,a+theta]，使 cos(y)≤cos(theta)。"""
    if not 0 < theta < PI:
        raise ValueError("theta 必须满足 0 < theta < pi")
    k = math.floor((a + PI) / TAU)
    alpha = a - k * TAU   # alpha ∈ [-pi, pi)
    if abs(alpha) >= theta:
        return a
    return k * TAU + (theta if alpha >= 0 else -theta)


def phase_maximum(phase: float) -> tuple[float, float]:
    """用全部驻点求固定 phase 下一个周期内的最大值。

    g'(x)=5[sin(5x+phase)-sin(x)]。
    全部驻点来自两族：
        x=k*pi/2-phase/4
        x=(2*k+1)*pi/6-phase/6
    phase 先归一化到 [0,2*pi)，k=-4,...,12 覆盖 [0,2*pi] 内全部根。
    浮点计算有舍入误差，但此方法不会像纯 x 网格扫描一样漏掉窄峰。
    """
    phase %= TAU
    candidates = [0.0, TAU]
    for k in range(-4, 13):
        for x in (k * PI / 2 - phase / 4,
                  (2 * k + 1) * PI / 6 - phase / 6):
            if -1e-12 <= x <= TAU + 1e-12:
                candidates.append(min(TAU, max(0.0, x)))
    best_x = max(candidates, key=lambda x: g(x, phase))
    return g(best_x, phase), best_x


def main() -> None:
    rng = random.Random(202519)

    # 第一问：2401 个网格点，其中包含 pi/6。
    grid = [i * PI / (4 * 2400) for i in range(2401)]
    best_x = max(grid, key=f)
    first_max = f(best_x)
    assert abs(first_max - ANSWER) < 1e-12
    assert abs(best_x - PI / 6) < 1e-12

    # 第二问：随机样本 + 端点和周期边界案例。
    cases = [(rng.uniform(-20 * PI, 20 * PI),
              rng.uniform(0.001, PI - 0.001)) for _ in range(5000)]
    for theta in (0.001, PI / 6, PI / 2, 5 * PI / 6, PI - 0.001):
        for k in (-2, 0, 3):
            for alpha in (0, theta, -theta, PI, -PI):
                cases.append((k * TAU + alpha, theta))
    for a, theta in cases:
        y = lemma_witness(a, theta)
        assert a - theta - 1e-10 <= y <= a + theta + 1e-10
        assert math.cos(y) <= math.cos(theta) + 1e-10

    # 第三问：721 个相位（含 0 与 2*pi），每个相位均枚举全部驻点。
    phases = [i * TAU / 720 for i in range(721)]
    maxima = [phase_maximum(phase)[0] for phase in phases]
    assert abs(min(maxima) - ANSWER) < 1e-12
    assert abs(max(maxima) - 6) < 1e-12

    # 每个相位用第二问的构造产生一个 g(x,phase)≥3sqrt(3) 的点。
    for phase in phases:
        y = lemma_witness(phase, 5 * PI / 6)
        x = (y - phase) / 5
        assert abs(x) <= PI / 6 + 1e-10
        assert g(x, phase) >= ANSWER - 1e-10

    # 独立交叉检查：25 个相位上，稠密 x 网格不应超过驻点法的最大值。
    dense_gaps = []
    for j in range(25):
        phase = j * TAU / 24
        exact_peak, _ = phase_maximum(phase)
        grid_peak = max(g(i * TAU / 12000, phase) for i in range(12001))
        assert grid_peak <= exact_peak + 1e-10
        dense_gaps.append(exact_peak - grid_peak)
    assert max(dense_gaps) < 1e-5

    # t=0 的全局上界所用五倍角多项式。
    for i in range(2001):
        x = -PI + i * TAU / 2000
        c = math.cos(x)
        assert abs(f(x) - (-16 * c**5 + 20 * c**3)) < 1e-12

    summary = {
        "execution": "Python standard library, actually executed",
        "random_seed": 202519,
        "theoretical_answer": "3*sqrt(3)",
        "answer_decimal": ANSWER,
        "part1_grid_points": len(grid),
        "part1_maximum": first_max,
        "part1_argmax_radians": best_x,
        "lemma_cases_passed": len(cases),
        "phase_points": len(phases),
        "phase_scan_minimum_peak": min(maxima),
        "phase_scan_maximum_peak": max(maxima),
        "phase_zero_peak": phase_maximum(0)[0],
        "phase_pi_peak": phase_maximum(PI)[0],
        "constructive_lower_bound_cases_passed": len(phases),
        "dense_crosscheck_phases": 25,
        "dense_crosscheck_max_gap": max(dense_gaps),
        "polynomial_identity_cases_passed": 2001,
        "dsh_execution": "Not executed in this session; prompts are supplied separately",
        "scope": "Finite numerical checks support, but do not replace, the analytical proof",
    }
    chart_data = {
        "first_question": {
            "x_over_pi": [i / 240 for i in range(61)],
            "f": [f(i * PI / 240) for i in range(61)],
        },
        "phase_scan": {
            "phase_over_pi": [i / 90 for i in range(181)],
            "maxima": [phase_maximum(i * PI / 90)[0] for i in range(181)],
        },
    }
    here = Path(__file__).resolve().parent
    (here / "verification.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (here / "chart_data.json").write_text(
        json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
