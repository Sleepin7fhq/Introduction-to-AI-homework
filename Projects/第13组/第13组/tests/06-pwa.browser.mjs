import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, cp, readFile, writeFile, rm, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setup, record, dbState, saved } from "./helpers.mjs";
test("阶段6：安装资源、离线重开、离线录入与导出、资源更新不丢数据", async () => {
  const dir = await mkdtemp(join(tmpdir(), "today-fit-pwa-"));
  await cp(new URL("../public/", import.meta.url), dir, { recursive: true });
  const t = await setup({ publicRoot: dir });
  try {
    const p = t.page;
    await record(p);
    await p.waitForFunction(() => !!navigator.serviceWorker.controller);
    const original = await dbState(p);
    const manifest = await (
      await t.context.request.get(t.url + "/manifest.webmanifest")
    ).json();
    assert.equal(manifest.display, "standalone");
    for (const i of manifest.icons) {
      assert.equal(
        (
          await t.context.request.get(t.url + "/" + i.src.replace("./", ""))
        ).status(),
        200,
      );
    }
    await t.context.setOffline(true);
    await p.reload();
    assert.equal(await p.getByLabel("杠铃卧推 第1组次数").inputValue(), "12");
    await p.getByLabel("杠铃卧推 第1组次数").fill("15");
    await saved(p);
    await p.close();
    const reopened = await t.context.newPage();
    await reopened.goto(t.url + "/#plan");
    await reopened
      .getByRole("button", { name: "继续训练", exact: false })
      .click();
    assert.equal(
      await reopened.getByLabel("杠铃卧推 第1组次数").inputValue(),
      "15",
    );
    await reopened
      .getByRole("button", { name: "完成训练", exact: true })
      .click();
    await reopened.waitForURL("**/#detail/*");
    await reopened.getByRole("link", { name: "我的", exact: true }).click();
    const downloaded = reopened.waitForEvent("download");
    await reopened
      .getByRole("button", { name: "导出备份", exact: true })
      .click();
    const backup = await readFile(await (await downloaded).path());
    assert.equal(
      JSON.parse(backup).data.workouts[0].exercises[0].sets[0].reps,
      15,
    );
    await reopened.locator("#backup-file").setInputFiles({
      name: "offline-backup.json",
      mimeType: "application/json",
      buffer: backup,
    });
    await reopened.getByRole("button", { name: "确认替换并恢复" }).click();
    await reopened
      .getByRole("status")
      .filter({ hasText: "恢复完成" })
      .waitFor();
    assert.equal(
      (await dbState(reopened)).workouts[0].exercises[0].sets[0].reps,
      15,
    );
    for (const name of ["计划", "记录", "进步", "我的"]) {
      await reopened.getByRole("link", { name, exact: true }).click();
      await reopened.locator("h1").waitFor();
    }
    await t.context.setOffline(false);
    await writeFile(
      join(dir, "sw.js"),
      (await readFile(join(dir, "sw.js"), "utf8")).replace(
        /shell-v\d+/,
        "shell-test-v2",
      ),
    );
    await reopened.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      await reg.update();
    });
    await reopened
      .getByRole("button", { name: "更新应用", exact: true })
      .waitFor();
    const before = await dbState(reopened);
    await reopened
      .getByRole("button", { name: "更新应用", exact: true })
      .click();
    await reopened.waitForFunction(async () =>
      (await caches.keys()).includes("today-fit-shell-test-v2"),
    );
    await reopened.waitForFunction(
      () => !!document.querySelector("#offline-status"),
    );
    assert.deepEqual(await dbState(reopened), before);
    assert.equal(before.workouts[0].id, original.workouts[0].id);
  } finally {
    await t.close();
    await rm(dir, { recursive: true, force: true });
  }
});
test("阶段6：响应式页面、键盘弹窗、运行错误与视觉截图", async () => {
  const t = await setup();
  try {
    const p = t.page,
      errors = [];
    p.on("pageerror", (e) => errors.push(e.message));
    await mkdir(new URL("../test-results/", import.meta.url), {
      recursive: true,
    });
    for (const width of [320, 390, 430, 768, 1280]) {
      await p.setViewportSize({ width, height: 900 });
      for (const name of ["计划", "记录", "进步", "我的"]) {
        await p.getByRole("link", { name, exact: true }).click();
        assert.equal(
          await p.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          true,
          `${name} at ${width}`,
        );
      }
      await p.getByRole("link", { name: "计划", exact: true }).click();
      if (width === 390 || width === 1280)
        await p.screenshot({
          path: `test-results/plan-${width}.png`,
          fullPage: true,
        });
    }
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.keyboard.press("Escape");
    assert.equal(await p.locator("dialog").evaluate((e) => e.open), false);
    await p.setViewportSize({ width: 390, height: 844 });
    await record(p);
    assert.equal(
      await p.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await p.screenshot({ path: "test-results/editor-390.png", fullPage: true });
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("group", { name: "动作进步，单位kg" }).waitFor();
    await p.screenshot({
      path: "test-results/progress-390.png",
      fullPage: true,
    });
    await p.setViewportSize({ width: 1280, height: 900 });
    await p.getByRole("link", { name: "记录", exact: true }).click();
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("group", { name: "动作进步，单位kg" }).waitFor();
    await p.screenshot({
      path: "test-results/progress-1280.png",
      fullPage: true,
    });
    assert.deepEqual(errors, []);
  } finally {
    await t.close();
  }
});
