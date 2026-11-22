"""Convert the original DeepPCB repository into a group-disjoint YOLO dataset."""
import argparse
import csv
import json
import shutil
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

NAMES = ["open", "short", "mousebite", "spur", "copper", "pin-hole"]
VAL = {"group12100", "group50600"}
TEST = {"group77000", "group92000"}


def prepare(repo, dest):
    rows = []
    areas = []
    counts = {key: [0] * 6 for key in ("train", "val", "test")}
    seen = set()
    for image in sorted((repo / "PCBData").glob("group*/*/*_test.jpg")):
        group = image.parents[1].name
        key = image.stem.removesuffix("_test")
        if key in seen:
            raise ValueError(f"Duplicate sample {key}")
        seen.add(key)
        split = "val" if group in VAL else "test" if group in TEST else "train"
        truth = image.parents[1] / (image.parent.name + "_not") / (key + ".txt")
        template = image.with_name(key + "_temp.jpg")
        with Image.open(image) as frame:
            w, h = frame.size
            frame.verify()
        if (w, h) != (640, 640) or not template.is_file():
            raise ValueError(f"Invalid pair {key}")
        lines = []
        for line in truth.read_text().splitlines():
            if not line.strip():
                continue
            x1, y1, x2, y2, category = map(int, line.split())
            if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h and 1 <= category <= 6):
                raise ValueError(f"{truth}: {line}")
            bw, bh = x2 - x1, y2 - y1
            if split == "train":
                areas.append(bw * bh)
            counts[split][category-1] += 1
            lines.append(f"{category-1} {(x1+x2)/(2*w):.9f} {(y1+y2)/(2*h):.9f} {bw/w:.9f} {bh/h:.9f}")
        for folder in ("images", "labels"):
            (dest / folder / split).mkdir(exist_ok=True, parents=True)
        shutil.copyfile(image, dest / "images" / split / (key + ".jpg"))
        (dest / "labels" / split / (key + ".txt")).write_text("\n".join(lines) + "\n")
        rows.append((key, group, split, len(lines)))
    if len(rows) != 1500 or not all(min(v) > 0 for v in counts.values()):
        raise ValueError("Unexpected corpus or missing class")
    with (dest / "manifest.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "group", "split", "boxes"])
        writer.writerows(rows)
    stats = {"images": {s: sum(r[2] == s for r in rows) for s in counts},
             "instances": counts, "small_area_px2": float(np.percentile(areas, 25))}
    (dest / "stats.json").write_text(json.dumps(stats, indent=2))
    config = {"path": dest.resolve().as_posix(), "train": "images/train", "val": "images/val",
              "test": "images/test", "names": NAMES}
    (dest / "data.yaml").write_text(yaml.safe_dump(config), encoding="utf8")
    print(stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.repo, args.destination)

