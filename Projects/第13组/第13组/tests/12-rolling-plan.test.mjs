import { test } from 'node:test';
import assert from 'node:assert/strict';
import { upcomingPlanDays } from '../public/model.js';

test('未来七天：含今天，跨周、跨月、跨年及闰日，星期映射正确', () => {
  for (const [start, end, indices] of [
    ['2026-10-16', '2026-10-22', [4, 5, 6, 0, 1, 2, 3]],
    ['2026-10-18', '2026-10-24', [6, 0, 1, 2, 3, 4, 5]],
    ['2026-10-30', '2026-11-05', [4, 5, 6, 0, 1, 2, 3]],
    ['2026-12-29', '2027-01-04', [1, 2, 3, 4, 5, 6, 0]],
    ['2028-02-28', '2028-03-05', [0, 1, 2, 3, 4, 5, 6]],
  ]) {
    const dates = upcomingPlanDays(start);
    assert.equal(dates.length, 7);
    assert.equal(dates[0].date, start);
    assert.equal(dates[6].date, end);
    assert.deepEqual(dates.map(d => d.index), indices);
    assert.equal(new Set(dates.map(d => d.date)).size, 7);
    assert.ok(dates.every((d, i) => d.date >= start && (!i || d.date > dates[i - 1].date)));
  }
  assert.equal(upcomingPlanDays('2028-02-28')[1].date, '2028-02-29');
});
