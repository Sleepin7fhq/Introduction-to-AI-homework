import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  newWorkout,
  newEntry,
  builtins,
  today,
  addDays,
  clone,
  syncEmptyDraft,
  addPlannedExercises,
  validateState,
  makeBackup,
  parseBackup,
} from "../public/model.js";

function fixture() {
  const s = initialState(),
    w = newWorkout();
  delete w.planCleared; // Existing v2 drafts predate the deliberate-clear marker.
  s.workouts.push(w);
  s.plan[(new Date().getDay() + 6) % 7] = {
    mode: "train",
    parts: ["胸"],
    exerciseIds: ["bench", "pushup"],
  };
  return { s, w };
}
test("计划同步：只自动接入当天未开始的空草稿，保留手动清空和其他记录", () => {
  const { s, w } = fixture();
  assert.equal(syncEmptyDraft(s), 2);
  assert.deepEqual(
    w.exercises.map((e) => e.exerciseId),
    ["bench", "pushup"],
  );
  const after = clone(s);
  assert.equal(syncEmptyDraft(s), 0);
  assert.deepEqual(s, after);
  for (const changes of [
    { planCleared: true },
    { phase: "active" },
    { mode: "backfill" },
    { date: addDays(today(), -1) },
    { status: "complete" },
    { startedAt: new Date().toISOString() },
    { exercises: [newEntry(builtins[2])] },
  ]) {
    const f = fixture();
    Object.assign(f.w, changes);
    const before = clone(f.s);
    assert.equal(syncEmptyDraft(f.s), 0);
    assert.deepEqual(f.s, before);
  }
});
test("计划同步：补入缺失动作保留已填组与打卡，标记兼容备份并校验", () => {
  const { s, w } = fixture();
  w.phase = "active";
  w.exercises = [newEntry(builtins[0])];
  Object.assign(w.exercises[0].sets[0], { weight: 25, reps: 10, done: true });
  const before = clone(w.exercises[0]),
    plan = clone(s.plan);
  assert.equal(addPlannedExercises(s, w), 1);
  assert.deepEqual(w.exercises[0], before);
  assert.deepEqual(s.plan, plan);
  assert.equal(addPlannedExercises(s, w), 0);
  validateState(s);
  w.exercises = [];
  w.planCleared = true;
  assert.deepEqual(parseBackup(JSON.stringify(makeBackup(s))).data, s);
  w.planCleared = "yes";
  assert.throws(() => validateState(s));
});
