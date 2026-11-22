from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from html import escape

import streamlit as st

from ai_service import (
    DETAIL, SHORT, UNKNOWN, Answer, Recognition, Turn, cloud_config, guide_answer,
    offline_recognition, read_settings, recognize,
)
from guide_data import GuideError, load_catalog
from photos import prepare_photo, read_photo, reference_photos
from search_service import search_status, search_guide, search_available

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "data/buildings.json"
REFERENCES = ROOT / "data/reference_images"
DEMO_IMAGE = ROOT / "data/demo-a.png"
OFFLINE, CLOUD = "离线模拟", "真实 API"
MANUAL, PHOTO = "按名称选择", "从照片识别"


@dataclass
class Visit:
    scope: tuple
    serial: int
    photo: bytes | None = None
    attempted: bool = False
    result: Recognition | None = None
    building_id: str | None = None
    guides: dict[str, Answer] = field(default_factory=dict)
    turns: list[Turn] = field(default_factory=list)
    web_answers: dict = field(default_factory=dict)
    web_errors: dict = field(default_factory=dict)
    web_attempts: set = field(default_factory=set)
    pending_question: str = ""
    failed_question: str = ""
    question_error: str = ""

    def select(self, building_id):
        if self.building_id != building_id:
            self.building_id = building_id
            self.guides.clear()
            self.turns.clear()
            self.web_answers.clear()
            self.web_errors.clear()
            self.web_attempts.clear()
            self.pending_question = ""
            self.failed_question = ""
            self.question_error = ""


def visit_for(scope):
    previous = st.session_state.get("visit")
    if previous is None or previous.scope != scope:
        serial = 1 if previous is None else previous.serial + 1
        st.session_state.visit = Visit(scope, serial)
    visit = st.session_state.visit
    # 热更新时保留当前导览，但丢弃旧版尚未清理引用的联网缓存。
    if not hasattr(visit, "web_attempts"):
        visit.web_attempts = set()
        visit.web_answers.clear()
        visit.web_errors.clear()
    return st.session_state.visit


def show_references(buildings):
    with st.expander("候选建筑与参考图", on_change="rerun", key="reference_gallery") as gallery:
        if gallery.open:
            for b in buildings.values():
                st.text(b.name)
                st.caption("、".join(b.visual_cues) or "暂缺外观描述")
                if not b.reference_images:
                    st.caption("参考图待补充。")
                    continue
                try:
                    refs = reference_photos(REFERENCES, {b.id: b})
                except GuideError as exc:
                    st.warning(str(exc))
                    continue
                for filename, (_, photo) in zip(b.reference_images, refs):
                    st.image(photo, width=180, caption=f"参考图 · {b.id} / {filename}",
                             alt=f"{b.name} 的已知参考照片")


def choose_from_photo(buildings, scope, config, ready):
    offline = scope[0] == OFFLINE
    has_demo = offline and "A" in buildings and buildings["A"].placeholder
    source = "上传照片"
    if has_demo:
        source = st.radio("照片来源", [source, "内置示意图"], horizontal=True, key="photo_source")

    upload = None
    if source == "上传照片":
        upload = st.file_uploader("选择待识别的 JPG 或 PNG", type=["jpg", "jpeg", "png"],
                                  max_upload_size=12, key=f"upload_{scope[0]}")
        if upload is None:
            visit_for((*scope, "empty"))
            return None
        fingerprint = sha256(upload.getbuffer()).hexdigest()
        visit = visit_for((*scope, "upload", upload.name, fingerprint))
    else:
        visit = visit_for((*scope, "demo"))

    try:
        if visit.photo is None:
            visit.photo = read_photo(DEMO_IMAGE) if upload is None else prepare_photo(upload.getvalue())
    except GuideError as exc:
        st.error(str(exc))
        return None

    left, right = st.columns([1, 1])
    with left:
        st.image(visit.photo, width="stretch", caption="待识别图 · 已校正方向并缩放",
                 alt="本次待判断的照片")
    with right:
        show_references(buildings)
        if offline:
            st.caption("离线模拟只匹配内置示意图，也可以练习手动更正。" if has_demo else
                       "离线模式可预览实拍照片并手动选楼。自动比对建筑需使用真实 API。")
        else:
            count = sum(len(b.reference_images) for b in buildings.values())
            st.caption(f"点击识别将向所选服务商发送待识别图、{count} 张参考图及三栋建筑的外观线索。")
        identify = st.button("识别照片", type="primary", key="identify",
                             disabled=not ready or visit.result is not None)
        if identify and ready and visit.result is None:
            visit.attempted = True
            visit.select(None)
            try:
                with st.spinner("正在比对照片…"):
                    if offline:
                        demo = read_photo(DEMO_IMAGE) if has_demo else None
                        visit.result = offline_recognition(visit.photo, demo, buildings)
                    else:
                        refs = reference_photos(REFERENCES, buildings)
                        visit.result = recognize(config, buildings, visit.photo, refs)
            except GuideError as exc:
                st.error(str(exc))
            else:
                st.rerun()
        if visit.result:
            bid = visit.result.building_id
            name = UNKNOWN if bid == UNKNOWN else buildings[bid].name
            label = "离线模拟结果" if offline else "模型判断"
            st.markdown(f"**{label}**")
            st.text(name)
            st.text(visit.result.reason)

    if not visit.attempted:
        return None
    options = list(buildings)
    suggested = visit.result.building_id if visit.result else None
    index = options.index(suggested) if suggested in options else None
    choice = st.selectbox("核对建筑，可手动更正", options, index=index,
                          format_func=lambda bid: buildings[bid].name, placeholder="请手动选择建筑",
                          key=f"correction_{visit.serial}_{suggested}")
    if choice != visit.building_id:
        visit.select(None)
    if st.button("确认建筑", key="confirm", disabled=choice is None or choice == visit.building_id):
        visit.select(choice)
        st.rerun()
    return visit if visit.building_id else None


def show_answer(building, answer, key, offline, visit=None, settings=None, question=""):
    can_search = not offline and visit is not None and search_available(settings)
    web = visit.web_answers.get(key) if visit else None
    missing = answer.coverage in ("none", "partial") or not answer.fact_ids
    if can_search and missing and not web and key not in visit.web_attempts:
        run_search(visit, key, settings, building, question)
        web = visit.web_answers.get(key)
    if offline:
        st.caption("离线模拟 · 查阅本地资料卡")
    for fid in answer.fact_ids:
        st.text(building.facts[fid].text)
    if answer.notice and not web and not can_search:
        st.text(answer.notice)
    if can_search and not web:
        failed = key in visit.web_attempts
        if failed:
            st.caption(visit.web_errors.get(key, "查询中断，请重试。"))
        if st.button("重试搜索" if failed else "联网补充", key=f"web_{key}"):
            run_search(visit, key, settings, building, question)
            st.rerun()
    if web:
        st.text(web.text)
    # 一次回复的所有出处只在末尾出现，同一 URL 或现场来源只保留一次。
    sources = [(s.title, s.url) for s in answer.sources(building)]
    if web:
        sources.extend((s.title, s.url) for s in web.sources)
    seen, links = set(), []
    for title, url in sources:
        identity = url or title
        if identity in seen:
            continue
        seen.add(identity)
        label = escape(title)
        links.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>' if url else label)
    if links:
        stamp = (" · 联网检索于 " + web.retrieved_at.strftime("%Y-%m-%d %H:%M")) if web else ""
        st.html('<div style="font-size:0.78rem;line-height:1.65;color:#74817c;margin-top:0.6rem">来源 · '
                + ' · '.join(links) + stamp + '</div>')
    if any(not building.facts[fid].source_ids for fid in answer.fact_ids):
        st.caption("占位资料，尚无真实来源。" if building.placeholder else "部分资料原句尚未填写来源。")


def run_search(visit, key, settings, building, question):
    # 请求前记录，避免控件重跑或失败后再次自动扣费；失败仅手动重试。
    visit.web_attempts.add(key)
    try:
        with st.spinner("正在查找相关资料…"):
            visit.web_answers[key] = search_guide(settings, building, question)
        visit.web_errors.pop(key, None)
    except GuideError as exc:
        visit.web_errors[key] = str(exc)


def queue_question(visit, input_key):
    visit.pending_question = st.session_state[input_key].strip()


def queue_retry(visit):
    visit.pending_question = visit.failed_question


def guide_panel(visit, building, config, ready, settings=None):
    offline = visit.scope[0] == OFFLINE
    st.divider()
    st.subheader(building.name)
    style = st.radio("讲解长度", [SHORT, DETAIL], horizontal=True, key="length")
    generate = st.button("生成讲解", key="generate", type="primary",
                         disabled=not ready or style in visit.guides)
    if generate and ready and style not in visit.guides:
        try:
            with st.spinner("正在整理讲解…"):
                visit.guides[style] = guide_answer(building, style, config)
        except GuideError as exc:
            st.error(str(exc))
        else:
            st.rerun()
    if style in visit.guides:
        with st.container(border=True):
            show_answer(building, visit.guides[style], f"{visit.serial}_guide_{style}", offline, visit, settings)
    if not visit.guides:
        return

    st.subheader("继续追问")
    transcript = st.container()
    if visit.failed_question:
        st.error(visit.question_error)
        st.text("上次未取得回复的问题：" + visit.failed_question)
        st.button("重试这条追问", key="retry_question", disabled=not ready,
                  on_click=queue_retry, args=(visit,))
    input_key = f"question_{visit.serial}_{building.id}"
    with st.container():
        st.chat_input("想了解这栋建筑的什么？", max_chars=400, disabled=not ready,
                      key=input_key, on_submit=queue_question, args=(visit, input_key))
    # 在发请求之前消费提交事件。后续控件重跑不会再次消费同一个问题。
    question, visit.pending_question = visit.pending_question, ""
    if question and ready:
        try:
            with st.spinner("正在查阅当前建筑资料…"):
                guide = visit.guides.get(style) or next(reversed(visit.guides.values()))
                reply = guide_answer(building, style, config, question=question,
                                     history=visit.turns, guide=guide)
                visit.turns.append(Turn(question, reply))
                visit.failed_question = ""
                visit.question_error = ""
        except GuideError as exc:
            visit.failed_question = question
            visit.question_error = str(exc)
        st.rerun()
    with transcript:
        for i, turn in enumerate(visit.turns):
            with st.chat_message("user"):
                st.text(turn.question)
            with st.chat_message("assistant"):
                show_answer(building, turn.answer, f"{visit.serial}_turn_{i}", offline, visit, settings, turn.question)


def main():
    st.set_page_config(page_title="校园建筑互动导览", page_icon="🏛️", layout="centered")
    st.title("校园建筑互动导览")
    mode = st.sidebar.radio("运行模式", [OFFLINE, CLOUD], key="mode")
    ready, config = True, None
    settings = None
    try:
        settings = read_settings(ROOT / "config.toml")
    except GuideError as exc:
        web_status = "联网补充暂不可用，无法读取配置文件。"
        if mode == CLOUD:
            ready = False
            st.warning(str(exc))
    else:
        web_status = search_status(settings)
        if mode == CLOUD:
            try:
                config = cloud_config(settings)
            except GuideError as exc:
                ready = False
                st.warning(str(exc))
        if config:
            st.sidebar.text(f"当前模型 · {config.model}")
    mode_note = ("离线模拟 · 在本机查阅建筑资料，无需密钥。"
                 if mode == OFFLINE else "真实 API · 点击识别、生成或提交追问时，向配置的服务商请求。")
    if mode == OFFLINE and search_available(settings):
        web_status = "切换到真实 API 模式可使用联网补充。"
    st.caption(f"{mode_note}  {web_status}")
    try:
        buildings = load_catalog(CARDS)
    except GuideError as exc:
        visit_for((mode, "invalid_catalog"))
        st.error(str(exc))
        return
    count = sum(b.placeholder for b in buildings.values())
    if count:
        st.info(f"当前有 {count} 张示例占位资料卡。卡中的描述用于演示操作。", icon=":material/info:")

    route = st.radio("选择导览方式", [MANUAL, PHOTO], horizontal=True, key="route")
    # 资料卡或使用场景发生变化时，即使编号相同也重新开始本次导览。
    endpoint = (config.base_url, config.model) if config else None
    scope = (mode, route, buildings, endpoint)
    if route == MANUAL:
        bid = st.selectbox("选择建筑", list(buildings), format_func=lambda key: buildings[key].name,
                           key="manual")
        visit = visit_for((*scope, bid))
        visit.select(bid)
    else:
        visit = choose_from_photo(buildings, scope, config, ready)
        if visit is None:
            return
    guide_panel(visit, buildings[visit.building_id], config, ready, settings)


if __name__ == "__main__":
    main()
