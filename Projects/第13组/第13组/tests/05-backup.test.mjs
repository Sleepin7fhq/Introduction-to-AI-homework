import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  newWorkout,
  newEntry,
  builtins,
  makeBackup,
  parseBackup,
  clone,
} from "../public/model.js";
export function fixture() {
  const s = initialState();
  s.goals = { weekly: 3, targetWeight: 65 };
  s.plan[0] = { mode: "train", parts: ["胸"], exerciseIds: ["bench"] };
  s.customExercises = [
    { id: "custom", name: "自定义动作", part: "核心", loaded: false },
  ];
  const w = newWorkout("2026-01-01");
  w.status = "complete";
  w.phase = "active";
  w.exercises = [newEntry(builtins[0])];
  w.exercises[0].sets[0].weight = 25;
  w.exercises[0].sets[0].reps = 10;
  w.exercises[0].sets[0].done = true;
  s.workouts = [w, newWorkout("2026-01-02")];
  const now = new Date().toISOString();
  s.weights = [
    {
      id: "weight",
      date: "2026-01-01",
      value: 70,
      bodyFat: 20,
      waist: 80,
      createdAt: now,
      updatedAt: now,
    },
  ];
  return s;
}
test("阶段5：空备份与完整备份往返", () => {
  for (const s of [initialState(), fixture()])
    assert.deepEqual(parseBackup(JSON.stringify(makeBackup(s))).data, s);
});
test("阶段5：损坏、版本、标识、引用、草稿、日期和数值校验", () => {
  assert.throws(() => parseBackup("{"));
  const base = makeBackup(fixture());
  const mutations = [
    (b) => (b.backupVersion = 99),
    (b) => (b.app = "other"),
    (b) => delete b.data.goals,
    (b) => b.data.workouts.push(clone(b.data.workouts[1])),
    (b) => (b.data.workouts[0].exercises[0].sets[0].weight = -1),
    (b) => (b.data.workouts[0].date = "2026-02-30"),
    (b) => (b.data.workouts[0].exercises[0].exerciseId = "missing"),
    (b) => b.data.weights.push({ ...b.data.weights[0], id: "other" }),
    (b) => (b.data.workouts[0].id = '"><script>'),
    (b) => (b.data.workouts[0].exercises[0].sets[0].reps = 1.5),
    (b) => (b.data.workouts[0].status = "draft"),
  ];
  for (const mutate of mutations) {
    const b = clone(base);
    mutate(b);
    assert.throws(() => parseBackup(JSON.stringify(b)));
  }
});
