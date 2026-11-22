import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  setup,
  record,
  dbState,
  saved,
  chromium,
  browserOptions,
} from "./helpers.mjs";

test("完整回归：自定义自重动作、非法输入、休息与清空计划", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByRole("checkbox", { name: "设为休息日" }).check();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.ok((await dbState(p)).plan.some((x) => x.mode === "rest"));
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByRole("checkbox", { name: "设为休息日" }).uncheck();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.ok((await dbState(p)).plan.every((x) => x.mode === "unset"));
    await p.getByRole("button", { name: "开始训练", exact: false }).click();
    await p.getByRole("button", { name: "添加动作", exact: true }).click();
    await p
      .getByRole("button", { name: "创建自定义动作", exact: false })
      .click();
    const name = "<b>我的卷腹</b>";
    await p.getByLabel("动作名称").fill(name);
    await p.getByLabel("训练部位").selectOption("核心");
    await p.getByRole("checkbox", { name: "需要填写负重" }).uncheck();
    await p.getByRole("button", { name: "创建并添加" }).click();
    assert.equal(await p.locator(".exercise h2").textContent(), name);
    assert.equal(await p.locator(".exercise h2 b").count(), 0);
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    await p.getByLabel(name + " 第1组次数").fill("1.5");
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    assert.equal((await dbState(p)).workouts[0].status, "draft");
    await p.getByLabel(name + " 第1组次数").fill("15");
    await saved(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    const before = (await dbState(p)).workouts[0];
    assert.equal(before.exercises[0].sets[0].weight, null);
    await p.getByRole("link", { name: "计划", exact: true }).click();
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.getByRole("checkbox", { name: "胸", exact: true }).check();
    await p.getByRole("button", { name: "保存", exact: true }).click();
    assert.deepEqual((await dbState(p)).workouts[0], before);
    await p.getByRole("button", { name: "开始训练", exact: false }).click();
    await p.getByRole("button", { name: "添加动作", exact: true }).click();
    await p.getByLabel("搜索动作").fill(name);
    assert.equal(await p.locator(".exercise-choice").count(), 1);
    await p.getByRole("button", { name: "关闭弹窗" }).click();
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await p.getByRole("button", { name: "补录训练", exact: false }).click();
    p.once("dialog", (d) => d.dismiss());
    await p.getByRole("button", { name: "开始记录", exact: true }).click();
    await p.waitForURL("**/#edit/*");
    assert.equal(
      (await dbState(p)).workouts.filter((w) => w.status === "draft").length,
      1,
    );
  } finally {
    await t.close();
  }
});

test("完整回归：保存失败保留输入、重试、跨页面冲突拒绝", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    const original = await dbState(p);
    await p.evaluate(() => {
      window.originalPut = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.originalPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await p.getByLabel("杠铃卧推 第1组重量").fill("35");
    await p.locator("[data-save]").filter({ hasText: "保存失败" }).waitFor();
    assert.equal(await p.getByLabel("杠铃卧推 第1组重量").inputValue(), "35");
    assert.deepEqual(await dbState(p), original);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.originalPut));
    await p.getByRole("button", { name: "重试保存" }).click();
    await saved(p);
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].weight,
      35,
    );
    const other = await t.context.newPage();
    await other.goto(t.url + "/#settings");
    await other.getByRole("button", { name: "编辑目标" }).click();
    await other.getByLabel("每周训练次数").fill("4");
    await other.getByRole("button", { name: "保存", exact: true }).click();
    await other.locator("dialog").waitFor({ state: "hidden" });
    await p.getByLabel("杠铃卧推 第1组重量").fill("40");
    await p.locator("[data-save]").filter({ hasText: "保存失败" }).waitFor();
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].weight,
      35,
    );
    assert.equal((await dbState(p)).goals.weekly, 4);
  } finally {
    await t.close();
  }
});

test("完整回归：关闭整个浏览器进程后，同一用户目录保留记录", async () => {
  const t = await setup(),
    dir = await mkdtemp(join(tmpdir(), "today-fit-profile-"));
  let context;
  try {
    context = await chromium.launchPersistentContext(dir, browserOptions());
    let p = await context.newPage();
    await p.goto(t.url);
    await record(p);
    const original = await dbState(p);
    await context.close();
    context = null;
    context = await chromium.launchPersistentContext(dir, browserOptions());
    p = await context.newPage();
    await p.goto(t.url);
    await p.getByRole("button", { name: "继续训练", exact: false }).click();
    assert.equal(await p.getByLabel("杠铃卧推 第1组重量").inputValue(), "20");
    assert.deepEqual(await dbState(p), original);
  } finally {
    await context?.close();
    await t.close();
    await rm(dir, { recursive: true, force: true });
  }
});

test("完整回归：历史保存失败后取消，详情仍显示原记录", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    const id = (await dbState(p)).workouts[0].id;
    await p.getByRole("link", { name: "编辑训练" }).click();
    await p.getByLabel("杠铃卧推 第1组重量").fill("45");
    await p.evaluate(() => {
      const original = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = original.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await p.getByRole("button", { name: "保存修改" }).click();
    await p.locator("[data-save]").filter({ hasText: "保存失败" }).waitFor();
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "取消", exact: true }).click();
    await p.waitForURL("**/#records");
    await p.locator(`a[href="#detail/${id}"]`).click();
    await p.waitForURL("**/#detail/*");
    await p
      .getByRole("heading", { name: "训练完成，做得不错。", exact: true })
      .waitFor();
    assert.match(await p.locator("main").textContent(), /20 kg/);
    assert.equal(
      (await dbState(p)).workouts[0].exercises[0].sets[0].weight,
      20,
    );
  } finally {
    await t.close();
  }
});

test("完整回归：损坏的本地数据不能被当成首次使用并清空", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await p.evaluate(async () => {
      const { openStore } = await import("/store.js");
      const db = await openStore();
      await new Promise((resolve, reject) => {
        const tx = db.transaction("state", "readwrite");
        tx.objectStore("state").put(null, "main");
        tx.oncomplete = resolve;
        tx.onabort = reject;
      });
    });
    await p.reload();
    await p.getByRole("heading", { name: "暂时无法读取数据" }).waitFor();
    assert.equal(await dbState(p), null);
  } finally {
    await t.close();
  }
});
