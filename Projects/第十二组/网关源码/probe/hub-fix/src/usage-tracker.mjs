import fs from "node:fs";
import path from "node:path";

// Agent 用量记账（按网关用户归因）。
// v1 为诚实估算：输入按消息字符估算（每 4 字符 ≈ 1 token），输出按 2× 估算；
// 后续可接入 WS usage 帧做精确记账（见 server.mjs 的 TODO）。
// 配额与单价是演示占位值，可在本文件修改。

const DAY_MS = 24 * 60 * 60 * 1000;
export const QUOTA_TOKENS_PER_DAY = 500000;            // 默认每人每天 50 万 token
export const COST_CNY_PER_MILLION_TOKENS = 4;          // 占位单价：每百万 token 4 元

export function usagePath(home) { return path.join(home, "logs", "usage.jsonl"); }

function dayKey(t) {
  const d = new Date(t);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function createUsageTracker(home) {
  const file = usagePath(home);
  return {
    // entry: { user, kind: "prompt"|"denied", sessionId, workspaceId, inputTokens, outputTokens }
    record(entry) {
      const line = { at: entry.at || new Date().toISOString(), ...entry };
      delete line.at2;
      fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
      fs.appendFileSync(file, JSON.stringify(line) + "\n", { mode: 0o600 });
    },
    query({ days = 7 } = {}) {
      const dayKeys = [];
      for (let i = 0; i < days; i++) dayKeys.push(dayKey(Date.now() - i * DAY_MS));
      const since = Date.now() - days * DAY_MS;
      const byUser = new Map(); // user -> day -> row
      if (fs.existsSync(file)) {
        const lines = fs.readFileSync(file, "utf8").split("\n");
        for (const line of lines) {
          let e;
          try { e = JSON.parse(line); } catch { continue; }
          const t = Date.parse(e.at);
          if (!Number.isFinite(t) || t < since) continue;
          if (typeof e.user !== "string" || !e.user) continue;
          const d = dayKey(t);
          let byDay = byUser.get(e.user);
          if (!byDay) { byDay = {}; byUser.set(e.user, byDay); }
          let row = byDay[d];
          if (!row) { row = { user: e.user, day: d, prompts: 0, denied: 0, inputTokens: 0, outputTokens: 0 }; byDay[d] = row; }
          if (e.kind === "prompt") row.prompts += 1;
          else if (e.kind === "denied") row.denied += 1;
          row.inputTokens += e.inputTokens || 0;
          row.outputTokens += e.outputTokens || 0;
        }
      }
      const rows = [];
      for (const byDay of byUser.values()) for (const row of Object.values(byDay)) rows.push(row);
      rows.sort((a, b) => (a.user < b.user ? -1 : a.user > b.user ? 1 : a.day < b.day ? -1 : 1));
      return { days: dayKeys, rows, quotaTokensPerDay: QUOTA_TOKENS_PER_DAY, costCnyPerMillionTokens: COST_CNY_PER_MILLION_TOKENS };
    }
  };
}
