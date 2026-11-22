"""Tune motion alignment and classification by signer-held-out validation."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import numpy as np

from train_real_frames import PARTS, PARENTS, canonical_distances, features, fill, fit_predict, score

FRAMES = 8
BASE = ("Participant_03", "Participant_04", "Participant_06", "Participant_07",
        "Participant_08", "Participant_09", "Participant_10")
TEST = ("Participant_01", "Participant_02", "Participant_05")
# name, DTW share, kernel gamma multiplier, ridge penalty, nearest-exemplar share
SETTINGS = (
    ("baseline", 0.0, 1.0, 0.05, 0.0),
    ("ridge-mild", 0.0, 1.0, 0.015, 0.0),
    ("ridge-fine", 0.0, 1.75, 0.025, 0.0),
    ("exemplar", 0.0, 1.0, 0.05, 0.22),
    ("align20", 0.20, 1.0, 0.050, 0.0),
    ("align40", 0.40, 1.0, 0.050, 0.0),
    ("align55", 0.55, 1.0, 0.050, 0.0),
    ("align40-mild", 0.40, 1.0, 0.015, 0.0),
    ("align55-fine", 0.55, 1.60, 0.025, 0.0),
    ("align40-exemplar", 0.40, 1.0, 0.05, 0.22),
    ("align70-fine", 0.70, 1.60, 0.025, 0.0),
)


def motion_sequence(hands, body, present, seen):
    center = fill(body[:, 1:3, :2].mean(axis=1), seen, (0.50, 0.37))
    width = np.linalg.norm(body[:, 1, :2] - body[:, 2, :2], axis=1)
    width = np.maximum(fill(width, seen, 0.35), 0.12)
    wrists, shapes, directions = [], [], []
    for side in range(2):
        found = present[:, side]
        points = fill(hands[:, side], found)
        relative = points - points[:, :1]
        scale = max(float(np.quantile(np.linalg.norm(relative[:, 9, :2], axis=-1), 0.65)), 0.025)
        relative /= scale
        bones = relative[:, 1:] - relative[:, PARENTS]
        bones /= np.maximum(np.linalg.norm(bones, axis=-1, keepdims=True), 0.07)
        pose_known = seen & (body[:, 5 + side, 3] > 0.28)
        detected = np.where(found[:, None], hands[:, side, 0, :2], body[:, 5 + side, :2])
        wrist = fill(detected, found | pose_known, center)
        wrists.append((wrist - center) / width[:, None])
        # Give the geometry of each hand and the path of each wrist comparable scale.
        shapes.append(relative[:, 1:, :2].reshape(len(hands), -1) * 0.22)
        directions.append(bones[:, :, :2].reshape(len(hands), -1) * 0.10)
    motion = np.concatenate([*wrists, *(x * 0.2 for x in directions), *shapes,
                             0.14 * present.astype(np.float32)], axis=1)
    clock = np.linspace(0, len(motion) - 1, FRAMES)
    resampled = np.column_stack([np.interp(clock, np.arange(len(motion)), trace) for trace in motion.T])
    return resampled.astype(np.float32)


def dtw_distance(query, reference):
    size = len(query)
    length = query.shape[1]
    right = reference.reshape(-1, query.shape[-1])
    norms = np.sum(right * right, axis=1)
    distance = np.empty((size, len(reference)), dtype=np.float32)
    for offset in range(0, size, 48):
        chunk = query[offset:offset + 48].reshape(-1, query.shape[-1])
        delta = np.maximum(np.sum(chunk * chunk, axis=1)[:, None] + norms[None]
                           - 2 * (chunk @ right.T), 0)
        delta = delta.reshape(-1, length, len(reference), length)
        shape = (len(delta), len(reference))
        infinity = np.full(shape, np.inf, dtype=np.float32)
        last = [np.zeros(shape, dtype=np.float32)] + [infinity] * length
        for i in range(length):
            row = [infinity]
            for j in range(length):
                if abs(i - j) > 2:
                    row.append(infinity)
                else:
                    step = delta[:, i, :, j]
                    # A repetition aligns speed changes but has a modest extra cost.
                    row.append(np.minimum(last[j] + step,
                               np.minimum(last[j + 1], row[-1]) + 1.12 * step + 0.018))
            last = row
        distance[offset:offset + len(delta)] = last[-1] / length
    return distance


def normalize_logits(values):
    return (values - values.mean(axis=1, keepdims=True)) / np.maximum(values.std(axis=1, keepdims=True), 1e-5)


def nearest_class(dist, labels):
    index = np.argsort(labels, kind="stable")
    values = dist[:, index].reshape(len(dist), 203, -1)
    nearest = np.partition(values, 1, axis=2)[:, :, :2]
    return -(0.65 * nearest.min(axis=2) + 0.35 * nearest.max(axis=2))


def evaluate_fold(blocks, distances, train, val, labels, settings):
    indices = np.r_[train, val]
    baseline = sum(weight * canonical_distances(block[indices], block[train])
                   for block, weight in zip(blocks, PARTS["geometry_weighted"]))
    aligned = distances[np.ix_(indices, train)]
    aligned /= max(float(np.median(aligned[:len(train)])), 1e-3)
    target = np.eye(203, dtype=np.float32)[labels[train]]
    matrices = {}
    outputs = {}
    for name, alignment, gamma, ridge, exemplar in settings:
        if (alignment, gamma) not in matrices:
            distance = (1 - alignment) * baseline + alignment * aligned
            kernel = 0.55 * np.exp((-0.55 * gamma) * distance) + 0.45 * np.exp((-1.65 * gamma) * distance)
            matrices[(alignment, gamma)] = (kernel, distance[len(train):])
        kernel, distance = matrices[(alignment, gamma)]
        key = (alignment, gamma, ridge)
        if key not in outputs:
            outputs[key] = fit_predict(kernel, target, ridge)
        prediction = normalize_logits(outputs[key])
        if exemplar:
            near = normalize_logits(nearest_class(distance, labels[train]))
            prediction = (1 - exemplar) * prediction + exemplar * near
        yield name, prediction


def load_features(manifest, directory):
    with manifest.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    blocks, sequence = [], []
    for row in rows:
        with np.load(directory / row["signer"] / (row["source_id"] + ".npz"), allow_pickle=False) as values:
            arguments = [values[key] for key in ("hands", "pose", "hand_mask", "pose_mask")]
            blocks.append(features(*arguments))
            sequence.append(motion_sequence(*arguments))
    return [np.stack(block) for block in zip(*blocks)], np.stack(sequence), \
        np.array([int(row["class_index"]) for row in rows]), np.array([row["signer"] for row in rows])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--landmarks", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    blocks, sequence, labels, people = load_features(args.manifest, args.landmarks)
    print("descriptors ready", sequence.shape, flush=True)
    train = np.flatnonzero(np.isin(people, BASE))
    test = np.flatnonzero(np.isin(people, TEST))
    if len(train) != 1421 or len(test) != 609:
        raise ValueError("Incomplete split")
    cache = args.out / "dtw.npy"
    if cache.exists():
        distances = np.load(cache, allow_pickle=False)
        if distances.shape != (len(sequence), len(sequence)):
            raise ValueError("Cached distances do not match the manifest")
    else:
        distances = dtw_distance(sequence, sequence)
        np.save(cache, distances, allow_pickle=False)
    print("DTW scores ready", flush=True)
    valid = {config[0]: np.empty((len(train), 203), dtype=np.float32) for config in SETTINGS}
    for person in BASE:
        held = people[train] == person
        for model, values in evaluate_fold(blocks, distances, train[~held], train[held], labels, SETTINGS):
            valid[model][held] = values
        print("validation", person, flush=True)
    cv = {name: score(values, labels[train]) for name, values in valid.items()}
    ordering = sorted(cv, key=lambda name: (cv[name]["top1"], cv[name]["top5"]), reverse=True)
    winner = ordering[0]
    outcome = {"validation": cv, "selected": winner, "settings": SETTINGS}
    print("locked:", winner, cv[winner], flush=True)
    (args.out / "locked.json").write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    comparators = [config for config in SETTINGS if config[0] in {"baseline", winner}]
    test_values = dict(evaluate_fold(blocks, distances, train, test, labels, comparators))
    outcome["test"] = {name: score(values, labels[test]) for name, values in test_values.items()}
    outcome["test_by_signer"] = {name: {person: score(values[people[test] == person], labels[test][people[test] == person])
                                         for person in TEST} for name, values in test_values.items()}
    np.savez_compressed(args.out / "predictions.npz", **test_values, label=labels[test], signer=people[test])
    (args.out / "metrics.json").write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    print(outcome["test"], flush=True)


if __name__ == "__main__":
    main()
