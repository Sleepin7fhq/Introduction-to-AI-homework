import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, record, saved, dbState } from "./helpers.mjs";

async function abortWrites(p) {
  await p.evaluate(() => {
    window.savedPut = IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.put = function (...args) {
      const request = window.savedPut.apply(this, args);
      this.transaction.abort();
      return request;
    };
  });
}

test("验收：缺失次数准确定位，自重空负重不抢焦点", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    await p.getByLabel("杠铃卧推 第1组次数").fill("");
    await saved(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    assert.equal(
      await p.evaluate(() => document.activeElement.getAttribute("aria-label")),
      "杠铃卧推 第1组次数",
    );
    await p.getByLabel("杠铃卧推 第1组次数").fill("10");
    await p.getByRole("button", { name: "添加动作", exact: true }).click();
    await p
      .getByRole("button", { name: "俯卧撑 胸 · 自重训练", exact: false })
      .click();
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    assert.equal(
      await p.evaluate(() => document.activeElement.getAttribute("aria-label")),
      "俯卧撑 第1组次数",
    );
    assert.equal((await dbState(p)).workouts[0].status, "draft");
  } finally {
    await t.close();
  }
});

test("验收：删除写入失败后，训练和身体指标仍在页面及数据库中", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    const before = await dbState(p);
    await abortWrites(p);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除训练", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "visible" });
    await p.getByRole("link", { name: "记录", exact: true }).click();
    await p
      .getByRole("heading", { name: "每一次，都有记录。", exact: true })
      .waitFor();
    assert.equal(
      await p.locator(`a[href="#detail/${before.workouts[0].id}"]`).count(),
      1,
    );
    assert.deepEqual(await dbState(p), before);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.savedPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "hidden" });
    assert.deepEqual((await dbState(p)).workouts, before.workouts);
    await p.goto(t.url + "/#weights");
    await p.getByRole("button", { name: "＋ 记录体重", exact: true }).click();
    await p.getByLabel("体重 · kg").fill("70");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    const weights = (await dbState(p)).weights;
    await abortWrites(p);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "visible" });
    await p.getByRole("link", { name: "我的", exact: true }).click();
    assert.match(await p.locator(".body-metrics").textContent(), /70/);
    assert.deepEqual((await dbState(p)).weights, weights);
  } finally {
    await t.close();
  }
});

test("验收：手机常用文字按钮触控宽度、编辑输入可见且可点击", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    for (const width of [320, 390, 430]) {
      await p.setViewportSize({ width, height: 640 });
      for (const name of ["收起陪练", "换一句", "返回"]) {
        const b = await p
          .getByRole("button", { name, exact: true })
          .boundingBox();
        assert.ok(
          b.width >= 44 && b.height >= 44,
          `${name} 应有 44px 触控区域，实际 ${b.width} × ${b.height}`,
        );
      }
      const input = p.getByLabel("杠铃卧推 第1组次数");
      await input.scrollIntoViewIfNeeded();
      await input.click();
      await input.fill("13");
      await saved(p);
      const visible = await input.evaluate((el) => {
        const r = el.getBoundingClientRect();
        return (
          r.top >= 0 &&
          r.bottom <= innerHeight &&
          document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) ===
            el
        );
      });
      assert.ok(visible);
      assert.ok(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
    }
  } finally {
    await t.close();
  }
});

test("验收：多条真实存储记录与图表逐项核对，修改删除后重新计算", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.clock.setFixedTime(new Date("2026-10-17T12:00:00"));
    const ids = await p.evaluate(async () => {
      const m = await import("/model.js"),
        store = await import("/store.js");
      const db = await store.openStore(),
        s = await store.readState(db);
      const workouts = [
        ["2026-09-28", 10],
        ["2026-10-16", 25],
        ["2026-10-16", 30],
      ].map(([date, weight]) => {
        const w = m.newWorkout(date);
        w.phase = "active";
        w.status = "complete";
        w.exercises = [m.newEntry(m.builtins[0]), m.newEntry(m.builtins[1])];
        Object.assign(w.exercises[0].sets[0], { weight, reps: 10, done: true });
        Object.assign(w.exercises[1].sets[0], { reps: 17, done: true });
        return w;
      });
      const repeat = m.newEntry(m.builtins[0]);
      Object.assign(repeat.sets[0], { weight: 35, reps: 8, done: true });
      workouts[2].exercises.push(repeat);
      const draft = m.newWorkout();
      draft.exercises = [m.newEntry(m.builtins[0])];
      Object.assign(draft.exercises[0].sets[0], { weight: 99, reps: 20 });
      s.workouts = [...workouts, draft];
      s.goals = { weekly: 3, targetWeight: 65 };
      const now = new Date().toISOString();
      s.weights = [
        ["2026-10-01", 72, null],
        ["2026-10-16", 70, null],
        ["2026-10-17", null, 20],
      ].map(([date, value, bodyFat]) => ({
        id: m.uid(),
        date,
        value,
        bodyFat,
        waist: null,
        createdAt: now,
        updatedAt: now,
      }));
      await store.writeState(db, s, s.revision);
      return workouts.map((w) => w.id);
    });
    await p.goto(t.url + "/#progress");
    await p.reload();
    await p.getByRole("group", { name: "动作进步，单位kg" }).waitFor();
    const labels = (kind) =>
      p
        .locator(`g[data-kind="${kind}"]`)
        .evaluateAll((es) => es.map((e) => e.getAttribute("aria-label")));
    assert.deepEqual(await labels("frequency"), [
      "2026-09-21，0 次",
      "2026-09-28，1 次",
      "2026-10-05，0 次",
      "2026-10-12，2 次",
    ]);
    assert.deepEqual(await labels("exercise"), [
      "2026-09-28，10 kg",
      "2026-10-16，25 kg",
      "2026-10-16，35 kg",
    ]);
    assert.deepEqual(await labels("weight"), [
      "2026-10-01，72 kg",
      "2026-10-16，70 kg",
    ]);
    assert.match(
      await p
        .locator("svg.chart")
        .allTextContents()
        .then((xs) => xs.join(" ")),
      /目标 65 kg/,
    );
    await p.locator('g[data-kind="exercise"]').last().click();
    assert.match(
      await p.locator("dialog").textContent(),
      /最高负重对应次数：8 次/,
    );
    await p.getByRole("button", { name: "关闭弹窗" }).click();
    await p.locator("#trend-exercise").selectOption("pushup");
    assert.deepEqual(await labels("exercise"), [
      "2026-09-28，17 次",
      "2026-10-16，17 次",
      "2026-10-16，17 次",
    ]);
    await p.goto(t.url + "/#edit/" + ids[1]);
    await p.getByLabel("杠铃卧推 第1组重量").fill("40");
    await p.getByRole("button", { name: "保存修改" }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.locator("#trend-exercise").selectOption("bench");
    assert.deepEqual(await labels("exercise"), [
      "2026-09-28，10 kg",
      "2026-10-16，40 kg",
      "2026-10-16，35 kg",
    ]);
    await p.goto(t.url + "/#detail/" + ids[1]);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除训练", exact: true }).click();
    await p.waitForURL("**/#records");
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("group", { name: "动作进步，单位kg" }).waitFor();
    assert.deepEqual(await labels("exercise"), [
      "2026-09-28，10 kg",
      "2026-10-16，35 kg",
    ]);
    assert.deepEqual(await labels("frequency"), [
      "2026-09-21，0 次",
      "2026-09-28，1 次",
      "2026-10-05，0 次",
      "2026-10-12，1 次",
    ]);
    assert.deepEqual(await labels("weight"), [
      "2026-10-01，72 kg",
      "2026-10-16，70 kg",
    ]);
    assert.ok(!(await p.locator("main").innerHTML()).includes("NaN"));
  } finally {
    await t.close();
  }
});

test("验收：放弃草稿失败后可继续原草稿，重试不会误删", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    const before = await dbState(p);
    await abortWrites(p);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "放弃草稿", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "visible" });
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await p
      .getByRole("button", { name: "继续未完成训练", exact: true })
      .click();
    assert.equal(await p.getByLabel("杠铃卧推 第1组重量").inputValue(), "20");
    assert.deepEqual(await dbState(p), before);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.savedPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await saved(p);
    assert.deepEqual((await dbState(p)).workouts, before.workouts);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "放弃草稿", exact: true }).click();
    await p.waitForURL("**/#plan");
    assert.equal((await dbState(p)).workouts.length, 0);
  } finally {
    await t.close();
  }
});
