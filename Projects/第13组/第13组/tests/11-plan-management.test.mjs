import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  clone,
  deletePlan,
  movePlan,
  newWorkout,
  newEntry,
  builtins,
} from "../public/model.js";
test("计划管理：删除、移动、互换、同日无操作，原训练数据不变", () => {
  const s = initialState();
  s.plan[0] = {
    mode: "train",
    parts: ["胸"],
    exerciseIds: ["bench", "pushup"],
  };
  s.plan[2] = { mode: "rest", parts: [], exerciseIds: [] };
  const w = newWorkout();
  w.exercises = [newEntry(builtins[0])];
  s.workouts.push(w);
  const before = clone(s);
  const deleted = deletePlan(s, 0);
  assert.deepEqual(deleted[0], { mode: "unset", parts: [], exerciseIds: [] });
  assert.deepEqual(deleted[2], s.plan[2]);
  const moved = movePlan(s, 0, 1);
  assert.deepEqual(moved[1], s.plan[0]);
  assert.equal(moved[0].mode, "unset");
  const swapped = movePlan(s, 0, 2);
  assert.deepEqual(swapped[0], s.plan[2]);
  assert.deepEqual(swapped[2], s.plan[0]);
  assert.deepEqual(movePlan(s, 0, 0), s.plan);
  assert.deepEqual(movePlan(s, 1, 0), s.plan);
  assert.deepEqual(s, before);
  assert.throws(() => deletePlan(s, -1));
  assert.throws(() => movePlan(s, 0, 7));
});
