import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  newWorkout,
  newEntry,
  builtins,
  frequency,
  exerciseTrend,
  weightTrend,
  rangeStart,
} from "../public/model.js";
test("阶段4：自然周范围、草稿排除、空周、同动作聚合与自重", () => {
  const s = initialState();
  for (const [date, status, weight] of [
    ["2026-10-18", "complete", 25],
    ["2026-10-18", "complete", 30],
    ["2026-10-19", "draft", 99],
  ]) {
    const w = newWorkout(date);
    w.status = status;
    w.exercises = [newEntry(builtins[0])];
    w.exercises[0].sets[0].weight = weight;
    w.exercises[0].sets[0].reps = 10;
    s.workouts.push(w);
  }
  assert.equal(rangeStart(s, 4, "2026-10-19"), "2026-09-28");
  assert.deepEqual(
    frequency(s, 4, "2026-10-19").map((x) => x.value),
    [0, 0, 2, 0],
  );
  assert.deepEqual(
    exerciseTrend(s, "bench", 4, "2026-10-19").map((x) => x.value),
    [25, 30],
  );
  const repeat = newEntry(builtins[0]);
  repeat.sets[0].weight = 35;
  repeat.sets[0].reps = 8;
  s.workouts[0].exercises.push(repeat);
  assert.deepEqual(exerciseTrend(s, "bench", 4, "2026-10-19")[0].reps, [8]);
  const self = newEntry(builtins[1]);
  self.sets[0].reps = 15;
  s.workouts[0].exercises.push(self);
  assert.equal(exerciseTrend(s, "pushup", 4, "2026-10-19")[0].value, 15);
  s.weights = [
    { id: "1", date: "2026-10-01", value: 70 },
    { id: "2", date: "2026-10-18", value: 69 },
  ];
  assert.equal(weightTrend(s, 4, "2026-10-19").length, 2);
});
