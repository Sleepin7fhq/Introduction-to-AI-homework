"""rl_core.py —— 网格迷宫环境 + TD(Q-learning) / MC(蒙特卡洛控制) 智能体。

整个实验只依赖 numpy，可以独立运行复现。
"""
import numpy as np

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))   # 上 下 左 右
UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3


class MazeEnv:
    """带随机滑移（slip）的网格迷宫。

    reward 模式：
      sparse     —— 每步 -1，陷阱 -10，终点 +10（默认）
      proximity  —— 在 sparse 基础上，只要站在终点「相邻格」每步额外 +2（易被钻空子）
      potential  —— sparse + 基于距离的势函数塑形 r += γ·Φ(s') - Φ(s)
      waypoint   —— 踩到钥匙 K 一次性 +3，用于教 Agent 学会「先绕去取钥匙再去终点」
    """

    def __init__(self, layout, slip=0.1, max_steps=150, mode="sparse",
                 step_cost=-1.0, goal_reward=10.0, pit_reward=-10.0,
                 prox_bonus=2.0, prox_radius=1, gamma=0.95, seed=0, start_p=0.0,
                 key_reward=3.0):
        self.rows = [list(r) for r in layout]
        self.H, self.W = len(self.rows), len(self.rows[0])
        self.n_states = self.H * self.W
        self.walls, self.pits = set(), set()
        self.start = self.goal = self.key = None
        for r in range(self.H):
            for c in range(self.W):
                ch = self.rows[r][c]
                i = r * self.W + c
                if ch == "#":
                    self.walls.add(i)
                elif ch == "P":
                    self.pits.add(i)
                elif ch == "S":
                    self.start = i
                elif ch == "G":
                    self.goal = i
                elif ch == "K":
                    self.key = i
        assert self.start is not None and self.goal is not None

        self.slip, self.max_steps, self.mode = slip, max_steps, mode
        self.step_cost, self.goal_reward, self.pit_reward = step_cost, goal_reward, pit_reward
        self.prox_bonus, self.prox_radius, self.gamma = prox_bonus, prox_radius, gamma
        self.key_reward = key_reward
        self.start_p = start_p
        self.rng = np.random.default_rng(seed)

        gr, gc = divmod(self.goal, self.W)
        self.manhattan = np.array([abs(i // self.W - gr) + abs(i % self.W - gc)
                                   for i in range(self.n_states)], dtype=np.float64)
        # 训练时可从中随机抽取初始位置的『普通格』
        self.free_cells = [i for i in range(self.n_states)
                           if i not in self.walls and i not in self.pits
                           and i != self.goal]
        self.reset()

    # ---------- 势函数 ----------
    def phi(self, s):
        if s == self.goal or s in self.pits:
            return 0.0
        return -0.5 * self.manhattan[s]

    def reset(self, random_start=False, rng=None):
        """random_start=True 时：以 start_p 的概率从固定起点 S 出发，
        否则从任意普通格出发——保证探索覆盖整个迷宫。"""
        if random_start and rng is not None and rng.random() >= self.start_p:
            self.s = int(self.free_cells[int(rng.integers(len(self.free_cells)))])
        else:
            self.s = self.start
        self.has_key = False
        self.t = 0
        self.trajectory = [self.s]
        return self.s

    def step(self, a):
        if self.rng.random() < self.slip:            # 滑移：执行随机动作
            a = int(self.rng.integers(4))
        r, c = divmod(self.s, self.W)
        dr, dc = DIRS[a]
        nr, nc = r + dr, c + dc
        bumped = not (0 <= nr < self.H and 0 <= nc < self.W) or \
            (nr * self.W + nc) in self.walls
        ns = self.s if bumped else nr * self.W + nc

        ret = self.step_cost
        done, event = False, "move"

        if ns in self.pits:
            ret += self.pit_reward
            done, event = True, "pit"
        elif ns == self.goal:
            ret += self.goal_reward
            done, event = True, "goal"
        elif self.mode == "waypoint" and self.key is not None and ns == self.key and not self.has_key:
            self.has_key = True
            ret += self.key_reward                  # 一次性「取钥匙」奖励
            event = "key"

        if not done and self.mode == "proximity" and self.manhattan[ns] <= self.prox_radius:
            ret += self.prox_bonus                 # 「站在终点旁边」就一直有奖励
        if self.mode == "potential":
            ret += self.gamma * self.phi(ns) - self.phi(self.s)

        self.s = ns
        self.t += 1
        truncated = self.t >= self.max_steps
        self.trajectory.append(ns)
        return ns, ret, done, {"event": event, "truncated": truncated}

    # ---------- 可视化辅助 ----------
    def greedy_policy(self, Q):
        return Q.argmax(axis=1)

    def rollout(self, Q, eps=0.0, max_steps=None, rng=None):
        rng = rng or np.random.default_rng(0)
        self.reset()
        total, steps = 0.0, 0
        limit = max_steps or self.max_steps
        while steps < limit:
            a = int(Q[self.s].argmax())
            if eps > 0 and rng.random() < eps:
                a = int(rng.integers(4))
            _, r, done, _ = self.step(a)
            total += r
            steps += 1
            if done:
                break
        return dict(return_=total, steps=steps, success=self.s == self.goal,
                    path=list(self.trajectory))

    def evaluate(self, Q, n=30, seed=12345):
        rng = np.random.default_rng(seed)
        res = [self.rollout(Q, 0.0, rng=rng) for _ in range(n)]
        return dict(success=float(np.mean([r["success"] for r in res])),
                    ret=float(np.mean([r["return_"] for r in res])),
                    steps=float(np.mean([r["steps"] for r in res])))


# ---------------------------------------------------------------- ε 策略
def eps_fixed(v):
    return lambda ep, sr: v


def eps_linear(start, end, T):
    return lambda ep, sr: max(end, start - (start - end) * ep / T)


def eps_exp(final, tau):
    return lambda ep, sr: final + (1.0 - final) * float(np.exp(-ep / tau))


def eps_adaptive(lo=0.02, hi=0.40):
    """自适应：最近的成功率越高，ε 越小；连续失败则放大探索。"""
    return lambda ep, sr: float(np.clip(1.0 - 1.05 * sr, lo, hi))


# ---------------------------------------------------------------- 训练器
def _select(Q, s, eps, rng):
    if rng.random() < eps:
        return int(rng.integers(Q.shape[1]))
    row = Q[s]
    best = row.max()
    cand = np.flatnonzero(row >= best - 1e-12)
    return int(cand[rng.integers(len(cand))])


def train_q(env, episodes, seed=0, alpha=0.1, gamma=0.95, eps_fn=None, Q0=None,
            eval_every=0, history_window=20, random_start=False):
    """表格型 Q-learning（TD，单步自举，off-policy）。"""
    rng = np.random.default_rng(seed)
    Q = np.zeros((env.n_states, 4)) if Q0 is None else Q0.copy()
    eps_fn = eps_fn or eps_fixed(0.1)
    rec = dict(success=[], steps=[], ret=[], eps=[], eval_ep=[], eval_success=[], eval_ret=[])
    recent = []
    for ep in range(episodes):
        sr = float(np.mean(recent)) if recent else 0.0
        eps = eps_fn(ep, sr)
        s = env.reset(random_start=random_start, rng=rng)
        total, steps, done = 0.0, 0, False
        while steps < env.max_steps:
            a = _select(Q, s, eps, rng)
            ns, r, done, info = env.step(a)
            target = r if done else r + gamma * Q[ns].max()
            Q[s, a] += alpha * (target - Q[s, a])
            s = ns
            total += r
            steps += 1
            if done:
                break
        succ = (env.s == env.goal)
        rec["success"].append(float(succ))
        rec["steps"].append(steps)
        rec["ret"].append(total)
        rec["eps"].append(eps)
        recent.append(succ)
        if len(recent) > history_window:
            recent.pop(0)
        if eval_every and (ep + 1) % eval_every == 0:
            m = env.evaluate(Q, n=20, seed=1000 + ep)
            rec["eval_ep"].append(ep + 1)
            rec["eval_success"].append(m["success"])
            rec["eval_ret"].append(m["ret"])
    return {k: np.array(v, dtype=float) for k, v in rec.items()}, Q


def train_mc(env, episodes, seed=0, alpha=0.1, gamma=0.95, eps_fn=None, Q0=None,
             eval_every=0, history_window=20, random_start=False):
    """首次访问蒙特卡洛控制（必须跑完整个回合才能更新）。"""
    rng = np.random.default_rng(seed)
    Q = np.zeros((env.n_states, 4)) if Q0 is None else Q0.copy()
    eps_fn = eps_fn or eps_fixed(0.1)
    rec = dict(success=[], steps=[], ret=[], eps=[], eval_ep=[], eval_success=[], eval_ret=[])
    recent = []
    for ep in range(episodes):
        sr = float(np.mean(recent)) if recent else 0.0
        eps = eps_fn(ep, sr)
        s = env.reset(random_start=random_start, rng=rng)
        states, actions, rewards = [], [], []
        steps, done = 0, False
        while steps < env.max_steps:
            a = _select(Q, s, eps, rng)
            ns, r, done, info = env.step(a)
            states.append(s)
            actions.append(a)
            rewards.append(r)
            s = ns
            steps += 1
            if done:
                break
        G = 0.0
        seen = set()
        for t in range(len(rewards) - 1, -1, -1):
            G = rewards[t] + gamma * G
            key = (states[t], actions[t])
            if key in seen:                      # 首次访问
                continue
            seen.add(key)
            Q[key] += alpha * (G - Q[key])
        succ = (env.s == env.goal)
        rec["success"].append(float(succ))
        rec["steps"].append(steps)
        rec["ret"].append(sum(rewards))
        rec["eps"].append(eps)
        recent.append(succ)
        if len(recent) > history_window:
            recent.pop(0)
        if eval_every and (ep + 1) % eval_every == 0:
            m = env.evaluate(Q, n=20, seed=1000 + ep)
            rec["eval_ep"].append(ep + 1)
            rec["eval_success"].append(m["success"])
            rec["eval_ret"].append(m["ret"])
    return {k: np.array(v, dtype=float) for k, v in rec.items()}, Q


# ---------------------------------------------------------------- 工具
def smooth(x, w=20):
    x = np.asarray(x, dtype=float)
    if len(x) < w:
        return x
    kern = np.ones(w) / w
    return np.convolve(x, kern, mode="valid")


def episodes_to_threshold(succ, thresh=0.9, window=30):
    s = smooth(succ, window)
    idx = np.flatnonzero(s >= thresh)
    if len(idx) == 0:
        return np.nan
    # 要求此后（近似）持续达标：首次达到并保持的回合
    for i in idx:
        if np.all(s[i:] >= thresh * 0.9):
            return i + window
    return float(idx[0] + window)


# ---------------------------------------------------------------- 模仿学习
def optimal_q(env, gamma=0.95, iters=300):
    """用值迭代求出该迷宫的最优 Q*（用于生成"示范"和计算最优策略）。"""
    V = np.zeros(env.n_states)
    terminal = set(env.pits) | {env.goal}
    for _ in range(iters):
        Q, _ = _backup(env, V, gamma, terminal)
        V2 = Q.max(axis=1)
        for t in terminal:
            V2[t] = 0.0
        if np.max(np.abs(V2 - V)) < 1e-10:
            V = V2
            break
        V = V2
    Q, _ = _backup(env, V, gamma, terminal)
    return Q


def _backup(env, V, gamma, terminal):
    """给定 V，计算 Q(s,a)=E[r+γV(s')]，动作按 1-slip / slip 均匀分布。"""
    Q = np.full((env.n_states, 4), -np.inf)
    for s in range(env.n_states):
        if s in env.walls or s in terminal:
            continue
        r, c = divmod(s, env.W)
        for a in range(4):
            val = 0.0
            for a2 in range(4):
                p = (1 - env.slip) if a2 == a else env.slip / 3.0
                if p == 0:
                    continue
                dr, dc = DIRS[a2]
                nr, nc = r + dr, c + dc
                if not (0 <= nr < env.H and 0 <= nc < env.W) or (nr * env.W + nc) in env.walls:
                    ns = s
                else:
                    ns = nr * env.W + nc
                ret = env.step_cost
                if ns in env.pits:
                    val += p * (ret + env.pit_reward)
                elif ns == env.goal:
                    val += p * (ret + env.goal_reward)
                else:
                    val += p * (ret + gamma * V[ns])
            Q[s, a] = val
    Q[np.isinf(Q)] = 0.0
    return Q, V


def demos_to_policy(env, demos):
    """从示范轨迹统计出「示范策略」π_demo(a|s)（没被覆盖的状态取均匀分布）。"""
    cnt = np.zeros((env.n_states, 4))
    for traj in demos:
        for s, a, _ in traj:
            cnt[s, a] += 1
    tot = cnt.sum(axis=1, keepdims=True)
    pi = np.full((env.n_states, 4), 0.25)
    m = tot[:, 0] > 0
    pi[m] = cnt[m] / tot[m]
    return pi


def policy_value(env, pi, gamma=0.95, iters=400):
    """策略评估：算出示范策略的状态价值 V^π 与 Q^π。"""
    V = np.zeros(env.n_states)
    terminal = set(env.pits) | {env.goal}
    for _ in range(iters):
        Q, _ = _backup(env, V, gamma, terminal)
        V2 = (Q * pi).sum(axis=1)
        for t in terminal:
            V2[t] = 0.0
        if np.max(np.abs(V2 - V)) < 1e-10:
            V = V2
            break
        V = V2
    Q, _ = _backup(env, V, gamma, terminal)
    return Q, V


def demos_to_qinit(env, demos, gamma=0.95):
    """模仿学习初始化：先统计示范策略 π_demo，再对它做策略评估，Q_init = Q^π_demo。"""
    pi = demos_to_policy(env, demos)
    Q, _ = policy_value(env, pi, gamma)
    return Q


def collect_demos(env, Q_teacher, n=20, eps=0.05, seed=0, avoid_goal=False):
    """按 ε-贪心的"老师策略"采集 n 条示范轨迹。"""
    rng = np.random.default_rng(seed)
    demos = []
    for _ in range(n):
        env.reset()
        traj, steps, done = [], 0, False
        while steps < env.max_steps:
            if avoid_goal:      # 故意走反方向的"错误示范"
                r, c = divmod(env.s, env.W)
                gr, gc = divmod(env.goal, env.W)
                cand = []
                for a, (dr, dc) in enumerate(DIRS):
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < env.H and 0 <= nc < env.W):
                        continue
                    if (nr * env.W + nc) in env.walls or (nr * env.W + nc) in env.pits:
                        continue
                    cand.append((abs(nr - gr) + abs(nc - gc), a))
                a = max(cand)[1] if cand else int(rng.integers(4))
            elif rng.random() < eps:
                a = int(rng.integers(4))
            else:
                a = int(Q_teacher[env.s].argmax())
            s0 = env.s
            _, rew, done, _ = env.step(a)
            traj.append((s0, a, rew))
            steps += 1
            if done:
                break
        demos.append(traj)
    return demos
