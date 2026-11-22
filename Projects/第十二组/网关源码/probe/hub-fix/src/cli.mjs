import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defaultConfig, defaultHome, saveConfig, loadConfig } from "./config.mjs";
import { createUser, resetPassword, setUserStatus, setDisplayName } from "./users.mjs";
import { compatibilityReport } from "./compat.mjs";
import { findDshRoot, patchReport, applySettingsPatch, rollbackSettingsPatch, settingsPatchStatus } from "./patch.mjs";
import { launchdPlist, launchdPath, LAUNCHD_LABEL } from "./service-launchd.mjs";
import { systemdUnit, systemdPath, SYSTEMD_UNIT } from "./service-systemd.mjs";

const entry = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "bin", "dsh-team-hub.js");

function printHelp() {
  console.log(`dsh-team-hub

用法：
  dsh-team-hub init [--port 3090] [--upstream http://127.0.0.1:3080]
  dsh-team-hub start
  dsh-team-hub selftest
  dsh-team-hub user add <name> [--role member|admin] [--display-name 显示名]
  dsh-team-hub user set-display-name <name> <显示名>
  dsh-team-hub user disable <name>
  dsh-team-hub user enable <name>
  dsh-team-hub user reset-password <name>
  dsh-team-hub patch status [--dsh-root <path>]
  dsh-team-hub patch apply [--dsh-root <path>]
  dsh-team-hub patch rollback [--dsh-root <path>]
  dsh-team-hub service install|uninstall|status

环境变量：
  DSH_TEAM_HUB_HOME  运行目录，默认 ~/.dsh-team-hub
`);
}

function option(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

async function init(args) {
  const home = defaultHome();
  if (fs.existsSync(path.join(home, "config.json"))) throw new Error("配置已存在，init 不会覆盖");
  const config = defaultConfig(home);
  config.listenPort = Number(option(args, "--port", config.listenPort));
  config.upstream = option(args, "--upstream", config.upstream);
  const admin = await createUser(config, { name: "admin", role: "admin" });
  const optionValues = new Set(["--port", "--upstream"].map(name => args.indexOf(name)).filter(i => i >= 0).map(i => args[i + 1]));
  for (const name of args.filter(arg => !arg.startsWith("--") && !optionValues.has(arg))) {
    await createUser(config, { name, role: "member" });
  }
  saveConfig(home, config);
  for (const dir of [config.workspaceRoot, config.sharedRoot, path.join(home, "logs")]) fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  console.log(`初始化完成：${home}`);
  console.log(`admin 初始密码：${admin.initialPassword}（仅显示一次，首次登录必须修改）`);
  for (const user of config.users.filter(u => u.role === "member")) console.log(`已创建 member：${user.name}`);
}

async function userCommand(args) {
  const [action, name] = args;
  const { home, config } = loadConfig();
  if (action === "add") {
    const result = await createUser(config, { name, role: option(args, "--role", "member") });
    const displayName = option(args, "--display-name", null);
    if (displayName) setDisplayName(config, name, displayName);
    saveConfig(home, config);
    console.log(`用户 ${name} 已创建，初始密码：${result.initialPassword}`);
    return;
  }
  if (action === "set-display-name") {
    setDisplayName(config, name, args[2]);
    saveConfig(home, config);
    console.log(`用户 ${name} 显示名已设为：${args[2]}`);
    return;
  }
  if (action === "disable" || action === "enable") {
    setUserStatus(config, name, action === "disable" ? "disabled" : "active");
    saveConfig(home, config);
    console.log(`用户 ${name} 已${action === "disable" ? "禁用" : "启用"}`);
    return;
  }
  if (action === "reset-password") {
    const result = await resetPassword(config, name);
    saveConfig(home, config);
    console.log(`用户 ${name} 新初始密码：${result.initialPassword}`);
    return;
  }
  throw new Error("未知 user 命令");
}

async function selftest() {
  const { config } = loadConfig();
  const report = await compatibilityReport(config);
  for (const check of report.checks) console.log(`${check.ok ? "✓" : "✗"} ${check.name} ${check.detail}`);
  if (!report.ok) process.exitCode = 1;
}

async function patchCommand(args) {
  const action = args[0];
  const dshRoot = option(args, "--dsh-root");
  if (action === "status") {
    const report = patchReport(dshRoot);
    if (report.status === "dsh-not-found") {
      console.log("未找到 dsh 安装目录。可用 --dsh-root <path> 显式指定。");
      process.exitCode = 1;
      return;
    }
    console.log("dsh 目录：" + report.root);
    const state = settingsPatchStatus(report.root);
    console.log(state === "patched" ? "settings host 模式补丁：已打 ✓" : state === "unpatched" ? "settings host 模式补丁：未打" : "settings bundle 未找到");
    return;
  }
  const root = findDshRoot(dshRoot);
  if (root === null) {
    console.log("未找到 dsh 安装目录。可用 --dsh-root <path> 显式指定。");
    process.exitCode = 1;
    return;
  }
  if (action === "apply") {
    const result = applySettingsPatch(root);
    console.log(result === "applied" ? "补丁已应用" : result === "unchanged" ? "补丁已是应用状态" : "settings bundle 未找到");
    if (result === "missing") process.exitCode = 1;
    return;
  }
  if (action === "rollback") {
    const result = rollbackSettingsPatch(root);
    console.log(result === "rolled-back" ? "补丁已回滚" : result === "no-backup" ? "无备份可回滚" : "settings bundle 未找到");
    if (result === "missing") process.exitCode = 1;
    return;
  }
  throw new Error("未知 patch 命令（status|apply|rollback）");
}

async function serviceCommand(args) {
  const action = args[0];
  const home = defaultHome();
  const isMac = process.platform === "darwin";
  const servicePath = isMac ? launchdPath() : systemdPath();
  const content = isMac ? launchdPlist({ home, entry }) : systemdUnit({ home, entry });
  if (action === "install") {
    fs.mkdirSync(path.dirname(servicePath), { recursive: true });
    fs.writeFileSync(servicePath, content);
    console.log(`服务文件已写入：${servicePath}`);
    console.log(isMac ? `启动：launchctl load ${servicePath}` : `启动：systemctl --user enable --now ${SYSTEMD_UNIT}`);
    return;
  }
  if (action === "uninstall") {
    if (fs.existsSync(servicePath)) fs.rmSync(servicePath);
    console.log(`服务文件已移除：${servicePath}`);
    return;
  }
  if (action === "status") {
    console.log(fs.existsSync(servicePath) ? `已安装：${servicePath}` : "未安装");
    return;
  }
  throw new Error("未知 service 命令");
}

export async function runCli(args) {
  const command = args[0];
  if (!command || command === "help" || command === "--help") return printHelp();
  if (command === "init") return init(args.slice(1));
  if (command === "user") return userCommand(args.slice(1));
  if (command === "patch") return patchCommand(args.slice(1));
  if (command === "selftest") return selftest();
  if (command === "service") return serviceCommand(args.slice(1));
  if (command === "start") {
    const { startServer } = await import("./server.mjs");
    return startServer();
  }
  throw new Error(`未知命令：${command}`);
}
