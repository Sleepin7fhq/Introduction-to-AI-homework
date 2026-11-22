import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export function sessionsPath(home) { return path.join(home, "sessions.json"); }

// 内存缓存 + mtime 判定重载：避免每个请求都 readFileSync + JSON.parse
// sessions.json。写路径（登录/登出/过期）仍同步落盘，但读热路径只做一次
// statSync 的 mtime 比较，命中缓存时零文件解析。
const stores = new Map();

function store(home) {
  let s = stores.get(home);
  if (!s) { s = { sessions: null, mtimeMs: -1 }; stores.set(home, s); }
  return s;
}

export function loadSessions(home) {
  const s = store(home);
  const file = sessionsPath(home);
  let mtimeMs = -1;
  try { mtimeMs = fs.statSync(file).mtimeMs; } catch { mtimeMs = -1; }
  if (s.sessions === null || mtimeMs !== s.mtimeMs) {
    if (!fs.existsSync(file)) s.sessions = {};
    else { try { s.sessions = JSON.parse(fs.readFileSync(file, "utf8")); } catch { s.sessions = {}; } }
    s.mtimeMs = mtimeMs;
  }
  return s.sessions;
}

export function saveSessions(home, sessions) {
  const s = store(home);
  fs.mkdirSync(home, { recursive: true, mode: 0o700 });
  const file = sessionsPath(home);
  fs.writeFileSync(file, JSON.stringify(sessions, null, 2), { mode: 0o600 });
  s.sessions = sessions;
  try { s.mtimeMs = fs.statSync(file).mtimeMs; } catch { s.mtimeMs = Date.now(); }
}

export function issueSession(home, username, ttlMs = 1000 * 60 * 60 * 24 * 14) {
  const sessions = loadSessions(home);
  const token = crypto.randomBytes(32).toString("base64url");
  const now = Date.now();
  sessions[token] = { username, createdAt: new Date(now).toISOString(), expiresAt: new Date(now + ttlMs).toISOString() };
  saveSessions(home, sessions);
  return { token, ...sessions[token] };
}

export function resolveSession(home, token) {
  if (!token) return null;
  const sessions = loadSessions(home);
  const session = sessions[token];
  if (!session) return null;
  if (Date.parse(session.expiresAt) <= Date.now()) {
    delete sessions[token];
    saveSessions(home, sessions);
    return null;
  }
  return session;
}

export function revokeSession(home, token) {
  if (!token) return false;
  const sessions = loadSessions(home);
  if (!sessions[token]) return false;
  delete sessions[token];
  saveSessions(home, sessions);
  return true;
}

export function revokeSessionsForUser(home, username) {
  const sessions = loadSessions(home);
  let count = 0;
  for (const [token, session] of Object.entries(sessions)) {
    if (session.username === username) { delete sessions[token]; count += 1; }
  }
  saveSessions(home, sessions);
  return count;
}

// 改密后撤销该账号的其他会话（保留当前会话，避免刚改完就被登出）。
export function revokeOtherSessions(home, username, keepToken) {
  const sessions = loadSessions(home);
  let count = 0;
  for (const [token, session] of Object.entries(sessions)) {
    if (session.username === username && token !== keepToken) { delete sessions[token]; count += 1; }
  }
  if (count) saveSessions(home, sessions);
  return count;
}

export function parseCookies(req) {
  const out = {};
  for (const part of String(req.headers.cookie || "").split(";")) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}
