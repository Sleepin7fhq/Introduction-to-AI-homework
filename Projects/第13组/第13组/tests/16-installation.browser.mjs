import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, record, dbState } from "./helpers.mjs";

test("手机安装：Manifest、图标安全区、离线直达与设备数据隔离", async () => {
  const t = await setup();
  try {
    const p = t.page;
    const manifest = await (
      await t.context.request.get(t.url + "/manifest.webmanifest")
    ).json();
    assert.equal(manifest.name, "今天练了吗");
    assert.equal(manifest.short_name, "今天练了吗");
    assert.equal(manifest.id, "./");
    assert.equal(manifest.scope, "./");
    assert.equal(manifest.start_url, "./#plan");
    assert.equal(manifest.display, "standalone");
    assert.equal(
      manifest.theme_color,
      await p.locator('meta[name="theme-color"]').getAttribute("content"),
    );
    assert.equal(
      await p
        .locator('meta[name="apple-mobile-web-app-title"]')
        .getAttribute("content"),
      manifest.name,
    );
    assert.equal(
      await p
        .locator('meta[name="apple-mobile-web-app-capable"]')
        .getAttribute("content"),
      "yes",
    );
    assert.ok(manifest.icons.some((i) => i.sizes === "192x192"));
    assert.ok(
      manifest.icons.some(
        (i) => i.sizes === "512x512" && i.purpose.includes("maskable"),
      ),
    );
    for (const icon of manifest.icons) {
      const result = await p.evaluate(async (icon) => {
        const image = new Image();
        image.src = icon.src;
        await image.decode();
        const canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(image, 0, 0);
        const { data } = ctx.getImageData(0, 0, image.width, image.height);
        let opaque = true,
          safe = true;
        for (let y = 0; y < image.height; y++)
          for (let x = 0; x < image.width; x++) {
            const i = (y * image.width + x) * 4;
            if (data[i + 3] !== 255) opaque = false;
            const foreground =
              data[i] !== data[0] ||
              data[i + 1] !== data[1] ||
              data[i + 2] !== data[2];
            if (
              foreground &&
              Math.hypot(x - image.width / 2, y - image.height / 2) >
                image.width * 0.4
            )
              safe = false;
          }
        return { size: `${image.width}x${image.height}`, opaque, safe };
      }, icon);
      assert.equal(result.size, icon.sizes);
      assert.equal(result.opaque, true);
      if (icon.purpose.includes("maskable"))
        assert.equal(result.safe, true, "图案位于系统裁剪安全圆内");
    }
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "我的", exact: true }).click();
    await p
      .getByText("离线已就绪 · 可断网打开和记录", { exact: true })
      .waitFor();
    await p
      .getByRole("button", { name: "查看安装与离线说明", exact: true })
      .click();
    assert.match(await p.locator("dialog").innerText(), /作为网页 App 打开/);
    assert.doesNotMatch(
      await p.locator("dialog").innerText(),
      /尚未发布到公网/,
    );
    await p.getByRole("button", { name: "知道了", exact: true }).click();
    const before = await dbState(p);
    await t.context.setOffline(true);
    await p.close();
    const offline = await t.context.newPage();
    for (const route of [
      "plan",
      "records",
      "progress",
      "settings",
      "achievements",
    ]) {
      await offline.goto(t.url + "/#" + route);
      await offline.locator("h1").waitFor();
      assert.deepEqual(
        await dbState(offline),
        before,
        `离线直达 ${route} 保留全部数据`,
      );
    }
    await offline.goto(t.url + "/#progress");
    await offline
      .getByRole("group", { name: "动作进步，单位kg", exact: true })
      .waitFor();
    assert.match(
      await offline
        .getByRole("group", { name: "动作进步，单位kg", exact: true })
        .locator(".chart-point")
        .getAttribute("aria-label"),
      /，20 kg$/,
    );
    const secondDevice = await t.browser.newContext();
    try {
      const other = await secondDevice.newPage();
      await other.goto(t.url);
      await other.locator("h1").waitFor();
      assert.equal(
        (await dbState(other)).workouts.length,
        0,
        "新设备不会自动读取原设备记录",
      );
    } finally {
      await secondDevice.close();
    }
    assert.deepEqual(await dbState(offline), before);
  } finally {
    await t.close();
  }
});
