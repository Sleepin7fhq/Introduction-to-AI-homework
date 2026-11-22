import { initialState, clone, validateState } from "./model.js";
export class ConflictError extends Error {
  constructor() {
    super("数据已在另一个页面更新，请先重新加载，避免覆盖新记录。");
    this.name = "ConflictError";
  }
}
export async function openStore() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open("today-fit", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("state");
    r.onsuccess = () => {
      r.result.onversionchange = () => r.result.close();
      resolve(r.result);
    };
    r.onerror = () => reject(r.error);
    r.onblocked = () => reject(new Error("请关闭其他旧版本页面后重试"));
  });
}
export function readState(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("state", "readonly");
    const r = tx.objectStore("state").get("main");
    tx.oncomplete = () =>
      resolve(r.result === undefined ? initialState() : r.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("读取事务被中止"));
  });
}
export function writeState(db, state, expected) {
  return new Promise((resolve, reject) => {
    validateState(state);
    let conflict = false;
    const tx = db.transaction("state", "readwrite");
    const store = tx.objectStore("state");
    const r = store.get("main");
    const next = clone(state);
    r.onsuccess = () => {
      // Check and replace within one transaction, so stale tabs cannot win a race.
      if ((r.result?.revision ?? 0) !== expected) {
        conflict = true;
        tx.abort();
        return;
      }
      next.revision = expected + 1;
      store.put(next, "main");
    };
    tx.oncomplete = () => resolve(next);
    tx.onabort = () =>
      reject(
        conflict
          ? new ConflictError()
          : tx.error || new Error("保存事务被中止"),
      );
    tx.onerror = () => {};
  });
}
