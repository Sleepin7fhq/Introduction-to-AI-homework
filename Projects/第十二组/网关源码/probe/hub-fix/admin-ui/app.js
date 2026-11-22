import { createShareState, moveShareMembers, setShareRole } from "./share-state.js";

const app = document.querySelector("#app");
const nav = [...document.querySelectorAll("nav a")];
// 渲染后要恢复的提示消息：renderUsers 会重写 #app.innerHTML（清掉 #message），
// 操作类提示（新初始密码、新建用户密码）先存这里，渲染完成后再写回。
let pendingMessage = "";

async function api(path, options = {}) {
  const response = await fetch("/__teamhub/api" + path, {
    headers: { "content-type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  if (response.status === 401) { location.href = "/login?next=/admin"; return null; }
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || response.statusText);
  return body;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c]));
}

function badge(text, cls = "") { return `<span class="badge ${cls}">${esc(text)}</span>`; }

async function render() {
  closeShareDialogs();
  const page = location.hash.slice(1) || "overview";
  nav.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + page));
  try {
    if (page === "users") return renderUsers();
    if (page === "workspaces") return renderWorkspaces();
    if (page === "usage") return renderUsage();
    if (page === "timeline") return renderTimeline();
    if (page === "audit") return renderAudit();
    if (page === "system") return renderSystem();
    return renderOverview();
  } catch (error) {
    app.innerHTML = `<section class="card"><h2>错误</h2><p class="error">${esc(error.message)}</p></section>`;
  }
}

async function renderOverview() {
  const data = await api("/overview");
  app.innerHTML = `<section class="card"><h2>总览</h2>
    <p>上游 DSH：<span class="mono">${esc(data.upstream)}</span></p>
    <p>用户：${data.users.length}；工作区：${data.workspaces.length}；会话：${data.sessions}</p></section>
    <section class="card"><h2>最近审计</h2>${auditTable(data.recentAudit)}</section>`;
}

async function renderUsers() {
  const users = await api("/users");
  app.innerHTML = `<section class="card"><h2>用户</h2>
    <form class="inline" id="create-user"><input name="name" placeholder="用户名" required>
    <select name="role"><option value="member">member</option><option value="admin">admin</option></select>
    <button>创建用户</button></form>
    <table><thead><tr><th>登录名</th><th>显示名</th><th>角色</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead><tbody>
    ${users.map(u => `<tr><td class="mono">${esc(u.name)}</td><td>${esc(u.displayName || u.name)}</td><td>${badge(u.role, u.role)}</td><td>${badge(u.status, u.status)}</td><td>${esc(u.lastLoginAt || "从未")}</td>
    <td><button class="secondary" data-action="rename" data-name="${esc(u.name)}" data-display="${esc(u.displayName || u.name)}">改名</button>
    <button class="secondary" data-action="reset" data-name="${esc(u.name)}">重置密码</button>
    <button class="secondary" data-action="${u.status === "disabled" ? "enable" : "disable"}" data-name="${esc(u.name)}">${u.status === "disabled" ? "启用" : "禁用"}</button></td></tr>`).join("")}
    </tbody></table><p id="message"></p></section>`;
  if (pendingMessage) {
    document.querySelector("#message").innerHTML = pendingMessage;
    pendingMessage = "";
  }
  document.querySelector("#create-user").onsubmit = async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const result = await api("/users", { method: "POST", body: { name: form.get("name"), role: form.get("role") } });
      const workspaceMessage = result.workspace ? `工作区已创建：${esc(result.workspace.title || result.user.name)}；` : "";
      pendingMessage = `${workspaceMessage}初始密码：<code class="mono">${esc(result.initialPassword)}</code>（只显示一次）`;
    } catch (error) {
      pendingMessage = `<span class="error">${esc(error.message)}</span>`;
    }
    await renderUsers();
  };
  app.onclick = async event => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const name = button.dataset.name;
    if (button.dataset.action === "rename") {
      const next = prompt("新的显示名（界面展示用，登录名不变）", button.dataset.display || "");
      if (next && next.trim()) await api(`/users/${encodeURIComponent(name)}/display-name`, { method: "POST", body: { displayName: next.trim() } });
      return renderUsers();
    }
    if (button.dataset.action === "reset") {
      const result = await api(`/users/${encodeURIComponent(name)}/reset-password`, { method: "POST" });
      pendingMessage = `新初始密码：<code class="mono">${esc(result.initialPassword)}</code>（只显示一次）`;
    } else {
      await api(`/users/${encodeURIComponent(name)}/status`, { method: "POST", body: { status: button.dataset.action === "disable" ? "disabled" : "active" } });
    }
    await renderUsers();
  };
}

async function renderWorkspaces() {
  const [rows, users] = await Promise.all([api("/workspaces"), api("/users")]);
  const eligible = users.filter(user => user.role === "member" && user.status === "active");
  app.innerHTML = `<section class="card"><h2>工作区共享</h2><p>授权成员可以查看共享工作区、浏览历史并发送文本消息；审批、重命名和设置仍由所有者处理。工作区所有者无需授权。</p>
    <div id="workspace-message"></div><table><thead><tr><th>工作区 / 路径</th><th>所有者</th><th>共享给</th><th>操作</th></tr></thead><tbody>
    ${rows.map((w, index) => `<tr><td>${esc(w.title)}<br><small class="mono">${esc(w.path || w.workspaceId)}</small></td><td>${esc(w.owner)}</td>
      <td>${(Object.entries(w.members || {}).map(([name, role]) => `${esc(name)}（${role === "viewer" ? "只读" : "协作"}）`).join("、")) || "未共享"}</td>
      <td><button data-share="${index}">设置共享成员</button></td></tr>`).join("")}
    </tbody></table></section>`;
  app.onclick = async event => {
    const button = event.target.closest("button[data-share]");
    if (!button) return;
    const workspace = rows[Number(button.dataset.share)];
    if (!workspace) return;
    try {
      const saved = await openShareDialog({
        workspace,
        users: eligible,
        onSubmit: members => api(`/workspaces/${encodeURIComponent(workspace.workspaceId)}/sharing`, {
          method: "POST", body: { members }
        })
      });
      if (!saved || (location.hash.slice(1) || "overview") !== "workspaces") return;
      await renderWorkspaces();
      document.querySelector("#workspace-message").textContent = "共享成员已更新；已登录成员刷新页面即可看到变化";
    } catch (error) {
      const message = document.querySelector("#workspace-message");
      if (message) message.textContent = error.message;
    }
  };
}

function closeShareDialogs() {
  for (const node of document.querySelectorAll(".modal-backdrop")) {
    if (typeof node.closeDialog === "function") node.closeDialog();
    else node.remove();
  }
}

function openShareDialog({ workspace, users, onSubmit }) {
  closeShareDialogs();
  let state = createShareState(users, workspace.owner, workspace.members || []);
  const selected = { granted: new Set(), available: new Set() };
  let busy = false;
  let done = false;
  const controller = new AbortController();
  const trigger = document.activeElement;
  let resolveResult;
  const result = new Promise(resolve => { resolveResult = resolve; });
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="share-dialog-title" aria-describedby="share-dialog-help">
      <h2 id="share-dialog-title">设置共享成员</h2>
      <p class="modal-subtitle">${esc(workspace.title)} <span class="mono">${esc(workspace.path || workspace.workspaceId)}</span></p>
      <p class="modal-help" id="share-dialog-help">点击成员姓名可多选，再用中间按钮调整是否授权。授权成员可以查看历史并发送文本消息；审批、重命名和设置仍由所有者处理。</p>
      <div class="dual-list">
        <section class="dual-list-column" aria-labelledby="granted-heading">
          <h3 class="dual-list-heading" id="granted-heading">已有权限 <span class="count" data-count="granted">0</span></h3>
          <div class="listbox" data-list="granted" role="listbox" aria-multiselectable="true" aria-labelledby="granted-heading" tabindex="0"></div>
        </section>
        <div class="move-buttons">
          <button type="button" class="secondary" data-move="revoke" aria-label="移除所选成员的权限" title="移除所选成员的权限" disabled>→</button>
          <button type="button" class="secondary" data-move="grant" aria-label="授权所选成员" title="授权所选成员" disabled>←</button>
        </div>
        <section class="dual-list-column" aria-labelledby="available-heading">
          <h3 class="dual-list-heading" id="available-heading">尚未授权 <span class="count" data-count="available">0</span></h3>
          <div class="listbox" data-list="available" role="listbox" aria-multiselectable="true" aria-labelledby="available-heading" tabindex="0"></div>
        </section>
      </div>
      <p class="error" id="share-dialog-error" role="alert" hidden></p>
      <div class="modal-actions">
        <button type="button" class="secondary" data-close>取消</button>
        <button type="button" data-save>保存</button>
      </div>
    </section>`;
  const dialog = backdrop.querySelector(".modal");
  const listNodes = {
    granted: backdrop.querySelector('[data-list="granted"]'),
    available: backdrop.querySelector('[data-list="available"]')
  };
  const countNodes = {
    granted: backdrop.querySelector('[data-count="granted"]'),
    available: backdrop.querySelector('[data-count="available"]')
  };
  const moveNodes = {
    grant: backdrop.querySelector('[data-move="grant"]'),
    revoke: backdrop.querySelector('[data-move="revoke"]')
  };
  const saveNode = backdrop.querySelector("[data-save]");
  const closeNode = backdrop.querySelector("[data-close]");
  const errorNode = backdrop.querySelector("#share-dialog-error");

  function renderLists() {
    // granted 是 { name: role }，available 是 [name]
    const grantedEntries = Object.entries(state.granted);
    countNodes.granted.textContent = String(grantedEntries.length);
    countNodes.available.textContent = String(state.available.length);

    const grantedList = listNodes.granted;
    grantedList.replaceChildren();
    for (const [name, role] of grantedEntries) {
      const candidate = state.candidates.find(user => user.name === name);
      const row = document.createElement("div");
      row.className = "granted-row";
      row.dataset.name = name;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-option";
      btn.dataset.name = name;
      btn.dataset.side = "granted";
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-selected", String(selected.granted.has(name)));
      btn.classList.toggle("selected", selected.granted.has(name));
      btn.textContent = candidate?.displayName && candidate.displayName !== name
        ? `${candidate.displayName}（${name}）` : name;
      const roleSel = document.createElement("select");
      roleSel.className = "role-select";
      roleSel.dataset.name = name;
      roleSel.setAttribute("aria-label", `设置 ${name} 的权限`);
      for (const r of ["chat", "viewer"]) {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r === "chat" ? "协作（可发消息）" : "只读（仅查看）";
        if (r === role) opt.selected = true;
        roleSel.append(opt);
      }
      row.append(btn, roleSel);
      grantedList.append(row);
    }
    if (!grantedEntries.length) {
      const empty = document.createElement("p");
      empty.className = "list-empty";
      empty.textContent = "还没有授权任何成员";
      grantedList.append(empty);
    }

    const availableList = listNodes.available;
    availableList.replaceChildren();
    for (const name of state.available) {
      const candidate = state.candidates.find(user => user.name === name);
      const option = document.createElement("button");
      option.type = "button";
      option.className = "list-option";
      option.dataset.name = name;
      option.dataset.side = "available";
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", String(selected.available.has(name)));
      option.classList.toggle("selected", selected.available.has(name));
      option.textContent = candidate?.displayName && candidate.displayName !== name
        ? `${candidate.displayName}（${name}）` : name;
      availableList.append(option);
    }
    if (!state.available.length) {
      const empty = document.createElement("p");
      empty.className = "list-empty";
      empty.textContent = "所有成员都已有权限";
      availableList.append(empty);
    }

    dialog.setAttribute("aria-busy", String(busy));
    moveNodes.grant.disabled = busy || selected.available.size === 0;
    moveNodes.revoke.disabled = busy || selected.granted.size === 0;
    saveNode.disabled = busy;
    closeNode.disabled = busy;
    saveNode.textContent = busy ? "保存中…" : "保存";
  }

  function finish(value) {
    if (done) return;
    done = true;
    controller.abort();
    backdrop.remove();
    if (trigger && trigger.isConnected) trigger.focus();
    resolveResult(value);
  }

  // Navigation replaces the page while this dialog may still be awaiting a
  // result; resolve it as cancelled instead of leaving the caller suspended.
  backdrop.closeDialog = () => finish(false);

  backdrop.addEventListener("click", async event => {
    const option = event.target.closest(".list-option");
    if (option) {
      const side = option.dataset.side;
      const name = option.dataset.name;
      if (selected[side].has(name)) selected[side].delete(name);
      else selected[side].add(name);
      renderLists();
      [...listNodes[side].children].find(node => node.dataset.name === name)?.focus();
      return;
    }
    const move = event.target.closest("button[data-move]");
    if (move) {
      const direction = move.dataset.move;
      const names = [...selected[direction === "grant" ? "available" : "granted"]];
      const next = moveShareMembers(state, direction, names);
      if (next !== state) {
        state = next;
        selected.granted.clear();
        selected.available.clear();
        renderLists();
      }
      return;
    }
    if (event.target.closest("[data-close]")) {
      if (!busy) finish(false);
      return;
    }
    if (event.target.closest("[data-save]")) {
      if (busy) return;
      busy = true;
      errorNode.hidden = true;
      renderLists();
      try {
        await onSubmit(state.granted);
        finish(true);
      } catch (cause) {
        busy = false;
        renderLists();
        errorNode.textContent = cause?.message || "保存失败，请重试";
        errorNode.hidden = false;
      }
      return;
    }
    if (event.target === backdrop) finish(false);
  }, { signal: controller.signal });

  backdrop.addEventListener("change", event => {
    const sel = event.target.closest("select.role-select");
    if (!sel || busy) return;
    state = setShareRole(state, sel.dataset.name, sel.value);
    renderLists();
  }, { signal: controller.signal });

  backdrop.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      event.preventDefault();
      if (!busy) finish(false);
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...dialog.querySelectorAll("button:not([disabled]), [tabindex='0']")]
      .filter(node => node.getClientRects().length);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, { signal: controller.signal });

  document.body.append(backdrop);
  renderLists();
  listNodes[state.granted.length ? "granted" : "available"].focus();
  return result;
}

function auditTable(rows) {
  return `<table><thead><tr><th>时间</th><th>类型</th><th>用户</th><th>详情</th></tr></thead><tbody>
  ${rows.map(row => `<tr><td>${esc(row.at)}</td><td>${esc(row.type)}</td><td>${esc(row.user || "")}</td><td class="mono">${esc(JSON.stringify({ ...row, at: undefined, type: undefined, user: undefined }))}</td></tr>`).join("")}
  </tbody></table>`;
}

async function renderUsage() {
  const data = await api("/usage?days=7");
  const total = r => r.inputTokens + r.outputTokens;
  const cost = tokens => (tokens / 1e6 * data.costCnyPerMillionTokens).toFixed(2);
  const over = r => total(r) > data.quotaTokensPerDay;
  app.innerHTML = `<section class="card"><h2>Agent 用量（近 7 天）</h2>
    <p>估算口径：input 按消息字符（每 4 字符 ≈ 1 token），output 按 2× 估算；成本为占位价（每百万 token ${data.costCnyPerMillionTokens} 元）。
    配额：每人每天 ${(data.quotaTokensPerDay / 1000).toFixed(0)}k token（演示占位值）。</p>
    <table><thead><tr><th>用户</th><th>日期</th><th>消息</th><th>被拒</th><th>输入 token</th><th>输出 token</th><th>合计</th><th>估成本</th><th>配额</th></tr></thead><tbody>
    ${data.rows.map(r => `<tr>
      <td class="mono">${esc(r.user)}</td><td>${esc(r.day)}</td><td>${r.prompts}</td><td>${r.denied}</td>
      <td class="mono">${r.inputTokens.toLocaleString()}</td><td class="mono">${r.outputTokens.toLocaleString()}</td>
      <td class="mono">${total(r).toLocaleString()}</td><td class="mono">¥${cost(total(r))}</td>
      <td>${over(r) ? badge("超额", "error") : "正常"}</td>
    </tr>`).join("") || `<tr><td colspan="9">暂无记录</td></tr>`}
    </tbody></table></section>`;
}

const TIMELINE_LABELS = {
  "auth.login": "登录系统",
  "auth.login-failed": "登录失败",
  "auth.login-throttled": "登录被限流",
  "auth.password-changed": "修改密码",
  "policy.allowed": "发送请求",
  "policy.denied": "被拒绝",
  "session.handoff": "转交接力棒",
  "admin.workspace-shares": "调整共享",
  "admin.user-created": "创建用户",
  "admin.user-status": "调整用户状态",
  "admin.password-reset": "重置密码",
  "workspace.created": "创建工作区",
  "ws.streams-closed-on-revoke": "撤销共享断流",
  "system.ownership-refresh-recovered": "归属表恢复同步"
};

function timelineDetail(r) {
  if (r.type === "policy.allowed" || r.type === "policy.denied") return r.method || "";
  if (r.type === "session.handoff") return `会话 ${(r.sessionId || "").slice(0, 8)}… 交给 ${r.holder}`;
  if (r.type === "admin.workspace-shares") {
    const names = Object.keys(r.members || {});
    return names.length ? `成员 ${names.join("、")}` : "清空共享";
  }
  if (r.type === "auth.login-failed") return `失败 ${r.failures ?? ""} 次`;
  if (r.type === "admin.user-created") return r.user || "";
  if (r.type === "admin.user-status") return `${r.user} → ${r.status}`;
  if (r.type === "ws.streams-closed-on-revoke") return `关闭 ${r.count ?? 0} 条流`;
  return "";
}

async function renderTimeline() {
  const rows = await api("/audit?limit=200");
  app.innerHTML = `<section class="card"><h2>审计时间线</h2>
    <p>谁在什么时候让 Agent 做了什么、被拦了什么、接力棒交到了谁手里——按时间倒序。</p>
    <ol class="timeline">
    ${rows.map(r => `<li><span class="mono">${esc(r.at)}</span>
      <b>${esc(r.user || "—")}</b>
      ${esc(TIMELINE_LABELS[r.type] || r.type)}
      <span class="mono">${esc(timelineDetail(r))}</span></li>`).join("") || "<li>暂无记录</li>"}
    </ol></section>`;
}

async function renderAudit() {
  const rows = await api("/audit?limit=200");
  app.innerHTML = `<section class="card"><h2>审计</h2>${auditTable(rows)}</section>`;
}

async function renderSystem() {
  const data = await api("/system");
  app.innerHTML = `<section class="card"><h2>系统</h2><pre class="mono">${esc(JSON.stringify(data, null, 2))}</pre>
  <button id="selftest">运行兼容性自检</button><p id="selftest-result"></p></section>
  <section class="card"><h2>归属表同步</h2>
  <p>最后同步时间：<span class="mono">${esc(data.ownershipLastSync || "尚未同步")}</span></p>
  <p>会话 <span class="mono">${data.ownershipSessions ?? 0}</span>；工作区 <span class="mono">${data.ownershipWorkspaces ?? 0}</span></p>
  <button id="refresh-ownership">立即刷新</button><p id="refresh-result"></p></section>`;
  document.querySelector("#selftest").onclick = async () => {
    const result = await api("/selftest", { method: "POST" });
    document.querySelector("#selftest-result").textContent = result.ok ? "自检通过" : "自检失败：" + result.error;
  };
  document.querySelector("#refresh-ownership").onclick = async () => {
    const result = await api("/ownership/refresh", { method: "POST" });
    document.querySelector("#refresh-result").textContent = result.ok
      ? `已同步：最后同步 ${result.lastSync}，会话 ${result.sessions}，工作区 ${result.workspaces}`
      : "同步失败：DSH 上游未就绪";
    if (result.ok) renderSystem();
  };
}

addEventListener("hashchange", render);
render();
