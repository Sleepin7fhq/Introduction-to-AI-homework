import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, record } from "./helpers.mjs";
test("阶段4：真实记录驱动图表、点选与范围切换", async () => {
  const t = await setup();
  try {
    const p = t.page;
    await record(p);
    await p.getByRole("button", { name: "完成训练", exact: true }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("group", { name: "动作进步，单位kg" }).waitFor();
    const dot = p.locator("g[data-kind=exercise]");
    assert.equal(await dot.count(), 1);
    assert.match(await dot.getAttribute("aria-label"), /20 kg/);
    await dot.focus();
    await p.keyboard.press("Enter");
    assert.match(await p.locator("dialog").textContent(), /12 次/);
    await p.getByRole("button", { name: "查看完整训练" }).click();
    await p.waitForURL("**/#detail/*");
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.getByRole("button", { name: "近 12 周", exact: true }).click();
    assert.equal(await p.locator("g[data-kind=frequency]").count(), 12);
    await p.locator("g[data-kind=frequency]").last().click();
    await p.waitForURL("**/#records");
    assert.match(await p.locator("main").textContent(), /杠铃卧推/);
    await p.getByRole("link", { name: "进步", exact: true }).click();
    await p.locator("#trend-exercise").selectOption("pushup");
    assert.equal(await p.locator("g[data-kind=exercise]").count(), 0);
    assert.ok(!(await p.locator("main").innerHTML()).includes("NaN"));
  } finally {
    await t.close();
  }
});
