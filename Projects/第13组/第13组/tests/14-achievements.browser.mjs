import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile, mkdir } from "node:fs/promises";
import { setup, record, saved, dbState } from "./helpers.mjs";
async function seed(p, count) {
  await p.clock.setFixedTime(new Date("2026-10-17T12:00:00"));
  await p.evaluate(async (count) => {
    const m = await import("/model.js"),
      store = await import("/store.js");
    const db = await store.openStore(),
      s = await store.readState(db);
    for (let i = 0; i < count; i++) {
      const date = m.addDays("2026-09-01", i),
        w = m.newWorkout(date);
      Object.assign(w, {
        status: "complete",
        phase: "active",
        createdAt: date + "T12:00:00.000Z",
      });
      w.exercises = [m.newEntry(m.builtins[0])];
      Object.assign(w.exercises[0].sets[0], {
        weight: 20,
        reps: 10,
        done: true,
      });
      s.workouts.push(w);
    }
    await store.writeState(db, s, s.revision);
  }, count);
  await p.reload();
  await p.getByRole("button", { name: "开始训练", exact: true }).waitFor();
}
const badge = (p, id) => p.locator(`[data-achievement="${id}"]`);

test("成就：真实完成解锁双徽章，页面状态、刷新与跨环境备份恢复一致", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await seed(p, 9);
    await p.getByRole("link", { name: "我的", exact: true }).click();
    await p.getByRole("link", { name: "查看全部成就", exact: false }).click();
    await badge(p, "workouts-10").waitFor();
    assert.match(
      await badge(p, "workouts-10").textContent(),
      /未解锁.*9 \/ 10/s,
    );
    assert.match(
      await badge(p, "record-bench").textContent(),
      /未解锁.*20 kg/s,
    );
    await p.getByRole("link", { name: "计划", exact: true }).click();
    await record(p);
    await p.getByLabel("杠铃卧推 第1组重量").fill("25");
    await saved(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).dblclick();
    await p.waitForURL("**/#detail/*");
    const notice = p.getByRole("region", { name: "新成就已解锁" });
    await notice.waitFor();
    assert.match(await notice.textContent(), /解锁 2 枚/);
    assert.match(await notice.textContent(), /十次，起步成章/);
    assert.match(await notice.textContent(), /杠铃卧推 · 突破自己/);
    assert.equal(
      await notice.evaluate((el) => getComputedStyle(el).animationName),
      "achievement-appear",
    );
    await p.emulateMedia({ reducedMotion: "reduce" });
    assert.equal(
      await notice.evaluate((el) => getComputedStyle(el).animationName),
      "none",
    );
    assert.equal((await dbState(p)).workouts.length, 10);
    await mkdir("test-results", { recursive: true });
    await p.screenshot({ path: "test-results/achievement-unlock.png" });
    await p.getByRole("link", { name: "查看我的成就", exact: false }).click();
    await badge(p, "workouts-10").waitFor();
    assert.match(
      await badge(p, "workouts-10").textContent(),
      /已解锁.*10 \/ 10/s,
    );
    assert.match(
      await badge(p, "workouts-30").textContent(),
      /未解锁.*10 \/ 30/s,
    );
    assert.match(
      await badge(p, "record-bench").textContent(),
      /已解锁.*25 kg/s,
    );
    for (const width of [320, 390, 430, 768, 1280]) {
      await p.setViewportSize({ width, height: 844 });
      assert.ok(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
    }
    await p.setViewportSize({ width: 390, height: 844 });
    await p.screenshot({
      path: "test-results/achievements-390.png",
      fullPage: true,
    });
    await p.reload();
    await badge(p, "workouts-10").waitFor();
    assert.match(await badge(p, "record-bench").textContent(), /已解锁/);
    assert.equal(await p.locator(".achievement-notice").count(), 0);
    await p.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    await t.context.setOffline(true);
    await p.reload();
    await badge(p, "workouts-10").waitFor();
    assert.match(await badge(p, "record-bench").textContent(), /已解锁/);
    await t.context.setOffline(false);
    await p.getByRole("link", { name: "我的", exact: true }).click();
    const download = p.waitForEvent("download");
    await p.getByRole("button", { name: "导出备份", exact: true }).click();
    const buffer = await readFile(await (await download).path());
    const original = await dbState(p);
    assert.equal(original.version, 2);
    assert.equal(Object.hasOwn(original, "achievements"), false);
    const ctx = await t.browser.newContext();
    try {
      const other = await ctx.newPage();
      await other.goto(t.url + "/#settings");
      await other
        .locator("#backup-file")
        .setInputFiles({
          name: "achievements.json",
          mimeType: "application/json",
          buffer,
        });
      await other.getByRole("button", { name: "确认替换并恢复" }).click();
      await other.getByRole("status").filter({ hasText: "恢复完成" }).waitFor();
      await other
        .getByRole("link", { name: "查看全部成就", exact: false })
        .click();
      await badge(other, "workouts-10").waitFor();
      assert.match(
        await badge(other, "record-bench").textContent(),
        /已解锁.*25 kg/s,
      );
      assert.deepEqual(
        { ...(await dbState(other)), revision: 0 },
        { ...original, revision: 0 },
      );
    } finally {
      await ctx.close();
    }
    const last = original.workouts.at(-1);
    await p.goto(t.url + "/#edit/" + last.id);
    await p.getByLabel("杠铃卧推 第1组重量").fill("20");
    await p.getByRole("button", { name: "保存修改" }).click();
    await p.waitForURL("**/#detail/*");
    assert.equal(await p.locator(".achievement-notice").count(), 0);
    await p.goto(t.url + "/#achievements");
    await badge(p, "record-bench").waitFor();
    assert.match(await badge(p, "record-bench").textContent(), /未解锁/);
    await p.goto(t.url + "/#detail/" + last.id);
    p.once("dialog", (d) => d.accept());
    await p.getByRole("button", { name: "删除训练", exact: true }).click();
    await p.waitForURL("**/#records");
    await p.goto(t.url + "/#achievements");
    await badge(p, "workouts-10").waitFor();
    assert.match(
      await badge(p, "workouts-10").textContent(),
      /未解锁.*9 \/ 10/s,
    );
  } finally {
    await t.close();
  }
});

test("成就：30 次门槛仅在写入成功后提示，关闭与刷新不重复播放", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await seed(p, 29);
    await record(p);
    const before = await dbState(p);
    await p.evaluate(() => {
      window.originalPut = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = window.originalPut.apply(this, args);
        this.transaction.abort();
        return r;
      };
    });
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.locator("#save-error").waitFor({ state: "visible" });
    assert.equal(await p.locator(".achievement-notice").count(), 0);
    assert.deepEqual(await dbState(p), before);
    await p.evaluate(() => (IDBObjectStore.prototype.put = window.originalPut));
    await p.getByRole("button", { name: "重试保存", exact: true }).click();
    await saved(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.locator(".achievement-notice").waitFor();
    assert.match(
      await p.locator(".achievement-notice").textContent(),
      /解锁 1 枚.*三十次，坚持有形/s,
    );
    await p.getByRole("button", { name: "关闭成就提示", exact: true }).click();
    assert.equal(await p.locator(".achievement-notice").count(), 0);
    await p.reload();
    await p
      .getByRole("heading", { name: "训练完成，做得不错。", exact: true })
      .waitFor();
    assert.equal(await p.locator(".achievement-notice").count(), 0);
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("link", { name: "我的成就", exact: true }).click();
    await badge(p, "workouts-30").waitFor();
    assert.match(
      await badge(p, "workouts-30").textContent(),
      /已解锁.*30 \/ 30/s,
    );
    assert.match(await badge(p, "record-bench").textContent(), /未解锁/);
  } finally {
    await t.close();
  }
});
