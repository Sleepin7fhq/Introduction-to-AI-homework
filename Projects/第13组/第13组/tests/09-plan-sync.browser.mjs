import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, dbState, saved } from "./helpers.mjs";

async function editToday(p, names) {
  await p.getByRole("link", { name: "计划", exact: true }).click();
  await p.getByRole("button", { name: "编辑安排", exact: true }).click();
  for (const name of names)
    await p.getByRole("checkbox", { name, exact: name.length === 1 }).check();
  await p.getByRole("button", { name: "保存", exact: true }).click();
  await p.locator("dialog").waitFor({ state: "hidden" });
}

test("计划同步回归：先建空草稿再安排动作，继续训练带入完整计划", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await editToday(p, ["胸"]);
    await p.getByRole("button", { name: "开始训练", exact: true }).click();
    await p.waitForURL("**/#edit/*");
    const original = (await dbState(p)).workouts[0];
    assert.equal(original.exercises.length, 0);
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await editToday(p, ["俯卧撑", "哑铃飞鸟", "硬拉"]);
    const w = (await dbState(p)).workouts[0];
    assert.deepEqual(
      w.exercises.map((e) => e.exerciseId),
      ["pushup", "fly", "deadlift"],
    );
    assert.equal(w.id, original.id);
    assert.equal(w.status, "draft");
    assert.equal(w.phase, "prepare");
    await p.getByRole("link", { name: "记录", exact: true }).click();
    await p
      .getByRole("button", { name: "继续未完成训练", exact: true })
      .click();
    await p.getByLabel("俯卧撑 第1组次数").waitFor();
    assert.deepEqual(await p.locator(".exercise h2").allTextContents(), [
      "俯卧撑",
      "哑铃飞鸟",
      "硬拉",
    ]);
    await p.reload();
    await p.getByLabel("硬拉 第1组重量").waitFor();
    assert.equal(await p.locator(".exercise").count(), 3);
  } finally {
    await t.close();
  }
});

test("计划同步回归：旧空草稿重开修复，手动清空不回填，补入不覆盖或重复", async () => {
  const t = await setup();
  try {
    const p = t.page;
    const id = await p.evaluate(async () => {
      const m = await import("/model.js"),
        store = await import("/store.js");
      const db = await store.openStore(),
        s = await store.readState(db),
        w = m.newWorkout();
      s.workouts.push(w);
      s.plan[(new Date().getDay() + 6) % 7] = {
        mode: "train",
        parts: ["胸"],
        exerciseIds: ["bench", "pushup"],
      };
      await store.writeState(db, s, s.revision);
      return w.id;
    });
    await p.reload();
    await p.getByRole("button", { name: "继续训练", exact: true }).waitFor();
    assert.equal((await dbState(p)).workouts[0].id, id);
    assert.equal((await dbState(p)).workouts[0].exercises.length, 2);
    await p.getByRole("button", { name: "继续训练", exact: true }).click();
    await p.getByLabel("杠铃卧推 第1组重量").waitFor();
    assert.equal((await dbState(p)).workouts[0].exercises.length, 2);
    await p.getByLabel("杠铃卧推 第1组重量").fill("25");
    await p.getByLabel("杠铃卧推 第1组次数").fill("10");
    await saved(p);
    await p.getByRole("button", { name: "移除俯卧撑", exact: true }).click();
    await p.getByRole("button", { name: "移除俯卧撑", exact: true }).waitFor({state:"hidden"});
    await saved(p);
    const before = (await dbState(p)).workouts[0].exercises[0];
    await p.reload();
    await p.getByLabel("杠铃卧推 第1组重量").waitFor();
    assert.equal(await p.locator(".exercise").count(), 1);
    await p.getByRole("button", { name: "补入计划动作", exact: true }).click();
    await saved(p);
    let w = (await dbState(p)).workouts[0];
    assert.deepEqual(w.exercises[0], before);
    assert.equal(w.exercises.length, 2);
    assert.equal(
      await p
        .getByRole("button", { name: "补入计划动作", exact: true })
        .count(),
      0,
    );
    await p.getByRole("button", { name: "移除杠铃卧推", exact: true }).click();
    await p.getByRole("button", { name: "移除杠铃卧推", exact: true }).waitFor({state:"hidden"});
    await p.getByRole("button", { name: "移除俯卧撑", exact: true }).click();
    await p.getByRole("button", { name: "移除俯卧撑", exact: true }).waitFor({state:"hidden"});
    await saved(p);
    await p.reload();
    assert.equal((await dbState(p)).workouts[0].exercises.length, 0);
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await p
      .getByRole("button", { name: "继续未完成训练", exact: true })
      .click();
    await p.getByRole("heading", {name:"从第一个动作开始",exact:true}).waitFor();
    assert.equal(await p.locator(".exercise").count(), 0);
    await p.getByRole("button", { name: "补入计划动作", exact: true }).click();
    await saved(p);
    assert.equal((await dbState(p)).workouts[0].exercises.length, 2);
  } finally {
    await t.close();
  }
});
