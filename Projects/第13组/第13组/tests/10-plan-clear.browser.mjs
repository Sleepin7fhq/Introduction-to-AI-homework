import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { setup, dbState } from "./helpers.mjs";

test("计划取消全部勾选：含自定义动作，取消不保存，保存后持久化且保留部位", async () => {
  const t = await setup();
  try {
    const p = t.page;
    const edit = () => p.getByRole("button", { name: "编辑安排", exact: true }).click();
    const clear = () => p.getByRole("button", { name: "取消全部勾选", exact: true }).click();
    await edit();
    await p.getByRole("checkbox", { name: "胸", exact: true }).check();
    await p.getByRole("checkbox", { name: "俯卧撑", exact: false }).check();
    await p.getByRole("checkbox", { name: "哑铃飞鸟", exact: false }).check();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    const before = await dbState(p);
    await edit();
    await p.locator(".plan-custom summary").click();
    await p.getByLabel("计划动作名称").fill("我的自定义动作");
    await p.getByRole("button", { name: "加入清单", exact: true }).click();
    assert.equal(await p.locator('[name=exercise]:checked').count(), 3);
    await clear();
    assert.equal(await p.locator('[name=exercise]:checked').count(), 0);
    assert.equal(await p.getByRole("checkbox", { name: "胸", exact: true }).isChecked(), true);
    assert.equal(await p.locator("dialog").isVisible(), true);
    assert.deepEqual(await dbState(p), before);
    await p.getByRole("button", { name: "取消", exact: true }).click();
    assert.deepEqual(await dbState(p), before);
    await edit();
    assert.equal(await p.locator('[name=exercise]:checked').count(), 2);
    for (const width of [320, 390, 1280]) {
      await p.setViewportSize({ width, height: 844 });
      assert.equal(await p.locator("dialog").evaluate(el => el.scrollWidth <= el.clientWidth), true);
    }
    await p.setViewportSize({ width: 390, height: 844 });
    await mkdir("test-results", { recursive: true });
    await p.getByRole("button", { name: "取消全部勾选", exact: true }).scrollIntoViewIfNeeded();
    await p.screenshot({ path: "test-results/plan-clear-button.png" });
    await clear();
    await clear();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    await p.reload();
    await edit();
    assert.equal(await p.locator('[name=exercise]:checked').count(), 0);
    assert.equal(await p.getByRole("checkbox", { name: "胸", exact: true }).isChecked(), true);
    const after = await dbState(p);
    assert.deepEqual(after.customExercises, before.customExercises);
    assert.deepEqual(after.workouts, before.workouts);
  } finally {
    await t.close();
  }
});
