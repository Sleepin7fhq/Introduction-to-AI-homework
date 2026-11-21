export const parts = ["胸", "背", "腿", "肩", "手臂", "核心", "有氧"];
export const days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
export const builtins = [
  ["bench", "杠铃卧推", "胸", true],
  ["pushup", "俯卧撑", "胸", false],
  ["fly", "哑铃飞鸟", "胸", true],
  ["row", "坐姿划船", "背", true],
  ["pullup", "引体向上", "背", false],
  ["pulldown", "高位下拉", "背", true],
  ["squat", "杠铃深蹲", "腿", true],
  ["deadlift", "硬拉", "腿", true],
  ["lunge", "徒手弓步蹲", "腿", false],
  ["press", "哑铃肩推", "肩", true],
  ["raise", "侧平举", "肩", true],
  ["curl", "哑铃弯举", "手臂", true],
  ["pushdown", "绳索下压", "手臂", true],
  ["crunch", "卷腹", "核心", false],
  ["legraise", "仰卧举腿", "核心", false],
  ["jump", "开合跳", "有氧", false],
].map(([id, name, part, loaded]) => ({ id, name, part, loaded }));
export const uid = () => crypto.randomUUID();
export const clone = (v) => structuredClone(v);
export function today(d = new Date()) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
export function validDate(s) {
  if (typeof s !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(s + "T12:00:00");
  return !isNaN(d) && today(d) === s;
}
export function addDays(s, n) {
  const d = new Date(s + "T12:00:00");
  d.setDate(d.getDate() + n);
  return today(d);
}
export function monday(s = today()) {
  return addDays(s, -((new Date(s + "T12:00:00").getDay() + 6) % 7));
}
export function upcomingPlanDays(start = today()) {
  return days.map((_, offset) => {
    const date = addDays(start, offset);
    const index = (new Date(date + "T12:00:00").getDay() + 6) % 7;
    return { date, index, label: days[index] };
  });
}
export const positive = (v) =>
  typeof v === "number" && Number.isFinite(v) && v > 0;
export const repsValid = (v) => positive(v) && Number.isSafeInteger(v);
export const loadValid = (v) =>
  typeof v === "number" && Number.isFinite(v) && v >= 0;
export function initialState() {
  return {
    version: 2,
    revision: 0,
    plan: days.map(() => ({ mode: "unset", parts: [], exerciseIds: [] })),
    goals: { weekly: null, targetWeight: null },
    customExercises: [],
    workouts: [],
    weights: [],
  };
}
export function workoutError(w) {
  if (!validDate(w.date) || w.date > today()) return "请选择今天或过去的日期";
  if (!w.exercises.length) return "请先添加一个动作";
  for (const e of w.exercises) {
    if (!e.sets.length) return `${e.name}：请添加一组`;
    for (const [j, s] of e.sets.entries()) {
      if (!repsValid(s.reps)) return `${e.name} 第 ${j + 1} 组：次数须为正整数`;
      if (
        (s.weight !== null && !loadValid(s.weight)) ||
        (e.loaded && s.weight === null)
      )
        return `${e.name} 第 ${j + 1} 组：请填写有效重量`;
    }
  }
  return "";
}
export function deletePlan(state, index) {
  if (!Number.isInteger(index) || index < 0 || index > 6)
    throw Error("请选择有效的星期");
  const plan = clone(state.plan);
  plan[index] = { mode: "unset", parts: [], exerciseIds: [] };
  return plan;
}
export function movePlan(state, from, to) {
  if (![from, to].every((i) => Number.isInteger(i) && i >= 0 && i < 7))
    throw Error("请选择有效的星期");
  const plan = clone(state.plan);
  if (from === to || plan[from].mode === "unset") return plan;
  [plan[from], plan[to]] = [plan[to], plan[from]];
  return plan;
}
export function newWorkout(
  date = today(),
  plan = null,
  catalog = builtins,
  mode = "live",
) {
  return {
    id: uid(),
    date,
    status: "draft",
    phase: mode === "backfill" ? "active" : "prepare",
    mode,
    startedAt: null,
    planParts: [...(plan?.parts || [])],
    planCleared: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    exercises: (plan?.exerciseIds || []).map((id) => {
      const exercise = catalog.find((e) => e.id === id);
      if (!exercise) throw Error("计划中的动作不存在，请先修改计划");
      return newEntry(exercise);
    }),
  };
}
export function newEntry(e) {
  return {
    id: uid(),
    exerciseId: e.id,
    name: e.name,
    part: e.part,
    loaded: e.loaded,
    sets: [{ id: uid(), weight: null, reps: null, done: false }],
  };
}
// Add missing planned actions without replacing any entered sets or progress.
export function addPlannedExercises(state, w) {
  if (!w || w.status !== "draft" || w.mode !== "live") return 0;
  const plan = state.plan[(new Date(w.date + "T12:00:00").getDay() + 6) % 7];
  const catalog = [...builtins, ...state.customExercises];
  const missing = plan.exerciseIds.filter(
    (id) => !w.exercises.some((e) => e.exerciseId === id),
  );
  if (!missing.length) return 0;
  const entries = missing.map((id) => {
    const e = catalog.find((e) => e.id === id);
    if (!e) throw Error("计划中的动作不存在，请先修改计划");
    return newEntry(e);
  });
  w.exercises.push(...entries);
  w.planParts = [...plan.parts];
  w.planCleared = false;
  w.updatedAt = new Date().toISOString();
  return entries.length;
}
export function syncEmptyDraft(state) {
  const w = state.workouts.find((w) => w.status === "draft");
  // Never repopulate a deliberate clear, a previous day's draft or an active workout.
  if (
    !w ||
    w.date !== today() ||
    w.phase !== "prepare" ||
    w.startedAt !== null ||
    w.exercises.length ||
    w.planCleared
  )
    return 0;
  return addPlannedExercises(state, w);
}
export function beginWorkout(state, id) {
  const next = clone(state);
  const w = next.workouts.find((w) => w.id === id);
  if (!w || w.status !== "draft") throw Error("没有可开始的训练");
  if (!w.exercises.length) throw Error("先添加今天要练的动作，再开始训练");
  if (w.phase === "active") return next;
  w.phase = "active";
  w.startedAt = new Date().toISOString();
  w.updatedAt = w.startedAt;
  return next;
}
export function completeWorkout(state, id) {
  const s = clone(state);
  const w = s.workouts.find((w) => w.id === id);
  if (!w) throw Error("训练不存在");
  if (w.status === "complete") return s;
  if (w.phase !== "active") throw Error("请先确认动作并开始训练");
  const err = workoutError(w);
  if (err) throw Error(err);
  w.status = "complete";
  w.exercises.forEach((e) => e.sets.forEach((set) => (set.done = true)));
  w.updatedAt = new Date().toISOString();
  return s;
}
export function weeklyCount(state, date = today()) {
  const start = monday(date),
    end = addDays(start, 6);
  return state.workouts.filter(
    (w) => w.status === "complete" && w.date >= start && w.date <= end,
  ).length;
}
export function rangeStart(state, weeks = 4, end = today()) {
  if (weeks !== "all") return addDays(monday(end), -(Number(weeks) - 1) * 7);
  const dates = [
    ...state.workouts.filter((w) => w.status === "complete").map((w) => w.date),
    ...state.weights.map((w) => w.date),
  ].sort();
  return monday(dates[0] || end);
}
export function frequency(state, weeks = 4, end = today()) {
  const start = rangeStart(state, weeks, end),
    out = [];
  for (let date = monday(start); date <= end; date = addDays(date, 7)) {
    out.push({
      date,
      value: state.workouts.filter(
        (w) =>
          w.status === "complete" &&
          w.date >= date &&
          w.date <= addDays(date, 6) &&
          w.date <= end,
      ).length,
    });
  }
  return out;
}
export function exerciseTrend(state, exerciseId, weeks = 4, end = today()) {
  const start = rangeStart(state, weeks, end);
  return state.workouts
    .filter((w) => w.status === "complete" && w.date >= start && w.date <= end)
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt),
    )
    .flatMap((w) => {
      const entries = w.exercises.filter((e) => e.exerciseId === exerciseId);
      if (!entries.length) return [];
      const loaded = entries[0].loaded,
        sets = entries.flatMap((e) => e.sets),
        value = Math.max(...sets.map((s) => (loaded ? s.weight : s.reps)));
      return [
        {
          date: w.date,
          value,
          id: w.id,
          loaded,
          reps: sets
            .filter((s) => (loaded ? s.weight : s.reps) === value)
            .map((s) => s.reps),
        },
      ];
    });
}
export function weightTrend(state, weeks = 4, end = today()) {
  const start = rangeStart(state, weeks, end);
  return state.weights
    .filter((w) => w.date >= start && w.date <= end && positive(w.value))
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((w) => ({ date: w.date, value: w.value, id: w.id }));
}
// Achievements are derived from records, so edits, deletions and restores stay consistent.
export function achievements(state) {
  const completed = state.workouts
    .filter((w) => w.status === "complete")
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) ||
        a.createdAt.localeCompare(b.createdAt) ||
        a.id.localeCompare(b.id),
    );
  const milestones = [10, 30].map((target) => ({
    id: `workouts-${target}`,
    kind: "count",
    title: target === 10 ? "十次，起步成章" : "三十次，坚持有形",
    description: `累计完成 ${target} 次训练`,
    target,
    progress: Math.min(completed.length, target),
    unlocked: completed.length >= target,
    unlockedAt: completed[target - 1]?.date || null,
  }));
  const records = new Map();
  for (const w of completed) {
    const session = new Map();
    for (const e of w.exercises) {
      if (!e.loaded) continue;
      for (const s of e.sets) {
        if (loadValid(s.weight) && repsValid(s.reps))
          session.set(
            e.exerciseId,
            Math.max(session.get(e.exerciseId) ?? 0, s.weight),
          );
      }
    }
    for (const [id, weight] of session) {
      const previous = records.get(id);
      records.set(id, {
        bestWeight: Math.max(previous?.bestWeight ?? 0, weight),
        unlockedAt:
          previous?.unlockedAt ||
          (previous && weight > previous.bestWeight ? w.date : null),
      });
    }
  }
  const personalBests = [...builtins, ...state.customExercises]
    .filter((e) => e.loaded)
    .map((e) => {
      const record = records.get(e.id);
      return {
        id: `record-${e.id}`,
        kind: "record",
        exerciseId: e.id,
        title: `${e.name} · 突破自己`,
        description: "在后续训练中，超过此前的最高重量",
        bestWeight: record?.bestWeight ?? null,
        unlocked: Boolean(record?.unlockedAt),
        unlockedAt: record?.unlockedAt || null,
      };
    });
  return [...milestones, ...personalBests];
}
export function validateState(s, legacy = false) {
  const check = (yes, msg) => {
    if (!yes) throw Error("数据校验失败：" + msg);
  };
  const text = (v) =>
    typeof v === "string" && v.trim().length > 0 && v.length <= 120;
  const array = (v, msg) => {
    check(Array.isArray(v), msg);
    return v;
  };
  const ids = new Set();
  const id = (v) => {
    check(
      typeof v === "string" && /^[a-zA-Z0-9_-]{1,80}$/.test(v),
      "标识格式不正确",
    );
    check(!ids.has(v), "存在重复标识");
    ids.add(v);
  };
  const stamp = (v) =>
    typeof v === "string" &&
    /^\d{4}-\d\d-\d\dT/.test(v) &&
    Number.isFinite(Date.parse(v));
  check(
    s && typeof s === "object" && s.version === (legacy ? 1 : 2),
    "不支持的数据版本",
  );
  check(Number.isSafeInteger(s.revision) && s.revision >= 0, "数据修订号无效");
  check(array(s.plan, "周计划缺失").length === 7, "周计划必须包含七天");
  for (const p of s.plan) {
    check(p && ["unset", "rest", "train"].includes(p.mode), "计划状态无效");
    const ps = array(p.parts, "训练部位缺失");
    check(
      ps.every(text) && new Set(ps).size === ps.length,
      "训练部位无效或重复",
    );
    check(
      p.mode === "train" ? ps.length > 0 : ps.length === 0,
      "休息和未安排不能包含训练部位",
    );
  }
  check(s.goals && typeof s.goals === "object", "目标缺失");
  check(s.goals.weekly === null || repsValid(s.goals.weekly), "每周次数无效");
  check(
    s.goals.targetWeight === null || positive(s.goals.targetWeight),
    "目标体重无效",
  );
  const catalog = new Map(builtins.map((e) => [e.id, e])),
    names = new Set(builtins.map((e) => e.name.toLowerCase()));
  for (const e of array(s.customExercises, "自定义动作缺失")) {
    check(e && typeof e === "object", "自定义动作无效");
    id(e.id);
    check(!catalog.has(e.id), "自定义动作标识与内置动作重复");
    check(
      text(e.name) && text(e.part) && typeof e.loaded === "boolean",
      "自定义动作字段无效",
    );
    check(!names.has(e.name.trim().toLowerCase()), "动作名称重复");
    names.add(e.name.trim().toLowerCase());
    catalog.set(e.id, e);
  }
  if (!legacy)
    for (const p of s.plan) {
      const exercises = array(p.exerciseIds, "计划动作清单缺失");
      check(
        exercises.every((id) => catalog.has(id)) &&
          new Set(exercises).size === exercises.length,
        "计划动作引用无效或重复",
      );
      check(
        p.mode === "train" || exercises.length === 0,
        "休息或未安排不能包含动作",
      );
    }
  let drafts = 0;
  for (const w of array(s.workouts, "训练记录缺失")) {
    check(w && typeof w === "object", "训练无效");
    id(w.id);
    check(validDate(w.date) && w.date <= today(), "训练日期无效");
    check(["draft", "complete"].includes(w.status), "训练状态无效");
    check(stamp(w.createdAt) && stamp(w.updatedAt), "训练时间无效");
    if (!legacy) {
      check(
        w.planCleared === undefined || typeof w.planCleared === "boolean",
        "计划清空标记无效",
      );
      check(
        ["prepare", "active"].includes(w.phase) &&
          ["live", "backfill"].includes(w.mode),
        "训练阶段无效",
      );
      check(w.startedAt === null || stamp(w.startedAt), "开始时间无效");
      check(
        array(w.planParts, "训练计划快照缺失").every(text),
        "训练计划快照无效",
      );
      check(w.status !== "complete" || w.phase === "active", "训练尚未开始");
      check(
        w.phase !== "prepare" || w.startedAt === null,
        "待确认训练不能有开始时间",
      );
    }
    if (w.status === "draft") drafts++;
    for (const e of array(w.exercises, "训练动作缺失")) {
      check(e && typeof e === "object", "动作无效");
      id(e.id);
      check(catalog.has(e.exerciseId), "动作引用不存在");
      check(
        text(e.name) &&
          text(e.part) &&
          typeof e.loaded === "boolean" &&
          e.loaded === catalog.get(e.exerciseId).loaded,
        "动作快照无效",
      );
      for (const set of array(e.sets, "组数据缺失")) {
        check(set && typeof set === "object", "组无效");
        id(set.id);
        check(set.weight === null || loadValid(set.weight), "重量无效");
        check(set.reps === null || repsValid(set.reps), "次数无效");
        if (!legacy) {
          check(typeof set.done === "boolean", "组完成状态无效");
          check(
            !set.done ||
              (w.phase === "active" &&
                repsValid(set.reps) &&
                (!e.loaded || loadValid(set.weight))),
            "已完成组的数据不完整",
          );
          check(w.status !== "complete" || set.done, "已完成训练仍有未完成组");
        }
      }
    }
    if (w.status === "complete")
      check(!workoutError(w), "已完成训练包含不完整数据");
  }
  check(drafts <= 1, "最多允许一份草稿");
  const dates = new Set();
  for (const w of array(s.weights, "体重数据缺失")) {
    check(w && typeof w === "object", "体重记录无效");
    id(w.id);
    check(
      validDate(w.date) && w.date <= today() && !dates.has(w.date),
      "体重日期无效或重复",
    );
    dates.add(w.date);
    check(
      (legacy ? positive(w.value) : measurementValid(w)) &&
        stamp(w.createdAt) &&
        stamp(w.updatedAt),
      "体重数值或时间无效",
    );
  }
  return s;
}
export function measurementValid(w) {
  return (
    (w.value === null || positive(w.value)) &&
    (w.bodyFat === null || (positive(w.bodyFat) && w.bodyFat < 100)) &&
    (w.waist === null || positive(w.waist)) &&
    [w.value, w.bodyFat, w.waist].some(positive)
  );
}
export function latestMetric(state, key) {
  return (
    state.weights
      .filter((w) => positive(w[key]))
      .sort((a, b) => b.date.localeCompare(a.date))[0] || null
  );
}
// Validate old data before upgrading; only the caller's successful transaction replaces it.
export function upgradeState(raw) {
  if (raw?.version !== 1) {
    validateState(raw);
    return clone(raw);
  }
  validateState(raw, true);
  const next = clone(raw);
  next.version = 2;
  next.plan.forEach((p) => (p.exerciseIds = []));
  next.workouts.forEach((w) => {
    w.phase = "active";
    w.mode = "live";
    w.startedAt = null;
    w.planParts = [];
    w.exercises.forEach((e) =>
      e.sets.forEach((s) => (s.done = w.status === "complete")),
    );
  });
  next.weights.forEach((w) => {
    w.bodyFat = null;
    w.waist = null;
  });
  validateState(next);
  return next;
}
export function makeBackup(state) {
  validateState(state);
  return {
    app: "today-fit",
    backupVersion: 2,
    exportedAt: new Date().toISOString(),
    data: clone(state),
  };
}
export function parseBackup(text) {
  let b;
  try {
    b = JSON.parse(text);
  } catch {
    throw Error("备份不是有效的 JSON 文件");
  }
  if (
    !b ||
    b.app !== "today-fit" ||
    ![1, 2].includes(b.backupVersion) ||
    b.data?.version !== b.backupVersion
  )
    throw Error("不是「今天练了吗」的兼容备份（支持版本 1、2）");
  if (
    typeof b.exportedAt !== "string" ||
    !Number.isFinite(Date.parse(b.exportedAt))
  )
    throw Error("备份时间无效");
  b.data = upgradeState(b.data);
  return b;
}
