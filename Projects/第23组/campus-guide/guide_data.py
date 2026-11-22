"""读取三张建筑资料卡。导览中的事实与来源都通过本地编号取得。"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class GuideError(Exception):
    """可直接展示给参观者或资料整理者的问题。"""


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    keywords: tuple[str, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Building:
    id: str
    name: str
    placeholder: bool
    visual_cues: tuple[str, ...]
    reference_images: tuple[str, ...]
    sources: dict[str, Source]
    facts: dict[str, Fact]
    guide_fact_ids: tuple[str, ...] = ()
    photo_label: str = ""


def records(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise GuideError(f"{label} 需要填写为记录列表。")
    return value


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise GuideError(f"{label} 需要填写文字。")
    return value.strip()


def strings(value, label):
    if not isinstance(value, list):
        raise GuideError(f"{label} 需要填写为文字列表，暂缺可写 []。")
    return tuple(required_text(item, label) for item in value)


def record_id(row, existing, label):
    key = required_text(row.get("id"), f"{label}的 id")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", key) or key in existing:
        raise GuideError(f"{label}编号须唯一，可用字母、数字、连字符和下划线。")
    return key


def read_sources(rows, label):
    sources = {}
    for row in records(rows, f"{label}的 sources"):
        key = record_id(row, sources, f"{label}的来源")
        title = required_text(row.get("title"), f"{label}来源 {key} 的 title")
        url = row.get("url", "")
        if not isinstance(url, str):
            raise GuideError(f"{label}来源 {key} 的 url 应为文字。")
        if url:
            try:
                parts = urlsplit(url)
                valid = (parts.scheme in ("http", "https") and parts.hostname
                         and parts.username is None and parts.port != 0)
                if not valid or re.search(r"[\s<>]", url):
                    raise ValueError
            except ValueError:
                raise GuideError(f"{label}来源 {key} 请填完整网页地址或空字符串。") from None
        sources[key] = Source(key, title, url)
    return sources


def load_catalog(path: Path) -> dict[str, Building]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise GuideError(f"建筑资料 JSON 第 {exc.lineno} 行附近格式有误，请检查逗号和引号。") from None
    except (OSError, UnicodeError):
        raise GuideError("无法读取 data/buildings.json，请确认文件存在且以 UTF-8 保存。") from None

    rows = records(raw, "建筑资料")
    if len(rows) != 3:
        raise GuideError("请在 data/buildings.json 中保留本次导览的三张建筑卡。")
    buildings = {}
    for row in rows:
        key = record_id(row, buildings, "建筑")
        name = required_text(row.get("name"), f"建筑 {key} 的 name")
        if type(row.get("placeholder")) is not bool:
            raise GuideError(f"{name} 的 placeholder 请填写 true 或 false。")
        cues = strings(row.get("visual_cues"), f"{name} 的 visual_cues")
        refs = strings(row.get("reference_images"), f"{name} 的 reference_images")
        for ref in refs:
            if (Path(ref).suffix.lower() not in {".jpg", ".jpeg", ".png"}
                    or "/" in ref or "\\" in ref or ":" in ref or "\x00" in ref):
                raise GuideError(f"{name} 的参考图请填写 reference_images 目录下的 JPG 或 PNG 文件名。")
        if len(refs) > 2 or len(set(refs)) != len(refs):
            raise GuideError(f"{name} 的 reference_images 最多填写两张不同的参考照片。")
        sources = read_sources(row.get("sources"), name)
        facts = {}
        for item in records(row.get("facts"), f"{name} 的 facts"):
            fid = record_id(item, facts, f"{name}的事实")
            line = required_text(item.get("text"), f"{name} 事实 {fid} 的 text")
            keywords = strings(item.get("keywords", []), f"{name} 事实 {fid} 的 keywords")
            ids = strings(item.get("source_ids"), f"{name} 事实 {fid} 的 source_ids")
            if not set(ids).issubset(sources):
                raise GuideError(f"{name} 事实 {fid} 引用了该卡 sources 里不存在的编号。")
            facts[fid] = Fact(fid, line, keywords, ids)
        guide_ids = strings(row.get("guide_fact_ids", []), f"{name} 的 guide_fact_ids")
        if len(set(guide_ids)) != len(guide_ids) or not set(guide_ids).issubset(facts):
            raise GuideError(f"{name} 的 guide_fact_ids 须分别指向本卡不同的事实编号。")
        photo_label = required_text(row["photo_label"], f"{name} 的 photo_label") if "photo_label" in row else ""
        buildings[key] = Building(key, name, row["placeholder"], cues, refs, sources, facts, guide_ids, photo_label)
    return buildings
