import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { setup, dbState } from "./helpers.mjs";
async function seed(t) {
  const data = await t.page.evaluate(async () => {
    const m = await import("/model.js"),
      store = await import("/store.js");
    const db = await store.openStore(),
      s = await store.readState(db),
      from = (new Date().getDay() + 6) % 7;
    s.plan[from] = {
      mode: "train",
      parts: ["胸"],
      exerciseIds: ["bench", "pushup"],
    };
    const occupied = (from + 2) % 7,
      empty = (from + 1) % 7;
    s.plan[occupied] = { mode: "rest", parts: [], exerciseIds: [] };
    const draft = m.newWorkout();
    draft.exercises = [m.newEntry(m.builtins[0])];
    Object.assign(draft.exercises[0].sets[0], { weight: 20, reps: 10 });
    s.workouts.push(draft);
    await store.writeState(db, s, s.revision);
    return { from, occupied, empty };
  });
  await t.page.reload();
  await t.page
    .getByRole("button", { name: "删除今日计划", exact: true })
    .waitFor();
  return data;
}
async function waitPlan(p, index, mode) {
  await p.waitForFunction(
    async ({ index, mode }) => {
      const m = await import("/store.js");
      return (await m.readState(await m.openStore())).plan[index].mode === mode;
    },
    { index, mode },
  );
}
async function drag(p, target, accept = true) {
  const handle = p.locator("[data-plan-drag]");
  await handle.scrollIntoViewIfNeeded();
  const a = await handle.boundingBox(),
    b = await p.locator(`[data-plan-target="${target}"]`).boundingBox();
  await p.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await p.mouse.down();
  await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 8 });
  assert.equal(
    await p.locator(".plan-drop-target").count(),
    1,
    "拖动到目标星期时应高亮该日",
  );
  p.once("dialog", (d) => (accept ? d.accept() : d.dismiss()));
  await p.mouse.up();
}
test("计划管理：删除确认、撤销、编辑弹窗删除、刷新与训练保留", async () => {
  const t = await setup();
  try {
    const p = t.page,
      { from } = await seed(t),
      before = await dbState(p);
    p.once("dialog", (d) => d.dismiss());
    await p.getByRole("button", { name: "删除今日计划", exact: true }).click();
    assert.deepEqual(await dbState(p), before);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除今日计划", exact: true }).click();
    await waitPlan(p, from, "unset");
    assert.deepEqual((await dbState(p)).workouts, before.workouts);
    await p.getByRole("button", { name: "撤销", exact: true }).click();
    await waitPlan(p, from, "train");
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    p.once("dialog", (d) => d.accept());
    await p
      .getByRole("dialog")
      .getByRole("button", { name: "删除今日计划", exact: true })
      .click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    await p.reload();
    await p.getByRole("button", { name: "编辑安排", exact: true }).waitFor();
    assert.equal((await dbState(p)).plan[from].mode, "unset");
    assert.deepEqual((await dbState(p)).workouts, before.workouts);
  } finally {
    await t.close();
  }
});
test("计划管理：真实鼠标拖动、取消、移动、互换、撤销及无效落点", async () => {
  const t = await setup();
  try {
    const p = t.page,
      { from, empty, occupied } = await seed(t),
      before = await dbState(p);
    await drag(p, empty, false);
    assert.deepEqual(await dbState(p), before);
    await drag(p, empty, true);
    await waitPlan(p, empty, "train");
    await p.locator(`[data-plan-drag="${empty}"]`).waitFor();
    assert.equal((await dbState(p)).plan[from].mode, "unset");
    await drag(p, occupied, true);
    await p.locator(`[data-plan-drag="${occupied}"]`).waitFor();
    let s = await dbState(p);
    assert.equal(s.plan[empty].mode, "rest");
    assert.deepEqual(s.plan[occupied], before.plan[from]);
    assert.deepEqual(s.workouts, before.workouts);
    await p.getByRole("button", { name: "撤销", exact: true }).click();
    await waitPlan(p, occupied, "rest");
    await p.locator(`[data-plan-target="${empty}"]`).click();
    const handle = p.locator("[data-plan-drag]"),
      box = await handle.boundingBox();
    const unchanged = await dbState(p);
    await p.mouse.move(box.x + 10, box.y + 10);
    await p.mouse.down();
    await p.mouse.move(10, 10, { steps: 5 });
    await p.mouse.up();
    assert.deepEqual(await dbState(p), unchanged);
    assert.equal(await p.locator(".plan-drag-ghost").count(), 0);
    await p.reload();
    await p.getByRole("button", { name: "编辑安排", exact: true }).waitFor();
    assert.deepEqual((await dbState(p)).plan, unchanged.plan);
  } finally {
    await t.close();
  }
});
test("计划管理：触屏拖动、取消手势、键盘移动与失败不丢计划", async () => {
  const t = await setup();
  try {
    const p = t.page,
      { from, empty } = await seed(t),
      before = await dbState(p);
    const cdp = await t.context.newCDPSession(p);
    const handle = p.locator("[data-plan-drag]");
    await handle.scrollIntoViewIfNeeded();
    let a = await handle.boundingBox(),
      b = await p.locator(`[data-plan-target="${empty}"]`).boundingBox();
    const touch = (type, x, y) =>
      cdp.send("Input.dispatchTouchEvent", {
        type,
        touchPoints:
          type === "touchEnd" || type === "touchCancel"
            ? []
            : [{ x, y, id: 1 }],
      });
    await touch("touchStart", a.x + 20, a.y + 20);
    await touch("touchMove", b.x + b.width / 2, b.y + b.height / 2);
    await touch("touchCancel");
    assert.equal(await p.locator(".plan-drag-ghost").count(), 0);
    assert.deepEqual(await dbState(p), before);
    await touch("touchStart", a.x + 20, a.y + 20);
    await touch("touchMove", b.x + b.width / 2, b.y + b.height / 2);
    assert.equal(
      await p.locator(".plan-drop-target").count(),
      1,
      "拖动到目标星期时应高亮该日",
    );
    p.once("dialog", (d) => d.accept());
    await touch("touchEnd");
    await p.locator(`[data-plan-drag="${empty}"]`).waitFor();
    assert.deepEqual((await dbState(p)).workouts, before.workouts);
    await p.locator("[data-plan-drag]").focus();
    await p.keyboard.press("Enter");
    await p.getByRole("heading", { name: /移动计划/ }).waitFor();
    p.once("dialog", (d) => d.accept());
    await p
      .locator(`[data-action="plan-move-to"][data-index="${from}"]`)
      .click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    await p
      .getByRole("button", { name: "删除今日计划", exact: true })
      .waitFor();
    await p.evaluate(() => {
      window.savedPut = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.savedPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    const unchanged = await dbState(p);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除今日计划", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "visible" });
    assert.deepEqual(await dbState(p), unchanged);
    assert.match(await p.locator(".today-card").textContent(), /杠铃卧推/);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.savedPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "hidden" });
    for (const width of [320, 390, 768, 1280]) {
      await p.setViewportSize({ width, height: 900 });
      assert.equal(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
      );
    }
    await p.setViewportSize({ width: 390, height: 844 });
    await p.reload();
    await p
      .getByRole("button", { name: "删除今日计划", exact: true })
      .waitFor();
    await mkdir("test-results", { recursive: true });
    await p.screenshot({
      path: "test-results/plan-management.png",
      fullPage: true,
    });
  } finally {
    await t.close();
  }
});
