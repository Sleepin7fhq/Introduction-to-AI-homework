"""Extract just the project's word frames from the nested NationalCSL-DP archive."""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from inspect_figshare import NestedFile

FRAME = re.compile(r"(\d+)\.(?:jpg|jpeg|png)", re.IGNORECASE)
SIGNERS = tuple(f"Participant_{number:02d}" for number in range(1, 11))


def select_images(outer: Path, label_map: Path, output: Path):
    vocabulary = json.loads(label_map.read_text(encoding="utf-8"))["meta"]["vocab"]
    words = {str(item["id"]).zfill(4): (index, item["label"], item["src_word"])
             for index, item in enumerate(vocabulary)}
    totals = {}
    rows = []
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(outer) as root:
        with root.open("gloss.csv") as glossary:
            published = {row[0]: row[1] for row in csv.reader(
                line.decode("utf-8-sig") for line in glossary) if len(row) > 1}
        mismatches = [(ident, name, published.get(ident)) for ident, (_, _, name) in words.items()
                      if name != published.get(ident)]
        print("gloss mismatches", mismatches, flush=True)
        for signer in SIGNERS:
            hits = defaultdict(list)
            with NestedFile(outer, root.getinfo(f"Pics/{signer}.zip")) as file, ZipFile(file) as pictures:
                for entry in pictures.infolist():
                    segments = entry.filename.split("/")
                    if len(segments) != 4 or segments[:2] != [signer, "front"] or segments[2] not in words:
                        continue
                    match = FRAME.fullmatch(segments[3])
                    if match and not entry.is_dir():
                        hits[segments[2]].append((int(match.group(1)), entry))
                for ident, files in sorted(hits.items()):
                    index, word, _ = words[ident]
                    directory = output / signer / "front" / ident
                    directory.mkdir(parents=True, exist_ok=True)
                    for number, entry in sorted(files):
                        target = directory / f"{number:05d}.jpg"
                        if not target.exists() or target.stat().st_size != entry.file_size:
                            temp = target.with_suffix(".tmp")
                            temp.write_bytes(pictures.read(entry))
                            temp.replace(target)
                    rows.append((signer, ident, index, word, len(files)))
            totals[signer] = {"words": len(hits), "frames": sum(map(len, hits.values())),
                              "missing_ids": sorted(words.keys() - hits.keys())}
            print(signer, totals[signer], flush=True)
        with NestedFile(outer, root.getinfo("Code/technical validation.zip")) as file, ZipFile(file) as validation:
            names = []
            for entry in validation.infolist():
                if "/front/" in entry.filename and entry.filename.lower().endswith(".npy"):
                    leaf = entry.filename.rsplit("/", 1)[1]
                    names.append(leaf.rsplit(".", 2)[0])
            overlap = sorted(set(names) & {item["src_word"] for item in vocabulary})
        total_video = {}
        for signer in ("Participant_07", "Participant_09"):
            with NestedFile(outer, root.getinfo(f"Videos/{signer}.zip")) as file, ZipFile(file) as videos:
                identifiers = {Path(name).stem.zfill(4) for name in videos.namelist()
                               if "/front/" in name and name.lower().endswith((".mp4", ".mts"))}
                total_video[signer] = sorted(identifiers & words.keys())
    with (output / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("signer", "source_id", "class_index", "label", "frames"))
        writer.writerows(rows)
    summary = {"frames": totals, "label_mismatches": mismatches, "published_keypoint_word_overlap": overlap,
               "original_video_word_overlap": total_video}
    (output / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print({k: v for k, v in summary.items() if k != "frames"}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("label_map", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    select_images(arguments.zip, arguments.label_map, arguments.output)
