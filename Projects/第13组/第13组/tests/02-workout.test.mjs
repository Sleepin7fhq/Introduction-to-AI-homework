import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  newWorkout,
  newEntry,
  builtins,
  completeWorkout,
  beginWorkout,
  weeklyCount,
  workoutError,
} from "../public/model.js";
test("阶段2：完成校验、自重与重复完成", () => {
  const s = initialState(),
    w = newWorkout();
  s.workouts.push(w);
  assert.match(workoutError(w), /添加/);
  w.exercises.push(newEntry(builtins[0]));
  assert.match(workoutError(w), /次数/);
  w.exercises[0].sets[0] = { id: "set", weight: 20, reps: 12, done: false };
  const next = completeWorkout(beginWorkout(s, w.id), w.id);
  assert.equal(weeklyCount(next), 1);
  assert.equal(weeklyCount(completeWorkout(next, w.id)), 1);
  assert.equal(weeklyCount(s), 0);
  w.exercises[0].sets[0].reps = 1.5;
  assert.throws(() => completeWorkout(beginWorkout(s, w.id), w.id));
  w.exercises = [newEntry(builtins[1])];
  w.exercises[0].sets[0].reps = 10;
  assert.equal(workoutError(w), "");
});
