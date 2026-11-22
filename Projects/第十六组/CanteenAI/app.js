"use strict";

const CANTEENS = {
  // 步行分钟数依据 campus-map.jpg 中可辨认的相对方位设置，仅为课程模拟估算，不代表精确路线。
  "沙塘园食堂": { emoji: "🍛", baseQueue: 7, phase: -5, walk: { "礼东": 9, "礼西": 10, "大礼堂": 8, "图书馆": 4, "五四楼": 5, "东南院": 5, "中山院": 4 } },
  "莘园食堂": { emoji: "🥘", baseQueue: 5, phase: 8, walk: { "礼东": 7, "礼西": 9, "大礼堂": 6, "图书馆": 8, "五四楼": 10, "东南院": 4, "中山院": 5 } },
  "香园食堂": { emoji: "🍜", baseQueue: 6, phase: 3, walk: { "礼东": 9, "礼西": 5, "大礼堂": 10, "图书馆": 8, "五四楼": 7, "东南院": 11, "中山院": 10 } }
};

const LOCATION_MAP = {
  "礼东": [57, 28], "礼西": [42, 27], "大礼堂": [73, 46], "图书馆": [46, 61],
  "五四楼": [38, 77], "东南院": [66, 75], "中山院": [55, 82]
};

const DISH_TEMPLATES = [
  ["红烧鸡腿饭", "鲜香", "米饭", 15, 16, ["高蛋白"], "🍗"], ["番茄鸡蛋面", "酸甜", "面食", 12, 14, ["无花生"], "🍜"],
  ["麻辣香锅", "香辣", "自选", 22, 20, [], "🌶️"], ["青椒肉丝饭", "鲜香", "米饭", 14, 15, ["高蛋白"], "🍚"],
  ["清汤牛肉面", "清淡", "面食", 16, 16, ["高蛋白", "无花生"], "🍜"], ["三鲜馄饨", "清淡", "面食", 11, 13, ["无花生"], "🥟"],
  ["糖醋里脊饭", "酸甜", "米饭", 17, 17, [], "🍱"], ["香菇青菜饭", "清淡", "米饭", 10, 14, ["素食", "无花生"], "🥬"],
  ["咖喱鸡肉饭", "鲜香", "米饭", 16, 17, ["高蛋白"], "🍛"], ["酸辣粉", "香辣", "粉面", 11, 13, [], "🍲"],
  ["鸡丝凉面", "鲜香", "面食", 13, 12, ["高蛋白"], "🥢"], ["菌菇豆腐煲", "清淡", "小锅", 15, 18, ["素食", "高蛋白", "无花生"], "🍲"],
  ["黑椒牛柳饭", "鲜香", "米饭", 19, 17, ["高蛋白"], "🥩"], ["蔬菜鸡蛋饼", "清淡", "面点", 9, 10, ["素食", "无花生"], "🥞"],
  ["重庆小面", "香辣", "面食", 10, 12, ["无花生"], "🍜"], ["鱼香茄子饭", "酸甜", "米饭", 12, 15, ["素食"], "🍆"],
  ["玉米排骨汤饭", "清淡", "汤饭", 18, 20, ["高蛋白", "无花生"], "🥣"], ["葱油拌面", "鲜香", "面食", 9, 11, ["素食", "无花生"], "🍝"],
  ["白灼时蔬饭", "清淡", "米饭", 11, 14, ["素食", "无花生"], "🥦"], ["豆花鸡片饭", "鲜香", "米饭", 16, 17, ["高蛋白", "无花生"], "🥣"]
];

// 20 类模拟菜品 × 3 个食堂 = 60 条本地模拟记录；不声称来自食堂真实菜单。
const DISHES = Object.keys(CANTEENS).flatMap((canteen, ci) => DISH_TEMPLATES.map((d, di) => ({
  id: `dish-${ci + 1}-${di + 1}`,
  name: `${d[0]}${ci === 0 ? "" : ci === 1 ? "·莘园模拟" : "·香园模拟"}`,
  baseName: d[0], taste: d[1], category: d[2], price: d[3] + [0, 1, 1][ci] + (di % 5 === 0 ? 1 : 0),
  eatTime: d[4] + (ci % 2), tags: d[5], emoji: d[6], canteen,
  spicy: ["香辣", "酸辣粉", "重庆小面"].some(x => d[1] === x || d[0] === x), containsPeanut: [2, 6, 9, 15].includes(di)
})));

const state = {
  departure: 705,
  selectedCanteen: "沙塘园食堂",
  currentResults: [],
  history: readStore("canteenai_history", []),
  favorites: readStore("canteenai_favorites", []),
  feedback: readStore("canteenai_feedback", {}),
  blindSeen: [],
  teamCount: 2
};

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

function readStore(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem(key)); return v ?? fallback; } catch { return fallback; }
}
function writeStore(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
function formatTime(min) { return `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`; }

function crowdLevel(canteen, minute) {
  const c = CANTEENS[canteen];
  const lunchPeak = 18 * Math.exp(-Math.pow((minute - (725 + c.phase)) / 26, 2));
  const latePeak = 6 * Math.exp(-Math.pow((minute - (775 - c.phase / 2)) / 35, 2));
  const wave = 1.2 * Math.sin((minute + c.phase * 3) / 13);
  return clamp(Math.round(c.baseQueue + lunchPeak + latePeak + wave), 2, 29);
}

function crowdPercent(canteen, minute) { return clamp(Math.round((crowdLevel(canteen, minute) / 29) * 100), 8, 100); }

function getPreferences() {
  return {
    budget: +$("#budget").value,
    freeTime: +$("#freeTime").value,
    location: $("#location").value,
    taste: $("input[name=taste]:checked").value,
    diets: $$("#dietChips input:checked").map(x => x.value)
  };
}

function scoreDish(dish, prefs) {
  if (prefs.diets.includes("不辣") && dish.spicy) return null;
  if (prefs.diets.includes("无花生") && dish.containsPeanut) return null;
  if (prefs.diets.includes("素食") && !dish.tags.includes("素食")) return null;
  if (prefs.diets.includes("高蛋白") && !dish.tags.includes("高蛋白")) return null;

  const walk = CANTEENS[dish.canteen].walk[prefs.location];
  const queue = crowdLevel(dish.canteen, state.departure);
  const total = walk + queue + dish.eatTime;
  const budgetScore = dish.price <= prefs.budget ? clamp(100 - (prefs.budget - dish.price) * 1.7, 70, 100) : clamp(100 - (dish.price - prefs.budget) * 22, 0, 65);
  const tasteScore = prefs.taste === "不限" ? 82 : dish.taste === prefs.taste ? 100 : dish.taste === "鲜香" ? 68 : 48;
  const queueScore = clamp(108 - queue * 4, 5, 100);
  const distanceScore = clamp(110 - walk * 6, 20, 100);
  const timeScore = total <= prefs.freeTime ? clamp(100 - (prefs.freeTime - total) * .35, 76, 100) : clamp(75 - (total - prefs.freeTime) * 10, 0, 75);
  const recentIndex = state.history.findIndex(h => h.dishId === dish.id);
  const favorite = state.favorites.includes(dish.id);
  const liked = state.feedback[dish.id] || 0;
  const memoryScore = clamp(72 + (favorite ? 22 : 0) + liked * 9 - (recentIndex >= 0 ? Math.max(12, 35 - recentIndex * 5) : 0), 20, 100);
  let score = budgetScore * .20 + tasteScore * .20 + queueScore * .18 + distanceScore * .17 + timeScore * .15 + memoryScore * .10;
  if (dish.price > prefs.budget) score -= 7;
  if (total > prefs.freeTime) score -= 10;
  return { dish, score: Math.round(clamp(score, 1, 99)), walk, queue, total, factors: { budgetScore, tasteScore, queueScore, distanceScore, timeScore, memoryScore } };
}

function recommend(showNotice = false) {
  const prefs = getPreferences();
  const results = DISHES.map(d => scoreDish(d, prefs)).filter(Boolean).sort((a, b) => b.score - a.score || a.total - b.total);
  state.currentResults = results;
  renderResults(results, prefs);
  updateRadar();
  if (showNotice) toast(`已从 ${results.length} 个符合忌口条件的方案中完成排序`);
}

function reasonFor(r, prefs) {
  const reasons = [];
  if (r.dish.price <= prefs.budget) reasons.push(`价格在 ${prefs.budget} 元预算内`);
  if (prefs.taste !== "不限" && r.dish.taste === prefs.taste) reasons.push(`符合“${prefs.taste}”口味`);
  if (r.queue <= 8) reasons.push("预测排队较短");
  if (r.walk <= 6) reasons.push(`从${prefs.location}步行较近`);
  if (r.total <= prefs.freeTime) reasons.push(`能在 ${prefs.freeTime} 分钟空闲内完成`);
  if (state.favorites.includes(r.dish.id)) reasons.push("是你收藏过的选择");
  return reasons.slice(0, 3).join("，") || "在预算、距离与总耗时之间取得较好平衡";
}

function renderResults(results, prefs) {
  const host = $("#topRecommendation");
  if (!results.length) {
    host.innerHTML = `<div class="empty-state"><b>没有满足全部忌口的菜品</b><br>请放宽一个筛选条件后重试。</div>`;
    $("#alternatives").innerHTML = ""; return;
  }
  const r = results[0], d = r.dish;
  host.innerHTML = `<div class="rec-top"><span class="rank-pill">雷达首选 · 模拟推荐</span><div class="score-ring" style="--score:${r.score}"><div><b>${r.score}%</b><small>匹配度</small></div></div></div>
    <div class="rec-main"><h3>${d.emoji} ${d.name}</h3><p>${d.canteen} · ${d.taste} · ${d.category}</p></div>
    <div class="rec-metrics"><div class="metric"><span>价格</span><b>¥${d.price}</b></div><div class="metric"><span>步行</span><b>${r.walk} 分钟</b></div><div class="metric"><span>预测排队</span><b>${r.queue} 分钟</b></div><div class="metric"><span>总耗时</span><b>${r.total} 分钟</b></div></div>
    <div class="reason-box"><b>为什么推荐：</b>${reasonFor(r, prefs)}。</div>
    <div class="rec-actions"><button class="primary-mini" data-action="eat" data-id="${d.id}">就吃这个</button><button data-action="favorite" data-id="${d.id}">${state.favorites.includes(d.id) ? "★ 已收藏" : "☆ 收藏"}</button><button data-action="like" data-id="${d.id}">👍 更喜欢</button><button data-action="refresh">换一批</button></div>`;
  $("#alternatives").innerHTML = results.slice(1, 5).map(r2 => `<article class="alt-card"><div class="alt-icon">${r2.dish.emoji}</div><div><h4>${r2.dish.name}</h4><p>${r2.dish.canteen} · ¥${r2.dish.price} · 共${r2.total}分钟</p></div><span class="alt-score">${r2.score}</span></article>`).join("");
  updateTimeImpact(r);
}

function parseNaturalLanguage() {
  const text = $("#nlInput").value.trim();
  if (!text) { toast("请先输入一句用餐需求"); return; }
  const found = [];
  const money = text.match(/(?:预算|不超过|最多)?\s*(\d{1,2})\s*元/);
  if (money) { $("#budget").value = clamp(+money[1], 8, 35); found.push(`预算 ${$("#budget").value} 元`); }
  const halfHour = /半小时|30分钟|三十分钟/.test(text);
  const minutes = text.match(/(?:只有|空闲|剩|共)?\s*(\d{2})\s*分钟/);
  if (halfHour || minutes) { $("#freeTime").value = halfHour ? 30 : clamp(+minutes[1], 20, 90); found.push(`空闲 ${$("#freeTime").value} 分钟`); }
  const location = ["礼东", "礼西", "大礼堂", "图书馆", "五四楼", "东南院", "中山院"].find(x => text.includes(x));
  if (location && [...$("#location").options].some(o => o.value === location)) { $("#location").value = location; found.push(`位置 ${location}`); }
  const tasteMap = [[/辣|重口/, "香辣"], [/清淡|少油|健康/, "清淡"], [/酸甜|番茄/, "酸甜"], [/鲜|香/, "鲜香"]];
  const taste = tasteMap.find(([re]) => re.test(text));
  if (taste) { const input = $(`input[name=taste][value="${taste[1]}"]`); input.checked = true; found.push(`口味 ${taste[1]}`); }
  $$("#dietChips input").forEach(i => i.checked = false);
  [[/不吃辣|不要辣|不能吃辣/, "不辣"], [/花生过敏|不要花生/, "无花生"], [/素食|吃素/, "素食"], [/高蛋白|健身/, "高蛋白"]].forEach(([re, val]) => { if (re.test(text)) { $(`#dietChips input[value="${val}"]`).checked = true; found.push(val); } });
  if (/面|粉/.test(text) && !taste) found.push("偏好面食（用于结果解释）");
  syncLabels();
  $("#parseResult").textContent = found.length ? `已识别：${found.join(" · ")}` : "未识别出明确数字或关键词，已按当前表单条件推荐";
  recommend(true);
  if (/面|粉/.test(text)) {
    // 明确表达“想吃面”时先按品类满足度分组，再在组内使用六因素总分排序。
    state.currentResults.sort((a, b) => Number(/面|粉/.test(b.dish.category)) - Number(/面|粉/.test(a.dish.category)) || b.score - a.score);
    renderResults(state.currentResults, getPreferences());
  }
}

function updateRadar() {
  $("#simTimeLabel").textContent = formatTime(state.departure);
  const p = state.departure < 700 ? "错峰准备期" : state.departure < 760 ? "午餐高峰" : "高峰回落期";
  $("#mealPeriod").textContent = p;
  $$(".canteen-node").forEach(node => {
    const name = node.dataset.canteen, wait = crowdLevel(name, state.departure), crowd = crowdPercent(name, state.departure);
    node.querySelector("small").textContent = `${wait} 分钟`;
    node.style.background = crowd > 72 ? "#cc5a3e" : crowd > 48 ? "#d88b42" : "#2f745d";
    node.style.color = crowd > 72 ? "#e36449" : crowd > 48 ? "#d89545" : "#2f745d";
    node.classList.toggle("selected", name === state.selectedCanteen);
    node.querySelector("b").style.color = "white"; node.querySelector("small").style.color = "white";
  });
  const location = $("#location").value, marker = $(".you-marker"), point = LOCATION_MAP[location] || LOCATION_MAP["礼东"];
  marker.style.left = `${point[0]}%`; marker.style.top = `${point[1]}%`; $("#youMarkerLabel").textContent = `${location} · 你在这里`;
  $("#selectedCanteen").textContent = state.selectedCanteen;
  drawChart();
}

function drawChart() {
  const canvas = $("#trendChart"), rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(320, rect.width * dpr); canvas.height = Math.max(220, rect.height * dpr);
  const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
  const w = rect.width, h = rect.height, pad = { l: 35, r: 12, t: 20, b: 30 };
  ctx.clearRect(0, 0, w, h); ctx.font = "11px Microsoft YaHei"; ctx.fillStyle = "#7f8c84";
  [0, 25, 50, 75, 100].forEach(v => { const y = pad.t + (h - pad.t - pad.b) * (1 - v / 100); ctx.beginPath(); ctx.strokeStyle = "#dfe2d9"; ctx.lineWidth = 1; ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke(); ctx.fillText(`${v}%`, 2, y + 4); });
  const times = Array.from({ length: 31 }, (_, i) => 660 + i * 5);
  const x = i => pad.l + i / (times.length - 1) * (w - pad.l - pad.r), y = v => pad.t + (h - pad.t - pad.b) * (1 - v / 100);
  function line(vals, color, dashed = false) { ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = dashed ? 1.5 : 3; ctx.setLineDash(dashed ? [6, 5] : []); vals.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))); ctx.stroke(); ctx.setLineDash([]); }
  const vals = times.map(t => crowdPercent(state.selectedCanteen, t));
  const avg = times.map(t => Object.keys(CANTEENS).reduce((s, c) => s + crowdPercent(c, t), 0) / Object.keys(CANTEENS).length);
  line(avg, "#91a197", true); line(vals, "#ee7437");
  const idx = Math.round((state.departure - 660) / 5); ctx.beginPath(); ctx.fillStyle = "#ee7437"; ctx.arc(x(idx), y(vals[idx]), 5, 0, Math.PI * 2); ctx.fill();
  [[0, "11:00"], [6, "11:30"], [12, "12:00"], [18, "12:30"], [24, "13:00"], [30, "13:30"]].forEach(([i, label]) => { ctx.fillStyle = "#7f8c84"; ctx.fillText(label, x(i) - 15, h - 7); });
}

function updateTimeImpact(top = state.currentResults[0]) {
  if (!top) return;
  const waits = Object.keys(CANTEENS).map(c => crowdLevel(c, state.departure));
  const fastest = Object.keys(CANTEENS)[waits.indexOf(Math.min(...waits))];
  $("#timeImpact").innerHTML = `<div><span>首选总耗时</span><b>${top.total} 分钟</b></div><div><span>此刻最短队列</span><b>${fastest.replace("食堂", "")}</b></div>`;
}

function renderMemory() {
  $("#memoryScore").textContent = state.history.length;
  const tastes = {};
  state.history.forEach(h => { tastes[h.taste] = (tastes[h.taste] || 0) + 1; });
  const sorted = Object.entries(tastes).sort((a, b) => b[1] - a[1]);
  $("#profileText").textContent = sorted.length ? `当前更偏爱${sorted.slice(0, 2).map(x => x[0]).join("、")}口味。推荐会对最近吃过的菜品降权，鼓励多样化。` : "还没有用餐记录，完成一次选择后雷达会开始学习。";
  $("#profileTags").innerHTML = sorted.length ? sorted.slice(0, 3).map(x => `<span>${x[0]} × ${x[1]}</span>`).join("") : "<span>等待探索</span>";
  $("#historyList").innerHTML = state.history.length ? state.history.slice(0, 5).map(h => `<div class="history-item"><span class="food-emoji">${h.emoji}</span><div><b>${h.name}</b><small>${h.canteen} · ${h.date}</small></div></div>`).join("") : `<div class="empty-state">还没有记录</div>`;
  const favDishes = state.favorites.map(id => DISHES.find(d => d.id === id)).filter(Boolean);
  $("#favoriteList").innerHTML = favDishes.length ? favDishes.slice(0, 5).map(d => `<div class="history-item"><span class="food-emoji">${d.emoji}</span><div><b>${d.name}</b><small>${d.canteen} · ¥${d.price}</small></div><button data-remove-fav="${d.id}" aria-label="取消收藏">×</button></div>`).join("") : `<div class="empty-state">点一下推荐卡片的“收藏”</div>`;
}

// ---------- 四模式共享工具 ----------
function passesDiet(dish, diets) {
  return !(diets.includes("不辣") && dish.spicy) && !(diets.includes("无花生") && dish.containsPeanut) &&
    !(diets.includes("素食") && !dish.tags.includes("素食")) && !(diets.includes("高蛋白") && !dish.tags.includes("高蛋白"));
}

function switchMode(mode) {
  $$(".mode-tab").forEach(tab => { const active = tab.dataset.mode === mode; tab.classList.toggle("active", active); tab.setAttribute("aria-selected", String(active)); });
  $$(".mode-pane").forEach(pane => { const active = pane.dataset.pane === mode; pane.hidden = !active; pane.classList.toggle("active", active); });
  $(".scenario-picker").style.visibility = mode === "smart" ? "visible" : "hidden";
  if (mode === "compare") setTimeout(() => { if ($("#compareRadar")) drawCompareRadar(JSON.parse($("#compareRadar").dataset.values || "[]")); }, 20);
}

// ---------- 选择困难模式 ----------
function candidateRow(index) {
  return `<div class="candidate-row" data-candidate="${index}"><div class="candidate-main"><span class="candidate-index">${index + 1}</span><input class="candidate-name" list="dishOptions" placeholder="输入或选择菜品" aria-label="候选菜品 ${index + 1}">${index === 2 ? '<button class="candidate-remove" type="button" aria-label="清空第三个候选">×</button>' : ""}</div>
    <div class="candidate-details"><input class="candidate-price" type="number" min="1" max="99" placeholder="价格"><select class="candidate-taste"><option>鲜香</option><option>清淡</option><option>香辣</option><option>酸甜</option></select><select class="candidate-canteen">${Object.keys(CANTEENS).map(c => `<option>${c}</option>`).join("")}</select></div><p class="candidate-hint">可手动修改价格、口味与食堂</p></div>`;
}

function renderCompareInputs() {
  $("#dishOptions").innerHTML = [...new Set(DISHES.map(d => d.baseName))].map(n => `<option value="${n}"></option>`).join("");
  $("#compareInputs").innerHTML = [0, 1, 2].map(candidateRow).join("");
}

function fillCandidate(row, name) {
  const dish = DISHES.find(d => d.name === name || d.baseName === name);
  if (!dish) { row.querySelector(".candidate-hint").textContent = name ? "数据库中没有该菜品，请手动补充信息" : "可手动修改价格、口味与食堂"; return; }
  row.querySelector(".candidate-price").value = dish.price; row.querySelector(".candidate-taste").value = dish.taste; row.querySelector(".candidate-canteen").value = dish.canteen;
  row.querySelector(".candidate-hint").textContent = `已匹配模拟数据库：${dish.canteen}`;
}

function collectCandidates() {
  return $$(".candidate-row").map((row, i) => {
    const name = row.querySelector(".candidate-name").value.trim(); if (!name) return null;
    const exact = DISHES.find(d => d.name === name || d.baseName === name);
    return { id: exact?.id || `manual-${i}`, name, baseName: exact?.baseName || name, emoji: exact?.emoji || "🍽️", price: +(row.querySelector(".candidate-price").value || exact?.price || 15), taste: row.querySelector(".candidate-taste").value, canteen: row.querySelector(".candidate-canteen").value, manual: !exact };
  }).filter(Boolean);
}

function compareDimension(candidate, location, taste) {
  const queue = crowdLevel(candidate.canteen, state.departure), walk = CANTEENS[candidate.canteen].walk[location];
  const eaten = state.history.filter(h => h.dishId === candidate.id || h.name.includes(candidate.baseName));
  return {
    price: clamp(110 - candidate.price * 3.2, 15, 100),
    taste: taste === "不限" ? 80 : candidate.taste === taste ? 100 : candidate.taste === "鲜香" ? 65 : 45,
    queue: clamp(108 - queue * 4, 8, 100), distance: clamp(110 - walk * 6, 15, 100),
    memory: clamp(68 + (state.favorites.includes(candidate.id) ? 25 : 0) + (state.feedback[candidate.id] || 0) * 8 - eaten.length * 8, 25, 100), queueMin: queue, walk
  };
}

function runComparison(e) {
  e?.preventDefault(); const candidates = collectCandidates();
  if (candidates.length < 2 || candidates.length > 3) { toast("请填写 2—3 个候选菜品"); return; }
  const location = $("#compareLocation").value, taste = $("#compareTaste").value;
  const scored = candidates.map(c => { const d = compareDimension(c, location, taste); return { c, d, score: Math.round(d.price * .20 + d.taste * .25 + d.queue * .20 + d.distance * .18 + d.memory * .17) }; }).sort((a, b) => b.score - a.score);
  const winner = scored[0], labels = { price: "价格优势", taste: "口味匹配", queue: "排队效率", distance: "距离便利", memory: "历史偏好" };
  $("#compareResult").innerHTML = `<div class="compare-chart-wrap"><h3>五维差异雷达</h3><p>所有分值均由当前模拟数据即时计算</p><canvas class="compare-radar" id="compareRadar" aria-label="候选菜品雷达对比图"></canvas><div class="radar-legend">${scored.map((x, i) => `<span><i style="background:${["#ee7437", "#24614f", "#6d79b8"][i]}"></i>${x.c.name}</span>`).join("")}</div></div>
    <div><div class="winner-card"><span class="rank-pill">最终推荐${winner.c.manual ? " · 手动菜品" : ""}</span><h3>${winner.c.emoji} ${winner.c.name}</h3><div class="winner-score">${winner.score}<small> / 100</small></div><p>${winner.c.canteen} · ¥${winner.c.price} · 排队 ${winner.d.queueMin} 分钟 · 步行 ${winner.d.walk} 分钟</p><div class="loser-reasons"><h4>其他候选未胜出的原因</h4>${scored.slice(1).map(x => { const gap = Object.keys(labels).sort((a, b) => (winner.d[b] - x.d[b]) - (winner.d[a] - x.d[a]))[0]; return `<div class="loser-item"><b>${x.c.name}（${x.score}分）</b><br>${labels[gap]}比首选低 ${Math.max(0, Math.round(winner.d[gap] - x.d[gap]))} 分${x.c.manual ? "；数据由你手动补充" : ""}</div>`; }).join("")}</div></div></div>`;
  const values = scored.map(x => ({ name: x.c.name, values: [x.d.price, x.d.taste, x.d.queue, x.d.distance, x.d.memory] }));
  $("#compareRadar").dataset.values = JSON.stringify(values); drawCompareRadar(values); toast("对比完成：五个维度已归一化到 100 分");
}

function drawCompareRadar(series) {
  const canvas = $("#compareRadar"); if (!canvas || !series.length) return;
  const rect = canvas.getBoundingClientRect(), dpr = devicePixelRatio || 1; canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr); const w = rect.width, h = rect.height, cx = w / 2, cy = h / 2 + 6, radius = Math.min(w, h) * .32, axes = 5;
  ctx.clearRect(0, 0, w, h); ctx.font = "12px Microsoft YaHei"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  for (let level = 1; level <= 4; level++) { ctx.beginPath(); for (let i = 0; i < axes; i++) { const a = -Math.PI / 2 + i * Math.PI * 2 / axes, r = radius * level / 4; const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.closePath(); ctx.strokeStyle = "#d3d9d0"; ctx.stroke(); }
  ["价格", "口味", "排队", "距离", "偏好"].forEach((label, i) => { const a = -Math.PI / 2 + i * Math.PI * 2 / axes; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * radius, cy + Math.sin(a) * radius); ctx.strokeStyle = "#d3d9d0"; ctx.stroke(); ctx.fillStyle = "#66776e"; ctx.fillText(label, cx + Math.cos(a) * (radius + 22), cy + Math.sin(a) * (radius + 22)); });
  series.forEach((s, si) => { const color = ["#ee7437", "#24614f", "#6d79b8"][si]; ctx.beginPath(); s.values.forEach((v, i) => { const a = -Math.PI / 2 + i * Math.PI * 2 / axes, r = radius * v / 100; const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); ctx.globalAlpha = .14; ctx.fillStyle = color; ctx.fill(); ctx.globalAlpha = 1; ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.stroke(); });
}

// ---------- 盲盒探索模式 ----------
function runBlindBox(e) {
  e?.preventDefault(); const level = $("input[name=adventure]:checked").value, diets = $$("#blindDietChips input:checked").map(x => x.value), location = $("#blindLocation").value;
  const weights = { safe: [.7, .3], medium: [.5, .5], bold: [.3, .7] }[level];
  const tasteCounts = {}; state.history.forEach(h => tasteCounts[h.taste] = (tasteCounts[h.taste] || 0) + 1); const preferred = Object.entries(tasteCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || getPreferences().taste;
  const candidates = DISHES.filter(d => passesDiet(d, diets)).map(d => {
    const exactEaten = state.history.filter(h => h.dishId === d.id).length, similarEaten = state.history.filter(h => h.taste === d.taste).length;
    const similarity = preferred === "不限" ? 75 : d.taste === preferred ? 100 : d.taste === "鲜香" ? 70 : 48;
    const novelty = clamp(100 - exactEaten * 50 - similarEaten * 4 - (state.blindSeen.includes(d.id) ? 35 : 0), 8, 100);
    const practical = (clamp(108 - crowdLevel(d.canteen, state.departure) * 4, 10, 100) + clamp(110 - CANTEENS[d.canteen].walk[location] * 6, 15, 100)) / 2;
    const feedback = (state.feedback[d.id] || 0) * 7; return { d, similarity, novelty, practical, score: similarity * weights[0] * .82 + novelty * weights[1] * .82 + practical * .18 + feedback };
  }).sort((a, b) => b.score - a.score);
  if (!candidates.length) { $("#blindResult").innerHTML = `<h3>没有安全可行的盲盒</h3><p>当前忌口组合过滤掉了全部模拟菜品。请放宽非过敏类条件后重试；系统不会为了探索强行推荐。</p>`; return; }
  const pick = candidates[0]; state.blindSeen.push(pick.d.id); const box = $("#blindBox"); box.classList.remove("revealed"); box.classList.add("opening");
  $("#blindResult").innerHTML = `<h3>正在计算探索边界…</h3><p>先过滤忌口，再评估相似度、新颖程度与时间成本。</p>`;
  setTimeout(() => { box.classList.remove("opening"); box.classList.add("revealed"); box.querySelector(".box-body span").textContent = pick.d.emoji; $("#blindResult").innerHTML = `<span class="discovery-pill">${{ safe: "稳妥尝鲜", medium: "适度冒险", bold: "大胆探索" }[level]} · 模拟推荐</span><h3>${pick.d.name}</h3><p>${pick.d.canteen} · ¥${pick.d.price}。${pick.novelty >= 75 ? "你还很少接触这类菜品" : "它与你熟悉的口味有连接"}，同时${pick.d.taste === preferred ? `保留了你偏爱的${preferred}风格` : `用${pick.d.taste}口味扩大探索半径`}。</p><div class="discovery-metrics"><div><span>偏好相似度</span><b>${Math.round(pick.similarity)}%</b></div><div><span>新颖程度</span><b>${Math.round(pick.novelty)}%</b></div><div><span>综合探索分</span><b>${Math.round(pick.score)}</b></div></div><div class="blind-feedback"><button data-blind="like" data-id="${pick.d.id}">👍 喜欢</button><button data-blind="dislike" data-id="${pick.d.id}">👎 不喜欢</button><button data-blind="eaten" data-id="${pick.d.id}">✓ 吃过了</button><button data-blind="next">再开一个</button></div>`; }, 720);
}

function handleBlindFeedback(e) {
  const btn = e.target.closest("[data-blind]"); if (!btn) return; const action = btn.dataset.blind; if (action === "next") { runBlindBox(); return; }
  const dish = DISHES.find(d => d.id === btn.dataset.id); if (!dish) return;
  if (action === "like" || action === "dislike") { state.feedback[dish.id] = clamp((state.feedback[dish.id] || 0) + (action === "like" ? 1 : -2), -3, 3); writeStore("canteenai_feedback", state.feedback); toast(action === "like" ? "已学习：提高相似菜品偏好" : "已学习：降低相似菜品偏好"); }
  if (action === "eaten") { state.history.unshift({ dishId: dish.id, name: dish.name, canteen: dish.canteen, taste: dish.taste, emoji: dish.emoji, date: new Date().toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) }); state.history = state.history.slice(0, 30); writeStore("canteenai_history", state.history); renderMemory(); toast("已加入饮食记忆"); }
}

// ---------- 多人组队模式 ----------
function memberRow(index, data = {}) {
  return `<div class="member-row" data-member="${index}"><input class="member-name" value="${data.name || `同学${index + 1}`}" aria-label="成员昵称"><input class="member-budget" type="number" min="8" max="50" value="${data.budget || 18}" aria-label="预算"><select class="member-taste"><option>不限</option><option>香辣</option><option>清淡</option><option>鲜香</option><option>酸甜</option></select><select class="member-diet"><option value="">无忌口</option><option value="不辣">不吃辣</option><option value="无花生">避开花生</option><option value="素食">素食</option><option value="高蛋白">高蛋白</option></select><input class="member-time" type="number" min="20" max="90" value="${data.time || 45}" aria-label="用餐时间"><button type="button" data-remove-member aria-label="移除成员">×</button></div>`;
}

function renderMembers(data) {
  const existing = data || Array.from({ length: state.teamCount }, (_, i) => ({ name: `同学${i + 1}` })); state.teamCount = existing.length;
  $("#memberList").innerHTML = existing.map((d, i) => memberRow(i, d)).join("");
  existing.forEach((d, i) => { const row = $$(".member-row")[i]; if (d.taste) row.querySelector(".member-taste").value = d.taste; if (d.diet) row.querySelector(".member-diet").value = d.diet; });
}

function teamDishScore(dish, member) {
  if (!passesDiet(dish, member.diet ? [member.diet] : [])) return null;
  const queue = crowdLevel(dish.canteen, state.departure), walk = CANTEENS[dish.canteen].walk[getPreferences().location], total = queue + walk + dish.eatTime;
  if (dish.price > member.budget || total > member.time) return null;
  const budget = clamp(105 - Math.abs(member.budget - dish.price) * 3, 55, 100), taste = member.taste === "不限" ? 82 : member.taste === dish.taste ? 100 : dish.taste === "鲜香" ? 63 : 42;
  const time = clamp(110 - total * 1.6, 35, 100), pref = clamp(70 + (state.favorites.includes(dish.id) ? 18 : 0) + (state.feedback[dish.id] || 0) * 7, 35, 100);
  return { dish, score: Math.round(budget * .27 + taste * .35 + time * .25 + pref * .13), total };
}

function runTeam(e) {
  e?.preventDefault(); const members = $$(".member-row").map(row => ({ name: row.querySelector(".member-name").value.trim() || "未命名成员", budget: +row.querySelector(".member-budget").value, taste: row.querySelector(".member-taste").value, diet: row.querySelector(".member-diet").value, time: +row.querySelector(".member-time").value }));
  if (members.length < 2 || members.length > 6) { toast("组队人数需要在 2—6 人之间"); return; }
  const plans = Object.keys(CANTEENS).map(canteen => {
    const picks = members.map(m => DISHES.filter(d => d.canteen === canteen).map(d => teamDishScore(d, m)).filter(Boolean).sort((a, b) => b.score - a.score)[0]);
    if (picks.some(x => !x)) return null; const scores = picks.map(x => x.score), avg = scores.reduce((a, b) => a + b, 0) / scores.length, min = Math.min(...scores);
    return { canteen, picks, avg, min, fairness: avg * .6 + min * .4 };
  }).filter(Boolean).sort((a, b) => b.fairness - a.fairness);
  if (!plans.length) { $("#teamResult").innerHTML = `<div class="no-solution"><span>🧩</span><h3>暂时没有共同可行方案</h3><p>至少一位成员在每个食堂都受到预算、忌口或时间约束。系统不会强行推荐，请尝试延长用餐时间或调整非过敏类条件。</p></div>`; return; }
  const p = plans[0], tastes = [...new Set(members.map(m => m.taste).filter(t => t !== "不限"))], budgets = members.map(m => m.budget), diets = members.filter(m => m.diet);
  const conflicts = [tastes.length > 1 ? `存在 ${tastes.join("、")} 的口味差异` : "成员口味较一致", Math.max(...budgets) - Math.min(...budgets) >= 8 ? `预算跨度达到 ${Math.max(...budgets) - Math.min(...budgets)} 元` : "预算区间接近", diets.length ? `${diets.length} 位成员有硬性饮食约束，已优先过滤` : "没有硬性忌口冲突"];
  $("#teamResult").innerHTML = `<div class="team-result-head"><div><span class="kicker">FAIR GROUP PLAN · 模拟推荐</span><h3>${CANTEENS[p.canteen].emoji} ${p.canteen}</h3><p>同一食堂、各选所爱；公平目标 = 平均满意度 60% + 最低满意度 40%</p></div><div class="fairness-badge"><b>${Math.round(p.fairness)}</b><small>公平指数</small></div></div><div class="member-results">${members.map((m, i) => `<div class="member-result"><div><b>${m.name}</b><small>${m.taste}${m.diet ? ` · ${m.diet}` : ""}</small></div><div><b>${p.picks[i].dish.emoji} ${p.picks[i].dish.name}</b><small>¥${p.picks[i].dish.price} · 总耗时 ${p.picks[i].total} 分钟</small><div class="satisfaction-bar"><i style="width:${p.picks[i].score}%"></i></div></div><span class="satisfaction-score">${p.picks[i].score}</span></div>`).join("")}</div><div class="conflict-box"><b>偏好冲突分析：</b>${conflicts.join("；")}。最低个人满意度为 ${Math.round(p.min)} 分，未用高平均分掩盖低分成员。</div>`;
  toast(`已比较 ${Object.keys(CANTEENS).length} 个共同食堂的公平方案`);
}

function handleRecommendationAction(e) {
  const btn = e.target.closest("button[data-action]"); if (!btn) return;
  const action = btn.dataset.action, dish = DISHES.find(d => d.id === btn.dataset.id);
  if (action === "refresh") { state.currentResults.push(state.currentResults.shift()); renderResults(state.currentResults, getPreferences()); toast("已换一组推荐顺序"); return; }
  if (!dish) return;
  if (action === "eat") {
    state.history.unshift({ dishId: dish.id, name: dish.name, canteen: dish.canteen, taste: dish.taste, emoji: dish.emoji, date: new Date().toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) });
    state.history = state.history.slice(0, 30); writeStore("canteenai_history", state.history); renderMemory(); recommend(); toast(`已记录：${dish.name}`);
  }
  if (action === "favorite") {
    state.favorites = state.favorites.includes(dish.id) ? state.favorites.filter(id => id !== dish.id) : [...state.favorites, dish.id];
    writeStore("canteenai_favorites", state.favorites); renderMemory(); recommend(); toast(state.favorites.includes(dish.id) ? "已加入收藏" : "已取消收藏");
  }
  if (action === "like") { state.feedback[dish.id] = clamp((state.feedback[dish.id] || 0) + 1, -2, 3); writeStore("canteenai_feedback", state.feedback); recommend(); toast("偏好已学习，下次会提高相似方案权重"); }
}

const SCENARIOS = {
  rush: { budget: 18, time: 30, location: "礼东", taste: "鲜香", diets: [], text: "下午还有课，只有半小时，我在礼东，预算18元，想吃鲜香的" },
  budget: { budget: 12, time: 50, location: "大礼堂", taste: "不限", diets: [], text: "月底预算12元，想找便宜又管饱的" },
  comfort: { budget: 18, time: 45, location: "图书馆", taste: "鲜香", diets: ["无花生"], text: "天气降温，想吃一碗热乎的面，预算18元" },
  light: { budget: 25, time: 50, location: "五四楼", taste: "清淡", diets: ["高蛋白", "不辣"], text: "我在五四楼，健身后想吃清淡高蛋白，不吃辣" }
};

function applyScenario(key) {
  const s = SCENARIOS[key]; if (!s) return;
  $("#budget").value = s.budget; $("#freeTime").value = s.time; $("#location").value = s.location; $("#nlInput").value = s.text;
  $(`input[name=taste][value="${s.taste}"]`).checked = true;
  $$("#dietChips input").forEach(i => i.checked = s.diets.includes(i.value));
  syncLabels(); recommend(); toast(`已载入场景：${$("#scenarioSelect").selectedOptions[0].textContent}`);
}

function syncLabels() { $("#budgetValue").textContent = $("#budget").value; $("#freeTimeValue").textContent = $("#freeTime").value; }
let toastTimer;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2400); }

function migrateLegacyMemory() {
  if (localStorage.getItem("canteenai_schema") === "siplou-3canteens-v1") return;
  const remapId = id => /^dish-1-/.test(id || "") ? id : /^dish-2-/.test(id || "") ? id.replace("dish-2-", "dish-3-") : null;
  state.history = state.history.map(h => {
    const id = h.canteen === "沙塘园食堂" ? h.dishId : h.canteen === "香园食堂" ? remapId(h.dishId) : null;
    const dish = DISHES.find(d => d.id === id); return dish ? { ...h, dishId: dish.id, name: dish.name, canteen: dish.canteen, taste: dish.taste, emoji: dish.emoji } : null;
  }).filter(Boolean);
  state.favorites = [...new Set(state.favorites.map(remapId).filter(id => DISHES.some(d => d.id === id)))];
  state.feedback = Object.entries(state.feedback).reduce((next, [id, value]) => { const mapped = remapId(id); if (mapped && DISHES.some(d => d.id === mapped)) next[mapped] = clamp((next[mapped] || 0) + value, -3, 3); return next; }, {});
  writeStore("canteenai_history", state.history); writeStore("canteenai_favorites", state.favorites); writeStore("canteenai_feedback", state.feedback);
  localStorage.setItem("canteenai_schema", "siplou-3canteens-v1");
}

function bindEvents() {
  $$(".mode-tab").forEach(tab => tab.addEventListener("click", () => switchMode(tab.dataset.mode)));
  $("#preferenceForm").addEventListener("submit", e => { e.preventDefault(); recommend(true); });
  ["#budget", "#freeTime"].forEach(s => $(s).addEventListener("input", () => { syncLabels(); recommend(); }));
  ["#tasteChips", "#dietChips"].forEach(s => $(s).addEventListener("change", () => recommend()));
  $("#location").addEventListener("change", () => { recommend(); updateRadar(); });
  $("#parseBtn").addEventListener("click", parseNaturalLanguage);
  $("#scenarioSelect").addEventListener("change", e => applyScenario(e.target.value));
  $("#topRecommendation").addEventListener("click", handleRecommendationAction);
  $("#favoriteList").addEventListener("click", e => { const id = e.target.dataset.removeFav; if (!id) return; state.favorites = state.favorites.filter(x => x !== id); writeStore("canteenai_favorites", state.favorites); renderMemory(); recommend(); });
  $("#timeSlider").addEventListener("input", e => { state.departure = +e.target.value; updateRadar(); recommend(); });
  $$(".canteen-node").forEach(n => n.addEventListener("click", () => { state.selectedCanteen = n.dataset.canteen; updateRadar(); }));
  const dialog = $("#methodDialog"); ["#openMethod", "#openMethod2"].forEach(s => $(s).addEventListener("click", () => dialog.showModal())); $("#closeMethod").addEventListener("click", () => dialog.close());
  $("#clearMemory").addEventListener("click", () => { if (!confirm("确定清空历史、收藏和反馈吗？此操作不可恢复。")) return; state.history = []; state.favorites = []; state.feedback = {}; ["canteenai_history", "canteenai_favorites", "canteenai_feedback"].forEach(k => localStorage.removeItem(k)); renderMemory(); recommend(); toast("饮食记忆已清空"); });
  $("#compareInputs").addEventListener("change", e => { if (e.target.matches(".candidate-name")) fillCandidate(e.target.closest(".candidate-row"), e.target.value.trim()); });
  $("#compareInputs").addEventListener("click", e => { if (e.target.matches(".candidate-remove")) { const row = e.target.closest(".candidate-row"); row.querySelectorAll("input").forEach(i => i.value = ""); row.querySelector(".candidate-hint").textContent = "第三个候选已清空（可选）"; } });
  $("#compareForm").addEventListener("submit", runComparison);
  $("#compareDemo").addEventListener("click", () => { const names = ["清汤牛肉面", "红烧鸡腿饭", "菌菇豆腐煲"]; $$(".candidate-row").forEach((row, i) => { row.querySelector(".candidate-name").value = names[i]; fillCandidate(row, names[i]); }); $("#compareTaste").value = "鲜香"; runComparison(); toast("已载入三菜对比演示"); });
  $("#blindForm").addEventListener("submit", runBlindBox); $("#blindResult").addEventListener("click", handleBlindFeedback);
  $("#blindDemo").addEventListener("click", () => { $("input[name=adventure][value=medium]").checked = true; $$("#blindDietChips input").forEach(i => i.checked = i.value === "不辣"); $("#blindLocation").value = "图书馆"; runBlindBox(); toast("已载入：不吃辣的适度冒险"); });
  $("#teamForm").addEventListener("submit", runTeam);
  $("#addMember").addEventListener("click", () => { if (state.teamCount >= 6) { toast("最多支持 6 人"); return; } state.teamCount++; $("#memberList").insertAdjacentHTML("beforeend", memberRow(state.teamCount - 1)); });
  $("#memberList").addEventListener("click", e => { if (!e.target.matches("[data-remove-member]")) return; if ($$(".member-row").length <= 2) { toast("至少保留 2 位成员"); return; } e.target.closest(".member-row").remove(); state.teamCount = $$(".member-row").length; });
  $("#teamDemo").addEventListener("click", () => { renderMembers([{ name: "小林", budget: 15, taste: "香辣", time: 35 }, { name: "阿禾", budget: 20, taste: "清淡", diet: "不辣", time: 45 }, { name: "沐沐", budget: 18, taste: "鲜香", diet: "无花生", time: 40 }, { name: "Leo", budget: 22, taste: "酸甜", diet: "高蛋白", time: 50 }]); runTeam(); toast("已载入四人组队演示"); });
  window.addEventListener("resize", () => requestAnimationFrame(() => { drawChart(); const radar = $("#compareRadar"); if (radar) drawCompareRadar(JSON.parse(radar.dataset.values || "[]")); }));
}

function init() {
  migrateLegacyMemory();
  $("#dishCount").textContent = DISHES.length;
  renderCompareInputs(); renderMembers(); syncLabels(); bindEvents(); renderMemory(); recommend(); updateRadar();
  console.info(`[CanteenAI] 已加载 ${DISHES.length} 条模拟菜品数据；全部算法在本地浏览器运行。`);
}

init();
