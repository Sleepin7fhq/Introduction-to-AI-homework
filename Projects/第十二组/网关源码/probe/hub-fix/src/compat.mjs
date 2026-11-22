import { WebSocket } from "ws";
import { DshBrowserAuth } from "./dsh-browser-auth.mjs";
import { upstreamRpc } from "./upstream.mjs";

// 常驻 workspace/follow 流：保持一条到 DSH /api/remote.mux 的 WS，增量合并
// baseline/upsert/remove/order/archived/pinned，避免每次归属刷新都开一条短命 WS。
// 失败后自动重建，保留 5s 超时保护。
class WorkspaceFollowClient {
  constructor(config) {
    this.config = config;
    this.items = [];
    this.archivedSessionIds = [];
    this.pinnedSessionIds = [];
    this.ready = false;
    this.socket = null;
    this.waiters = [];
    this.lastError = null;
  }

  _apply(value) {
    if (!value) return;
    if (value.type === "baseline" && value.value) {
      if (Array.isArray(value.value.items)) this.items = value.value.items;
      if (Array.isArray(value.value.archivedSessionIds)) this.archivedSessionIds = value.value.archivedSessionIds;
      if (Array.isArray(value.value.pinnedSessionIds)) this.pinnedSessionIds = value.value.pinnedSessionIds;
      this.ready = true;
      this._flush();
    } else if (value.type === "upsert" && value.workspace && typeof value.workspace.workspaceId === "string") {
      const idx = this.items.findIndex(w => w.workspaceId === value.workspace.workspaceId);
      if (idx >= 0) this.items[idx] = value.workspace; else this.items.push(value.workspace);
    } else if (value.type === "remove" && value.workspaceId) {
      this.items = this.items.filter(w => w.workspaceId !== value.workspaceId);
    } else if (value.type === "order" && Array.isArray(value.workspaceIds)) {
      const byId = new Map(this.items.map(w => [w.workspaceId, w]));
      const ordered = value.workspaceIds.map(id => byId.get(id)).filter(Boolean);
      if (ordered.length) this.items = ordered;
    } else if (value.type === "archived" && Array.isArray(value.archivedSessionIds)) {
      this.archivedSessionIds = value.archivedSessionIds;
    } else if (value.type === "pinned" && Array.isArray(value.pinnedSessionIds)) {
      this.pinnedSessionIds = value.pinnedSessionIds;
    }
  }

  _flush() { for (const w of this.waiters.splice(0)) w(); }

  _teardown(error) {
    this.lastError = error || new Error("workspace/follow closed");
    this.socket = null;
    this.ready = false;
    this._flush();
  }

  _connect() {
    const upstream = new URL(this.config.upstream);
    upstream.protocol = "ws:";
    upstream.pathname = "/api/remote.mux";
    return new DshBrowserAuth(this.config).cookieHeader().then(cookie => new Promise((resolve, reject) => {
      const socket = new WebSocket(upstream, { headers: { cookie, origin: new URL(this.config.upstream).origin }, handshakeTimeout: 5000 });
      let settled = false;
      const deadline = setTimeout(() => { if (!settled) { settled = true; socket.terminate(); reject(new Error("workspace/follow connect timeout")); } }, 5000);
      socket.once("open", () => {
        clearTimeout(deadline);
        if (settled) return;
        settled = true;
        socket.send(JSON.stringify({ type: "open", streamId: "ws-follow", endpoint: "workspace/follow", payload: { args: {} } }));
        // 不因这条常驻流而阻止进程退出（CLI selftest 等短命进程需要）。
        try { socket._socket?.unref?.(); } catch {}
        resolve(socket);
      });
      socket.once("error", e => { clearTimeout(deadline); if (!settled) { settled = true; reject(e || new Error("workspace/follow connect failed")); } });
    }));
  }

  _attach(socket) {
    socket.on("message", data => {
      let frame;
      try { frame = JSON.parse(data.toString("utf8")); } catch { return; }
      if (frame.streamId !== "ws-follow") return;
      if (frame.type === "error") { this._teardown(new Error("workspace/follow stream error")); return; }
      if (frame.type === "item") this._apply(frame.value);
    });
    socket.once("error", () => this._teardown(new Error("workspace/follow socket error")));
    socket.once("close", () => this._teardown(new Error("workspace/follow socket closed")));
  }

  async baseline(timeoutMs = 5000) {
    if (this.ready) {
      return { items: this.items.slice(), archivedSessionIds: this.archivedSessionIds.slice(), pinnedSessionIds: this.pinnedSessionIds.slice() };
    }
    if (!this.socket) {
      const socket = await this._connect();
      this.socket = socket;
      this._attach(socket);
    }
    await new Promise(resolve => {
      const timer = setTimeout(resolve, timeoutMs);
      this.waiters.push(() => { clearTimeout(timer); resolve(); });
    });
    if (this.ready) {
      return { items: this.items.slice(), archivedSessionIds: this.archivedSessionIds.slice(), pinnedSessionIds: this.pinnedSessionIds.slice() };
    }
    throw this.lastError || new Error("workspace/follow timed out");
  }

  close() { if (this.socket) { this.socket.terminate(); this.socket = null; this.ready = false; } }
}

const clients = new Map();

function followClient(config) {
  let client = clients.get(config.upstream);
  if (!client) {
    client = new WorkspaceFollowClient(config);
    clients.set(config.upstream, client);
  }
  client.config = config;
  return client;
}

export async function workspaceBaseline(config) {
  return followClient(config).baseline();
}

export async function compatibilityReport(config) {
  const startedAt = Date.now();
  const checks = [];
  const add = (name, ok, detail = "") => checks.push({ name, ok, detail });
  try {
    const sessions = await upstreamRpc(config, "session/list", { args: { _request: {} } });
    add("session/list", Array.isArray(sessions?.items), `${sessions?.items?.length ?? 0} sessions`);
  } catch (error) { add("session/list", false, error.message); }
  try {
    const workspaces = await workspaceBaseline(config);
    add("workspace/follow", true, `${workspaces.items.length} workspaces`);
  } catch (error) { add("workspace/follow", false, error.message); }
  return { ok: checks.every(check => check.ok), durationMs: Date.now() - startedAt, checks };
}
