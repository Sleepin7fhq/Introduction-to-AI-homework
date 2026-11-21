import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { setup, dbState, saved } from "./helpers.mjs";
import { legacyFixture } from "./legacy-fixture.mjs";

async function navigate(p, label) {
  await p.getByRole("link", { name: label, exact: true }).click();
}
async function rawState(p, data) {
  await p.evaluate(async (data) => {
    const { openStore } = await import("/store.js");
    const db = await openStore();
    await new Promise((resolve, reject) => {
      const tx = db.transaction("state", "readwrite");
      tx.objectStore("state").put(data, "main");
      tx.oncomplete = resolve;
      tx.onabort = reject;
    });
  }, data);
}

test("新版流程：计划自定义动作 → 记录确认与临时修改 → 陪练打卡续练 → 庆祝与真实统计", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByLabel("杠铃卧推", { exact: false }).check();
    await p.getByLabel("俯卧撑", { exact: false }).check();
    await p.locator(".plan-custom summary").click();
    await p.getByLabel("计划动作名称").fill("弹力带划船");
    await p.getByLabel("动作部位").selectOption("背");
    await p.getByRole("button", { name: "加入清单", exact: true }).click();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    const plan = (await dbState(p)).plan;
    assert.equal(plan.flatMap((x) => x.exerciseIds).length, 3);
    await navigate(p, "记录");
    assert.match(await p.locator(".daily-plan").textContent(), /弹力带划船/);
    assert.equal((await dbState(p)).workouts.length, 0);
    await p
      .getByRole("button", { name: "确认今天的训练", exact: true })
      .click();
    await p
      .getByRole("heading", { name: "今天，按这个练？", exact: true })
      .waitFor();
    assert.equal((await dbState(p)).workouts[0].phase, "prepare");
    await p.getByRole("button", { name: "移除俯卧撑", exact: true }).click();
    await p
      .getByRole("button", { name: "移除弹力带划船", exact: true })
      .click();
    assert.deepEqual((await dbState(p)).plan, plan);
    await p.reload();
    assert.equal(await p.locator(".exercise").count(), 1);
    assert.equal(await p.locator(".coach").count(), 0);
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    await p.locator(".coach").waitFor();
    assert.equal((await dbState(p)).workouts[0].phase, "active");
    await p
      .getByRole("button", { name: "完成杠铃卧推第1组", exact: true })
      .click();
    assert.match(await p.locator("#toast").textContent(), /先填好/);
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].done,
      false,
    );
    await p.getByLabel("杠铃卧推 第1组次数").fill("1.5");
    await p.getByRole("button", { name: "收起陪练", exact: true }).click();
    await p.getByRole("button", { name: "开启陪练", exact: true }).click();
    assert.equal(await p.getByLabel("杠铃卧推 第1组次数").inputValue(), "1.5");
    await p.getByLabel("杠铃卧推 第1组重量").fill("25");
    await p.getByLabel("杠铃卧推 第1组次数").fill("10");
    await saved(p);
    await p
      .getByRole("button", { name: "完成杠铃卧推第1组", exact: true })
      .click();
    await p
      .getByRole("button", { name: "取消打卡杠铃卧推第1组", exact: true })
      .waitFor();
    assert.match(await p.locator(".coach-count").textContent(), /1 \/ 1/);
    await p.reload();
    await p
      .getByRole("button", { name: "取消打卡杠铃卧推第1组", exact: true })
      .waitFor();
    assert.equal((await dbState(p)).workouts[0].status, "draft");
    const first = await p.locator("#coach-message").textContent();
    await p.getByRole("button", { name: "换一句", exact: true }).click();
    assert.notEqual(await p.locator("#coach-message").textContent(), first);
    await p.clock.install();
    // Re-render installs the interval under the controlled browser clock.
    await p.getByRole("button", { name: "收起陪练", exact: true }).click();
    await p.getByRole("button", { name: "开启陪练", exact: true }).click();
    const second = await p.locator("#coach-message").textContent();
    await p.clock.runFor(20001);
    assert.notEqual(await p.locator("#coach-message").textContent(), second);
    await p.getByLabel("杠铃卧推 第1组次数").fill("11");
    await saved(p);
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].done,
      false,
    );
    assert.match(await p.locator(".coach-count").textContent(), /0 \/ 1/);
    await p
      .getByRole("button", { name: "完成杠铃卧推第1组", exact: true })
      .click();
    await p
      .getByRole("button", { name: "取消打卡杠铃卧推第1组", exact: true })
      .waitFor();
    await mkdir("test-results", { recursive: true });
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
    await p.screenshot({
      path: "test-results/training-coach.png",
      fullPage: true,
    });
    await p.getByRole("button", { name: "完成训练", exact: true }).dblclick();
    await p.waitForURL("**/#detail/*");
    await p
      .getByRole("heading", { name: "今天，练了！", exact: true })
      .waitFor();
    assert.match(
      await p.locator(".celebration-stats").textContent(),
      /1个动作1组练习1本周训练/,
    );
    await p.emulateMedia({ reducedMotion: "reduce" });
    assert.equal(
      await p
        .locator(".confetti")
        .evaluate((el) => getComputedStyle(el).display),
      "none",
    );
    await p.screenshot({
      path: "test-results/training-celebration.png",
      fullPage: true,
    });
    assert.equal((await dbState(p)).workouts.length, 1);
    await p.getByRole("link", { name: "编辑训练", exact: true }).click();
    await p.getByLabel("杠铃卧推 第1组重量").fill("30");
    await p.getByRole("button", { name: "保存修改", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    assert.equal(await p.locator(".celebration").count(), 0);
    await navigate(p, "进步");
    assert.match(
      await p.getByRole("group", { name: /动作进步，单位kg/ }).textContent(),
      /30 kg/,
    );
    assert.deepEqual((await dbState(p)).plan, plan);
  } finally {
    await t.close();
  }
});

test("新版身体指标：独立填写、重复日期取消/更新、最新值、恢复和删除", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await navigate(p, "我的");
    await p.getByRole("button", { name: "记录身体指标", exact: true }).click();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.match(await p.locator(".modal-error").textContent(), /至少一项/);
    await p.getByLabel("测量日期").fill("2026-01-01");
    await p.getByLabel("体重 · kg", { exact: true }).fill("70");
    await p.getByLabel("体脂率 · %").fill("20");
    await p.getByLabel("腰围 · cm").fill("80");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    await p.getByRole("button", { name: "记录身体指标", exact: true }).click();
    await p.getByLabel("测量日期").fill("2026-01-02");
    await p.getByLabel("体脂率 · %").fill("19");
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    await p.reload();
    assert.match(
      await p.locator(".body-metrics").textContent(),
      /70kg2026-01-01.*19%2026-01-02.*80cm2026-01-01/,
    );
    const before = await dbState(p);
    await p.getByRole("button", { name: "记录身体指标", exact: true }).click();
    await p.getByLabel("测量日期").fill("2026-01-01");
    assert.equal(
      await p.getByLabel("体重 · kg", { exact: true }).inputValue(),
      "70",
    );
    await p.getByLabel("腰围 · cm").fill("79");
    p.once("dialog", (d) => d.dismiss());
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.deepEqual(await dbState(p), before);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "保存", exact: true }).click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    const snapshot = await dbState(p);
    assert.equal(snapshot.weights[1].waist, 79);
    const downloadPromise = p.waitForEvent("download");
    await p.getByRole("button", { name: "导出备份", exact: true }).click();
    const download = await downloadPromise,
      path = await download.path();
    const { readFile } = await import("node:fs/promises");
    const payload = JSON.parse(await readFile(path, "utf8"));
    assert.equal(payload.backupVersion, 2);
    assert.deepEqual(payload.data, snapshot);
    await p.locator("#backup-file").setInputFiles(path);
    await p
      .getByRole("button", { name: "确认替换并恢复", exact: true })
      .click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    assert.deepEqual((await dbState(p)).weights, snapshot.weights);
    await mkdir("test-results", { recursive: true });
    await p.screenshot({
      path: "test-results/body-metrics.png",
      fullPage: true,
    });
    await navigate(p, "进步");
    await p.getByRole("button", { name: "全部", exact: true }).click();
    assert.equal(
      await p.locator('[data-kind="weight"].chart-point').count(),
      1,
    );
    await p.getByRole("link", { name: "管理体重记录", exact: false }).click();
    const row = p.locator(".settings-row").filter({ hasText: "19" });
    p.once("dialog", (d) => d.accept());
    await row.getByRole("button", { name: "删除", exact: true }).click();
    assert.equal((await dbState(p)).weights.length, 1);
    assert.equal((await dbState(p)).weights[0].value, 70);
  } finally {
    await t.close();
  }
});

test("新版升级：实际旧 IndexedDB 和旧备份恢复，升级中止保留原数据", async () => {
  const t = await setup();
  try {
    const p = t.page,
      old = legacyFixture();
    await rawState(p, old);
    await p.reload();
    await p.getByRole("button", { name: "继续训练", exact: false }).waitFor();
    let s = await dbState(p);
    assert.equal(s.version, 2);
    assert.equal(s.revision, 9);
    assert.equal(s.workouts[0].exercises[0].sets[0].weight, 20);
    assert.equal(s.workouts[1].phase, "active");
    assert.equal(s.weights[0].value, 70);
    await navigate(p, "我的");
    await p
      .locator("#backup-file")
      .setInputFiles({
        name: "legacy.json",
        mimeType: "application/json",
        buffer: Buffer.from(
          JSON.stringify({
            app: "today-fit",
            backupVersion: 1,
            exportedAt: "2026-01-03T10:00:00Z",
            data: old,
          }),
        ),
      });
    await p
      .getByRole("button", { name: "确认替换并恢复", exact: true })
      .click();
    await p.locator("dialog").waitFor({ state: "hidden" });
    assert.equal((await dbState(p)).version, 2);
    await rawState(p, old);
    await p.addInitScript(() => {
      const original = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const request = original.apply(this, args);
        this.transaction.abort();
        return request;
      };
    });
    await p.reload();
    await p
      .getByRole("heading", { name: "暂时无法读取数据", exact: true })
      .waitFor();
    assert.deepEqual(await dbState(p), old);
  } finally {
    await t.close();
  }
});

test("新版：取消计划不保存新动作，开始/完成写入失败不伪造成功", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.locator(".plan-custom summary").click();
    await p.getByLabel("计划动作名称").fill("未保存动作");
    await p.getByRole("button", { name: "加入清单", exact: true }).click();
    await p.getByRole("button", { name: "取消", exact: true }).click();
    assert.equal((await dbState(p)).customExercises.length, 0);
    await p.getByRole("button", { name: "开始训练", exact: true }).click();
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    assert.match(await p.locator("#toast").textContent(), /先添加/);
    await p.getByRole("button", { name: "添加动作", exact: true }).click();
    await p.getByRole("button", { name: "杠铃卧推 胸 · 负重训练" }).click();
    await p.getByLabel("杠铃卧推 第1组重量").fill("20");
    await p.getByLabel("杠铃卧推 第1组次数").fill("12");
    await saved(p);
    await p.evaluate(() => {
      window.originalPut = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.originalPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    await p.locator("[data-save]").filter({ hasText: "保存失败" }).waitFor();
    assert.equal((await dbState(p)).workouts[0].phase, "prepare");
    assert.equal(await p.locator(".coach").count(), 0);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.originalPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await saved(p);
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    await p.locator(".coach").waitFor();
    await p.evaluate(() => {
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.originalPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.locator("[data-save]").filter({ hasText: "保存失败" }).waitFor();
    assert.equal((await dbState(p)).workouts[0].status, "draft");
    assert.equal(await p.locator(".celebration").count(), 0);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.originalPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await saved(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    assert.equal((await dbState(p)).workouts[0].status, "complete");
  } finally {
    await t.close();
  }
});
