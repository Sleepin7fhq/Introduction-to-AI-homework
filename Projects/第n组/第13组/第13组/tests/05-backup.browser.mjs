import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { setup, record, dbState } from "./helpers.mjs";
test("阶段5：真实文件下载、取消恢复、跨浏览器上下文恢复与失败不改原数据", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByRole("checkbox", { name: "胸", exact: true }).check();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.getByRole("button", { name: "设置训练目标" }).click();
    await p.getByLabel("每周训练次数").fill("3");
    await p.getByLabel("目标体重 · kg").fill("65");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "计划", exact: true }).click();
    await record(p);
    await p.getByRole("button", { name: "添加动作", exact: true }).click();
    await p.getByRole("button", { name: /创建自定义动作/ }).click();
    await p.getByLabel("动作名称").fill("备份测试动作");
    await p.getByRole("button", { name: "创建并添加" }).click();
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("button", { name: /记录体重/ }).click();
    await p.getByLabel("体重 · kg").fill("70");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.getByRole("link", { name: "我的", exact: true }).click();
    const download = p.waitForEvent("download");
    await p.getByRole("button", { name: "导出备份", exact: true }).click();
    const file = await download;
    const data = await readFile(await file.path());
    const backup = JSON.parse(data);
    assert.equal(backup.data.workouts.length, 2);
    assert.equal(backup.data.workouts[0].status, "complete");
    assert.equal(backup.data.workouts[1].status, "draft");
    assert.equal(backup.data.customExercises.length, 1);
    assert.equal(backup.data.weights[0].value, 70);
    assert.equal(backup.data.goals.weekly, 3);
    assert.equal(backup.data.goals.targetWeight, 65);
    assert.ok(backup.data.plan.some((day) => day.parts.includes("胸")));
    const original = await dbState(p);
    await p.locator("#backup-file").setInputFiles({
      name: "bad.json",
      mimeType: "application/json",
      buffer: Buffer.from("{"),
    });
    await p.getByRole("status").filter({ hasText: "不是有效" }).waitFor();
    assert.deepEqual(await dbState(p), original);
    await p.locator("#backup-file").setInputFiles({
      name: "backup.json",
      mimeType: "application/json",
      buffer: data,
    });
    await p.getByRole("button", { name: "取消", exact: true }).click();
    assert.deepEqual(await dbState(p), original);
    const ctx = await t.browser.newContext();
    const other = await ctx.newPage();
    await other.goto(t.url + "/#settings");
    await other.locator("#backup-file").setInputFiles({
      name: "backup.json",
      mimeType: "application/json",
      buffer: data,
    });
    await other.getByRole("button", { name: "确认替换并恢复" }).click();
    await other.getByRole("status").filter({ hasText: "恢复完成" }).waitFor();
    const restored = await dbState(other);
    assert.deepEqual(
      { ...restored, revision: 0 },
      { ...original, revision: 0 },
    );
    await other.locator("#backup-file").setInputFiles({
      name: "backup.json",
      mimeType: "application/json",
      buffer: data,
    });
    await other.evaluate(() => {
      window.originalPut = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.originalPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await other.getByRole("button", { name: "确认替换并恢复" }).click();
    await other
      .locator(".modal-error")
      .filter({ hasText: /中止|abort/i })
      .waitFor();
    assert.deepEqual(await dbState(other), restored);
    await other.evaluate(
      () => (IDBObjectStore.prototype.put = window.originalPut),
    );
    await ctx.close();
  } finally {
    await t.close();
  }
});
