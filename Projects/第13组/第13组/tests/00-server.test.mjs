import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "../server.mjs";

test("静态服务器：跨平台目录、资源类型和发布目录隔离", async () => {
  const directory = await mkdtemp(join(tmpdir(), "fitbuddy-server-"));
  const root = join(directory, "public");
  await mkdir(root);
  await writeFile(join(root, "index.html"), "<h1>FitBuddy</h1>");
  await writeFile(join(root, "app.js"), "export const ready = true;");
  await writeFile(join(directory, "private.txt"), "not public");
  const server = createServer(root);
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    const base = `http://127.0.0.1:${server.address().port}`;
    const page = await fetch(base);
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type"), /text\/html/);
    assert.equal(await page.text(), "<h1>FitBuddy</h1>");
    const script = await fetch(base + "/app.js");
    assert.equal(script.status, 200);
    assert.match(script.headers.get("content-type"), /javascript/);
    assert.equal(script.headers.get("x-content-type-options"), "nosniff");
    for (const path of ["/private.txt", "/package.json", "/.git/config", "/missing"]) {
      const response = await fetch(base + path);
      assert.equal(response.status, 404, path);
    }
    // Encoded slash is decoded by the server, after URL normalization.
    const traversal = await fetch(base + "/..%2fprivate.txt");
    assert.equal(traversal.status, 403);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  }
});
