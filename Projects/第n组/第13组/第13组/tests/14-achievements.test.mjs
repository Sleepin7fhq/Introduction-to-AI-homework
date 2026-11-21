import { test } from "node:test";
import assert from "node:assert/strict";
import {
  achievements,
  initialState,
  newWorkout,
  newEntry,
  builtins,
  addDays,
  makeBackup,
  parseBackup,
} from "../public/model.js";

function workout(date, weight = 20, exercise = builtins[0]) {
  const w = newWorkout(date);
  Object.assign(w, {
    status: "complete",
    phase: "active",
    createdAt: date + "T12:00:00.000Z",
  });
  w.exercises = [newEntry(exercise)];
  Object.assign(w.exercises[0].sets[0], { weight, reps: 10, done: true });
  return w;
}
const badge = (s, id) => achievements(s).find((a) => a.id === id);

test("成就：累计门槛 9/10/29/30，仅完成训练计数且日期真实", () => {
  const s = initialState();
  for (let i = 0; i < 30; i++) {
    s.workouts.push(workout(addDays("2026-09-01", i)));
    if ([9, 10, 29, 30].includes(i + 1)) {
      assert.equal(badge(s, "workouts-10").unlocked, i + 1 >= 10);
      assert.equal(badge(s, "workouts-30").unlocked, i + 1 >= 30);
      assert.equal(badge(s, "workouts-30").progress, i + 1);
    }
  }
  assert.equal(badge(s, "workouts-10").unlockedAt, "2026-09-10");
  assert.equal(badge(s, "workouts-30").unlockedAt, "2026-09-30");
  s.workouts.pop();
  s.workouts.push(newWorkout());
  assert.equal(badge(s, "workouts-30").unlocked, false);
  assert.equal(badge(s, "workouts-30").progress, 29);
});

test("成就：首次与同次加重不解锁、追平不解锁、跨次严格突破才解锁", () => {
  const s = initialState();
  assert.equal(badge(s, "record-bench").bestWeight, null);
  const first = workout("2026-09-01");
  const repeat = newEntry(builtins[0]);
  Object.assign(repeat.sets[0], { weight: 25, reps: 8, done: true });
  first.exercises.push(repeat);
  s.workouts.push(first);
  assert.equal(badge(s, "record-bench").unlocked, false);
  assert.equal(badge(s, "record-bench").bestWeight, 25);
  s.workouts.push(workout("2026-09-02", 25));
  assert.equal(badge(s, "record-bench").unlocked, false);
  const draft = workout("2026-09-03", 999);
  draft.status = "draft";
  s.workouts.push(draft);
  assert.equal(badge(s, "record-bench").unlocked, false);
  s.workouts.push(workout("2026-09-04", 25.5));
  assert.equal(badge(s, "record-bench").unlocked, true);
  assert.equal(badge(s, "record-bench").unlockedAt, "2026-09-04");
  s.workouts.push(workout("2026-09-05", 30));
  assert.equal(badge(s, "record-bench").bestWeight, 30);
  assert.equal(badge(s, "record-bench").unlockedAt, "2026-09-04");
});

test("成就：按日期与同日创建时间排序，修改删除后撤销，备份往返不改原数据", () => {
  const s = initialState();
  const early = workout("2026-09-01", 20),
    later = workout("2026-09-01", 25);
  later.createdAt = "2026-09-01T13:00:00.000Z";
  s.workouts = [later, early];
  const before = structuredClone(s);
  assert.equal(badge(s, "record-bench").unlocked, true);
  assert.deepEqual(s, before);
  assert.deepEqual(
    achievements(parseBackup(JSON.stringify(makeBackup(s))).data),
    achievements(s),
  );
  early.exercises[0].sets[0].weight = 30;
  assert.equal(badge(s, "record-bench").unlocked, false);
  s.workouts = [later];
  assert.equal(badge(s, "record-bench").unlocked, false);
  s.workouts.push(workout("2026-08-31", 10));
  assert.equal(
    badge(s, "record-bench").unlocked,
    true,
    "补录早期基准后重新计算",
  );
});

test("成就：负重自定义动作独立比较，自重不生成重量徽章，零基准有效", () => {
  const s = initialState();
  const custom = {
    id: "custom-test",
    name: "自定义划船",
    part: "背",
    loaded: true,
  };
  s.customExercises.push(custom);
  s.workouts = [
    workout("2026-09-01", 0, custom),
    workout("2026-09-02", 5, custom),
    workout("2026-09-01", 20, builtins[1]),
    workout("2026-09-02", 30, builtins[1]),
  ];
  assert.equal(badge(s, "record-custom-test").unlocked, true);
  assert.equal(badge(s, "record-custom-test").bestWeight, 5);
  assert.equal(badge(s, "record-bench").unlocked, false);
  assert.equal(badge(s, "record-pushup"), undefined);
});
