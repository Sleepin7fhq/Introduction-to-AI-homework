import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { setup, dbState, saved } from "./helpers.mjs";

test("视觉改版：响应式层级、徽章网格、输入焦点与原数据保持", async () => {
  const t = await setup();
  try {
    const p = t.page,
      errors = [];
    p.on("pageerror", (e) => errors.push(e.message));
    await p.clock.setFixedTime(new Date("2026-10-17T12:00:00"));
    await p.evaluate(async () => {
      const m = await import("/model.js"),
        store = await import("/store.js");
      const db = await store.openStore(),
        s = await store.readState(db);
      s.plan[5] = {
        mode: "train",
        parts: ["胸", "腿"],
        exerciseIds: ["bench", "squat"],
      };
      s.goals = { weekly: 3, targetWeight: 65 };
      for (let i = 0; i < 10; i++) {
        const date = m.addDays("2026-10-07", i),
          w = m.newWorkout(date);
        Object.assign(w, {
          status: "complete",
          phase: "active",
          createdAt: date + "T12:00:00.000Z",
        });
        w.exercises = [m.newEntry(m.builtins[0])];
        Object.assign(w.exercises[0].sets[0], {
          weight: 20 + i,
          reps: 10,
          done: true,
        });
        s.workouts.push(w);
      }
      const stamp = new Date().toISOString();
      s.weights = [
        {
          id: m.uid(),
          date: "2026-10-17",
          value: 68.5,
          bodyFat: 18.5,
          waist: 78,
          createdAt: stamp,
          updatedAt: stamp,
        },
      ];
      await store.writeState(db, s, s.revision);
    });
    await p.reload();
    await p.getByRole("heading", { name: "未来七天", exact: true }).waitFor();
    const before = await dbState(p);
    await mkdir("test-results", { recursive: true });
    for (const width of [320, 390, 430, 768, 1280]) {
      await p.setViewportSize({ width, height: 900 });
      for (const route of [
        "plan",
        "records",
        "progress",
        "settings",
        "achievements",
      ]) {
        await p.goto(t.url + "/#" + route);
        await p.locator("h1").waitFor();
        await p.waitForFunction(() =>
          document.getAnimations().every((a) => a.playState !== "running"),
        );
        assert.ok(
          await p.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          `${route} @ ${width}`,
        );
        if (route === "plan" && width <= 800) {
          const today = await p.locator(".today-card").boundingBox();
          const progress = await p.locator(".progress-card").boundingBox();
          assert.ok(
            progress.y > today.y + today.height,
            "手机优先显示训练安排，随后显示周目标",
          );
        }
        if (route === "achievements") {
          const columns = await p
            .locator(".achievement-grid")
            .first()
            .evaluate(
              (el) =>
                getComputedStyle(el).gridTemplateColumns.split(" ").length,
            );
          assert.equal(columns, width < 360 ? 1 : width >= 1100 ? 3 : 2);
        }
        if (width === 390 || width === 1280) {
          await p.screenshot({
            path: `test-results/refresh-${route}-${width}.png`,
            fullPage: true,
          });
        }
      }
    }
    assert.deepEqual(
      await dbState(p),
      before,
      "界面浏览和布局切换不得更改任何业务数据",
    );
    await p.setViewportSize({ width: 390, height: 844 });
    await p.getByRole("link", { name: "计划", exact: true }).click();
    await p.getByRole("button", { name: "编辑安排", exact: true }).click();
    await p.screenshot({ path: "test-results/refresh-plan-dialog.png" });
    await p.getByRole("button", { name: "取消", exact: true }).click();
    assert.deepEqual(await dbState(p), before);
    await p.getByRole("button", { name: "开始训练", exact: true }).click();
    await p
      .getByRole("button", { name: "确认并开始训练", exact: true })
      .click();
    await p.getByRole("heading", { name: "训练进行中", exact: true }).waitFor();
    await saved(p);
    const input = p.getByLabel("杠铃卧推 第1组重量");
    await input.fill("25");
    await saved(p);
    assert.equal(
      await input.evaluate((el) => document.activeElement === el),
      true,
    );
    assert.equal(
      await input.evaluate((el) => getComputedStyle(el).fontSize),
      "16px",
    );
    await p.getByLabel("杠铃卧推 第1组次数").fill("12");
    await saved(p);
    await p.screenshot({
      path: "test-results/refresh-editor-390.png",
      fullPage: true,
    });
    await p.emulateMedia({ reducedMotion: "reduce" });
    await p.getByRole("button", { name: "返回", exact: true }).click();
    await p.waitForURL("**/#records");
    assert.equal(
      await p
        .locator(".main")
        .evaluate((el) => getComputedStyle(el).animationName),
      "none",
    );
    assert.deepEqual(errors, []);
  } finally {
    await t.close();
  }
});
