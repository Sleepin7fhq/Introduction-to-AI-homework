import { test } from "node:test";
import assert from "node:assert/strict";
import { setup, dbState } from "./helpers.mjs";
test("阶段1：导航、真实存储、冲突、事务中止和窄屏", async () => {
  const t = await setup();
  try {
    for (const width of [320, 390, 430, 768, 1280]) {
      await t.page.setViewportSize({ width, height: 844 });
      for (const label of ["计划", "记录", "进步", "我的"]) {
        await t.page.getByRole("link", { name: label, exact: true }).click();
        assert.equal(
          await t.page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          true,
        );
      }
    }
    await t.page.evaluate(async () => {
      const { openStore, readState, writeState } = await import("/store.js");
      const db = await openStore();
      const s = await readState(db);
      s.goals.weekly = 3;
      await writeState(db, s, s.revision);
    });
    await t.page.reload();
    assert.equal((await dbState(t.page)).goals.weekly, 3);
    const conflict = await t.page.evaluate(async () => {
      const m = await import("/store.js");
      const db = await m.openStore();
      const a = await m.readState(db);
      await m.writeState(
        db,
        { ...a, goals: { ...a.goals, weekly: 4 } },
        a.revision,
      );
      try {
        await m.writeState(db, a, a.revision);
        return false;
      } catch (e) {
        return e.name === "ConflictError";
      }
    });
    assert.equal(conflict, true);
    assert.equal((await dbState(t.page)).goals.weekly, 4);
    const aborted = await t.page.evaluate(async () => {
      const m = await import("/store.js");
      const db = await m.openStore();
      const s = await m.readState(db);
      const original = IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put = function (...args) {
        const r = original.apply(this, args);
        this.transaction.abort();
        return r;
      };
      try {
        await m.writeState(
          db,
          { ...s, goals: { ...s.goals, weekly: 9 } },
          s.revision,
        );
        return false;
      } catch {
        return (await m.readState(db)).goals.weekly === 4;
      } finally {
        IDBObjectStore.prototype.put = original;
      }
    });
    assert.equal(aborted, true);
  } finally {
    await t.close();
  }
});
