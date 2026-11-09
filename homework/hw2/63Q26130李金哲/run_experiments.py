"""run_experiments.py —— 跑完四组实验，输出 results/ 下的 json + npz。

用法：python run_experiments.py
"""
import json
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rl_core import (MazeEnv, train_q, train_mc, eps_fixed, eps_linear, eps_exp,
                     eps_adaptive, episodes_to_threshold, optimal_q,
                     collect_demos, demos_to_qinit, smooth)
from mazes import LAYOUTS, REWARD_MAP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)

SEEDS1 = 8
SEEDS4 = 10
EP1, EP2, EP3, EP4 = 800, 3000, 2000, 800
EVAL_EVERY = 10
_N_REWARD_MAP = MazeEnv(REWARD_MAP).n_states
npz = {}
summary = {}


def agg(curves):
    a = np.array(curves, dtype=float)
    return a.mean(axis=0), a.std(axis=0)


# ============================================================ 实验一：TD vs MC × 三种布局
def experiment1():
    t0 = time.time()
    data = {}
    for lname in ("simple", "multipit", "deadend"):
        for algo, fn in (("TD", train_q), ("MC", train_mc)):
            curves, steps_curves, conv = [], [], []
            finals, fsteps = [], []
            for seed in range(SEEDS1):
                env = MazeEnv(LAYOUTS[lname], max_steps=200, seed=seed)
                rec, Q = fn(env, EP1, seed=seed, alpha=0.1, gamma=0.95,
                            eps_fn=eps_fixed(0.1), eval_every=EVAL_EVERY,
                            random_start=True)
                curves.append(rec["eval_success"])
                steps_curves.append(rec["steps"])
                conv.append(episodes_to_threshold(rec["eval_success"], 0.9, 3))
                m = env.evaluate(Q, n=40)
                finals.append(float(np.mean(rec["eval_success"][-5:])))
                fsteps.append(m["steps"])
            m, s = agg(curves)
            key = f"{lname}_{algo}"
            npz[f"exp1_{key}_mean"] = m
            npz[f"exp1_{key}_std"] = s
            data[key] = dict(mean=m.tolist(), std=s.tolist(),
                             conv=float(np.nanmean(conv)) if not np.all(np.isnan(conv)) else None,
                             conv_list=[float(c) for c in conv],
                             final_success=float(np.mean(finals)),
                             final_std=float(np.mean(s[-5:])),
                             final_steps=float(np.mean(fsteps)))
            print(f"[exp1] {key:16s} 收敛回合={np.nanmean(conv):7.1f}  "
                  f"末段成功率={np.mean(finals):.2f}±{np.mean(s[-5:]):.2f}  步数={np.mean(fsteps):5.1f}")
    summary["exp1"] = data
    summary["exp1_eval_ep"] = list(range(EVAL_EVERY, EP1 + 1, EVAL_EVERY))
    summary["exp1_elapsed"] = round(time.time() - t0, 1)


# ============================================================ 实验二：奖励函数设计与奖励黑客
MODES = {
    "sparse": dict(),
    "proximity": dict(prox_bonus=3.0, prox_radius=3),
    "potential": dict(),
}


def experiment2():
    t0 = time.time()
    data = {}
    for mode, kw in MODES.items():
        curves, mode_ret = [], []
        task_succ, task_steps, true_ret = [], [], []
        visits = np.zeros(_N_REWARD_MAP)
        for seed in range(SEEDS1):
            env = MazeEnv(REWARD_MAP, max_steps=200, seed=seed, mode=mode, **kw)
            rec, Q = train_q(env, EP2, seed=seed, alpha=0.1, gamma=0.95,
                             eps_fn=eps_linear(0.3, 0.05, EP2 * 0.6),
                             eval_every=EVAL_EVERY, random_start=True)
            curves.append(rec["eval_success"])
            mode_ret.append(smooth(rec["ret"], 20))
            # 任务层面：在该奖励函数自己的环境里评估"是否真的到达终点"
            m = env.evaluate(Q, n=40)
            task_succ.append(m["success"])
            task_steps.append(m["steps"])
            # 统一口径：用任务本身的 sparse 奖励再算一次真实回报
            judge = MazeEnv(REWARD_MAP, max_steps=200, seed=999, mode="sparse")
            true_ret.append(judge.evaluate(Q, n=40)["ret"])
            if seed == 0:
                rng = np.random.default_rng(seed)
                for _ in range(30):
                    r = judge.rollout(Q, 0.0, rng=rng)
                    for st in r["path"]:
                        visits[int(st)] += 1
        m, s = agg(curves)
        mr, _ = agg(mode_ret)
        key = mode
        npz[f"exp2_{key}_mean"] = m
        npz[f"exp2_{key}_std"] = s
        conv = episodes_to_threshold(m, 0.9, 3)
        data[key] = dict(mean=m.tolist(), std=s.tolist(),
                         mode_ret=mr.tolist(),
                         task_success=float(np.mean(task_succ)),
                         task_steps=float(np.mean(task_steps)),
                         true_ret=float(np.mean(true_ret)),
                         conv=float(conv) if not np.isnan(conv) else None,
                         visits=visits.reshape(env.H, env.W).tolist())
        print(f"[exp2] {key:10s} 任务成功率={np.mean(task_succ):.2f}  "
              f"真实回报={np.mean(true_ret):7.2f}  步数={np.mean(task_steps):6.1f}  "
              f"收敛回合={conv}")
    summary["exp2"] = data
    summary["exp2_elapsed"] = round(time.time() - t0, 1)


# ============================================================ 实验三：示范质量 → 学习速度
def experiment3():
    t0 = time.time()
    env_teacher = MazeEnv(LAYOUTS["multipit"], max_steps=200, seed=0)
    Qstar = optimal_q(env_teacher)
    teacher_eval = env_teacher.evaluate(Qstar, n=40)
    print(f"[exp3] 老师(最优策略)自评成功率={teacher_eval['success']:.2f}")

    configs = [("none", None), ("expert", 0.05), ("good", 0.20),
               ("fair", 0.45), ("random", 1.00), ("reverse", None)]
    data = {}
    for name, eps in configs:
        curves, init_succ = [], []
        for seed in range(SEEDS1):
            env = MazeEnv(LAYOUTS["multipit"], max_steps=200, seed=seed)
            if name == "none":
                Q0 = np.zeros((env.n_states, 4))
                demos = []
            else:
                demos = collect_demos(env, Qstar, n=20, eps=(eps or 0.0),
                                      seed=seed, avoid_goal=(name == "reverse"))
                Q0 = demos_to_qinit(env, demos)
            m0 = env.evaluate(Q0, n=40)
            init_succ.append(m0["success"])
            rec, Q = train_q(env, EP3, seed=seed, alpha=0.1, gamma=0.95,
                             eps_fn=eps_fixed(0.1), Q0=Q0, eval_every=EVAL_EVERY,
                             random_start=True)
            curves.append(rec["eval_success"])
        m, s = agg(curves)
        npz[f"exp3_{name}_mean"] = m
        npz[f"exp3_{name}_std"] = s
        conv = episodes_to_threshold(m, 0.9, 3)
        data[name] = dict(mean=m.tolist(), std=s.tolist(),
                          init_success=float(np.mean(init_succ)),
                          conv=float(conv) if not np.isnan(conv) else None,
                          demo_len=float(np.mean([len(d) for d in demos])) if demos else 0.0)
        print(f"[exp3] {name:8s} 初始成功率={np.mean(init_succ):.2f}  "
              f"收敛回合={conv if not np.isnan(conv) else -1:6.1f}  "
              f"示范长度={data[name]['demo_len']:.1f}")
    summary["exp3"] = data
    summary["exp3_teacher_success"] = teacher_eval["success"]
    summary["exp3_elapsed"] = round(time.time() - t0, 1)


# ============================================================ 实验四：ε 衰减策略
def experiment4():
    t0 = time.time()
    strategies = {
        "固定 ε=0.10": eps_fixed(0.10),
        "固定 ε=0.30": eps_fixed(0.30),
        "线性衰减 1.0→0.05": eps_linear(1.0, 0.05, 300),
        "指数衰减 τ=120": eps_exp(0.05, 120.0),
        "自适应衰减": eps_adaptive(0.02, 0.40),
    }
    data = {}
    for name, fn in strategies.items():
        curves, rets, stds, train_succ, eps_traj = [], [], [], [], []
        for seed in range(SEEDS4):
            env = MazeEnv(LAYOUTS["multipit"], max_steps=200, seed=seed)
            rec, Q = train_q(env, EP4, seed=seed, alpha=0.1, gamma=0.95,
                             eps_fn=fn, eval_every=EVAL_EVERY, random_start=True)
            curves.append(rec["eval_success"])
            rets.append(float(np.mean(rec["ret"][-100:])))
            stds.append(float(np.std(rec["ret"][-100:])))
            train_succ.append(float(np.mean(rec["success"][-100:])))
            eps_traj.append(rec["eps"])
        m, s = agg(curves)
        npz[f"exp4_{name}_mean"] = m
        npz[f"exp4_{name}_std"] = s
        conv = episodes_to_threshold(m, 0.9, 3)
        ebar = np.array(eps_traj).mean(axis=0)
        ebar = ebar.reshape(len(ebar) // 50, 50).mean(axis=1)     # 每 50 回合取均值
        data[name] = dict(mean=m.tolist(), std=s.tolist(),
                          conv=float(conv) if not np.isnan(conv) else None,
                          final_success=float(m[-1]),
                          final_ret=float(np.mean(rets)),
                          ret_std=float(np.mean(stds)),
                          train_success=float(np.mean(train_succ)),
                          tail_std=float(np.mean(s[-4:])),
                          eps_traj=ebar.round(4).tolist())
        print(f"[exp4] {name:18s} 收敛回合={conv if not np.isnan(conv) else -1:6.1f}  "
              f"贪心成功率={m[-1]:.2f}  带探索成功率={np.mean(train_succ):.2f}  "
              f"末段回报={np.mean(rets):7.2f}±{np.mean(stds):5.2f}")
    summary["exp4"] = data
    summary["exp4_elapsed"] = round(time.time() - t0, 1)


if __name__ == "__main__":
    t0 = time.time()
    experiment1()
    experiment2()
    experiment3()
    experiment4()
    summary["total_elapsed"] = round(time.time() - t0, 1)
    np.savez(os.path.join(OUT, "curves.npz"), **npz)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    # 把最优 Q 表也存一份，供画策略图
    env = MazeEnv(LAYOUTS["multipit"], max_steps=200, seed=0)
    qstar = optimal_q(env)
    np.save(os.path.join(OUT, "qstar_multipit.npy"), qstar)
    print(f"\n全部完成，用时 {summary['total_elapsed']}s，结果写入 {OUT}")
