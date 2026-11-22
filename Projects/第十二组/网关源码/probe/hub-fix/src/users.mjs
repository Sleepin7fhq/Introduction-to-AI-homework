import { generatePassword, hashPassword, verifyPassword } from "./passwords.mjs";

export function publicUser(user) {
  return {
    name: user.name,
    displayName: user.displayName || user.name,
    role: user.role,
    status: user.status || "active",
    mustChangePassword: Boolean(user.mustChangePassword),
    createdAt: user.createdAt,
    updatedAt: user.updatedAt,
    lastLoginAt: user.lastLoginAt || null
  };
}

export function findUser(config, name) {
  return config.users.find(u => u.name === name) || null;
}

export async function createUser(config, { name, role = "member", password = generatePassword() }) {
  // 先校验后变更：非法用户名若在 push 之后才被 validateConfig 拒绝，会污染
  // 内存中的 context.config，导致此后所有 saveConfig 全部失败（审计 P2）。
  if (typeof name !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,31}$/.test(name)) throw new Error(`非法用户名：${name}`);
  if (!["admin", "member"].includes(role)) throw new Error(`非法角色：${role}`);
  if (findUser(config, name)) throw new Error(`用户已存在：${name}`);
  const { salt, hash } = await hashPassword(password);
  const now = new Date().toISOString();
  const user = { name, role, status: "active", salt, hash, mustChangePassword: true, createdAt: now, updatedAt: now };
  config.users.push(user);
  return { user, initialPassword: password };
}

export function setUserStatus(config, name, status) {
  const user = findUser(config, name);
  if (!user) throw new Error(`用户不存在：${name}`);
  if (user.role === "admin" && status === "disabled") {
    const activeAdmins = config.users.filter(u => u.role === "admin" && (u.status || "active") === "active" && u.name !== name);
    if (activeAdmins.length === 0) throw new Error("不能禁用最后一个启用的 admin");
  }
  user.status = status;
  user.updatedAt = new Date().toISOString();
  return user;
}

export function setDisplayName(config, name, displayName) {
  const user = findUser(config, name);
  if (!user) throw new Error(`用户不存在：${name}`);
  if (typeof displayName !== "string" || displayName.length < 1 || displayName.length > 32) throw new Error("显示名长度需为 1-32 字符");
  user.displayName = displayName;
  user.updatedAt = new Date().toISOString();
  return user;
}

export async function resetPassword(config, name, password = generatePassword()) {
  const user = findUser(config, name);
  if (!user) throw new Error(`用户不存在：${name}`);
  const { salt, hash } = await hashPassword(password);
  user.salt = salt;
  user.hash = hash;
  user.mustChangePassword = true;
  user.updatedAt = new Date().toISOString();
  return { user, initialPassword: password };
}

export async function changePassword(config, name, currentPassword, nextPassword) {
  const user = findUser(config, name);
  if (!user || !(await verifyPassword(currentPassword, user.salt, user.hash))) throw new Error("当前密码不正确");
  if (typeof nextPassword !== "string" || nextPassword.length < 8) throw new Error("新密码至少 8 位");
  const { salt, hash } = await hashPassword(nextPassword);
  user.salt = salt;
  user.hash = hash;
  user.mustChangePassword = false;
  user.updatedAt = new Date().toISOString();
  return user;
}

// 未知账号也执行一次 scrypt（固定假盐假哈希），消除"已知账号慢、未知账号快"
// 的登录时序侧信道（审计 P3 枚举）。
const DUMMY_CREDENTIALS = { salt: "0123456789abcdef0123456789abcdef", hash: "a".repeat(128) };

export async function authenticate(config, name, password) {
  const user = findUser(config, name);
  if (!user || (user.status || "active") !== "active") {
    await verifyPassword(password, DUMMY_CREDENTIALS.salt, DUMMY_CREDENTIALS.hash);
    return null;
  }
  if (!(await verifyPassword(password, user.salt, user.hash))) return null;
  user.lastLoginAt = new Date().toISOString();
  return user;
}
