import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, dbState, saved, record } from "./helpers.mjs";
test("阶段3：历史取消、保存、日期补录、删除与体重冲突", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "编辑训练" }).click();
    await p.getByLabel("杠铃卧推 第1组重量").fill("30");
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "取消", exact: true }).click();
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].weight,
      20,
    );
    await p.getByRole("link", { name: /杠铃卧推/ }).click();
    await p.getByRole("link", { name: "编辑训练" }).click();
    await p.getByLabel("杠铃卧推 第1组重量").fill("30");
    await p.getByLabel("训练日期").fill("2026-01-01");
    await p.getByRole("button", { name: "保存修改" }).click();
    await p.waitForURL("**/#detail/*");
    assert.equal((await dbState(p)).workouts[0].date, "2026-01-01");
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].weight,
      30,
    );
    p.once("dialog", (d) => d.dismiss());
    await p.getByRole("button", { name: "删除训练" }).click();
    assert.equal((await dbState(p)).workouts.length, 1);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除训练" }).click();
    await p.waitForURL("**/#records");
    assert.equal((await dbState(p)).workouts.length, 0);
    await p.getByRole("button", { name: "补录训练", exact: false }).click();
    await p.getByLabel("训练日期").fill("2026-01-02");
    await p.getByRole("button", { name: "开始记录" }).click();
    await p.waitForURL("**/#edit/*");
    assert.equal((await dbState(p)).workouts[0].date, "2026-01-02");
    await p.goto(t.url + "/#weights");
    await p.getByRole("button", { name: "＋ 记录体重", exact: true }).click();
    await p.getByLabel("体重 · kg").fill("70");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.getByRole("button", { name: "＋ 记录体重", exact: true }).click();
    await p.getByLabel("体重 · kg").fill("69");
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.equal((await dbState(p)).weights.length, 1);
    assert.equal((await dbState(p)).weights[0].value, 69);
    await p.getByRole("button", { name: "修改", exact: true }).click();
    await p.getByLabel("测量日期").fill("2026-01-01");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.equal((await dbState(p)).weights[0].date, "2026-01-01");
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除", exact: true }).click();
    assert.equal((await dbState(p)).weights.length, 0);
  } finally {
    await t.close();
  }
});
