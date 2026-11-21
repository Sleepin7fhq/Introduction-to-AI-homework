import assert from "node:assert/strict";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import {
  chromium,
  browserOptions,
  record,
  saved,
  dbState,
} from "./helpers.mjs";
const target = process.argv[2];
if (!target) throw new Error("用法：npm run test:deployment -- https://your-site.example");
const parsed = new URL(target);
if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash)
  throw new Error("请提供不含账号、查询参数或片段的 HTTPS 部署地址");
const url = parsed.href.replace(/\/$/, "");
await mkdir("test-results", { recursive: true });
const browser = await chromium.launch(browserOptions());
const report = { url, resources: [], checks: [] };
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  for (const name of [
    "index.html",
    "app.js",
    "styles.css",
    "model.js",
    "store.js",
    "sw.js",
    "manifest.webmanifest",
    "icon-192.png",
    "icon-512.png",
  ]) {
    const response = await context.request.get(url + "/" + name, {
      timeout: 30000,
    });
    assert.equal(response.status(), 200, name);
    assert.deepEqual(
      await response.body(),
      await readFile(new URL("../public/" + name, import.meta.url)),
      name + " 与本地发布内容一致",
    );
    report.resources.push({
      name,
      status: response.status(),
      type: response.headers()["content-type"],
      cache: response.headers()["cache-control"],
    });
  }
  assert.match(
    report.resources.find((r) => r.name === "manifest.webmanifest").type,
    /application\/manifest\+json/,
  );
  assert.match(
    report.resources.find((r) => r.name === "sw.js").cache,
    /no-cache/,
  );
  const page = await context.newPage(),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url);
  await page.locator("h1").waitFor();
  assert.equal(await page.evaluate(() => isSecureContext), true);
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  report.checks.push(
    "HTTPS 默认 TLS 校验通过，安全上下文与 Service Worker 已就绪",
  );
  const cdp = await context.newCDPSession(page);
  report.installability = await cdp.send("Page.getInstallabilityErrors");
  assert.deepEqual(report.installability.installabilityErrors, []);
  await record(page);
  await page.reload();
  assert.equal(await page.getByLabel("杠铃卧推 第1组次数").inputValue(), "12");
  await page.getByRole("button", { name: "完成训练", exact: true }).click();
  await page.waitForURL("**/#detail/*");
  const completed = await dbState(page);
  assert.equal(completed.workouts.length, 1);
  assert.equal(completed.workouts[0].status, "complete");
  await page.getByRole("link", { name: "进步", exact: true }).click();
  const chart = page.getByRole("group", {
    name: "动作进步，单位kg",
    exact: true,
  });
  await chart.waitFor();
  assert.match(
    await chart.locator(".chart-point").getAttribute("aria-label"),
    /，20 kg$/,
  );
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.playState !== "running"),
  );
  await page.screenshot({
    path: "test-results/live-progress-390.png",
    fullPage: true,
  });
  report.checks.push("线上逐组录入、刷新保存、完成训练与真实 20 kg 图表正确");
  for (const width of [320, 390, 430, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of [
      "plan",
      "records",
      "progress",
      "settings",
      "achievements",
    ]) {
      await page.goto(url + "/#" + route);
      await page.locator("h1").waitFor();
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        route + " @ " + width,
      );
    }
  }
  report.checks.push("5 种屏宽 × 5 页面无页面横向溢出");
  await context.setOffline(true);
  await page.close();
  const offline = await context.newPage();
  await offline.setViewportSize({ width: 390, height: 844 });
  for (const route of [
    "plan",
    "records",
    "progress",
    "settings",
    "achievements",
  ]) {
    await offline.goto(url + "/#" + route);
    await offline.locator("h1").waitFor();
    assert.deepEqual(await dbState(offline), completed);
  }
  await offline.goto(url + "/#plan");
  await offline.locator("h1").waitFor();
  await record(offline);
  await offline.getByLabel("杠铃卧推 第1组重量").fill("25");
  await saved(offline);
  await offline.reload();
  assert.equal(
    await offline.getByLabel("杠铃卧推 第1组重量").inputValue(),
    "25",
  );
  await offline.getByRole("button", { name: "完成训练", exact: true }).click();
  await offline.waitForURL("**/#detail/*");
  await offline.getByRole("link", { name: "进步", exact: true }).click();
  await offline
    .getByRole("group", { name: "动作进步，单位kg", exact: true })
    .getByRole("button", { name: /，25 kg$/ })
    .waitFor();
  assert.deepEqual(
    await offline
      .getByRole("group", { name: "动作进步，单位kg", exact: true })
      .locator(".chart-point")
      .evaluateAll((nodes) =>
        nodes.map((n) => n.getAttribute("aria-label").split("，")[1]),
      ),
    ["20 kg", "25 kg"],
  );
  report.checks.push(
    "断网关闭重开全部模块、离线新增并保存 25 kg 训练、图表重算通过",
  );
  await offline.getByRole("link", { name: "我的", exact: true }).click();
  const download = offline.waitForEvent("download");
  await offline.getByRole("button", { name: "导出备份", exact: true }).click();
  const backup = await readFile(await (await download).path());
  const latest = await dbState(offline);
  const second = await browser.newContext();
  const other = await second.newPage();
  await other.goto(url);
  await other.locator("h1").waitFor();
  assert.equal((await dbState(other)).workouts.length, 0);
  await other.getByRole("link", { name: "我的", exact: true }).click();
  await other
    .locator("#backup-file")
    .setInputFiles({
      name: "live-test.json",
      mimeType: "application/json",
      buffer: backup,
    });
  await other
    .getByRole("button", { name: "确认替换并恢复", exact: true })
    .click();
  await other.getByRole("status").filter({ hasText: "恢复完成" }).waitFor();
  assert.deepEqual((await dbState(other)).workouts, latest.workouts);
  report.checks.push(
    "离线导出、独立设备空库、恢复后训练一致；全程仅测试浏览器数据",
  );
  assert.deepEqual(errors, []);
  report.checks.push("无页面 JavaScript 异常");
  report.result = "passed";
  await writeFile(
    "test-results/live-verification.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
