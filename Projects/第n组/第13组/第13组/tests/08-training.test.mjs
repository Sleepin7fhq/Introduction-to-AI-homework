import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  newWorkout,
  beginWorkout,
  completeWorkout,
  validateState,
  clone,
  builtins,
  upgradeState,
  makeBackup,
  parseBackup,
  measurementValid,
  latestMetric,
  weightTrend,
} from "../public/model.js";

import { legacyFixture } from "./legacy-fixture.mjs";
test("新版：计划快照、准备/训练阶段、有效组、完成幂等与备份往返", () => {
  let s = initialState();
  s.plan[0] = {
    mode: "train",
    parts: ["胸"],
    exerciseIds: ["bench", "pushup"],
  };
  const w = newWorkout("2026-01-01", s.plan[0]);
  s.workouts.push(w);
  assert.equal(w.phase, "prepare");
  assert.deepEqual(
    w.exercises.map((e) => e.exerciseId),
    ["bench", "pushup"],
  );
  assert.throws(() => completeWorkout(s, w.id), /先确认/);
  w.exercises.pop();
  assert.deepEqual(s.plan[0].exerciseIds, ["bench", "pushup"]);
  s = beginWorkout(s, w.id);
  assert.ok(s.workouts[0].startedAt);
  assert.deepEqual(beginWorkout(s, w.id), s);
  assert.throws(() => completeWorkout(s, w.id), /次数/);
  Object.assign(s.workouts[0].exercises[0].sets[0], {
    weight: 20,
    reps: 12,
    done: true,
  });
  validateState(s);
  const malformed = clone(s);
  malformed.workouts[0].exercises[0].sets[0].reps = null;
  assert.throws(() => validateState(malformed));
  const completed = completeWorkout(s, w.id);
  assert.deepEqual(completeWorkout(completed, w.id), completed);
  assert.deepEqual(
    parseBackup(JSON.stringify(makeBackup(completed))).data,
    completed,
  );
  s.plan[0].exerciseIds = ["missing"];
  assert.throws(() => validateState(s));
  s.plan[0].exerciseIds = ["bench", "bench"];
  assert.throws(() => validateState(s));
  const empty = initialState();
  empty.workouts.push(newWorkout());
  assert.throws(() => beginWorkout(empty, empty.workouts[0].id), /先添加/);
  assert.equal(
    newWorkout("2026-01-01", null, builtins, "backfill").phase,
    "active",
  );
});
test("新版：旧数据与旧备份无损升级，损坏旧数据拒绝", () => {
  const old = legacyFixture(),
    before = clone(old),
    next = upgradeState(old);
  assert.deepEqual(old, before);
  assert.equal(next.version, 2);
  assert.deepEqual(next.plan[0], {
    mode: "train",
    parts: ["胸"],
    exerciseIds: [],
  });
  assert.equal(next.workouts[0].exercises[0].sets[0].weight, 20);
  assert.equal(next.workouts[0].exercises[0].sets[0].done, true);
  assert.equal(next.workouts[1].phase, "active");
  assert.equal(next.weights[0].value, 70);
  assert.equal(next.weights[0].bodyFat, null);
  const backup = {
    app: "today-fit",
    backupVersion: 1,
    exportedAt: "2026-01-03T10:00:00Z",
    data: old,
  };
  assert.deepEqual(parseBackup(JSON.stringify(backup)).data, next);
  old.weights[0].value = -1;
  assert.throws(() => upgradeState(old));
  backup.data = old;
  assert.throws(() => parseBackup(JSON.stringify(backup)));
});
test("新版：独立身体指标校验、最新值日期、体脂记录不污染体重曲线", () => {
  const s = initialState(),
    stamp = "2026-01-01T10:00:00Z";
  s.weights = [
    {
      id: "a",
      date: "2026-01-01",
      value: 70,
      bodyFat: 20,
      waist: null,
      createdAt: stamp,
      updatedAt: stamp,
    },
    {
      id: "b",
      date: "2026-01-02",
      value: null,
      bodyFat: 19,
      waist: 80,
      createdAt: stamp,
      updatedAt: stamp,
    },
  ];
  validateState(s);
  assert.equal(latestMetric(s, "value").date, "2026-01-01");
  assert.equal(latestMetric(s, "bodyFat").bodyFat, 19);
  assert.equal(weightTrend(s, "all").length, 1);
  assert.equal(
    measurementValid({ value: null, bodyFat: null, waist: 80 }),
    true,
  );
  for (const values of [
    { value: null, bodyFat: null, waist: null },
    { value: 0, bodyFat: null, waist: null },
    { value: null, bodyFat: 100, waist: null },
    { value: null, bodyFat: -1, waist: null },
    { value: null, bodyFat: null, waist: Infinity },
  ])
    assert.equal(measurementValid(values), false);
  assert.deepEqual(parseBackup(JSON.stringify(makeBackup(s))).data, s);
});
