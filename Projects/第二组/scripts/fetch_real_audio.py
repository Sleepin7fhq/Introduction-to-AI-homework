"""fetch_real_audio.py —— 下载真实音频样例（用于答辩演示的离线推理）。

数据源：Wikimedia Commons（自由许可音频）。下载后统一转成 16kHz / 16bit / 单声道 WAV。
网络不稳定时脚本会指数退避重试；已存在的文件会跳过。
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "DormNoiseDemo/1.0 (educational offline project; non-commercial)"

# (本地文件名, Commons 文件标题)
WANTED = [
    ("applause.ogg", "File:Applause.ogg"),
    ("cheering.ogg", "File:Cheering.ogg"),
    ("shouting.ogg", "File:Shouting.ogg"),
    ("gameplay.ogg", "File:Playing a video game.ogg"),
    ("game_intro.ogg", "File:Paratrooper (video game intro music).ogg"),
    ("drum.ogg", "File:Drum.ogg"),
    ("guitar_solo.ogg", "File:Wikipedia guitar solo.ogg"),
    ("piano.ogg", "File:Piano.ogg"),
    ("male_voice.ogg", "File:English male voice speech word No.ogg"),
    ("crowd.ogg", "File:Crowd.ogg"),
    ("talk.ogg", "File:Talking.ogg"),
    ("video_game.ogg", "File:Video game music.ogg"),
]


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolve_url(title: str, tries: int = 6) -> str | None:
    api = ("https://commons.wikimedia.org/w/api.php?action=query&titles="
           + urllib.parse.quote(title)
           + "&prop=imageinfo&iiprop=url&format=json")
    for attempt in range(tries):
        try:
            data = json.loads(_get(api, timeout=40).decode("utf-8"))
            page = list(data["query"]["pages"].values())[0]
            if "imageinfo" in page:
                return page["imageinfo"][0]["url"].split("?")[0]
            return None
        except Exception as exc:  # 网络抖动/限流
            print(f"  resolve retry {attempt + 1}/{tries}: {exc}")
            time.sleep(10 * (attempt + 1))
    return None


def download(url: str, dest: Path, tries: int = 6) -> bool:
    for attempt in range(tries):
        try:
            dest.write_bytes(_get(url))
            print(f"  ✓ {dest.name}  {dest.stat().st_size} bytes")
            return True
        except Exception as exc:
            print(f"  dl retry {attempt + 1}/{tries}: {exc}")
            time.sleep(10 * (attempt + 1))
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir",
                    default=str(Path(__file__).resolve().parent.parent / "assets" / "audio_demo" / "_src"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ok, failed = [], []
    for name, title in WANTED:
        dest = out / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  = {name} 已存在")
            ok.append(name)
            continue
        url = resolve_url(title)
        if not url:
            print(f"  × {name} 未在 Commons 找到")
            failed.append(name)
            continue
        if download(url, dest):
            ok.append(name)
        else:
            failed.append(name)
        time.sleep(8)

    print("\n成功:", ok)
    print("失败:", failed)


if __name__ == "__main__":
    main()
