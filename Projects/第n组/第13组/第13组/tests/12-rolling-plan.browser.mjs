import { test } from 'node:test';
import assert from 'node:assert/strict';
import { setup, dbState } from './helpers.mjs';

test('未来七天：日期、计划映射、跨周编辑和移动、刷新与次日窗口', async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.clock.setFixedTime(new Date('2026-10-16T12:00:00'));
    await p.reload();
    await p.getByRole('heading', { name: '未来七天', exact: true }).waitFor();
    const expected = [4, 5, 6, 0, 1, 2, 3];
    assert.deepEqual(await p.locator('.week-strip .day').evaluateAll(es => es.map(e => Number(e.dataset.index))), expected);
    assert.deepEqual(await p.locator('.week-strip .day').evaluateAll(es => es.map(e => e.getAttribute('aria-label'))), [
      '周五 2026-10-16', '周六 2026-10-17', '周日 2026-10-18', '周一 2026-10-19', '周二 2026-10-20', '周三 2026-10-21', '周四 2026-10-22',
    ]);
    assert.match(await p.locator('.card-head').first().textContent(), /10.16 — 10.22/);
    assert.deepEqual(await p.locator('.plan-row').evaluateAll(es => es.map(e => Number(e.dataset.index))), expected);
    assert.equal(await p.locator('.day.selected').getAttribute('data-index'), '4');
    await p.getByRole('button', { name: '周一 2026-10-19', exact: true }).click();
    await p.getByRole('button', { name: '编辑安排', exact: true }).click();
    await p.getByRole('dialog').getByRole('checkbox', { name: '设为休息日', exact: true }).check();
    await p.getByRole('button', { name: '保存', exact: true }).click();
    await p.locator('dialog').waitFor({ state: 'hidden' });
    assert.equal((await dbState(p)).plan[0].mode, 'rest');
    assert.equal((await dbState(p)).plan[3].mode, 'unset');
    await p.locator('[data-plan-drag]').click();
    assert.deepEqual(await p.locator('[data-action="plan-move-to"]').evaluateAll(es => es.map(e => Number(e.dataset.index))), expected);
    assert.match(await p.locator('[data-action="plan-move-to"][data-index="3"]').textContent(), /周四 10.22/);
    p.once('dialog', d => d.accept());
    await p.locator('[data-action="plan-move-to"][data-index="3"]').click();
    await p.locator('dialog').waitFor({ state: 'hidden' });
    await p.locator('[data-plan-drag="3"]').waitFor();
    const moved = await dbState(p);
    assert.equal(moved.plan[0].mode, 'unset');
    assert.equal(moved.plan[3].mode, 'rest');
    await p.reload();
    await p.getByRole('heading', { name: '未来七天', exact: true }).waitFor();
    assert.deepEqual((await dbState(p)).plan, moved.plan);
    for (const width of [320, 390, 1280]) {
      await p.setViewportSize({ width, height: 844 });
      assert.ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    await p.clock.setFixedTime(new Date('2026-10-17T12:00:00'));
    await p.reload();
    await p.getByRole('heading', { name: '未来七天', exact: true }).waitFor();
    assert.equal(await p.locator('.day').first().getAttribute('aria-label'), '周六 2026-10-17');
    assert.equal(await p.locator('.day').last().getAttribute('aria-label'), '周五 2026-10-23');
    assert.equal(await p.locator('.day.selected').getAttribute('data-index'), '5');
  } finally {
    await t.close();
  }
});
