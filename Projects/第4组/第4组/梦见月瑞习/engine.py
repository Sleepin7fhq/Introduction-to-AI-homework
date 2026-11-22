# -*- coding: utf-8 -*-
"""
「梦见月」引擎：三段式状态机 + 双后端（大模型 / 本地规则）。

- 有 DSH_DEMO_API_KEY 时走 OpenAI 兼容接口（DeepSeek / 通义 / 豆包 / vLLM 均可）；
- 没有或调用失败时，自动降级到本地规则引擎，保证现场永远不会开天窗。
"""

import json
import os
import re
import threading
import time
import urllib.request
import urllib.error

from knowledge import BY_ID

# ---------------------------------------------------------------- 配置

API_KEY = os.environ.get("DSH_DEMO_API_KEY", "").strip()
API_BASE = os.environ.get("DSH_DEMO_API_BASE", "https://api.deepseek.com").rstrip("/")
API_MODEL = os.environ.get("DSH_DEMO_MODEL", "deepseek-chat")
TIMEOUT = float(os.environ.get("DSH_DEMO_TIMEOUT", "25"))


def configure(key=None, base=None, model=None):
    """运行时改配置（界面上填完 key 之后调用）。"""
    global API_KEY, API_BASE, API_MODEL
    if key is not None:
        API_KEY = (key or "").strip()
    if base:
        API_BASE = base.strip().rstrip("/")
    if model:
        API_MODEL = model.strip()


def mask_key(k=None):
    k = (k if k is not None else API_KEY) or ""
    if not k:
        return ""
    if len(k) <= 8:
        return "****"
    return k[:3] + "****" + k[-4:]


_LLM_FAIL_UNTIL = 0.0

# ---------------------------------------------------------------- 访客额度
# Key 只存在服务器这台机器上，浏览器永远拿不到；但访客每点一次 AI，
# 花的都是你的余额。所以给访客单独记一个额度，用完自动降级到本地引擎。

_CTX = threading.local()
_visitor_calls = 0
_visitor_limit = 300
_visitor_enabled = True
_visitor_lock = threading.Lock()


def set_client(is_local):
    _CTX.is_local = bool(is_local)


def is_local():
    return getattr(_CTX, "is_local", True)


def usage():
    return {"calls": _visitor_calls, "limit": _visitor_limit,
            "enabled": _visitor_enabled, "left": max(0, _visitor_limit - _visitor_calls)}


def configure_visitor(enabled=None, limit=None):
    global _visitor_enabled, _visitor_limit
    if enabled is not None:
        _visitor_enabled = bool(enabled)
    if limit is not None:
        _visitor_limit = max(0, int(limit))


def _count_visitor_call():
    global _visitor_calls
    with _visitor_lock:
        _visitor_calls += 1


def _visitor_ok():
    return _visitor_enabled and _visitor_calls < _visitor_limit


def note_llm_failure():
    """连续失败就别再试了，冷却 60 秒，避免现场每次请求都卡 25 秒。"""
    global _LLM_FAIL_UNTIL
    _LLM_FAIL_UNTIL = time.time() + 60


def llm_enabled():
    if not API_KEY or time.time() < _LLM_FAIL_UNTIL:
        return False
    if not is_local() and not _visitor_ok():
        return False
    return True


def engine_name():
    return f"大模型 · {API_MODEL}" if llm_enabled() else "本地规则引擎（无 API Key）"


def test_connection():
    """打一个最小请求，把服务端的报错原样带回来，方便定位 401/402/404。"""
    body = {
        "model": API_MODEL,
        "messages": [{"role": "user", "content": "只回复两个字：收到"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + "/chat/completions",
        data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + API_KEY},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"].strip()
        return {"ok": True, "reply": text[:40],
                "latency_ms": int((time.time() - t0) * 1000),
                "model": payload.get("model", API_MODEL)}
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:  # noqa: BLE001
            detail = ""
        hint = {
            401: "Key 不对或者没生效，检查有没有复制全（通常以 sk- 开头）",
            402: "余额不足，去平台充值",
            403: "这个 Key 没有该模型的权限",
            404: "接口地址或模型名写错了",
            429: "请求太频繁或额度用完了，等一会儿再试",
        }.get(e.code, "")
        return {"ok": False, "status": e.code, "detail": detail, "hint": hint}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:200],
                "hint": "连不上服务器，检查网络/代理，或确认接口地址是否正确"}


def _call_llm(system, user, retries=1, temperature=0.7, max_tokens=900):
    """OpenAI 兼容的 chat/completions 调用，失败抛异常由上层降级。"""
    body = {
        "model": API_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if not is_local():
        _count_visitor_call()
    last = None
    for _ in range(retries + 1):
        req = urllib.request.Request(
            API_BASE + "/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + API_KEY,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"LLM 调用失败: {last}")


def _json_block(text):
    """从模型输出里抠出第一个 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no json")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------- 文本分析

DEF_RE = re.compile(r"(是指|指的是|意思是|定义为|所谓|叫作|叫做|是一种|是一个|就是)")
BOUND_STRONG = re.compile(r"(只有.{0,12}(才|时|能)|在.{0,10}情况下|情况下|前提下|适用范围|只适用于|一般来说|通常|不一定|仅当|前提是|除非)")
BOUND_WEAK = re.compile(r"(当.{0,12}时)")
BOUND_RE = re.compile(BOUND_STRONG.pattern[:-1] + "|" + BOUND_WEAK.pattern[1:])
COUNTER_RE = re.compile(r"(反例|例外|不成立|不一定|失效|反过来)")
MECH_RE = re.compile(r"(因为|所以|由于|导致|使得|从而|因此|结果|于是)")
MECH_COUNT_RE = re.compile(r"(因为|所以|由于|导致|使得|从而|因此)")
EX_RE = re.compile(r"(比如|例如|举个例子|打个比方|就像|好比|相当于|类比)")


def analyze(text):
    t = (text or "").strip()
    han = len(re.findall(r"[\u4e00-\u9fff]", t))
    return {
        "han": han,
        "has_def": bool(DEF_RE.search(t)),
        "has_bound": bool(BOUND_RE.search(t)),
        "has_counter": bool(COUNTER_RE.search(t)),
        "has_mech": bool(MECH_RE.search(t)),
        "mech_count": len(MECH_COUNT_RE.findall(t)),
        "has_ex": bool(EX_RE.search(t)),
    }


def split_sentences(text):
    parts = re.split(r"[。！？!?；;\n]+", text or "")
    return [p.strip() for p in parts if len(p.strip()) >= 4]


def first_with(text, regex, exclude=None):
    for s in split_sentences(text):
        if re.search(regex, s) and not (exclude and re.search(exclude, s)):
            return s
    return ""


def clip(s, n=46):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "…"


# ---------------------------------------------------------------- 会话

class Session:
    __slots__ = ("sid", "concept", "text", "q_index", "questions",
                 "answers", "feats", "created", "mode")

    def __init__(self, sid, concept):
        self.sid = sid
        self.concept = concept
        self.text = ""
        self.q_index = -1
        self.questions = []      # [{"dim","q"}]
        self.answers = []        # [{"q","a","skipped"}]
        self.feats = None
        self.created = time.time()
        self.mode = "local"


SESSIONS = {}


FREE_CONCEPT = {
    "id": "free", "name": "自由概念", "subject": "自由输入",
    "points": ["一句话说清它是什么", "说清它在什么条件下成立", "说清它为什么会这样"],
    "traps": [{"say": "我懂了！所以只要满足了前面那些条件，它就一定成立，对吧？",
               "q": "那有没有哪种情况，你说的这一套其实是不成立的？"}],
    "questions": [
        {"dim": "边界", "q": "这个道理在什么条件下会失效？你能说出那条边界吗？"},
        {"dim": "反例", "q": "能不能举一个反例：看起来完全符合你的描述，结论却是反的？"},
        {"dim": "机制", "q": "从前提走到结论，中间到底发生了什么？"},
    ],
}


def new_session(sid, concept_id, custom_name=""):
    if concept_id == "free":
        concept = dict(FREE_CONCEPT)
        if custom_name.strip():
            concept["name"] = custom_name.strip()[:20]
    else:
        concept = BY_ID.get(concept_id)
    if concept is None:
        return None
    s = Session(sid, concept)
    SESSIONS[sid] = s
    return s


def get_session(sid):
    return SESSIONS.get(sid)


# ---------------------------------------------------------------- 本地：装懂 + 第一问

GENERIC_TRAPS = [
    ("我大概懂了——是不是说，{name}就是把某个东西换成另一个说法，本质上没有区别？",
     "那你能不能给我一个『看起来很符合你说的，但其实不成立』的情况？"),
]


def local_misread(session, feats):
    c = session.concept
    trap = c["traps"][0]
    say = trap["say"]
    q = trap.get("q") or c["questions"][0]["q"]

    # 若用户已经明显讲了边界与机制，就让 AI 的误解更“进一层”
    if feats["has_bound"] and feats["has_mech"] and len(c["traps"]) > 1:
        trap = c["traps"][1]
        say, q = trap["say"], trap.get("q") or q

    span = first_with(session.text, r"(就是|是指|也就是|换句话说)") or split_sentences(session.text)[:1]
    if isinstance(span, list):
        span = span[0] if span else ""
    return {"say": say, "defect": "把条件当成了结论", "span": clip(span), "q": q}


def local_misread_free(text, feats):
    """自由概念（不在概念包里）时，用结构特征构造误解。"""
    sents = split_sentences(text)
    core = sents[0] if sents else text[:40]
    name = "你说的这个东西"
    if not feats["has_bound"]:
        say = "我懂了！所以只要满足了前面说的条件，它就一定成立，对吧？"
        q = "那有没有什么情况下，你说的这套是不成立的？"
        defect = "缺少适用边界"
    elif not feats["has_mech"]:
        say = "我大概懂了，但我没听出中间发生了什么——是不是 A 之后就直接变成 B 了？"
        q = "从 A 到 B 之间，到底经过了哪一步？"
        defect = "缺少因果机制"
    else:
        say = "我懂了！你是在说，{x}本质上就是另一件事换个名字，对吧？".format(x=clip(core, 18))
        q = "那如果不换个名字，只改一个条件，结论还成立吗？"
        defect = "概念被泛化"
    return {"say": say, "defect": defect, "span": clip(core), "q": q}


# ---------------------------------------------------------------- 追问序列

def pick_questions(concept, first_q):
    """三轮节奏：先咬住漏洞，再给方向让人自由说，最后自己抛个话题一起聊。"""
    qs = concept["questions"]
    by_dim = {x["dim"]: x["q"] for x in qs}
    mech = by_dim.get("机制") or qs[-1]["q"]
    counter = by_dim.get("反例") or qs[0]["q"]

    menu = ("这个我记下了。那我想换个角度，你挑一个方向说就行，哪个顺手说哪个：\n"
            "① 举个具体例子\n"
            "② " + mech + "\n"
            "③ " + counter)

    from knowledge import get_branch
    branch = get_branch(concept.get("subject", ""))
    b = branch[abs(hash(concept["id"])) % len(branch)]
    return [first_q, menu, b]


# ---------------------------------------------------------------- 回答与脚手架

SKIP_RE = re.compile(r"(不知道|讲不清|说不清|跳过|想不起|卡住|没想过|说不明白|答不上|不会)")


def judge_answer(session, text):
    """只分两种：卡住了 / 说了一句。梦见月没有资格判对错——那是诊断卡的事。"""
    a = (text or "").strip()
    if SKIP_RE.search(a):
        return "skip"
    core = re.sub(r"[^\w]", "", a)          # 去掉标点空格，只剩实词
    if len(core) < 2:                         # "嗯……" "啊" 这种
        return "skip"
    if re.fullmatch(r"[嗯哦啊呃额哈嘿]+", core):
        return "skip"
    return "attempt"


REACT_ATTEMPT = [
    "「{a}」……哦，这么一说我好像顺过来一点了。",
    "「{a}」……原来是这样，我之前的理解果然歪了。",
    "「{a}」……懂了懂了，你这个说法我记住了。",
]


def local_react(session, answer_text):
    """梦见月的反馈：接住了就往下问，接不住就自己承认，绝不说教、绝不评判。"""
    a = (answer_text or "").strip()
    verdict = judge_answer(session, a)
    msgs = []

    if verdict == "skip":
        msgs.append({"text": "啊，你也卡住了？……那说明这块确实绕，不怪你。"})
    else:
        tpl = REACT_ATTEMPT[len(session.answers) % len(REACT_ATTEMPT)]
        msgs.append({"text": tpl.format(a=a[:40])})

    nxt = session.q_index + 1
    if nxt < len(session.questions):
        q = session.questions[nxt]
        if verdict == "skip":
            msgs.append({"text": "那我不为难你——跳过这个，我换个方向：" + q})
        elif nxt == 1:
            msgs.append({"text": q})          # 这一段本身就是完整的引导语
        else:
            msgs.append({"text": "最后一个，我不问概念了，随便聊个别的——" + q})
        session.q_index = nxt
        return msgs, False

    msgs.append({"text": "好，我这边的问题问完了。我们来看看诊断卡。"})
    return msgs, True


# ---------------------------------------------------------------- 诊断

DIMS = [("clarity", "清晰度"), ("boundary", "边界感"),
        ("mechanism", "机制感"), ("transfer", "迁移力")]

WEIGHTS = {"clarity": 0.30, "boundary": 0.30, "mechanism": 0.25, "transfer": 0.15}


def _clamp5(x):
    return max(1.0, min(5.0, round(x * 2) / 2.0))


def _answers_text(session):
    return "。".join(a["a"].strip() for a in session.answers if not a["skipped"])


def local_score(session):
    f = session.feats
    n = f["han"]
    at = _answers_text(session)
    fa = analyze(at) if at else None

    clarity = 1.5 + 1.5 * f["has_def"] + 0.5 * (n >= 80) + 0.5 * (n >= 160)

    b_txt = 1.0 + 2.2 * f["has_bound"] + 0.6 * f["has_counter"]
    m_txt = 1.0 + 2.2 * f["has_mech"] + 0.6 * (f["mech_count"] >= 2)
    t_txt = 1.0 + 1.9 * f["has_ex"] + 0.5 * (n >= 250)

    # 追问环节补上的东西也算数：讲解里没有、但回答里讲出来了，就按回答给分
    b_ans = 1.0 + 2.2 * fa["has_bound"] + 0.6 * fa["has_counter"] if fa else 0
    m_ans = 1.0 + 2.2 * fa["has_mech"] + 0.6 * (fa["mech_count"] >= 2) if fa else 0
    t_ans = 1.0 + 1.9 * fa["has_ex"] if fa else 0

    raw = {"clarity": clarity,
           "boundary": max(b_txt, b_ans),
           "mechanism": max(m_txt, m_ans),
           "transfer": max(t_txt, t_ans)}
    return {k: _clamp5(v) for k, v in raw.items()}


def local_card(session):
    c = session.concept
    at = _answers_text(session)
    t = session.text + ("。" + at if at else "")
    scores = local_score(session)

    def evidence(key):
        good = scores[key] >= 3.0
        if key == "clarity":
            s_ = first_with(t, DEF_RE)
            if good and s_:
                return ("你说了“" + clip(s_) + "”，这是全文最清楚的一句定义。", "good")
            if good:
                return ("整体表述清楚，术语前后一致。", "good")
            return ("全文没有出现“X 是指……”“所谓 X 就是……”这样的定义句，读者只能自己猜。", "bad")
        if key == "boundary":
            s_ = (first_with(t, BOUND_STRONG, exclude=EX_RE)
                  or first_with(t, BOUND_WEAK, exclude=EX_RE))
            if good and s_:
                return ("你给了限定：“" + clip(s_) + "”。", "good")
            return ("没有出现“在……条件下”“只有……才……”“不一定”这类限定。"
                    "任何结论都有失效的时候，不说边界，就等于默认它永远成立。", "bad")
        if key == "mechanism":
            s_ = first_with(t, MECH_RE)
            if good and s_:
                return ("你讲了因果：“" + clip(s_) + "”。", "good")
            return ("只说了“是什么”，没说“为什么”。全文找不到一个“因为……所以……”。", "bad")
        s_ = first_with(t, EX_RE)
        if good and s_:
            return ("你举了例子：“" + clip(s_) + "”。", "good")
        return ("没有例子也没有类比。一个没有例子的定义，很难被别人接住。", "bad")

    items = []
    for key, label in DIMS:
        txt, tone = evidence(key)
        items.append({"key": key, "label": label,
                      "score": scores[key], "evidence": txt, "tone": tone})

    total = round(sum(WEIGHTS[k] * scores[k] for k, _ in DIMS) / 5 * 100)

    missing = [i for i in items if i["tone"] == "bad"]
    if missing:
        rewrite = ("你已经把“是什么”讲出来了。想让一个完全不懂的人真的听懂，还差两样："
                   "一句边界——「这个结论只在 ______ 的情况下成立」；"
                   "一句机制——「之所以会这样，是因为 ______」。把这两个空填上再讲一遍，"
                   "你会发现卡住的地方就在空里。")
    else:
        rewrite = ("这段讲解结构是完整的：有定义、有边界、有因果、有例子。"
                   "下一步可以试试把例子换成一个反例——如果连反例都能讲通，"
                   "说明你是真的掌握了，而不是背下来了。")

    return {
        "concept": c["name"],
        "scores": [{"key": k, "label": lab, "value": scores[k]} for k, lab in DIMS],
        "total": total,
        "evidence": items,
        "rewrite": rewrite,
        "dimension_note": "分数只是提示，证据才是重点。每条扣分都能指回你的原句。",
    }


# ---------------------------------------------------------------- 大模型分支

SYS_ROLE = (
    "你叫“梦见月”，是「梦见月瑞习」里的 AI 学生：聪明、好奇、态度诚恳，"
    "但对用户即将讲解的领域没有任何背景知识。"
    "你的任务不是展示知识，而是通过“合理的误解”和追问，帮助用户发现他讲解中的模糊之处。"
    "硬性约束：一，只能用用户已经说过的词复述，不得引入新术语；二，误解必须能追溯到用户原话中的某一处歧义；"
    "三，每次只问一个问题；四，不直接给出正确答案；五，语气友好，不评判用户本人；六，全部用中文，口语化，不超过 80 字。"
    "七，不要一直围着同一个点追问。第二、三轮可以适当发散：给一个具体情境、一个生活类比，或者聊聊这个概念周边的话题。"
    "八，如果用户说不知道、答得很短，或者明显卡住，就用「你可以挑一个方向说：①……②……③……」的形式给两三个可选角度，让人有东西可接。"
)

SYS_JUDGE = (
    "你是一个严格的表达评估器。只评价“这次讲解的表达质量”，不评价人。"
    "每个维度必须引用用户原句作为证据；找不到证据就不给高分。输出严格 JSON，不要任何解释性文字。"
)


def llm_misread(session):
    c = session.concept
    user = (
        "概念：" + c["name"] + "\n"
        "用户的讲解：\n" + session.text + "\n\n"
        "请找出其中最关键的一处歧义，并以“梦见月”的身份写一段自信但恰好错在这一处的复述，"
        "再提出一个追问。\n"
        '输出 JSON：{"misread":"...","defect":"术语未定义|必要条件当充分条件|因果倒置|缺少适用边界",'
        '"span":"原文片段","question":"..."}'
    )
    data = _json_block(_call_llm(SYS_ROLE, user))
    return data


def llm_react(session, answer_text):
    user = (
        "概念：" + session.concept["name"] + "\n"
        "你刚才的追问：" + (session.questions[session.q_index] if session.q_index >= 0 else "") + "\n"
        "用户的回答：" + answer_text + "\n\n"
        "先给一句不超过 20 字的反馈。然后换一个角度继续，不要追问刚才那个点上的细节，"
        "从下面三种里挑一种：让用户举个例子、给一个具体情境让用户判断、或者问它和另一个容易混淆的概念有什么区别。"
        "不要给答案。"
        '输出 JSON：{"ack":"...","next_question":"..."}'
    )
    return _json_block(_call_llm(SYS_ROLE, user))


def llm_card(session):
    c = session.concept
    qa = "；".join("问：" + a["q"] + " 答：" + a["a"] for a in session.answers)
    user = (
        "概念：" + c["name"] + "\n用户的讲解：\n" + session.text + "\n追问记录：" + qa + "\n\n"
        "请按清晰度、边界感、机制感、迁移力四个维度打分（0-5，可为 0.5 的倍数），"
        "每个维度必须引用原句作为证据。不要给标准答案，只指出缺什么。\n"
        '输出 JSON：{"clarity":{"score":3.5,"evidence":"..."},"boundary":{"score":2,"evidence":"..."},'
        '"mechanism":{"score":2.5,"evidence":"..."},"transfer":{"score":2,"evidence":"..."},'
        '"rewrite":"不超过 120 字的建议"}'
    )
    return _json_block(_call_llm(SYS_JUDGE, user))


def llm_card_to_card(session, data):
    items, scores = [], {}
    for key, label in DIMS:
        node = data.get(key, {})
        try:
            val = float(node.get("score", 2))
        except (TypeError, ValueError):
            val = 2.0
        val = max(0.0, min(5.0, round(val * 2) / 2))
        scores[key] = val
        ev = str(node.get("evidence", ""))[:160]
        items.append({"key": key, "label": label, "score": val,
                      "evidence": ev or "模型没有给出证据。",
                      "tone": "good" if val >= 4 else "bad"})
    total = round(sum(WEIGHTS[k] * scores[k] for k, _ in DIMS) / 5 * 100)
    return {
        "concept": session.concept["name"],
        "scores": [{"key": k, "label": lab, "value": scores[k]} for k, lab in DIMS],
        "total": total,
        "evidence": items,
        "rewrite": str(data.get("rewrite", ""))[:300],
        "dimension_note": "分数只是提示，证据才是重点。每条扣分都能指回你的原句。",
    }


# ---------------------------------------------------------------- 对外 API

def api_start(sid, concept_id, custom_name=""):
    s = new_session(sid, concept_id, custom_name)
    if s is None:
        return {"error": "concept not found"}
    c = s.concept
    return {
        "concept": {"id": c["id"], "name": c["name"], "subject": c["subject"],
                    "hint": c["points"][0]},
        "engine": engine_name(),
        "state": {"step": 2, "q_index": -1, "total_questions": 3},
    }


def api_explain(sid, text):
    s = get_session(sid)
    if s is None:
        return {"error": "session not found"}
    text = (text or "").strip()
    if len(text) < 20:
        return {"error": "再多讲几句吧，至少 20 个字——真实的讲解不会是这么短的。"}

    s.text = text
    s.feats = analyze(text)
    s.answers = []
    s.q_index = 0

    misread = None
    if llm_enabled():
        try:
            d = llm_misread(s)
            misread = {"say": d["misread"], "defect": d.get("defect", ""),
                       "span": d.get("span", ""), "q": d["question"]}
            s.mode = "llm"
        except Exception:  # noqa: BLE001
            note_llm_failure()
            misread = None
    if misread is None:
        if s.concept.get("id") == "free":
            misread = local_misread_free(text, s.feats)
        else:
            misread = local_misread(s, s.feats)
        s.mode = "local"

    s.questions = pick_questions(s.concept, misread["q"])
    msgs = [
        {"role": "ai", "kind": "misread", "text": misread["say"]},
        {"role": "ai", "kind": "probe", "text": "那我问你一个问题：" + misread["q"]},
    ]
    return {
        "messages": msgs,
        "misread": {"defect": misread["defect"], "span": misread["span"]},
        "engine": ("大模型 · " + API_MODEL) if s.mode == "llm" else "本地规则",
        "state": {"step": 3, "q_index": 0, "total_questions": 3,
                  "current_question": s.questions[0]},
    }


def api_answer(sid, answer):
    s = get_session(sid)
    if s is None:
        return {"error": "session not found"}
    answer = (answer or "").strip()
    if s.q_index < 0 or s.q_index >= len(s.questions):
        return {"error": "当前没有待回答的问题"}

    verdict = judge_answer(s, answer)
    skipped = (verdict == "skip")
    s.answers.append({"q": s.questions[s.q_index], "a": answer,
                      "dim": ["边界", "反例", "机制"][min(s.q_index, 2)],
                      "skipped": skipped})

    msgs, done = local_react(s, answer)

    # 还有下一轮时才让模型接管；最后一轮保持“我们来看诊断卡”的收尾，不会被模型拖住
    if llm_enabled() and not skipped and not done and s.q_index < len(s.questions) - 1:
        try:
            d = llm_react(s, answer)
            msgs = [{"role": "ai", "kind": "ack", "text": d["ack"]},
                    {"role": "ai", "kind": "probe", "text": d["next_question"]}]
        except Exception:  # noqa: BLE001
            note_llm_failure()

    out = {"messages": msgs,
           "state": {"step": 3, "q_index": s.q_index,
                     "total_questions": len(s.questions), "done": done}}
    if 0 <= s.q_index < len(s.questions):
        out["state"]["current_question"] = s.questions[s.q_index]
    return out


def api_diagnose(sid):
    s = get_session(sid)
    if s is None:
        return {"error": "session not found"}
    if not s.text:
        return {"error": "还没有讲解内容"}

    if llm_enabled():
        try:
            data = llm_card(s)
            card = llm_card_to_card(s, data)
            return {"card": card, "engine": "大模型 · " + API_MODEL}
        except Exception:  # noqa: BLE001
            note_llm_failure()
    return {"card": local_card(s), "engine": "本地规则"}
