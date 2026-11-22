import { test } from "node:test";
import assert from "node:assert/strict";
import {
  validDate,
  monday,
  addDays,
  today,
  initialState,
  positive,
  loadValid,
  repsValid,
} from "../public/model.js";
test("真实日期、跨月跨年与周一边界", () => {
  assert.equal(validDate("2026-02-30"), false);
  assert.equal(validDate("2024-02-29"), true);
  assert.equal(monday("2026-10-18"), "2026-10-12");
  assert.equal(monday("2026-10-19"), "2026-10-19");
  assert.equal(addDays("2025-12-31", 1), "2026-01-01");
  for (const tz of [
    "Asia/Shanghai",
    "America/Los_Angeles",
    "Pacific/Auckland",
  ]) {
    process.env.TZ = tz;
    assert.equal(today(new Date(2026, 9, 16, 0, 5)), "2026-10-16");
    assert.equal(monday("2026-01-01"), "2025-12-29");
  }
});
test("初始状态不包含虚构记录，数值约束明确", () => {
  const s = initialState();
  assert.equal(s.plan.length, 7);
  assert.equal(s.workouts.length, 0);
  assert.equal(s.goals.weekly, null);
  assert.equal(positive(Infinity), false);
  assert.equal(repsValid(1.5), false);
  assert.equal(loadValid(0), true);
  assert.equal(loadValid(-1), false);
});
