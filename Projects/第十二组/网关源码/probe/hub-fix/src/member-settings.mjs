import fs from "node:fs";
import path from "node:path";
const NS = "ui-settings-general";
const VERSION = "2026-09-28.1";
const FIELD = "welcomeNoticeVersion";
const SCHEMA = { type: "object", properties: { [FIELD]: { type: "string" } } };
const record = value => value !== null && typeof value === "object" && !Array.isArray(value);
const exact = (value, keys) => record(value) && Object.keys(value).sort().join() === [...keys].sort().join();

// POSIX 专属的所有权/权限检查（uid、mode 位）；Windows 无 getuid，stat.uid 恒为 0、
// mode 恒为 0o666，若照搬 POSIX 判断会把一切文件判为 unsafe，导致网关无法重启
// （实测：成员在界面关闭欢迎提示生成 member-welcome.json 后，第二次启动必崩）。
function unsafeStat(stat) {
  if (!stat.isFile()) return true;
  if (typeof process.getuid === "function") {
    if (stat.uid !== process.getuid()) return true;
    if (stat.mode & 0o077) return true;
  }
  return false;
}

// This namespace is synthesized from gateway-private state, never Host settings.
export function memberWelcomeSettings(home) {
  const file = path.join(home, "member-welcome.json");
  let state = {};
  try {
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    let parsed;
    try {
      const stat = fs.fstatSync(fd);
      if (unsafeStat(stat)) throw new Error("unsafe member settings file");
      parsed = JSON.parse(fs.readFileSync(fd, "utf8"));
    } finally { fs.closeSync(fd); }
    if (!record(parsed) || Object.entries(parsed).some(([name, row]) => !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,31}$/.test(name) ||
        !exact(row, ["version", "revision"]) || row.version !== VERSION ||
        !Number.isSafeInteger(row.revision) || row.revision < 0)) throw new Error("invalid member settings file");
    state = parsed;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  function view(name) {
    const entry = Object.hasOwn(state, name) ? state[name] : undefined;
    return { autoGenerate: false, ns: NS, schema: SCHEMA,
      value: entry ? { [FIELD]: entry.version } : {}, base: {}, user: {},
      applies: "live", secrets: [], revision: entry?.revision ?? 0 };
  }
  return {
    describe(name) { return { writable: false, hasDocument: false, namespaces: [view(name)] }; },
    mutate(name, args) {
      if (typeof name !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,31}$/.test(name)) return null;
      if (!exact(args, ["ns", "ops", "expectedRevision"]) && !exact(args, ["ns", "ops"])) return null;
      if (args.ns !== NS || !Array.isArray(args.ops) || args.ops.length !== 1 ||
          !exact(args.ops[0], ["op", "path", "value"]) || args.ops[0].op !== "set" ||
          !Array.isArray(args.ops[0].path) || args.ops[0].path.length !== 1 || args.ops[0].path[0] !== FIELD ||
          args.ops[0].value !== VERSION ||
          (args.expectedRevision !== undefined && (!Number.isSafeInteger(args.expectedRevision) || args.expectedRevision < 0))) return null;
      const revision = Object.hasOwn(state, name) ? state[name].revision : 0;
      if (args.expectedRevision !== undefined && args.expectedRevision !== revision) return null;
      const next = { ...state, [name]: { version: VERSION, revision: revision + 1 } };
      const temporary = `${file}.${process.pid}.tmp`;
      try {
        try {
          const stat = fs.lstatSync(file);
          if (unsafeStat(stat) || stat.isSymbolicLink()) throw new Error("unsafe member settings file");
        } catch (error) { if (error.code !== "ENOENT") throw error; }
        fs.writeFileSync(temporary, JSON.stringify(next), { mode: 0o600, flag: "wx" });
        fs.renameSync(temporary, file);
      } catch (error) {
        try { fs.unlinkSync(temporary); } catch {}
        throw error;
      }
      state = next;
      return view(name);
    }
  };
}
