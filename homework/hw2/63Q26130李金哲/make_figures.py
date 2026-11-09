"""make_figures.py —— 生成报告所需的全部插图（figures/*.png）。"""
import json
import os
import sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from plot_kit import (canvas, finish, axes, line, band, legend, legend_row, bars,
                      font, COLORS, INK, MUTED, _s, SCALE)
from rl_core import MazeEnv
from mazes import LAYOUTS, REWARD_MAP

FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

with open(os.path.join(HERE, "results", "summary.json"), encoding="utf-8") as f:
    S = json.load(f)

WALL_C = (74, 82, 92)
FLOOR_C = (252, 252, 254)
PIT_C = (176, 58, 58)
START_C = (46, 139, 87)
GOAL_C = (214, 158, 14)
PATH_C = (231, 76, 60)


def bfs_path(layout):
    from collections import deque
    env = MazeEnv(layout)
    dist, par = {env.start: 0}, {env.start: None}
    q = deque([env.start])
    while q:
        s = q.popleft()
        r, c = divmod(s, env.W)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < env.H and 0 <= nc < env.W):
                continue
            ns = nr * env.W + nc
            if ns in env.walls or ns in env.pits or ns in dist:
                continue
            dist[ns] = dist[s] + 1
            par[ns] = s
            q.append(ns)
    if env.goal not in dist:
        return env, [], -1
    path, cur = [], env.goal
    while cur is not None:
        path.append(cur)
        cur = par[cur]
    return env, path[::-1], dist[env.goal]


def maze_panel(d, x, y, cell, layout, title, show_path=True, heat=None,
               path_color=PATH_C, subtitle=None):
    env = MazeEnv(layout)
    H, W = env.H, env.W
    for r in range(H):
        for c in range(W):
            i = r * W + c
            x0, y0 = x + c * cell, y + r * cell
            fill = WALL_C if i in env.walls else (PIT_C if i in env.pits else FLOOR_C)
            d.rectangle([_s(x0), _s(y0), _s(x0 + cell), _s(y0 + cell)], fill=fill,
                        outline=(216, 221, 228), width=_s(1))
    if heat is not None:
        hmax = max(h for row in heat for h in row) or 1
        for r in range(H):
            for c in range(W):
                i = r * W + c
                v = heat[r][c] / hmax
                if i in env.walls or v <= 0:
                    continue
                a = int(24 + 165 * v ** 0.55)
                box = (_s(x + c * cell), _s(y + r * cell),
                       _s(x + (c + 1) * cell), _s(y + (r + 1) * cell))
                tile = d._image.crop(box).convert("RGBA")
                ov = Image.new("RGBA", tile.size, (39, 84, 156, a))
                d._image.paste(Image.alpha_composite(tile, ov).convert("RGB"), box[:2])
    # 陷阱里的字母
    fp = font(cell * 0.40, bold=True)
    for i in env.pits:
        r, c = divmod(i, W)
        d.text((_s(x + c * cell + cell / 2 - d.textlength("P", font=fp) / SCALE / 2),
                _s(y + r * cell + cell * 0.20)), "P", font=fp, fill=(255, 255, 255))
    if show_path:
        _, path, _ = bfs_path(layout)
        if path:
            pts = [(_s(x + (p % W) * cell + cell / 2), _s(y + (p // W) * cell + cell / 2))
                   for p in path]
            d.line(pts, fill=path_color, width=_s(cell * 0.15), joint="curve")
    f = font(cell * 0.44, bold=True)
    for i, (ch, col) in ((env.start, ("S", START_C)), (env.goal, ("G", GOAL_C))):
        r, c = divmod(i, W)
        x0, y0 = x + c * cell, y + r * cell
        d.ellipse([_s(x0 + cell * 0.13), _s(y0 + cell * 0.13),
                   _s(x0 + cell * 0.87), _s(y0 + cell * 0.87)], fill=col)
        d.text((_s(x0 + cell / 2 - d.textlength(ch, font=f) / SCALE / 2),
                _s(y0 + cell * 0.23)), ch, font=f, fill=(255, 255, 255))
    if title:
        d.text((_s(x + 2), _s(y - 30)), title, font=font(14, bold=True), fill=INK)
    if subtitle:
        d.text((_s(x + 2), _s(y + H * cell + 8)), subtitle, font=font(11), fill=MUTED)


def fig1():
    W, H = 1380, 520
    img, d = canvas(W, H)
    cell, gap, y0 = 42, 60, 62
    specs = [("simple", "简单版：开阔空间，仅 1 个陷阱"),
             ("multipit", "多坑版：同尺寸墙体 + 4 个陷阱"),
             ("deadend", "死胡同版：9 条盲道，探索最难")]
    x = 42
    for key, title in specs:
        env, path, dist = bfs_path(LAYOUTS[key])
        maze_panel(d, x, y0, cell, LAYOUTS[key], title,
                   subtitle=f"可走格 {env.n_states - len(env.walls)} 个 · 最短路 {dist} 步")
        x += env.W * cell + gap
    legend_row(d, [("起点 S", START_C, "square"), ("终点 G", GOAL_C, "square"),
                   ("陷阱 P", PIT_C, "square"), ("墙", WALL_C, "square"),
                   ("最短路径", PATH_C, "line")], 42, 490, size=12)
    return finish(img, os.path.join(FIG, "fig1_mazes.png"))


def fig2():
    W, H = 1380, 530
    img, d = canvas(W, H)
    eps = S["exp1_eval_ep"]
    names = {"simple": "简单版", "multipit": "多坑版", "deadend": "死胡同版"}
    pw, ph = 400, 300
    for i, lay in enumerate(("simple", "multipit", "deadend")):
        x = 78 + i * 440
        X, Y = axes(d, (x, 70, x + pw, 70 + ph), (0, 800), (0, 1.02),
                    xlabel="训练回合", ylabel="贪心策略成功率" if i == 0 else "",
                    title=names[lay], xticks=[0, 200, 400, 600, 800],
                    yticks=[0, 0.25, 0.5, 0.75, 1.0])
        for algo, col in (("TD", COLORS["TD"]), ("MC", COLORS["MC"])):
            m = np.array(S["exp1"][f"{lay}_{algo}"]["mean"])
            s = np.array(S["exp1"][f"{lay}_{algo}"]["std"])
            band(d, X, Y, eps, np.clip(m - s, 0, 1), np.clip(m + s, 0, 1), col, 26)
            line(d, X, Y, eps, m, col, 2.4)
    legend_row(d, [("Q-learning（TD）", COLORS["TD"], "line"),
                   ("蒙特卡洛控制（MC）", COLORS["MC"], "line")], 78, 442, size=13)
    d.text((_s(78), _s(482)), "曲线为 8 个随机种子的均值，阴影为 ±1 标准差；"
           "评估时 ε=0（纯贪心策略），每 10 回合评估一次", font=font(11), fill=MUTED)
    return finish(img, os.path.join(FIG, "fig2_td_vs_mc.png"))


def fig3():
    W, H = 1380, 560
    img, d = canvas(W, H)
    labels = {"sparse": "稀疏奖励（基线）", "proximity": "邻近奖励（被钻空子）",
              "potential": "势函数塑形（PBRS）"}
    X, Y = axes(d, (78, 100, 760, 400), (0, 3000), (-10, 380),
                xlabel="训练回合", ylabel="每回合获得的（塑形后）奖励",
                title="训练时的奖励曲线", xticks=[0, 1000, 2000, 3000])
    for mode in ("sparse", "proximity", "potential"):
        mr = np.array(S["exp2"][mode]["mode_ret"])
        line(d, X, Y, np.arange(len(mr)) + 20, mr, COLORS[mode], 2.4)
    legend_row(d, [(labels[m], COLORS[m], "line") for m in
                   ("sparse", "proximity", "potential")], 78, 464, size=11, pad=14)

    visits = np.array(S["exp2"]["proximity"]["visits"])
    maze_panel(d, 890, 100, 44, REWARD_MAP, "邻近奖励 Agent 的停留热区",
               show_path=False, heat=visits.tolist(),
               subtitle=None)
    d.text((_s(890), _s(100 + 9 * 44 + 10)), "颜色越深 = 停留越久：它在离终点 2~3 格处",
           font=font(11), fill=MUTED)
    d.text((_s(890), _s(100 + 9 * 44 + 28)), "来回打转，从不真正踏进终点",
           font=font(11), fill=MUTED)
    d.text((_s(78), _s(500)),
           "邻近奖励把「每回合奖励」刷到 300 以上，真实任务成功率却只有 0.09 —— 典型的奖励黑客",
           font=font(12), fill=PIT_C)
    return finish(img, os.path.join(FIG, "fig3_reward_hack.png"))


def fig4():
    W, H = 1380, 560
    img, d = canvas(W, H)
    eps = list(range(10, 2001, 10))
    names = {"none": "无示范", "expert": "专家示范", "good": "良好示范",
             "fair": "一般示范", "random": "随机示范", "reverse": "反向示范"}
    order = ("none", "expert", "good", "fair", "random", "reverse")
    X, Y = axes(d, (78, 100, 780, 400), (0, 2000), (0, 1.02),
                xlabel="训练回合", ylabel="贪心策略成功率",
                title="不同示范质量下的学习曲线", xticks=[0, 500, 1000, 1500, 2000],
                yticks=[0, 0.25, 0.5, 0.75, 1.0])
    for k in order:
        line(d, X, Y, eps, S["exp3"][k]["mean"], COLORS[k], 2.2)
    legend_row(d, [(names[k], COLORS[k], "line") for k in order], 78, 466, size=11, pad=12)

    vals = [S["exp3"][k]["init_success"] for k in order]
    bars(d, (900, 100, 1330, 400), vals, ["无", "专家", "良好", "一般", "随机", "反向"],
         [COLORS[k] for k in order], ylim=(0, 1.05),
         title="模仿初始化后的初始成功率", ylabel="成功率")
    d.text((_s(78), _s(505)),
           "示范越好，起点越高、收敛越快；随机 / 反向示范等于往 Q 表里灌错误价值，"
           "2000 回合内都没能恢复", font=font(12), fill=MUTED)
    return finish(img, os.path.join(FIG, "fig4_imitation.png"))


def fig5():
    W, H = 1380, 560
    img, d = canvas(W, H)
    eps = list(range(10, 801, 10))
    order = ["固定 ε=0.10", "固定 ε=0.30", "线性衰减 1.0→0.05", "指数衰减 τ=120", "自适应衰减"]
    cols = [(120, 128, 138), (192, 57, 43), (31, 138, 92), (27, 110, 194), (214, 158, 14)]
    short = ["固定 0.10", "固定 0.30", "线性衰减", "指数衰减", "自适应"]
    X, Y = axes(d, (78, 100, 720, 400), (0, 800), (0, 1.02),
                xlabel="训练回合", ylabel="贪心策略成功率",
                title="不同 ε 策略的学习曲线", xticks=[0, 200, 400, 600, 800],
                yticks=[0, 0.25, 0.5, 0.75, 1.0])
    for name, c in zip(order, cols):
        line(d, X, Y, eps, S["exp4"][name]["mean"], c, 2.2)
    legend_row(d, [(s, c, "line") for s, c in zip(short, cols)], 78, 466, size=11, pad=12)

    X2, Y2 = axes(d, (800, 100, 1330, 400), (0, 800), (0, 1.02),
                  xlabel="训练回合", ylabel="ε 取值", title="ε 随回合的实际变化",
                  xticks=[0, 200, 400, 600, 800], yticks=[0, 0.25, 0.5, 0.75, 1.0])
    for name, c in zip(order, cols):
        tr = S["exp4"][name]["eps_traj"]
        line(d, X2, Y2, [50 * i + 25 for i in range(len(tr))], tr, c, 2.2)
    d.text((_s(78), _s(505)),
           "衰减策略后期几乎不再乱走：带探索成功率 0.90~0.91、末段回报 −0.6；"
           "固定 ε=0.3 只有 0.75 / −6.1", font=font(12), fill=MUTED)
    return finish(img, os.path.join(FIG, "fig5_epsilon.png"))


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        p = f()
        print("saved", os.path.basename(p), os.path.getsize(p) // 1024, "KB")
