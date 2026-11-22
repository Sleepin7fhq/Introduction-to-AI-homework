// Regenerate every demo payload from one live session id, so the demo script never
// carries a hard-coded session that has since gone stale.
//
//   node demo\make-payloads.mjs <sessionId>
//
// Writes UTF-8 without BOM. PowerShell 5.1 mangles inline JSON on the command line
// (see report §6.9), so every request body in the demo MUST come from a file via
// curl.exe --data-binary "@file".
import fs from "node:fs";
import path from "node:path";

const sid = process.argv[2];
if (!sid) {
  console.error("usage: node demo/make-payloads.mjs <sessionId>");
  process.exit(1);
}

// Workspace ids rotate: every time the gateway provisions a member workspace through
// upstream workspace/create (e.g. when it starts before DSH is ready, so the ownership
// table is empty), upstream mints a NEW workspaceId for the same path and the previous
// id becomes stale (sharing it answers 409 "上游工作区已变更"). So never hard-code it —
// resolve the current bob workspace id from the admin API unless argv[3] overrides it.
async function resolveBobWorkspace() {
  if (process.argv[3]) return process.argv[3];
  const { login, adminApi } = await import("../probe/lib-hub.mjs");
  const admin = await login("admin", "AdminPass!2026");
  const w = await adminApi(admin.s, "/__teamhub/api/workspaces");
  const bob = (w.json || []).find((x) => x.owner === "bob");
  if (!bob) throw new Error("cannot resolve bob workspace id (is the gateway up?)");
  return bob.workspaceId;
}

const BOB_WS = await resolveBobWorkspace();
console.log("bob workspace:", BOB_WS);
const outDir = path.join(process.cwd(), "demo", "payloads");
fs.mkdirSync(outDir, { recursive: true });

const rpc = (rpcId, method, args) => JSON.stringify({
  type: "client-request", rpcId, method, payload: { args },
});

const files = {
  // RPC bodies (client-request envelope)
  "read-secret.json": rpc("d1", "workspaceFiles/read", {
    workspaceFileScopeId: sid, path: "secret-plan.txt", range: { offset: 1, limit: 200 },
  }),
  "read-escape.json": rpc("d2", "workspaceFiles/read", {
    workspaceFileScopeId: sid, path: "../alice/alice-notes.txt", range: { offset: 1, limit: 200 },
  }),
  "read-absolute.json": rpc("d3", "workspaceFiles/read", {
    workspaceFileScopeId: sid, path: "C:/Windows/win.ini", range: { offset: 1, limit: 200 },
  }),
  "read-traversal.json": rpc("d3b", "workspaceFiles/read", {
    workspaceFileScopeId: sid, path: "../../../../etc/passwd", range: { offset: 1, limit: 200 },
  }),
  "prompt-queue.json": rpc("d4", "session/prompt", {
    request: {
      sessionId: sid, mode: "queue", requestId: "demo-q1", clientTimeZone: "Asia/Shanghai",
      content: [{ type: "text", text: "hello from alice (queued)" }],
    },
  }),
  "prompt-interrupt.json": rpc("d5", "session/prompt", {
    request: {
      sessionId: sid, mode: "interrupt", requestId: "demo-i1", clientTimeZone: "Asia/Shanghai",
      content: [{ type: "text", text: "interrupt attempt" }],
    },
  }),
  "prompt-image.json": rpc("d6", "session/prompt", {
    request: {
      sessionId: sid, mode: "queue", requestId: "demo-g1", clientTimeZone: "Asia/Shanghai",
      content: [{ type: "image", mediaType: "image/png", data: "AAAA" }],
    },
  }),
  "rename-session.json": rpc("d6b", "session/rename", {
    request: { sessionId: sid, title: "alice tries to rename" },
  }),
  "page-session.json": rpc("d7", "session/page", {
    request: { address: { kind: "session", sessionId: sid }, throughSeq: 0 },
  }),
  "session-create.json": rpc("d8", "session/create", {
    request: { workspaceId: BOB_WS },
  }),

  // Admin API bodies (bare JSON)
  "share-alice.json": JSON.stringify({ members: ["alice"] }),
  "share-none.json": JSON.stringify({ members: [] }),
  "new-user.json": JSON.stringify({ name: "carol", role: "member" }),

  // Deliberately malformed: reproduces finding D on an unpatched gateway.
  "bad.json": "{members:[]}",
};

for (const [name, text] of Object.entries(files)) {
  const p = path.join(outDir, name);
  fs.writeFileSync(p, text + "\n", { encoding: "utf8" }); // no BOM
}

console.log("session id : " + sid);
console.log("written    : " + Object.keys(files).length + " files in demo\\payloads\\");
for (const name of Object.keys(files)) console.log("  " + name);
