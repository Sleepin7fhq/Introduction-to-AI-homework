import {
  parts,
  days,
  builtins,
  uid,
  clone,
  today,
  validDate,
  addDays,
  upcomingPlanDays,
  positive,
  repsValid,
  workoutError,
  newWorkout,
  deletePlan,
  movePlan,
  newEntry,
  completeWorkout,
  beginWorkout,
  addPlannedExercises,
  syncEmptyDraft,
  upgradeState,
  latestMetric,
  measurementValid,
  loadValid,
  weeklyCount,
  rangeStart,
  frequency,
  exerciseTrend,
  weightTrend,
  achievements,
  makeBackup,
  parseBackup,
} from "./model.js";
import { openStore, readState, writeState } from "./store.js";
const app = document.querySelector("#app"),
  modal = document.querySelector("#modal"),
  toastEl = document.querySelector("#toast");
const escape = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const paths = {
  plan: "M4 5h16v16H4z M8 3v4 M16 3v4 M4 10h16 M8 14h2 M14 14h2 M8 18h2",
  records: "M7 4h10v17H4V7h3 M8 3h8v4H8z M8 12h5 M8 16h7",
  progress: "M4 20h17 M5 16l5-6 4 3 6-9 M16 4h4v4",
  settings: "M20 21v-2a7 7 0 0 0-14 0v2 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  plus: "M12 5v14 M5 12h14",
  arrow: "M5 12h14 M14 7l5 5-5 5",
  back: "M19 12H5 M10 7l-5 5 5 5",
  close: "M6 6l12 12 M6 18L18 6",
  check: "M5 12l4 4L19 6",
  dumbbell: "M3 8v8 M6 5v14 M6 12h12 M18 5v14 M21 8v8",
  leaf: "M19 4C7 2 3 10 7 16s15 1 12-12 M7 17l9-9",
  download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
  shield: "M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6",
  award:
    "M12 3a6 6 0 1 0 0 12 6 6 0 0 0 0-12 M8 14l-2 7 6-3 6 3-2-7 M10 9l1.5 1.5L14 7",
};
const icon = (n) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[n] || paths.dumbbell}"/></svg>`;
const button = (label, action, cls = "secondary", extra = "") =>
  `<button class="${cls}" data-action="${action}" ${extra}>${label}</button>`;
const empty = (title, text, action = "") =>
  `<div class="empty"><div class="empty-symbol">${icon("leaf")}</div><h3>${title}</h3><p>${text}</p>${action}</div>`;
const dateText = (d) =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date(d + "T12:00:00"));
let db,
  state,
  revision,
  queue = Promise.resolve(),
  pending = 0,
  failed = false,
  saveLabel = "已保存",
  busy = false,
  selected = (new Date().getDay() + 6) % 7,
  month = today().slice(0, 7),
  undo = null,
  toastTimer,
  editing = null,
  editOriginal = null,
  range = 4,
  selectedExercise = "bench",
  recordWeek = null,
  backup = null,
  coachTimer,
  coachIndex = 0,
  coachCollapsed = false,
  celebrateId = null,
  achievementCelebration = null;
let lastRoute = location.hash || "#plan",
  allowLeave = false,
  renderedRoute = null;
function route() {
  return (location.hash.slice(1) || "plan").split("/");
}
function go(hash) {
  location.hash = hash;
}
function toast(text, undoFn) {
  clearTimeout(toastTimer);
  undo = undoFn || null;
  toastEl.innerHTML = `${escape(text)}${undoFn ? button("撤销", "undo", "") : ""}`;
  toastTimer = setTimeout(() => {
    toastEl.innerHTML = "";
    undo = null;
  }, 6500);
}
function saveStatus(label) {
  saveLabel = label;
  document.querySelectorAll("[data-save]").forEach((el) => {
    el.textContent = label;
    el.classList.toggle("error", failed || label.includes("失败"));
  });
  const box = document.querySelector("#save-error");
  if (box) box.hidden = !failed;
}
function persist() {
  const snapshot = clone(state);
  pending++;
  saveStatus("保存中…");
  const job = queue.then(async () => {
    if (failed) return false;
    try {
      const saved = await writeState(db, snapshot, revision);
      revision = saved.revision;
      state.revision = revision;
      return true;
    } catch (e) {
      failed = true;
      saveStatus("保存失败");
      toast(e.message + " 当前输入仍保留，请重试或重新加载。");
      return false;
    } finally {
    }
  });
  queue = job.then((ok) => {
    pending--;
    saveStatus(failed ? "保存失败" : pending ? "保存中…" : "已保存");
    return ok;
  });
  return queue;
}
function openModal(title, content, submit) {
  modal.innerHTML = `<div class="modal-head"><h2 id="modal-title">${title}</h2>${button(icon("close"), "close", "icon-btn", 'aria-label="关闭弹窗"')}</div><form id="dialog-form">${content}<p class="modal-error" role="alert"></p></form>`;
  modal.onsubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    if (!form.reportValidity()) return;
    const submitter = e.submitter;
    if (submitter) submitter.disabled = true;
    try {
      await submit(new FormData(form), form);
    } catch (err) {
      modal.querySelector(".modal-error").textContent = err.message;
    } finally {
      if (submitter) submitter.disabled = false;
    }
  };
  modal.showModal();
}
function modalActions(label = "保存") {
  return `<div class="modal-actions">${button("取消", "close", "secondary")}<button type="submit" class="primary">${label}</button></div>`;
}
function closeModal() {
  modal.close();
}
function header(title, sub, actions = "") {
  return `<header class="page-head"><div><p class="eyebrow">今天练了吗 · YOUR DAILY PRACTICE</p><h1>${title}</h1><p class="muted">${sub}</p></div>${actions || `<div class="date-badge">${dateText(today())}</div>`}</header>`;
}
function shell(content, active, editor = false) {
  const currentRoute = location.hash || "#plan";
  app.className =
    `${editor ? "editing" : ""} ${renderedRoute !== currentRoute ? "route-enter" : ""}`.trim();
  renderedRoute = currentRoute;
  app.innerHTML = `<div class="shell"><aside class="sidebar"><a class="brand" href="#plan"><span class="brand-mark">${icon("dumbbell")}</span>今天练了吗</a><p class="tagline">每一次，都算数</p><nav class="nav" aria-label="主导航">${[
    ["plan", "计划"],
    ["records", "记录"],
    ["progress", "进步"],
    ["settings", "我的"],
  ]
    .map(
      ([id, n]) =>
        `<a class="${active === id ? "active" : ""}" ${active === id ? 'aria-current="page"' : ""} href="#${id}">${icon(id)}<span>${n}</span></a>`,
    )
    .join(
      "",
    )}</nav><div class="sidebar-note"><span class="status-dot"></span>属于你的训练空间<br>数据仅保存在当前设备</div></aside><main class="main"><div id="save-error" class="notice error" ${failed ? "" : "hidden"}>保存失败，当前输入还在页面中。${button("重试保存", "retry", "link")}${button("重新加载", "reload", "link")}</div>${content}${editor ? "" : '<p class="footer-note">不必每次都完美，每一次都算数。</p>'}</main></div>`;
}
function render() {
  finishPlanDrag();
  clearInterval(coachTimer);
  const [p, id] = route();
  if (p !== "detail" || id !== celebrateId) celebrateId = null;
  if (p !== "detail" || id !== achievementCelebration?.workoutId)
    achievementCelebration = null;
  if (p === "edit") {
    renderEditor(id);
    return;
  }
  if (p === "detail") {
    renderDetail(id);
    return;
  }
  if (p === "weights") {
    renderWeights();
    return;
  }
  if (p === "plan") renderPlan();
  else if (p === "records") renderRecords();
  else if (p === "progress") renderProgress();
  else if (p === "settings") renderSettings();
  else if (p === "achievements") renderAchievements();
  else {
    history.replaceState(null, "", "#plan");
    renderPlan();
  }
}
function renderPlan() {
  const count = weeklyCount(state),
    goal = state.goals.weekly,
    dates = upcomingPlanDays(),
    selectedDate = dates.find((d) => d.index === selected).date,
    plan = state.plan[selected],
    draft = state.workouts.find((w) => w.status === "draft");
  const title =
    plan.mode === "rest"
      ? "让身体，休息一下"
      : plan.mode === "train"
        ? plan.parts.map(escape).join(" · ")
        : "今天，想练点什么？";
  shell(
    `${header("把训练，变成日常。", "照自己的节奏，一点点向前。")}<div class="grid plan-grid"><div class="stack"><section class="card plan-calendar"><div class="card-head"><h2>未来七天</h2><small>${dates[0].date.slice(5).replace("-", ".")} — ${dates[6].date.slice(5).replace("-", ".")}</small></div><div class="week-strip">${dates
      .map(({ date, index: i, label: d }) => {
        return `<button data-action="day" data-index="${i}" data-plan-target="${i}" class="day ${selected === i ? "selected" : ""} ${date === today() ? "today" : ""}" aria-label="${d} ${date}" aria-pressed="${selected === i}"><small>${d.replace("周", "")}</small><b>${Number(date.slice(8))}</b><i class="${state.workouts.some((w) => w.date === date && w.status === "complete") ? "done" : ""}"></i></button>`;
      })
      .join(
        "",
      )}</div><div class="today-card"><div class="row"><span class="pill">${selectedDate === today() ? "今日安排" : days[selected]} · ${plan.mode === "rest" ? "休息日" : plan.mode === "train" ? "训练日" : "未安排"}</span>${button("编辑安排", "plan-edit", "link")}</div>${plan.mode !== "unset" ? `<div class="plan-tools">${button("⠿ 调整训练日", "plan-move", "plan-drag-handle", `data-plan-drag="${selected}" data-index="${selected}" aria-describedby="plan-move-help"`)}${button(selectedDate === today() ? "删除今日计划" : "删除当日计划", "plan-delete", "link danger-text", `data-index="${selected}"`)}</div><p class="caption" id="plan-move-help">拖到上方星期，或点击选择日期。调整每周固定安排。</p>` : ""}<h2>${title}</h2><p>${plan.mode === "rest" ? "恢复也是训练的一部分，今天也可以自由记录。" : plan.mode === "train" ? "计划已就位。训练前先确认今天的动作清单。" : "不用准备得很完美，从你的第一个动作开始。"}</p><p class="plan-preview">${plan.exerciseIds.map((id) => escape([...builtins, ...state.customExercises].find((e) => e.id === id)?.name)).join(" · ") || "尚未安排具体动作"}</p>${selectedDate !== today() ? '<p class="caption">下方入口用于今天的训练，将带入今天的计划。</p>' : ""}${button(`${icon(draft ? "records" : "plus")}${draft ? "继续训练" : "开始训练"}${icon("arrow")}`, "start", "primary full")}</div></section><section class="card plan-week"><div class="card-head"><h2>一周的节奏</h2><small>每周重复</small></div><div class="plan-list">${dates.map(({ date, index: i, label: d }) => `<button class="plan-row" data-action="plan-edit" data-index="${i}"><span class="weekday ${i === (new Date().getDay() + 6) % 7 ? "current" : ""}">${d} · ${date.slice(5).replace("-", ".")}${date === today() ? " · 今天" : ""}</span><span class="part">${state.plan[i].mode === "rest" ? "休息日" : state.plan[i].mode === "unset" ? "未安排" : state.plan[i].parts.map(escape).join(" · ")}　›</span></button>`).join("")}</div></section></div><div class="stack"><section class="card progress-card"><div class="card-head"><h2>本周完成</h2><span class="pill">${goal && count >= goal ? "已达标" : "慢慢积累"}</span></div><div class="ring" style="--progress:${goal ? Math.min(count / goal, 1) * 100 : 0}%"><div class="ring-inner"><strong>${count}<span>${goal ? " / " + goal : ""}</span></strong><span>次训练</span></div></div><div class="progress-text"><p class="caption">${goal ? (count >= goal ? "做得不错，继续保持自己的节奏。" : `距离本周目标，还差 ${goal - count} 次。`) : "设一个小目标，让坚持更有方向。"}</p><div class="divider"></div>${button(goal ? "调整训练目标" : "设置训练目标", "goals", "link")}</div></section><section class="card plan-recent"><div class="card-head"><h2>最近一次</h2>${icon("records")}</div>${recent()}</section><div class="quote"><strong>“今天的你，比昨天多一点。”</strong>记录不是为了比较，而是看见自己的坚持。</div></div></div>`,
    "plan",
  );
}
async function commitPlanChange(plan, message, offerUndo = true) {
  if (busy) return false;
  busy = true;
  try {
    await queue;
    if (failed) {
      toast("请先处理保存失败，再调整计划");
      return false;
    }
    const before = clone(state.plan);
    state.plan = plan;
    if (!(await persist())) {
      state.plan = before;
      render();
      if (modal.open)
        modal.querySelector(".modal-error").textContent =
          "保存失败，原计划未更改。请关闭弹窗后重试保存，再调整计划。";
      return false;
    }
    if (modal.open) closeModal();
    render();
    const after = JSON.stringify(state.plan);
    toast(
      message,
      offerUndo
        ? async () => {
            if (JSON.stringify(state.plan) !== after) {
              toast("计划已有新修改，无法撤销此次调整");
              return;
            }
            await commitPlanChange(before, "已撤销计划调整", false);
          }
        : undefined,
    );
    return true;
  } finally {
    busy = false;
  }
}
async function movePlannedDay(from, to) {
  if (busy || from === to || state.plan[from].mode === "unset") return;
  const occupied = state.plan[to].mode !== "unset";
  const prompt = occupied
    ? `${days[to]}已有安排，要与${days[from]}互换吗？两天的动作清单都会保留。`
    : `将${days[from]}的计划移到${days[to]}？原来的${days[from]}将变为未安排。`;
  if (!confirm(prompt + "这会调整每周固定安排，已有训练记录和草稿不变。"))
    return;
  if (
    await commitPlanChange(
      movePlan(state, from, to),
      occupied
        ? `已互换${days[from]}与${days[to]}的计划`
        : `已将计划移到${days[to]}`,
    )
  ) {
    selected = to;
    render();
  }
}
function choosePlanDay(from) {
  openModal(
    "移动计划 · " + days[from],
    `<p class="caption">选择未来七天内的日期。目标日已有安排时，将确认互换；调整每周固定安排。</p><div class="results">${upcomingPlanDays()
      .map(({ date, index: i, label: day }) =>
        button(
          `<span>${day} ${date.slice(5).replace("-", ".")} · ${state.plan[i].mode === "unset" ? "未安排" : state.plan[i].mode === "rest" ? "休息日" : state.plan[i].parts.map(escape).join(" · ")}</span>`,
          "plan-move-to",
          "exercise-choice",
          `type="button" data-from="${from}" data-index="${i}" ${from === i ? "disabled" : ""}`,
        ),
      )
      .join(
        "",
      )}</div><div class="modal-actions">${button("取消", "close", "secondary")}</div>`,
    () => {},
  );
}
function recent() {
  const w = state.workouts
    .filter((w) => w.status === "complete")
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) || b.updatedAt.localeCompare(a.updatedAt),
    )[0];
  return w
    ? `<p class="caption">${dateText(w.date)}</p><h3 style="margin:12px 0">${w.exercises.map((e) => escape(e.name)).join(" · ")}</h3><a class="link" href="#detail/${w.id}">查看训练 ${icon("arrow")}</a>`
    : `<p class="caption">第一次记录，就从今天开始。<br>完成训练后，你会在这里看见它。</p>`;
}
function editPlan(index = selected) {
  const p = state.plan[index],
    additions = [];
  const option = (e, checked = false) =>
    `<label class="plan-choice"><input type="checkbox" name="exercise" value="${escape(e.id)}" ${checked ? "checked" : ""}><span>${escape(e.name)}<small>${escape(e.part)} · ${e.loaded ? "负重" : "自重"}</small></span></label>`;
  openModal(
    `安排${days[index]}训练`,
    `<div class="form-grid"><div class="chips">${parts.map((x) => `<label class="check-chip"><input type="checkbox" name="part" value="${x}" ${p.parts.includes(x) ? "checked" : ""}>${x}</label>`).join("")}</div><label>自定义内容<input name="custom" maxlength="60" placeholder="例如：拉伸、活动恢复" value="${escape(p.parts.filter((x) => !parts.includes(x)).join("、"))}"></label><div class="row" style="flex-wrap:wrap;gap:8px"><h3>这一天的动作清单</h3><button type="button" class="link" id="plan-clear-exercises">取消全部勾选</button></div><p class="caption">训练前会自动带入记录，临时调整不改动周计划。</p><div class="plan-choices">${[...builtins, ...state.customExercises].map((e) => option(e, p.exerciseIds.includes(e.id))).join("")}</div><details class="plan-custom"><summary>＋ 自己输入一个动作</summary><div class="form-grid"><label>计划动作名称<input name="new-name" maxlength="60" placeholder="例如：弹力带划船"></label><label>动作部位<select name="new-part">${parts.map((x) => `<option>${x}</option>`).join("")}</select></label><label class="check-chip"><input name="new-loaded" type="checkbox" checked>需要填写负重</label><button type="button" class="secondary" id="plan-add-custom">加入清单</button></div></details><label class="check-chip"><input type="checkbox" name="rest" ${p.mode === "rest" ? "checked" : ""}>设为休息日</label><p class="caption">每周重复。留空保存可清除安排，不影响已有训练。</p>${p.mode !== "unset" ? button(index === (new Date().getDay() + 6) % 7 ? "删除今日计划" : "删除当日计划", "plan-delete", "danger full", `type="button" data-index="${index}"`) : ""}</div>${modalActions()}`,
    async (fd) => {
      if (String(fd.get("new-name")).trim())
        throw Error("请先点击「加入清单」，或清空尚未加入的动作名称");
      const exerciseIds = fd.has("rest") ? [] : fd.getAll("exercise");
      const catalog = [...builtins, ...state.customExercises, ...additions];
      const list = [
        ...fd.getAll("part"),
        ...String(fd.get("custom"))
          .split("、")
          .map((x) => x.trim())
          .filter(Boolean),
        ...exerciseIds.map((id) => catalog.find((e) => e.id === id).part),
      ];
      state.customExercises.push(
        ...additions.filter(
          (e) =>
            exerciseIds.includes(e.id) &&
            !state.customExercises.some((x) => x.id === e.id),
        ),
      );
      state.plan[index] = {
        mode: fd.has("rest") ? "rest" : list.length ? "train" : "unset",
        parts: fd.has("rest") ? [] : [...new Set(list)],
        exerciseIds,
      };
      syncEmptyDraft(state);
      if (await persist()) {
        closeModal();
        render();
        toast("计划和动作清单已保存");
      }
    },
  );
  modal.querySelector("#plan-clear-exercises").onclick = () => {
    modal.querySelectorAll("[name=exercise]").forEach((input) => {
      input.checked = false;
    });
  };
  modal.querySelector("#plan-add-custom").onclick = () => {
    const input = modal.querySelector('[name="new-name"]'),
      name = input.value.trim();
    const error = modal.querySelector(".modal-error");
    if (!name) {
      error.textContent = "请先填写动作名称";
      input.focus();
      return;
    }
    if (
      [...builtins, ...state.customExercises, ...additions].some(
        (e) => e.name.toLowerCase() === name.toLowerCase(),
      )
    ) {
      error.textContent = "已有同名动作，请直接在清单中勾选";
      return;
    }
    const e = {
      id: uid(),
      name,
      part: modal.querySelector('[name="new-part"]').value,
      loaded: modal.querySelector('[name="new-loaded"]').checked,
    };
    additions.push(e);
    modal
      .querySelector(".plan-choices")
      .insertAdjacentHTML("beforeend", option(e, true));
    input.value = "";
    error.textContent = "";
    modal.querySelector("[name=rest]").checked = false;
    modal
      .querySelector(".plan-choices")
      .lastElementChild.scrollIntoView({ block: "nearest" });
  };
  modal.querySelector("[name=rest]").onchange = (e) => {
    if (e.target.checked) {
      modal
        .querySelectorAll("[name=part],[name=exercise]")
        .forEach((x) => (x.checked = false));
      modal.querySelector("[name=custom]").value = "";
    }
  };
  modal.querySelector("#dialog-form").addEventListener("input", (e) => {
    if (e.target.matches("[name=part],[name=custom],[name=exercise]"))
      modal.querySelector("[name=rest]").checked = false;
  });
}
function goals() {
  openModal(
    "给自己一个小目标",
    `<div class="form-grid"><label>每周训练次数<input name="weekly" type="number" inputmode="numeric" min="1" step="1" placeholder="暂不设置" value="${state.goals.weekly ?? ""}"></label><label>目标体重 · kg<input name="target" type="number" inputmode="decimal" min="0.01" step="any" placeholder="暂不设置" value="${state.goals.targetWeight ?? ""}"></label><p class="caption">留空即可清除目标，目标体重不会生成实测记录。</p></div>${modalActions()}`,
    async (fd) => {
      const weekly = fd.get("weekly") === "" ? null : Number(fd.get("weekly")),
        target = fd.get("target") === "" ? null : Number(fd.get("target"));
      if (
        (weekly !== null && !repsValid(weekly)) ||
        (target !== null && !positive(target))
      )
        throw Error("请填写有效目标");
      state.goals = { weekly, targetWeight: target };
      if (await persist()) {
        closeModal();
        render();
        toast("目标已保存");
      }
    },
  );
}
async function start(date = today(), mode = "live") {
  if (busy) return;
  const draft = state.workouts.find((w) => w.status === "draft");
  if (draft) {
    if (syncEmptyDraft(state)) await persist();
    go("edit/" + draft.id);
    return;
  }
  busy = true;
  const plan = state.plan[(new Date(date + "T12:00:00").getDay() + 6) % 7];
  const w = newWorkout(
    date,
    mode === "live" ? plan : null,
    [...builtins, ...state.customExercises],
    mode,
  );
  state.workouts.push(w);
  const ok = await persist();
  busy = false;
  if (ok) go("edit/" + w.id);
}
function currentWorkout() {
  const id = route()[1];
  return editing?.id === id ? editing : state.workouts.find((w) => w.id === id);
}
function dirty() {
  return editing && JSON.stringify(editing) !== editOriginal;
}
function saveWorkout() {
  const w = currentWorkout();
  w.updatedAt = new Date().toISOString();
  if (editing) {
    saveStatus("尚未保存修改");
    return Promise.resolve(true);
  }
  return persist();
}
const encouragements = [
  "今天愿意开始，就已经很棒了。",
  "再专注这一组，按自己的节奏来。",
  "慢慢来，每一次认真完成都算数。",
  "喝口水，歇一歇，再继续也很好。",
  "不必和别人比较，今天是自己的练习。",
  "累了就休息，照顾身体也是训练的一部分。",
];
function coachCard(w) {
  const sets = w.exercises.flatMap((e) => e.sets),
    done = sets.filter((s) => s.done).length;
  return `<section class="card coach" aria-label="训练陪伴"><div class="card-head"><span class="pill">${icon("leaf")} 你的训练搭子</span>${button(coachCollapsed ? "开启陪练" : "收起陪练", "coach-toggle", "link")}</div>${coachCollapsed ? '<p class="caption">安静专注，按自己的节奏来。</p>' : `<div class="coach-content"><div class="coach-orbit" style="--progress:${sets.length ? (done / sets.length) * 100 : 0}%"><span>${icon("leaf")}</span></div><div><h2 id="coach-message">${encouragements[coachIndex % encouragements.length]}</h2><p class="caption">每完成一组，点左侧圆圈为自己打个勾。</p></div></div><div class="row"><strong class="coach-count">${done} / ${sets.length} 组已打卡</strong>${button("换一句", "coach-next", "link")}</div>`}</section>`;
}
function scheduleCoach() {
  clearInterval(coachTimer);
  if (document.querySelector("#coach-message"))
    coachTimer = setInterval(() => {
      if (!document.hidden && !modal.open) refreshCoach();
    }, 20000);
}
function refreshCoach() {
  const message = document.querySelector("#coach-message");
  if (message)
    message.textContent = encouragements[++coachIndex % encouragements.length];
}
function celebration(w) {
  const sets = w.exercises.flatMap((e) => e.sets);
  return `<section class="celebration" aria-label="训练完成庆祝"><div class="confetti" aria-hidden="true">${Array.from({ length: 12 }, (_, i) => `<i style="--i:${i}"></i>`).join("")}</div><div class="celebration-mark">${icon("leaf")}</div><p class="eyebrow">TODAY, YOU SHOWED UP</p><h2>今天，练了！</h2><p>给坚持的自己，一朵小绿花。</p><div class="celebration-stats"><span><b>${w.exercises.length}</b>个动作</span><span><b>${sets.length}</b>组练习</span><span><b>${weeklyCount(state)}</b>本周训练</span></div><p class="caption">今天的努力已保存，休息一下吧。</p><a class="primary" href="#progress">看看我的进步 ${icon("arrow")}</a></section>`;
}
function plannedWorkoutNotice(w) {
  if (editing || w.mode !== "live") return "";
  const index = (new Date(w.date + "T12:00:00").getDay() + 6) % 7,
    plan = state.plan[index];
  const catalog = [...builtins, ...state.customExercises];
  const missing = plan.exerciseIds.filter(
    (id) => !w.exercises.some((e) => e.exerciseId === id),
  );
  return `<section class="notice preparation"><strong>${w.phase === "prepare" ? "先确认，再开始" : "本次训练的计划"}</strong><p>${days[index]}计划：${plan.parts.map(escape).join(" · ") || (plan.mode === "rest" ? "休息日" : "自由训练")}</p><p>${plan.exerciseIds.map((id) => escape(catalog.find((e) => e.id === id)?.name)).join(" · ") || "计划尚未安排具体动作，可直接添加动作。"}</p>${missing.length ? `<p>本次清单还未包含 ${missing.length} 个计划动作。补入会保留已填写的组和进度。</p>${button("补入计划动作", "sync-plan", "secondary")}` : ""}<p>本次调整不会改动周计划。</p></section>`;
}
function renderEditor(id) {
  const original = state.workouts.find((w) => w.id === id);
  if (!original) {
    go("records");
    return;
  }
  if (original.status === "complete" && editing?.id !== id) {
    editing = clone(original);
    editOriginal = JSON.stringify(original);
  }
  const w = currentWorkout();
  shell(
    `<div class="editor"><div class="editor-header"><div class="row">${button(`${icon("back")} 返回`, "editor-back", "link")}<span data-save class="save-state">${editing ? "编辑历史记录" : saveLabel}</span></div><div class="editor-head"><div><p class="eyebrow">ONE SET AT A TIME</p><h1>${editing ? "修改训练" : w.phase === "prepare" ? "今天，按这个练？" : w.mode === "backfill" ? "补录训练" : "训练进行中"}</h1></div><label><span class="caption">训练日期</span><input id="workout-date" type="date" value="${w.date}" max="${today()}" required></label></div></div>${plannedWorkoutNotice(w)}${!editing && w.phase === "active" && w.mode === "live" ? coachCard(w) : ""}${w.exercises.length ? w.exercises.map((e, i) => `<section class="card exercise"><div class="card-head"><div><p class="mini-label">动作 ${String(i + 1).padStart(2, "0")} · ${escape(e.part)}</p><h2>${escape(e.name)}</h2></div>${button(icon("close"), "remove-exercise", "icon-btn", `data-index="${i}" aria-label="移除${escape(e.name)}"`)}</div><div class="set-row set-labels"><span>组</span><span>重量 / kg${e.loaded ? "" : " · 可不填"}</span><span>次数</span><span></span></div>${e.sets.map((s, j) => `<div class="set-row">${!editing && w.phase === "active" && w.mode === "live" ? button(s.done ? icon("check") : j + 1, "set-done", `set-check ${s.done ? "checked" : ""}`, `data-index="${i}" data-set="${j}" aria-label="${s.done ? "取消打卡" : "完成"}${escape(e.name)}第${j + 1}组" aria-pressed="${s.done}"`) : `<span class="caption">${j + 1}</span>`}<input aria-label="${escape(e.name)} 第${j + 1}组重量" data-entry="${i}" data-set="${j}" data-field="weight" type="number" min="0" step="any" inputmode="decimal" placeholder="${e.loaded ? "0" : "自重"}" value="${s.weight ?? ""}"><input aria-label="${escape(e.name)} 第${j + 1}组次数" data-entry="${i}" data-set="${j}" data-field="reps" type="number" min="1" step="1" inputmode="numeric" placeholder="—" value="${s.reps ?? ""}">${button("−", "remove-set", "icon-btn", `data-index="${i}" data-set="${j}" aria-label="删除${escape(e.name)}第${j + 1}组"`)}</div>`).join("")}${button("＋ 添加一组", "add-set", "add-set", `data-index="${i}"`)}</section>`).join("") : empty("从第一个动作开始", "选择今天练的动作，逐组记录你的每一次努力。")}${button(`${icon("plus")} 添加动作`, "exercises", "secondary full")}<div id="workout-error" role="alert" class="modal-error"></div><div class="editor-actions">${editing ? button("取消", "cancel-edit", "secondary") : button("放弃草稿", "discard", "link")} ${button(editing ? "保存修改" : w.phase === "prepare" ? "确认并开始训练" : `${icon("check")} 完成训练`, !editing && w.phase === "prepare" ? "begin" : "complete", "primary")}</div></div>`,
    "records",
    true,
  );
  scheduleCoach();
}
function chooseExercise() {
  openModal(
    "添加训练动作",
    `<div class="form-grid"><label>搜索动作<input id="exercise-search" type="search" placeholder="例如：卧推、深蹲"></label><label>训练部位<select id="exercise-part"><option value="">全部部位</option>${parts.map((p) => `<option>${p}</option>`).join("")}</select></label></div><div class="results" id="exercise-results"></div>${button("＋ 创建自定义动作", "custom-exercise", "link full")}`,
    () => {},
  );
  const refresh = () => {
    const q = modal.querySelector("#exercise-search").value.trim(),
      p = modal.querySelector("#exercise-part").value;
    const list = [...builtins, ...state.customExercises].filter(
      (e) =>
        (!q || e.name.toLowerCase().includes(q.toLowerCase())) &&
        (!p || e.part === p),
    );
    modal.querySelector("#exercise-results").innerHTML = list.length
      ? list
          .map((e) =>
            button(
              `<span>${escape(e.name)}<br><small>${escape(e.part)} · ${e.loaded ? "负重训练" : "自重训练"}</small></span><span>＋</span>`,
              "pick-exercise",
              "exercise-choice",
              `data-id="${escape(e.id)}" type="button"`,
            ),
          )
          .join("")
      : '<p class="caption">没有匹配动作，可以创建自己的动作。</p>';
  };
  modal.querySelector("#exercise-search").oninput = refresh;
  modal.querySelector("#exercise-part").onchange = refresh;
  refresh();
}
function customExercise() {
  closeModal();
  openModal(
    "创建自己的动作",
    `<div class="form-grid"><label>动作名称<input name="name" required maxlength="60" placeholder="给动作起个名字"></label><label>训练部位<select name="part">${parts.map((p) => `<option>${p}</option>`).join("")}</select></label><label class="check-chip"><input name="loaded" type="checkbox" checked>需要填写负重</label></div>${modalActions("创建并添加")}`,
    async (fd) => {
      const name = String(fd.get("name")).trim();
      if (!name) throw Error("动作名称不能为空");
      if (
        [...builtins, ...state.customExercises].some(
          (e) => e.name.toLowerCase() === name.toLowerCase(),
        )
      )
        throw Error("已有同名动作，请关闭弹窗后选择已有动作");
      const e = {
        id: uid(),
        name,
        part: fd.get("part"),
        loaded: fd.has("loaded"),
      };
      state.customExercises.push(e);
      currentWorkout().exercises.push(newEntry(e));
      if (await saveWorkout()) {
        if (editing) await persist();
        closeModal();
        render();
      }
    },
  );
}
function renderRecords() {
  const list = state.workouts
    .filter(
      (w) =>
        w.status === "complete" &&
        (recordWeek
          ? w.date >= recordWeek && w.date <= addDays(recordWeek, 6)
          : w.date.startsWith(month)),
    )
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) || b.updatedAt.localeCompare(a.updatedAt),
    );
  const draft = state.workouts.find((w) => w.status === "draft");
  const plan = state.plan[(new Date().getDay() + 6) % 7];
  const plannedNames = plan.exerciseIds.map((id) =>
    escape(
      [...builtins, ...state.customExercises].find((e) => e.id === id)?.name,
    ),
  );
  const daily = `<section class="card daily-plan"><div class="card-head"><h2>今天的训练</h2><span class="pill">${draft ? "有未完成训练" : plan.mode === "train" ? "已同步周计划" : plan.mode === "rest" ? "计划休息日" : "自由安排"}</span></div><h3>${plan.parts.map(escape).join(" · ") || "照自己的节奏来"}</h3><p class="plan-preview">${plannedNames.join(" · ") || (plan.mode === "rest" ? "今天安排休息，也可以自己添加训练。" : "周计划还没有具体动作，可以自己添加。")}</p><p class="caption">${draft ? "空白待确认清单会带入今天的计划；已有动作可在训练页补入计划，保留原数据。" : "先核对动作，有变化就在本次训练里调整。"}</p>${button(draft ? "继续未完成训练" : "确认今天的训练", "start", "primary full")}</section>`;
  shell(
    `${header("每一次，都有记录。", "积累属于你的训练日历。", button("＋ 补录训练", "backfill", "primary"))}${daily}<section class="card"><div class="card-head"><h2>${recordWeek ? `${recordWeek} 这一周` : "训练记录"}</h2>${recordWeek ? button("返回月份", "clear-week", "link") : `<label aria-label="月份"><input id="record-month" type="month" value="${month}" aria-label="查看月份"></label>`}</div>${draft ? `<div class="notice row"><span>有一份未完成训练 · ${draft.date}</span><a class="link" href="#edit/${draft.id}">继续记录 ›</a></div>` : ""}${list.length ? list.map((w) => `<article class="record"><a href="#detail/${w.id}"><small>${dateText(w.date)}</small><h3>${w.exercises.map((e) => escape(e.name)).join(" · ")}</h3><div class="row"><p>${w.exercises.length} 个动作 · ${w.exercises.reduce((n, e) => n + e.sets.length, 0)} 组</p><span class="link">查看记录 ›</span></div></a></article>`).join("") : empty("这一段，还等你来记录", "完成一份训练，或补录过去的努力。", button("记录一次训练", "backfill", "secondary"))}</section>`,
    "records",
  );
}
function renderDetail(id) {
  const w = state.workouts.find((w) => w.id === id);
  if (!w) {
    go("records");
    return;
  }
  shell(
    `<div class="editor"><a href="#records" class="link">${icon("back")} 返回记录</a>${achievementNotice(id)}${celebrateId === id ? celebration(w) : ""}${header("训练完成，做得不错。", dateText(w.date))}${w.exercises.map((e) => `<section class="card exercise"><div class="card-head"><h2>${escape(e.name)}</h2><small>${escape(e.part)} · ${e.sets.length} 组</small></div>${e.sets.map((s, i) => `<div class="settings-row"><span class="caption">第 ${i + 1} 组</span><strong>${s.weight === null ? "自重" : s.weight + " kg"} <span class="muted">×</span> ${s.reps} 次</strong></div>`).join("")}</section>`).join("")}<div class="toolbar"><a class="primary" href="#edit/${id}">编辑训练</a>${button("删除训练", "delete-workout", "danger", `data-id="${id}"`)}</div></div>`,
    "records",
  );
}
function achievementNotice(id) {
  if (achievementCelebration?.workoutId !== id) return "";
  const unlocked = achievements(state).filter(
    (a) => a.unlocked && achievementCelebration.ids.includes(a.id),
  );
  if (!unlocked.length) return "";
  return `<section class="achievement-notice" aria-label="新成就已解锁"><div class="row"><span class="achievement-emblem">${icon("award")}</span>${button(icon("close"), "dismiss-achievements", "icon-btn", 'aria-label="关闭成就提示"')}</div><div role="status"><h2>坚持，有了新的印记</h2><p>解锁 ${unlocked.length} 枚成就徽章</p><ul>${unlocked.map((a) => `<li>${escape(a.title)}</li>`).join("")}</ul></div><a class="link" href="#achievements">查看我的成就 ${icon("arrow")}</a></section>`;
}
function renderAchievements() {
  const all = achievements(state),
    unlocked = all.filter((a) => a.unlocked),
    locked = all.filter((a) => !a.unlocked),
    count = state.workouts.filter((w) => w.status === "complete").length;
  const card = (a) =>
    `<article class="card achievement-card ${a.unlocked ? "unlocked" : "locked"}" data-achievement="${escape(a.id)}"><div class="row"><span class="achievement-emblem">${a.kind === "count" ? `<b>${a.target}</b>` : icon("award")}</span><span class="pill">${a.unlocked ? "已解锁" : "未解锁"}</span></div><h3>${escape(a.title)}</h3><p class="caption">${a.description}</p>${a.kind === "count" ? `<progress max="${a.target}" value="${a.progress}" aria-label="累计完成 ${a.target} 次训练进度"></progress><p class="caption">${a.progress} / ${a.target} 次</p>` : `<p class="achievement-record">${a.bestWeight === null ? "先完成一次，留下你的起点" : `历史最高 <strong>${a.bestWeight} kg</strong>`}</p>`}${a.unlocked ? `<p class="caption">解锁于 ${a.unlockedAt}</p>` : a.kind === "record" && a.bestWeight !== null ? '<p class="caption">在后续训练中超过它，即可解锁</p>' : ""}</article>`;
  const group = (title, items, message) =>
    `<section class="achievement-section"><h2>${title} · ${items.length}</h2>${items.length ? `<div class="achievement-grid">${items.map(card).join("")}</div>` : `<p class="caption">${message}</p>`}</section>`;
  shell(
    `<a class="link" href="#settings">${icon("back")} 返回我的</a>${header("每一份坚持，都有回响。", "属于你的成就，来自真实的每一次训练。")}<section class="card achievement-summary"><span class="achievement-emblem">${icon("award")}</span><div><h2>我的成就</h2><p><strong>${unlocked.length}</strong> / ${all.length} 枚已解锁 · 累计完成 ${count} 次训练</p></div></section>${group("已解锁", unlocked, "徽章还在等你。完成训练，慢慢留下自己的印记。")}${group("待解锁", locked, "当前成就已全部解锁，继续按自己的节奏训练吧。")}<p class="caption achievement-rules">仅统计已完成训练，草稿不计入。重量突破按训练日期排序，同日按记录创建时间排序；首次记录作为基准，同一次训练内加重或追平纪录不解锁。每个负重动作对应一枚徽章，自重动作不比较重量。补录、修改、删除和恢复备份后，会按现有记录重新计算；条件不再满足时，徽章恢复为未解锁。无需为了徽章勉强加重。</p>`,
    "settings",
  );
}
let chartData = {};
function chart(points, kind, unit, target = null) {
  if (!points.length)
    return empty("还没有足够的记录", "记录一次，变化就有了起点。");
  const main = document.querySelector(".main");
  const style = main && getComputedStyle(main);
  const contentWidth = main
    ? main.clientWidth -
      parseFloat(style.paddingLeft) -
      parseFloat(style.paddingRight)
    : innerWidth - 40;
  const cardWidth =
    innerWidth > 1050 && kind !== "frequency"
      ? (contentWidth - 22) / 2
      : contentWidth;
  const width = Math.max(280, Math.round(cardWidth - 52), points.length * 48),
    height = 210,
    left = 38,
    right = 18,
    top = 20,
    bottom = 35,
    plot = height - top - bottom;
  const peak = Math.max(...points.map((p) => p.value), target || 0, 1);
  const min =
    kind === "weight"
      ? Math.max(
          0,
          Math.min(...points.map((p) => p.value), target ?? Infinity) - 2,
        )
      : 0;
  const max =
    kind === "weight"
      ? peak + 2
      : kind === "frequency"
        ? Math.max(2, Math.ceil((peak * 1.16) / 2) * 2)
        : Math.min(Number.MAX_VALUE, peak * 1.16);
  const y = (v) => top + plot * (1 - (v - min) / (max - min));
  const x = (i) => left + ((width - left - right) * (i + 0.5)) / points.length;
  const labelStep = Math.max(1, Math.ceil(points.length / 7));
  return `<div class="chart-scroll"><svg class="chart" style="min-width:${width}px" viewBox="0 0 ${width} ${height}" role="group" aria-label="${{ frequency: "每周训练次数", exercise: "动作进步", weight: "体重趋势" }[kind]}，单位${unit}">${[0, 0.5, 1].map((f) => `<line x1="${left}" y1="${y(min + (max - min) * f)}" x2="${width - right}" y2="${y(min + (max - min) * f)}" stroke="#e8ecdf" stroke-dasharray="3 5"/><text x="${left - 8}" y="${y(min + (max - min) * f) + 4}" text-anchor="end">${Number((min + (max - min) * f).toFixed(kind === "frequency" ? 0 : 1))}</text>`).join("")}${target ? `<line x1="${left}" y1="${y(target)}" x2="${width - right}" y2="${y(target)}" stroke="#75934a" stroke-dasharray="5 5"/><text x="${width - right}" y="${y(target) - 6}" text-anchor="end">目标 ${target} ${unit}</text>` : ""}${kind !== "frequency" && points.length > 1 ? `<polyline points="${points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ")}" fill="none" stroke="#416329" stroke-width="2.5" stroke-linejoin="round"/>` : ""}${points.map((p, i) => `<g class="chart-point" role="button" tabindex="0" data-action="chart-point" data-kind="${kind}" data-index="${i}" aria-label="${p.date}，${p.value} ${unit}"><rect x="${x(i) - 22}" y="0" width="44" height="${height}" fill="transparent"/>${kind === "frequency" ? `<rect x="${x(i) - 12}" y="${y(p.value)}" width="24" height="${Math.max(2, plot - (y(p.value) - top))}" rx="5" fill="#a9c85f"/>` : `<circle cx="${x(i)}" cy="${y(p.value)}" r="5" fill="white" stroke="#416329" stroke-width="2.5"/>`}<title>${p.date} · ${p.value} ${unit}</title></g>${i % labelStep === 0 || i === points.length - 1 ? `<text x="${x(i)}" y="${height - 10}" text-anchor="middle">${p.date.slice(5).replace("-", "/")}</text>` : ""}`).join("")}</svg></div><details class="data-list"><summary>查看全部数值与详情</summary>${points.map((p, i) => button(`${p.date}　${p.value} ${unit}　›`, "chart-point", "", `data-kind="${kind}" data-index="${i}"`)).join("")}</details>`;
}
function renderProgress() {
  const choices = [
    ...new Map(
      [
        ...builtins,
        ...state.customExercises,
        ...state.workouts.flatMap((w) =>
          w.exercises.map((e) => ({
            id: e.exerciseId,
            name: e.name,
            loaded: e.loaded,
          })),
        ),
      ].map((e) => [e.id, e]),
    ).values(),
  ];
  if (!choices.some((e) => e.id === selectedExercise))
    selectedExercise = choices[0]?.id || "bench";
  const selected = choices.find((e) => e.id === selectedExercise);
  chartData = {
    frequency: frequency(state, range),
    exercise: exerciseTrend(state, selectedExercise, range),
    weight: weightTrend(state, range),
  };
  const total = chartData.frequency.reduce((s, x) => s + x.value, 0);
  const latest = latestMetric(state, "value");
  shell(
    `${header("进步，正在发生。", "看见自己的坚持，也给变化一点时间。", `<a class="secondary" href="#achievements">${icon("award")} 我的成就</a>`)}<div class="row" style="margin-bottom:24px;flex-wrap:wrap"><p class="caption">${rangeStart(state, range)} 至 ${today()}</p><div class="tabs" aria-label="统计时间范围">${[
      [4, "近 4 周"],
      [12, "近 12 周"],
      ["all", "全部"],
    ]
      .map(([v, n]) =>
        button(
          n,
          "range",
          range === v ? "selected" : "",
          `data-range="${v}" aria-pressed="${range === v}"`,
        ),
      )
      .join(
        "",
      )}</div></div><div class="stats-grid"><section class="card wide"><div class="card-head"><div><h2>训练频率</h2><p class="caption">每一周，都是新的积累</p></div><div class="metric">${total}<small>次训练</small></div></div>${chart(chartData.frequency, "frequency", "次", state.goals.weekly)}<p class="chart-summary">${total ? "点击柱形查看该周训练记录。" : "这段时间还没有完成训练。草稿不计入统计。"}</p></section><section class="card"><div class="card-head"><h2>动作进步</h2>${icon("dumbbell")}</div><label>选择动作<select id="trend-exercise">${choices.map((e) => `<option value="${escape(e.id)}" ${selectedExercise === e.id ? "selected" : ""}>${escape(e.name)}</option>`).join("")}</select></label><p class="caption" style="margin-top:15px">${selected?.loaded ? "每次训练最高负重 · kg" : "每次训练单组最高次数 · 次"}</p>${chart(chartData.exercise, "exercise", selected?.loaded ? "kg" : "次")}<p class="chart-summary">${selected?.loaded ? "结合次数观察变化，重量只是进步的一个角度。" : "自重动作以最高次数观察，不混用重量轴。"}</p></section><section class="card"><div class="card-head"><h2>体重趋势</h2>${button("＋ 记录体重", "weight-add", "link")}</div><div class="metric">${latest?.value ?? "—"}<small>kg · 最新记录</small></div>${chart(chartData.weight, "weight", "kg", state.goals.targetWeight)}<a class="link" href="#weights">管理体重记录 ›</a></section></div>`,
    "progress",
  );
}
function renderWeights() {
  const rows = [...state.weights].sort((a, b) => b.date.localeCompare(a.date));
  shell(
    `<div class="editor"><a href="#progress" class="link">${icon("back")} 返回进步</a>${header("身体指标记录", "每个数值，都只是观察自己的一个角度。", button("＋ 记录体重", "weight-add", "primary"))}<section class="card">${rows.length ? rows.map((w) => `<div class="settings-row"><div><p>${dateText(w.date)}</p><div class="measurement-values">${w.value !== null ? `<strong>${w.value} <small>kg 体重</small></strong>` : ""}${w.bodyFat !== null ? `<strong>${w.bodyFat} <small>% 体脂率</small></strong>` : ""}${w.waist !== null ? `<strong>${w.waist} <small>cm 腰围</small></strong>` : ""}</div></div><div class="toolbar">${button("修改", "weight-edit", "link", `data-id="${w.id}"`)}${button("删除", "weight-delete", "link", `data-id="${w.id}"`)}</div></div>`).join("") : empty("从一个真实的数字开始", "体重、体脂率、腰围，按实际测量填写。", button("记录体重", "weight-add", "secondary"))}</section></div>`,
    "progress",
  );
}
function editWeight(id) {
  const w = state.weights.find((x) => x.id === id);
  const base = w || state.weights.find((x) => x.date === today());
  openModal(
    w ? "修改身体指标" : "记录身体指标",
    `<div class="form-grid"><label>测量日期<input name="date" type="date" required value="${base?.date || today()}" max="${today()}"></label><label>体重 · kg<input name="value" type="number" inputmode="decimal" min="0.01" step="any" value="${base?.value ?? ""}" placeholder="例如 65.5"></label><label>体脂率 · %<input name="bodyFat" type="number" inputmode="decimal" min="0.01" max="99.99" step="any" value="${base?.bodyFat ?? ""}" placeholder="填写实测体脂率"></label><label>腰围 · cm<input name="waist" type="number" inputmode="decimal" min="0.01" step="any" value="${base?.waist ?? ""}" placeholder="填写实测腰围"></label><p class="caption">至少填写一项。已有日期会带入原值；留空的项目在保存时会清除。各项仅记录实测，不自动估算。</p></div>${modalActions()}`,
    async (fd) => {
      const date = fd.get("date"),
        values = Object.fromEntries(
          ["value", "bodyFat", "waist"].map((key) => [
            key,
            fd.get(key) === "" ? null : Number(fd.get(key)),
          ]),
        );
      if (!validDate(date) || date > today() || !measurementValid(values))
        throw Error("请填写有效日期及至少一项指标，体脂率须大于 0 且小于 100");
      const existing = state.weights.find(
        (x) => x.date === date && x.id !== id,
      );
      if (
        existing &&
        !confirm(
          `${date} 已有身体指标记录，替换为本次填写内容？留空项目将清除。`,
        )
      )
        return;
      const now = new Date().toISOString();
      state.weights = state.weights.filter(
        (x) => x.id !== id && x.id !== existing?.id,
      );
      state.weights.push({
        id: w?.id || existing?.id || uid(),
        date,
        ...values,
        createdAt: w?.createdAt || existing?.createdAt || now,
        updatedAt: now,
      });
      if (await persist()) {
        closeModal();
        render();
        toast("身体指标已保存");
      }
    },
  );
  if (!id)
    modal.querySelector('[name="date"]').onchange = (e) => {
      const day = state.weights.find((x) => x.date === e.target.value);
      for (const key of ["value", "bodyFat", "waist"])
        modal.querySelector(`[name="${key}"]`).value = day?.[key] ?? "";
    };
}
function backfill() {
  openModal(
    "补录一次训练",
    `<label>训练日期<input name="date" type="date" value="${today()}" max="${today()}" required></label><p class="caption" style="margin-top:14px">选择训练发生的日期，再记录具体动作。</p>${modalActions("开始记录")}`,
    async (fd) => {
      const date = fd.get("date");
      if (!validDate(date) || date > today())
        throw Error("请选择今天或过去的日期");
      const draft = state.workouts.find((w) => w.status === "draft");
      if (draft) {
        if (
          !confirm(
            "已有一份未完成训练。确定放弃原草稿并补录？点击取消可继续原草稿。",
          )
        ) {
          closeModal();
          go("edit/" + draft.id);
          return;
        }
        state.workouts = state.workouts.filter((w) => w.id !== draft.id);
      }
      closeModal();
      await start(date, "backfill");
    },
  );
}
let offlineLabel = "离线资源尚未就绪";
function renderSettings() {
  const latest = latestMetric(state, "value");
  const metrics = [
    ["value", "体重", "kg"],
    ["bodyFat", "体脂率", "%"],
    ["waist", "腰围", "cm"],
  ];
  const earned = achievements(state).filter((a) => a.unlocked).length;
  const body = `<section class="card"><div class="card-head"><h2>我的成就</h2>${icon("award")}</div><p class="caption">已解锁 ${earned} 枚徽章，每一次坚持都有迹可循。</p><a class="link" href="#achievements">查看全部成就 ${icon("arrow")}</a></section><section class="card body-card"><div class="card-head"><h2>我的身体指标</h2>${icon("leaf")}</div><p class="caption">记下真实变化，了解自己的节奏。</p><div class="body-metrics">${metrics
    .map(([key, label, unit]) => {
      const m = latestMetric(state, key);
      return `<div><span class="mini-label">${label}</span><strong>${m?.[key] ?? "—"}<small>${unit}</small></strong><span class="caption">${m?.date || "尚未记录"}</span></div>`;
    })
    .join(
      "",
    )}</div><div class="toolbar">${button("记录身体指标", "weight-add", "primary")}<a class="link" href="#weights">查看与修改历史 ›</a></div></section>`;
  shell(
    `${header("为自己，设定方向。", "小小的目标，长久的陪伴。")}<div class="grid"><div class="stack">${body}<section class="card"><div class="card-head"><h2>我的目标</h2>${button("编辑目标", "goals", "link")}</div><div class="settings-row"><div><h3>每周训练</h3><p>按完成的训练次数计算</p></div><span class="value">${state.goals.weekly === null ? "未设置" : state.goals.weekly + " 次"}</span></div><div class="settings-row"><div><h3>目标体重</h3><p>朝着自己的方向前进</p></div><span class="value">${state.goals.targetWeight === null ? "未设置" : state.goals.targetWeight + " kg"}</span></div><div class="settings-row"><div><h3>最新体重</h3><p>${latest?.date || "尚未记录实测体重"}</p></div><a class="link" href="#weights">${latest ? latest.value + " kg" : "去记录"} ›</a></div></section><section class="card"><div class="card-head"><h2>数据与备份</h2>${icon("shield")}</div><div class="settings-row"><div><h3>导出全部数据</h3><p>计划、训练、身体指标与目标</p></div>${button("导出备份", "export", "secondary")}</div><div class="settings-row"><div><h3>从备份恢复</h3><p>选择 JSON 文件，确认后完整替换</p></div>${button("选择文件", "import", "secondary")}</div><input id="backup-file" type="file" accept=".json,application/json" hidden><p class="caption" style="margin-top:16px">备份文件未加密，请保存在你信任的位置。</p></section></div><div class="stack"><section class="card"><div class="card-head"><h2>只属于你的数据</h2>${icon("leaf")}</div><p class="caption">所有记录保存在当前设备，不上传云端。正常关闭后可以继续；不同设备或浏览器之间不会自动同步。</p><div class="divider"></div><p class="caption">清除网站数据、设备重置或浏览器回收存储可能移除记录。请定期导出备份，换设备时通过文件恢复。</p></section><section class="card"><div class="card-head"><h2>随时打开，随手记录</h2>${icon("plus")}</div><p class="caption">安装到主屏幕后，像 App 一样打开。</p>${button("查看安装与离线说明", "install-help", "link full")}<p class="caption" id="offline-status">${offlineLabel}</p></section></div></div>`,
    "settings",
  );
}
async function exportBackup() {
  await queue;
  if (failed) throw Error("请先处理保存失败，再导出备份");
  const persisted = await readState(db),
    payload = makeBackup(persisted),
    blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    }),
    url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `今天练了吗-备份-${today()}-${new Date().toTimeString().slice(0, 8).replaceAll(":", "")}.json`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
  toast("已生成备份文件，请在系统下载中保存。");
}
async function importFile(file) {
  if (!file) return;
  try {
    backup = parseBackup(await file.text());
    openModal(
      "恢复备份 · 请先核对",
      `<p class="caption">备份时间：${escape(new Date(backup.exportedAt).toLocaleString("zh-CN"))}</p><div class="backup-summary">${[
        [
          backup.data.workouts.filter((w) => w.status === "complete").length,
          "次已完成训练",
        ],
        [
          backup.data.workouts.filter((w) => w.status === "draft").length,
          "份未完成草稿",
        ],
        [backup.data.weights.length, "条身体指标记录"],
        [backup.data.customExercises.length, "个自定义动作"],
      ]
        .map(([n, label]) => `<div><b>${n}</b><span>${label}</span></div>`)
        .join(
          "",
        )}</div><p class="notice error">确认后，当前设备的计划、目标和全部记录将被这份备份完整替换。不会自动合并。</p><div class="modal-actions">${button("先备份当前数据", "export", "secondary")}${button("取消", "close", "secondary")}<button type="submit" class="primary">确认替换并恢复</button></div>`,
      async () => {
        await queue;
        if (failed) throw Error("请先处理当前保存失败，再恢复备份");
        busy = true;
        try {
          const restored = await writeState(db, backup.data, revision);
          state = restored;
          revision = restored.revision;
          saveStatus("已保存");
          editing = null;
          recordWeek = null;
          closeModal();
          render();
          toast("恢复完成，全部页面已更新");
        } finally {
          busy = false;
        }
      },
    );
  } catch (err) {
    toast(err.message + "，原数据未改动。");
  }
}
async function action(el) {
  const a = el.dataset.action;
  if (busy) return;
  if (a === "close") {
    closeModal();
    return;
  }
  if (a === "undo") {
    const fn = undo;
    undo = null;
    toastEl.innerHTML = "";
    if (fn) await fn();
    return;
  }
  if (a === "update") {
    if (dirty()) {
      toast("请先保存或取消历史修改，再更新应用");
      return;
    }
    await queue;
    if (failed) {
      toast("请先处理保存失败");
      return;
    }
    if (updateWorker) {
      navigator.serviceWorker.addEventListener(
        "controllerchange",
        () => location.reload(),
        { once: true },
      );
      updateWorker.postMessage("ACTIVATE_UPDATE");
    }
    return;
  }
  if (a === "export") {
    await exportBackup();
    return;
  }
  if (a === "import") {
    document.querySelector("#backup-file").click();
    return;
  }
  if (a === "install-help") {
    openModal(
      "安装与离线使用",
      `<div class="form-grid"><p><strong>iPhone</strong><br>使用 Safari 打开正式 HTTPS 地址，点击分享，选择「添加到主屏幕」。如有「作为网页 App 打开」，保持开启，再点「添加」。</p><p><strong>安卓</strong><br>使用 Chrome 打开正式 HTTPS 地址，在菜单选择「安装应用」或「添加到主屏幕」。</p><p class="caption">首次联网打开后，等待「我的」显示「离线已就绪」，再断网测试。手机请使用正式 HTTPS 地址，不能使用电脑的 localhost 地址。</p><p class="caption">电脑、手机及不同网站地址各自保存数据，不会自动同步。请固定使用同一正式地址，并从桌面图标进入；定期在「我的」导出备份。</p><p class="caption">${offlineLabel}</p></div><div class="modal-actions">${button("知道了", "close", "primary")}</div>`,
      () => {},
    );
    return;
  }
  if (a === "retry") {
    failed = false;
    await persist();
    return;
  }
  if (a === "reload") {
    if (confirm("重新加载会丢弃当前未保存输入，继续吗？")) location.reload();
    return;
  }
  if (a === "day") {
    selected = Number(el.dataset.index);
    render();
    return;
  }
  if (a === "plan-delete") {
    const index = Number(el.dataset.index);
    if (state.plan[index].mode === "unset") return;
    if (
      !confirm(
        `删除${days[index]}的每周固定计划？部位与动作安排将清空，已有训练记录和草稿保留。${modal.open ? "弹窗中未保存的调整也会放弃。" : ""}`,
      )
    )
      return;
    await commitPlanChange(deletePlan(state, index), "已删除当日计划");
    return;
  }
  if (a === "plan-move") {
    choosePlanDay(Number(el.dataset.index));
    return;
  }
  if (a === "plan-move-to") {
    await movePlannedDay(Number(el.dataset.from), Number(el.dataset.index));
    return;
  }
  if (a === "plan-edit") {
    editPlan(
      el.dataset.index === undefined ? selected : Number(el.dataset.index),
    );
    return;
  }
  if (a === "goals") {
    goals();
    return;
  }
  if (a === "start") {
    await start();
    return;
  }
  if (a === "dismiss-achievements") {
    achievementCelebration = null;
    render();
    return;
  }
  if (a === "coach-toggle") {
    coachCollapsed = !coachCollapsed;
    document.querySelector(".coach").outerHTML = coachCard(currentWorkout());
    scheduleCoach();
    return;
  }
  if (a === "coach-next") {
    refreshCoach();
    return;
  }
  if (a === "sync-plan") {
    const invalid = [...document.querySelectorAll(".editor input")].find(
      (x) => !x.checkValidity(),
    );
    if (invalid) {
      invalid.reportValidity();
      return;
    }
    const w = currentWorkout();
    if (editing || !w || w.status !== "draft") return;
    const count = addPlannedExercises(state, w);
    if (!count) return;
    const ok = await saveWorkout();
    render();
    if (ok) toast(`已补入 ${count} 个计划动作，原有组和进度已保留`);
    return;
  }
  if (a === "begin") {
    const invalid = [...document.querySelectorAll(".editor input")].find(
      (x) => !x.checkValidity(),
    );
    if (invalid) {
      invalid.reportValidity();
      return;
    }
    const w = currentWorkout();
    // Persist preparation first; a failed start leaves the same recoverable draft.
    await queue;
    if (failed) {
      toast("请先重试保存");
      return;
    }
    const next = beginWorkout(state, w.id),
      before = clone(state);
    busy = true;
    state = next;
    const ok = await persist();
    busy = false;
    if (ok) {
      coachCollapsed = false;
      coachIndex = 0;
      render();
    } else state = before;
    return;
  }
  if (a === "set-done") {
    const w = currentWorkout();
    if (!w || editing || w.phase !== "active") return;
    const e = w.exercises[Number(el.dataset.index)],
      set = e.sets[Number(el.dataset.set)];
    const invalid = [...document.querySelectorAll(".editor input")].find(
      (x) => !x.checkValidity(),
    );
    if (invalid) {
      invalid.reportValidity();
      return;
    }
    if (
      !set.done &&
      (!repsValid(set.reps) || (e.loaded && !loadValid(set.weight)))
    ) {
      toast("先填好这一组的实际重量和次数，再打卡");
      return;
    }
    set.done = !set.done;
    if (await saveWorkout()) {
      coachIndex++;
      render();
      toast(set.done ? "这一组，拿下！休息一下再继续。" : "已取消这一组的打卡");
    }
    return;
  }
  if (["exercises", "add-set"].includes(a)) {
    const invalid = [...document.querySelectorAll(".editor input")].find(
      (x) => !x.checkValidity(),
    );
    if (invalid) {
      invalid.reportValidity();
      return;
    }
  }
  if (a === "exercises") {
    chooseExercise();
    return;
  }
  if (a === "custom-exercise") {
    customExercise();
    return;
  }
  if (a === "pick-exercise") {
    const e = [...builtins, ...state.customExercises].find(
      (x) => x.id === el.dataset.id,
    );
    currentWorkout().exercises.push(newEntry(e));
    await saveWorkout();
    closeModal();
    render();
    return;
  }
  if (a === "add-set") {
    const e = currentWorkout().exercises[Number(el.dataset.index)],
      last = e.sets.at(-1);
    e.sets.push({
      id: uid(),
      weight: last?.weight ?? null,
      reps: last?.reps ?? null,
      done: false,
    });
    await saveWorkout();
    render();
    return;
  }
  if (a === "remove-set" || a === "remove-exercise") {
    const w = currentWorkout(),
      copy = clone(w),
      i = Number(el.dataset.index);
    if (a === "remove-set")
      w.exercises[i].sets.splice(Number(el.dataset.set), 1);
    else {
      w.exercises.splice(i, 1);
      if (!editing && w.exercises.length === 0) w.planCleared = true;
    }
    await saveWorkout();
    render();
    const after = JSON.stringify(w);
    toast(a === "remove-set" ? "已删除这一组" : "已移除动作", async () => {
      const now = currentWorkout();
      if (!now || now.id !== copy.id || JSON.stringify(now) !== after) {
        toast("记录已发生变化，无法撤销，请重新添加。");
        return;
      }
      Object.assign(now, copy);
      await saveWorkout();
      render();
    });
    return;
  }
  if (a === "discard") {
    if (confirm("放弃这份未完成训练？已记录的草稿内容将删除。")) {
      const before = state.workouts;
      busy = true;
      state.workouts = state.workouts.filter((w) => w.id !== route()[1]);
      const ok = await persist();
      busy = false;
      if (ok) go("plan");
      else {
        state.workouts = before;
        toast("草稿未删除，请先重试保存，再重新操作。");
      }
    }
    return;
  }
  if (a === "editor-back" || a === "cancel-edit") {
    if (dirty() && !confirm("放弃尚未保存的修改？原训练记录不会改变。")) return;
    editing = null;
    editOriginal = null;
    allowLeave = true;
    go("records");
    return;
  }
  if (a === "complete") {
    if (busy) return;
    const inputs = [...document.querySelectorAll(".editor input")];
    const invalid = inputs.find((x) => !x.checkValidity());
    if (invalid) {
      invalid.reportValidity();
      return;
    }
    const w = currentWorkout(),
      err = workoutError(w);
    if (err) {
      document.querySelector("#workout-error").textContent = err;
      for (const [i, e] of w.exercises.entries()) {
        if (!e.sets.length) {
          document
            .querySelector(`[data-action="add-set"][data-index="${i}"]`)
            ?.focus();
          break;
        }
        const j = e.sets.findIndex(
          (s) => !repsValid(s.reps) || (e.loaded && !loadValid(s.weight)),
        );
        if (j !== -1) {
          const field = !repsValid(e.sets[j].reps) ? "reps" : "weight";
          document
            .querySelector(
              `[data-entry="${i}"][data-set="${j}"][data-field="${field}"]`,
            )
            ?.focus();
          break;
        }
      }
      return;
    }
    busy = true;
    el.disabled = true;
    await queue;
    if (failed) {
      busy = false;
      el.disabled = false;
      toast("请先重试保存");
      return;
    }
    const beforeCommit = clone(state);
    let ok;
    if (editing) {
      w.exercises.forEach((e) => e.sets.forEach((s) => (s.done = true)));
      state.workouts = state.workouts.map((x) =>
        x.id === w.id ? clone(w) : x,
      );
      ok = await persist();
    } else {
      state = completeWorkout(state, w.id);
      ok = await persist();
    }
    busy = false;
    if (ok) {
      clearTimeout(toastTimer);
      toastEl.innerHTML = "";
      undo = null;
      celebrateId = !editing && w.mode === "live" ? w.id : null;
      if (!editing) {
        const previous = new Set(
          achievements(beforeCommit)
            .filter((a) => a.unlocked)
            .map((a) => a.id),
        );
        const ids = achievements(state)
          .filter((a) => a.unlocked && !previous.has(a.id))
          .map((a) => a.id);
        achievementCelebration = ids.length ? { workoutId: w.id, ids } : null;
      }
      editing = null;
      editOriginal = null;
      allowLeave = true;
      go("detail/" + w.id);
    } else {
      // A failed commit must not turn an unsaved edit into the visible original.
      state = beforeCommit;
      el.disabled = false;
    }
    return;
  }
  if (a === "range") {
    range = el.dataset.range === "all" ? "all" : Number(el.dataset.range);
    render();
    return;
  }
  if (a === "chart-point") {
    const kind = el.dataset.kind,
      p = chartData[kind][Number(el.dataset.index)];
    if (kind === "frequency") {
      recordWeek = p.date;
      go("records");
    } else if (kind === "weight") {
      editWeight(p.id);
    } else {
      openModal(
        "这次训练的进步",
        `<p>${p.date}</p><div class="metric" style="margin:20px 0">${p.value}<small>${p.loaded ? "kg" : "次"}</small></div><p class="caption">${p.loaded ? "最高负重对应次数：" + p.reps.join("、") + " 次" : "自重动作 · 单组最高次数"}</p><div class="modal-actions">${button("查看完整训练", "chart-detail", "primary", `data-id="${p.id}"`)}</div>`,
        () => {},
      );
    }
    return;
  }
  if (a === "chart-detail") {
    closeModal();
    go("detail/" + el.dataset.id);
    return;
  }
  if (a === "backfill") {
    backfill();
    return;
  }
  if (a === "delete-workout") {
    const w = state.workouts.find((w) => w.id === el.dataset.id);
    if (
      confirm(
        `删除 ${w.date} 的训练（${w.exercises.map((e) => e.name).join("、")}）？`,
      )
    ) {
      const before = state.workouts;
      busy = true;
      state.workouts = state.workouts.filter((x) => x.id !== w.id);
      const ok = await persist();
      busy = false;
      if (ok) {
        go("records");
        toast("训练已删除");
      } else {
        state.workouts = before;
        toast("训练未删除，请先重试保存，再重新操作。");
      }
    }
    return;
  }
  if (a === "weight-add" || a === "weight-edit") {
    editWeight(el.dataset.id);
    return;
  }
  if (a === "weight-delete") {
    const w = state.weights.find((w) => w.id === el.dataset.id);
    if (confirm(`删除 ${w.date} 的全部身体指标记录？`)) {
      const before = state.weights;
      busy = true;
      state.weights = state.weights.filter((x) => x.id !== w.id);
      const ok = await persist();
      busy = false;
      if (ok) {
        render();
        toast("身体指标已删除");
      } else {
        state.weights = before;
        toast("身体指标未删除，请先重试保存，再重新操作。");
      }
    }
    return;
  }
  if (a === "clear-week") {
    recordWeek = null;
    render();
    return;
  }
}
let planDrag = null;
function finishPlanDrag() {
  if (!planDrag) return;
  planDrag.ghost?.remove();
  planDrag.target?.classList.remove("plan-drop-target");
  planDrag.handle.classList.remove("dragging");
  const { handle, cancelClick } = planDrag;
  if (cancelClick)
    setTimeout(() => handle.removeEventListener("click", cancelClick), 0);
  if (planDrag.handle.hasPointerCapture(planDrag.id))
    planDrag.handle.releasePointerCapture(planDrag.id);
  planDrag = null;
}
document.addEventListener("pointerdown", (e) => {
  const handle = e.target.closest("[data-plan-drag]");
  if (!handle || busy || modal.open || !e.isPrimary || e.button !== 0) return;
  planDrag = {
    handle,
    id: e.pointerId,
    from: Number(handle.dataset.planDrag),
    x: e.clientX,
    y: e.clientY,
    ghost: null,
    target: null,
  };
  handle.setPointerCapture(e.pointerId);
});
document.addEventListener("pointermove", (e) => {
  const drag = planDrag;
  if (!drag || drag.id !== e.pointerId) return;
  if (!drag.ghost && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < 8)
    return;
  e.preventDefault();
  if (!drag.ghost) {
    drag.ghost = document.createElement("div");
    drag.ghost.className = "plan-drag-ghost";
    drag.ghost.textContent =
      days[drag.from] +
      " · " +
      (state.plan[drag.from].parts.join(" · ") || "休息日");
    drag.ghost.setAttribute("aria-hidden", "true");
    document.body.append(drag.ghost);
    drag.handle.classList.add("dragging");
    // Suppress the synthetic click after dragging; a normal tap still opens the picker.
    drag.cancelClick = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };
    drag.handle.addEventListener("click", drag.cancelClick, { once: true });
  }
  drag.ghost.style.left = Math.min(e.clientX + 12, innerWidth - 170) + "px";
  drag.ghost.style.top = Math.max(0, e.clientY - 50) + "px";
  drag.target?.classList.remove("plan-drop-target");
  drag.target = document
    .elementFromPoint(e.clientX, e.clientY)
    ?.closest("[data-plan-target]");
  if (drag.target && Number(drag.target.dataset.planTarget) !== drag.from)
    drag.target.classList.add("plan-drop-target");
});
document.addEventListener("pointerup", (e) => {
  if (!planDrag || planDrag.id !== e.pointerId) return;
  const { from, target, ghost } = planDrag;
  const to = target ? Number(target.dataset.planTarget) : from;
  finishPlanDrag();
  if (ghost && to !== from)
    movePlannedDay(from, to).catch((err) => toast(err.message));
});
document.addEventListener("pointercancel", finishPlanDrag);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") finishPlanDrag();
});
addEventListener("blur", finishPlanDrag);
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (el) {
    e.preventDefault();
    action(el).catch((err) => toast(err.message));
  }
});
document.addEventListener("change", (e) => {
  if (e.target.id === "backup-file") {
    importFile(e.target.files[0]);
    e.target.value = "";
  }
  if (e.target.id === "trend-exercise") {
    selectedExercise = e.target.value;
    render();
  }
});
document.addEventListener("keydown", (e) => {
  if (
    e.target.matches(".chart-point") &&
    (e.key === "Enter" || e.key === " ")
  ) {
    e.preventDefault();
    action(e.target);
  }
});
document.addEventListener("input", (e) => {
  const el = e.target;
  if (el.matches("[data-field]")) {
    if (!el.checkValidity()) {
      el.classList.add("required-error");
      saveStatus("输入待修正");
      return;
    }
    el.classList.remove("required-error");
    const w = currentWorkout();
    const set =
      w.exercises[Number(el.dataset.entry)].sets[Number(el.dataset.set)];
    set[el.dataset.field] = el.value === "" ? null : Number(el.value);
    if (!editing && set.done) {
      set.done = false;
      const check = el.closest(".set-row").querySelector(".set-check");
      check?.classList.remove("checked");
      check?.setAttribute("aria-pressed", "false");
      check?.setAttribute(
        "aria-label",
        `完成${w.exercises[Number(el.dataset.entry)].name}第${Number(el.dataset.set) + 1}组`,
      );
      if (check) check.textContent = Number(el.dataset.set) + 1;
      const count = document.querySelector(".coach-count"),
        sets = w.exercises.flatMap((e) => e.sets),
        done = sets.filter((s) => s.done).length;
      if (count) count.textContent = `${done} / ${sets.length} 组已打卡`;
      document
        .querySelector(".coach-orbit")
        ?.style.setProperty("--progress", `${(done / sets.length) * 100}%`);
    }
    saveWorkout();
  }
  if (el.id === "workout-date") {
    if (!el.checkValidity() || !validDate(el.value)) {
      saveStatus("日期待修正");
      return;
    }
    currentWorkout().date = el.value;
    saveWorkout();
  }
  if (el.id === "record-month") {
    month = el.value || today().slice(0, 7);
    recordWeek = null;
    render();
  }
});
addEventListener("hashchange", () => {
  if (dirty() && !allowLeave) {
    if (!confirm("放弃尚未保存的修改？原训练记录不会改变。")) {
      history.replaceState(null, "", lastRoute);
      return;
    }
  }
  if (route()[0] !== "edit") {
    editing = null;
    editOriginal = null;
  }
  allowLeave = false;
  lastRoute = location.hash;
  render();
});
addEventListener("beforeunload", (e) => {
  if (dirty() || pending || failed) {
    e.preventDefault();
    e.returnValue = "";
  }
});
try {
  db = await openStore();
  const raw = await readState(db);
  state = upgradeState(raw);
  revision = raw.revision;
  const synced = syncEmptyDraft(state);
  if (raw.version !== state.version || synced)
    state = await writeState(db, state, revision);
  revision = state.revision;
  render();
} catch (err) {
  app.innerHTML = `<div class="boot-error card"><h1>暂时无法读取数据</h1><p>${escape(err.message)}。原数据未被清空。</p>${button("重新加载", "reload", "primary")}</div>`;
}
let updateWorker = null;
async function registerOffline() {
  if (!("serviceWorker" in navigator)) {
    offlineLabel = "当前浏览器不支持离线缓存";
    return;
  }
  try {
    const registration = await navigator.serviceWorker.register("./sw.js");
    const ready = await navigator.serviceWorker.ready;
    const mark = () => {
      if (ready.active && navigator.serviceWorker.controller) {
        offlineLabel = "离线已就绪 · 可断网打开和记录";
        const el = document.querySelector("#offline-status");
        if (el) el.textContent = offlineLabel;
      }
    };
    mark();
    navigator.serviceWorker.addEventListener("controllerchange", mark);
    const offer = () => {
      if (registration.waiting) {
        updateWorker = registration.waiting;
        clearTimeout(toastTimer);
        toastEl.innerHTML = `新版本已准备好，保存后可更新。${button("更新应用", "update", "")}`;
      }
    };
    offer();
    registration.addEventListener("updatefound", () => {
      const worker = registration.installing;
      worker?.addEventListener("statechange", () => {
        if (worker.state === "installed" && navigator.serviceWorker.controller)
          offer();
      });
    });
    if (navigator.storage?.persist) navigator.storage.persist().catch(() => {});
  } catch {
    offlineLabel = "离线缓存未完成，请联网重试";
    const el = document.querySelector("#offline-status");
    if (el) el.textContent = offlineLabel;
  }
}
if (state) registerOffline();
