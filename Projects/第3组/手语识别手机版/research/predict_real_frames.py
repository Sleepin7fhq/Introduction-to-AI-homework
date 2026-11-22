"""Predict a CSL word from a saved dual-hand landmark sequence."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import numpy as np

from train_real_frames import PARTS, canonical_distances, features


def predict(blocks, model):
    name = str(model["kernel_name"])
    distance = np.zeros((len(blocks[0]), len(model["coefficient"])), dtype=np.float32)
    for index, weight in enumerate(PARTS[name]):
        if weight == 0:
            continue
        train = model[f"reference_{index}"].astype(np.float32)
        if f"scale_{index}" not in model:
            raw = canonical_distances(np.concatenate((train, blocks[index])), train)
            distance += weight * raw[len(train):]
            continue
        query = blocks[index] / model[f"scale_{index}"]
        square = (np.sum(query * query, axis=1)[:, None] + np.sum(train * train, axis=1)[None, :]
                  - 2 * (query @ train.T))
        distance += weight * np.maximum(square, 0) / model[f"median_{index}"]
    matrix = 0.55 * np.exp(-0.55 * distance) + 0.45 * np.exp(-1.65 * distance)
    return matrix @ model["coefficient"]


def load_features(path):
    with np.load(path, allow_pickle=False) as source:
        return features(source["hands"], source["pose"], source["hand_mask"], source["pose_mask"])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("landmarks", type=Path)
    cli.add_argument("--model", type=Path, default=Path(__file__).parent / "dual_motion_model.npz")
    cli.add_argument("--label-map", type=Path, default=Path(__file__).parent / "label_map.json")
    cli.add_argument("--top", type=int, default=5, choices=range(1, 204), metavar="1-203")
    args = cli.parse_args()
    blocks = [item[None, :] for item in load_features(args.landmarks)]
    with np.load(args.model, allow_pickle=False) as model:
        scores = predict(blocks, model)[0]
    names = json.loads(args.label_map.read_text(encoding="utf-8"))["labels"]
    chosen = np.argsort(-scores, kind="stable")[:args.top]
    print(json.dumps([{"word": names[str(index)], "index": int(index)} for index in chosen],
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
