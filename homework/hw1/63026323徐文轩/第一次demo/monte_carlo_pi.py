# -*- coding: utf-8 -*-
"""
蒙特卡洛方法估计圆周率 pi —— 数学实验
=====================================================

实验区域 : 边长 2 的正方形  [-1, 1] x [-1, 1]
目标区域 : 半径 1 的单位圆    x^2 + y^2 <= 1

核心公式 :  pi ~= 4 * (圆内点数 / 总点数)

重要说明:
    整个"模拟与估计"过程中, 程序完全没有使用 pi 的数值。
    真实的 pi 只在最后一步(计算误差、画参考线)才被引入用于比较。

输出文件(全部保存在本脚本所在目录):
    monte_carlo_pi.png      -- 第一幅图: N=5000 的随机点分布
    pi_convergence.png      -- 第二幅图: 估计值随 N 的收敛过程
    monte_carlo_results.csv -- 四组实验的结果记录
"""

import math
import os
import time

import numpy as np

import matplotlib
matplotlib.use("Agg")          # 无窗口后端, 只存图片文件
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle

# ----------------------------------------------------------------------
# 0. 基本设置
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 中文字体: 依次尝试, 取第一个系统里真实存在的字体
_CANDIDATE_FONTS = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
                    "Source Han Sans SC", "WenQuanYi Micro Hei", "DejaVu Sans"]
_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}
for _name in _CANDIDATE_FONTS:
    if _name in _INSTALLED:
        plt.rcParams["font.sans-serif"] = [_name]
        break
plt.rcParams["axes.unicode_minus"] = False     # 负号正常显示
plt.rcParams["figure.dpi"] = 120

SEED = 2025                       # 固定随机种子, 保证结果可复现
SAMPLE_SIZES = [100, 1000, 10000, 100000]

# 真实 pi: 只用于"最后"的比较, 不参与任何模拟计算
PI_TRUE = math.pi


# ----------------------------------------------------------------------
# 1. 核心函数: 抛点 -> 数圆内点数 -> 估计 pi
# ----------------------------------------------------------------------
def monte_carlo_pi(n, rng):
    """在 [-1,1]^2 上均匀撒 n 个点, 返回 (pi估计值, 圆内点数, x数组, y数组)"""
    x = rng.uniform(-1.0, 1.0, n)          # x 坐标: [-1,1] 上均匀分布
    y = rng.uniform(-1.0, 1.0, n)          # y 坐标: [-1,1] 上均匀分布
    inside = (x * x + y * y) <= 1.0        # 落点是否在单位圆内
    n_inside = int(np.count_nonzero(inside))
    pi_hat = 4.0 * n_inside / n            # 关键公式
    return pi_hat, n_inside, x, y, inside


# ----------------------------------------------------------------------
# 2. 四组实验: N = 100 / 1000 / 10000 / 100000
# ----------------------------------------------------------------------
def run_experiments(sample_sizes, base_seed=SEED):
    """四组相互独立的随机实验"""
    records = []
    for k, n in enumerate(sample_sizes):
        rng = np.random.default_rng(base_seed + 1000 * k)   # 每组独立种子
        t0 = time.perf_counter()
        pi_hat, n_inside, _, _, _ = monte_carlo_pi(n, rng)
        elapsed = time.perf_counter() - t0
        records.append({
            "N": n,
            "n_inside": n_inside,
            "n_outside": n - n_inside,
            "ratio": n_inside / n,
            "pi_hat": pi_hat,
            "abs_error": abs(pi_hat - PI_TRUE),
            "rel_error_pct": abs(pi_hat - PI_TRUE) / PI_TRUE * 100.0,
            "seconds": elapsed,
        })
    return records


def print_records(records):
    print("=" * 78)
    print("四组蒙特卡洛实验 (真实 pi = %.10f, 仅用于比较误差)" % PI_TRUE)
    print("=" * 78)
    header = "%8s %10s %10s %10s %9s %10s" % (
        "N", "圆内点数", "圆内比例", "pi估计值", "绝对误差", "相对误差%")
    print(header)
    print("-" * 78)
    for r in records:
        print("%8d %10d %10.5f %10.5f %9.5f %9.3f%%" % (
            r["N"], r["n_inside"], r["ratio"], r["pi_hat"],
            r["abs_error"], r["rel_error_pct"]))
    print("-" * 78)
    # 检验: 绝对误差是否大致按 1/sqrt(N) 缩小
    for a, b in zip(records[:-1], records[1:]):
        ratio_n = b["N"] / a["N"]
        print("N: %6d -> %6d (x%g)   误差缩小到原来的 %.2f 倍   "
              "理论(1/sqrt)约 %.2f 倍"
              % (a["N"], b["N"], ratio_n,
                 b["abs_error"] / a["abs_error"] if a["abs_error"] > 0 else float("nan"),
                 1.0 / math.sqrt(ratio_n)))
    print()


# ----------------------------------------------------------------------
# 3. 第一幅图: N = 5000 的随机点分布
# ----------------------------------------------------------------------
def plot_demo(n_demo=5000, seed=SEED + 7):
    rng = np.random.default_rng(seed)
    pi_hat, n_inside, x, y, inside = monte_carlo_pi(n_demo, rng)

    fig, ax = plt.subplots(figsize=(7.6, 7.6))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.90, bottom=0.10)

    # 圆外的点: 灰色小叉
    ax.scatter(x[~inside], y[~inside], s=14, marker="x", linewidths=0.8,
               c="#9aa0a6", alpha=0.75, label="圆外的点 (%d 个)" % (n_demo - n_inside))
    # 圆内的点: 红色实心圆
    ax.scatter(x[inside], y[inside], s=16, marker="o", linewidths=0,
               c="#e8452c", alpha=0.70, label="圆内的点 (%d 个)" % n_inside)

    # 单位圆边界
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec="#1a3d7c", lw=2.2, zorder=5))
    # 正方形边界
    ax.add_patch(plt.Rectangle((-1, -1), 2, 2, fill=False, ec="black", lw=1.6, zorder=5))

    ax.set_xlim(-1.04, 1.04)
    ax.set_ylim(-1.04, 1.04)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("蒙特卡洛方法估计 π：在正方形内随机撒 %d 个点" % n_demo,
                 fontsize=14, pad=12)
    ax.grid(alpha=0.18, linestyle=":")
    ax.legend(loc="upper right", fontsize=10, framealpha=0.92)

    txt = ("随机点数 N = %d\n"
           "落在圆内 = %d\n"
           "圆内比例 = %.4f\n"
           "π ≈ 4 × %.4f = %.4f"
           % (n_demo, n_inside, n_inside / n_demo, n_inside / n_demo, pi_hat))
    ax.text(0.03, 0.965, txt, transform=ax.transAxes, fontsize=11.5,
            va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.55", facecolor="#fffbe6",
                      edgecolor="#1a3d7c", linewidth=1.3, alpha=0.95))

    out = os.path.join(BASE_DIR, "monte_carlo_pi.png")
    fig.savefig(out)
    plt.close(fig)
    print("[图1] 已保存: %s   (N=%d, 圆内=%d, pi估计=%.5f)"
          % (out, n_demo, n_inside, pi_hat))
    return pi_hat, n_inside, n_demo


# ----------------------------------------------------------------------
# 4. 第二幅图: 估计值随 N 的收敛过程
# ----------------------------------------------------------------------
def convergence_data(max_n=100000, n_runs=8, base_seed=SEED + 20):
    """做 n_runs 条独立的"长实验", 记录累计估计值曲线"""
    n_axis = np.arange(1, max_n + 1)
    curves = np.empty((n_runs, max_n))
    for i in range(n_runs):
        rng = np.random.default_rng(base_seed + i)
        x = rng.uniform(-1.0, 1.0, max_n)
        y = rng.uniform(-1.0, 1.0, max_n)
        inside = (x * x + y * y) <= 1.0
        cum = np.cumsum(inside)                    # 累计圆内点数
        curves[i] = 4.0 * cum / n_axis             # 累计估计值
    return n_axis, curves


def plot_convergence(records, max_n=100000, n_runs=8):
    n_axis, curves = convergence_data(max_n=max_n, n_runs=n_runs)

    fig, axes = plt.subplots(1, 2, figsize=(15.0, 6.2))
    fig.subplots_adjust(left=0.06, right=0.985, top=0.87, bottom=0.11, wspace=0.22)

    # ---------- (a) 累计估计值 vs N ----------
    ax = axes[0]
    ck = np.unique(np.round(np.logspace(0, np.log10(max_n), 260)).astype(int))
    ck = ck[(ck >= 1) & (ck <= max_n)]

    for i in range(n_runs):
        ax.plot(ck, curves[i][ck - 1], lw=0.8, alpha=0.35, color="#7a8ea8",
                label="单次实验的累计估计" if i == 0 else None)
    ax.plot(ck, curves[0][ck - 1], lw=2.4, color="#e8452c",
            label="第 1 次实验（加粗）")
    ax.axhline(PI_TRUE, color="#1a3d7c", ls="--", lw=2.0,
               label="真实 π = %.5f（仅作参考线）" % PI_TRUE)

    # 四组实验的结果点
    ax.scatter([r["N"] for r in records], [r["pi_hat"] for r in records],
               s=70, marker="D", c="black", zorder=6,
               label="四组实验的估计值")
    for r in records:
        ax.annotate("%.3f" % r["pi_hat"], (r["N"], r["pi_hat"]),
                    textcoords="offset points", xytext=(6, 8), fontsize=9.5)

    ax.set_xscale("log")
    ax.set_xlim(1, max_n * 1.15)
    ax.set_ylim(PI_TRUE - 0.75, PI_TRUE + 0.75)
    ax.set_xlabel("随机点数量 N（对数坐标）")
    ax.set_ylabel("π 的估计值  4 × 圆内比例")
    ax.set_title("(a) 估计值随样本量的收敛过程", fontsize=13)
    ax.grid(alpha=0.25, which="both", linestyle=":")
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.93)

    # ---------- (b) 平均绝对误差 vs N ----------
    ax2 = axes[1]
    err = np.abs(curves - PI_TRUE)
    mean_err = err.mean(axis=0)
    ax2.plot(n_axis, mean_err, lw=2.2, color="#e8452c",
             label="%d 次独立实验的平均绝对误差" % n_runs)

    guide = mean_err[9] * np.sqrt(10.0) / np.sqrt(n_axis)   # 以 N=10 处为基准
    ax2.plot(n_axis, guide, lw=1.6, ls="--", color="#1a3d7c",
             label="参照斜率 ∝ 1/√N")

    for r in records:
        ax2.scatter([r["N"]], [r["abs_error"]], s=62, marker="D", c="black",
                    zorder=6, label="四组实验的误差" if r["N"] == records[0]["N"] else None)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(1, max_n * 1.15)
    ax2.set_ylim(2e-4, 4.0)
    ax2.set_xlabel("随机点数量 N（对数坐标）")
    ax2.set_ylabel("|π 的估计值 − 真实 π|（对数坐标）")
    ax2.set_title("(b) 误差随样本量的下降趋势", fontsize=13)
    ax2.grid(alpha=0.25, which="both", linestyle=":")
    ax2.legend(loc="lower left", fontsize=9.5, framealpha=0.93)

    fig.suptitle("蒙特卡洛方法估计 π：样本量越大，结果越稳定",
                 fontsize=15, y=0.965)
    out = os.path.join(BASE_DIR, "pi_convergence.png")
    fig.savefig(out)
    plt.close(fig)
    print("[图2] 已保存: %s" % out)


# ----------------------------------------------------------------------
# 5. 结果写入 CSV
# ----------------------------------------------------------------------
def save_csv(records):
    out = os.path.join(BASE_DIR, "monte_carlo_results.csv")
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write("N,圆内点数,圆外点数,圆内比例,pi估计值,绝对误差,相对误差百分比,耗时秒\n")
        for r in records:
            f.write("%d,%d,%d,%.6f,%.6f,%.6f,%.4f,%.6f\n" % (
                r["N"], r["n_inside"], r["n_outside"], r["ratio"],
                r["pi_hat"], r["abs_error"], r["rel_error_pct"], r["seconds"]))
    print("[数据] 已保存: %s" % out)


def save_convergence_stats(records, max_n=100000, n_runs=8):
    """多次重复实验: 统计不同 N 处的平均绝对误差, 说明"误差随 N 下降"是趋势而非必然"""
    n_axis, curves = convergence_data(max_n=max_n, n_runs=n_runs)
    out = os.path.join(BASE_DIR, "monte_carlo_convergence.csv")
    print("\n" + "=" * 78)
    print("重复 %d 次独立实验的统计（用于观察趋势）" % n_runs)
    print("=" * 78)
    print("%8s %12s %12s %12s %12s" % ("N", "平均估计值", "平均绝对误差",
                                        "最大绝对误差", "最小绝对误差"))
    print("-" * 78)
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write("N,平均估计值,平均绝对误差,最大绝对误差,最小绝对误差\n")
        for r in records:
            n = r["N"]
            vals = curves[:, n - 1]
            e = np.abs(vals - PI_TRUE)
            print("%8d %12.5f %12.5f %12.5f %12.5f"
                  % (n, vals.mean(), e.mean(), e.max(), e.min()))
            f.write("%d,%.6f,%.6f,%.6f,%.6f\n"
                    % (n, vals.mean(), e.mean(), e.max(), e.min()))
    print("-" * 78)
    print("[数据] 已保存: %s\n" % out)


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("中文字体:", plt.rcParams["font.sans-serif"][0])
    records = run_experiments(SAMPLE_SIZES)
    print_records(records)
    save_csv(records)
    save_convergence_stats(records)
    plot_demo(n_demo=5000)
    plot_convergence(records)
    print("\n全部完成。")
