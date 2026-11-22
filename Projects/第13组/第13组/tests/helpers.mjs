import { chromium } from "playwright";
import { createServer } from "../server.mjs";
export { chromium };
export async function setup(options = {}) {
  const server = createServer(options.publicRoot);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const url = `http://localhost:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch(browserOptions());
  } catch (e) {
    await new Promise((r) => server.close(r));
    throw e;
  }
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  await page.goto(url);
  return {
    server,
    url,
    browser,
    context,
    page,
    async close() {
      await browser.close();
      await new Promise((r) => server.close(r));
    },
  };
}
export async function dbState(page) {
  return page.evaluate(async () => {
    const m = await import("/store.js");
    return m.readState(await m.openStore());
  });
}
export async function saved(page) {
  await page.waitForFunction(
    () => document.querySelector("[data-save]")?.textContent === "已保存",
  );
}

export async function record(page) {
  await page.getByRole("button", { name: "开始训练" }).click();
  await page.getByRole("button", { name: "添加动作", exact: true }).click();
  await page.getByRole("button", { name: "杠铃卧推 胸 · 负重训练" }).click();
  await page.getByLabel("杠铃卧推 第1组重量").fill("20");
  await page.getByLabel("杠铃卧推 第1组次数").fill("12");
  await saved(page);
  await page
    .getByRole("button", { name: "确认并开始训练", exact: true })
    .click();
  await page.getByRole("button", { name: "完成训练", exact: true }).waitFor();
  await saved(page);
}

export function browserOptions() {
  return {
    headless: true,
    executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined,
  };
}
