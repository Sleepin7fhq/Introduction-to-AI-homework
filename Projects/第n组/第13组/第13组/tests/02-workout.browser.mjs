import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, dbState, saved, record } from "./helpers.mjs";
test("阶段2：计划目标、真实逐组输入、续写、删除撤销及完成", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByRole("checkbox", { name: "胸", exact: true }).check();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.ok((await dbState(p)).plan.some((x) => x.parts.includes("胸")));
    await p.getByRole("button", { name: "设置训练目标", exact: true }).click();
    await p.getByLabel("每周训练次数").fill("3");
    await p.getByLabel("目标体重 · kg").fill("65");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.equal((await dbState(p)).goals.weekly, 3);
    await record(p);
    await p.getByRole("button", { name: "添加一组" }).click();
    assert.equal(await p.getByLabel("杠铃卧推 第2组重量").inputValue(), "20");
    await p.getByLabel("杠铃卧推 第2组重量").fill("25");
    await p.getByLabel("杠铃卧推 第2组次数").fill("10");
    await saved(p);
    await p.reload();
    assert.equal(await p.getByLabel("杠铃卧推 第2组重量").inputValue(), "25");
    await p.getByRole("button", { name: "删除杠铃卧推第2组" }).click();
    await p.getByRole("button", { name: "撤销", exact: true }).click();
    assert.equal(await p.getByLabel("杠铃卧推 第2组次数").inputValue(), "10");
    await p.getByRole("button", { name: "完成训练", exact: true }).dblclick();
    await p.waitForURL("**/#detail/*");
    const s = await dbState(p);
    assert.equal(s.workouts.length, 1);
    assert.equal(s.workouts[0].status, "complete");
    assert.equal(s.workouts[0].exercises[0].sets.length, 2);
  } finally {
    await t.close();
  }
});
