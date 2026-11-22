"""Compare single-hand, dual-hand and body-aware sign classification on matched clips."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import numpy as np

PARENTS = np.array([0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19])
TIPS = np.array([4, 8, 12, 16, 20])
PA, PB = np.triu_indices(21, 1)
PARTS = {
    "single": (1, 0, 0, 0, 0),
    "dual": (0.45, 0.55, 0, 0, 0),
    "trajectory": (0, 0, 0.55, 0.45, 0),
    "full": (0.20, 0.25, 0.28, 0.22, 0.05),
    "movement_weighted": (0.10, 0.16, 0.37, 0.34, 0.03),
    "geometry_weighted": (0.27, 0.37, 0.18, 0.16, 0.02),
}


def fill(data, observed, fallback=0):
    steps = np.flatnonzero(observed)
    if not len(steps):
        return np.broadcast_to(fallback, data.shape).astype(np.float32).copy()
    shape = data.shape
    traces = data[steps].reshape(len(steps), -1)
    return np.column_stack([np.interp(np.arange(len(data)), steps, trace) for trace in traces.T]
                           ).reshape(shape).astype(np.float32)


def temporal(values):
    a = np.asarray(values, dtype=np.float32).reshape(len(values), -1)
    clock = np.linspace(0, len(a) - 1, 8)
    points = np.column_stack([np.interp(clock, np.arange(len(a)), trace) for trace in a.T])
    chunks = np.array_split(a, 3)
    segments = np.concatenate([part.mean(axis=0) for part in chunks])
    pooled = np.r_[a.mean(axis=0), a.std(axis=0), a.max(axis=0) - a.min(axis=0)]
    return np.r_[points.ravel() * 0.75, segments, pooled].astype(np.float32)


def features(hands, body, hand_mask, pose_mask):
    length = len(hands)
    filled_body = fill(body, pose_mask)
    center = fill(filled_body[:, 1:3, :2].mean(axis=1), pose_mask, (0.50, 0.37))
    width = np.linalg.norm(filled_body[:, 1, :2] - filled_body[:, 2, :2], axis=1)
    width = np.maximum(fill(width, pose_mask, 0.35), 0.12)
    pose_xy = (filled_body[..., :2] - center[:, None]) / width[:, None, None]
    if not pose_mask.any():
        pose_xy.fill(0)
    locals = []
    similarity = []
    wrists = []
    angles = []
    for side in range(2):
        visible = hand_mask[:, side]
        points = fill(hands[:, side], visible)
        local = points - points[:, :1]
        scale = max(float(np.quantile(np.linalg.norm(local[:, 9, :2], axis=-1), 0.65)), 0.025)
        local /= scale
        bones = local[:, 1:] - local[:, PARENTS]
        bones /= np.maximum(np.linalg.norm(bones, axis=-1, keepdims=True), 0.07)
        palm = local[:, 9, :2].copy()
        palm /= np.maximum(np.linalg.norm(palm, axis=-1, keepdims=True), 0.08)
        tangent = np.stack((palm[:, 1], -palm[:, 0]), axis=1)
        canonical = np.stack(((local[..., :2] * tangent[:, None]).sum(axis=-1),
                              (local[..., :2] * palm[:, None]).sum(axis=-1)), axis=-1)
        radii = np.linalg.norm(local[:, PA, :2] - local[:, PB, :2], axis=-1)
        geometry = np.concatenate((local[:, 1:, :2].reshape(length, -1), 0.45 * canonical.reshape(length, -1),
                                   0.60 * bones[..., :2].reshape(length, -1),
                                   radii * 0.45, local[:, TIPS, 2] * 0.32), axis=1)
        fallback_wrist = fill(body[:, 5 + side, :2], pose_mask & (body[:, 5 + side, 3] > 0.28), center)
        wrist = np.where(visible[:, None], hands[:, side, 0, :2], fallback_wrist)
        known = visible | (pose_mask & (body[:, 5 + side, 3] > 0.28))
        wrist = fill(wrist, known, center)
        wrists.append((wrist - center) / width[:, None])
        locals.append(geometry)
        similarity.append(visible.mean())
        angles.append(palm.copy())
    dominant = int(np.argmax(np.asarray(similarity) + 0.10 * np.array([np.std(w, axis=0).sum() for w in wrists])))
    anatomy = np.stack(wrists, axis=1)
    out_motion = np.concatenate((anatomy.reshape(length, 4), (wrists[0] - wrists[1]), pose_xy[:, 0]), axis=1)
    delta = np.diff(out_motion, axis=0)
    motion = np.concatenate((delta, np.abs(delta)), axis=1)
    arms = np.concatenate((pose_xy[:, 3:7].reshape(length, 8), np.stack(angles, axis=1).reshape(length, 4)), axis=1)
    mask_summary = np.r_[hand_mask.mean(axis=0), hand_mask.all(axis=1).mean(), pose_mask.mean()].astype(np.float32)
    return (temporal(locals[dominant]), temporal(np.concatenate(locals, axis=1)),
            temporal(out_motion), np.r_[temporal(motion), temporal(arms)], mask_summary)


def canonical_distances(query, reference):
    scale = max(float(reference.std(axis=0).mean()), 1e-3)
    x, y = query / scale, reference / scale
    squared = np.maximum(np.sum(x * x, axis=1)[:, None] + np.sum(y * y, axis=1)[None, :] - 2 * x @ y.T, 0)
    n = len(reference)
    return squared / max(float(np.median(squared[:n, :])), 1e-3)


def kernels(features, train, query, sets):
    indices = np.r_[train, query]
    dist = [canonical_distances(value[indices], value[train]) for value in features]
    for name in sets:
        weights = PARTS[name]
        combined = sum(weight * block for weight, block in zip(weights, dist) if weight)
        gram = 0.55 * np.exp(-0.55 * combined) + 0.45 * np.exp(-1.65 * combined)
        yield name, gram


def fit_predict(gram, target, strength):
    n = len(target)
    solve = gram[:n].copy()
    solve.flat[::n + 1] += strength
    return gram[n:] @ np.linalg.solve(solve, target)


def score(logits, truth):
    order = np.argsort(-logits, axis=1, kind="stable")
    return {"n": int(len(truth)), "top1": int((order[:, 0] == truth).sum()),
            "top5": int((order[:, :5] == truth[:, None]).any(axis=1).sum())}


def cv_score(features, y, signers, people, modes, reg):
    scores = {(mode, lam): np.zeros((sum(np.isin(signers, people)), 203), dtype=np.float32)
              for mode in modes for lam in reg}
    used = np.flatnonzero(np.isin(signers, people))
    for person in people:
        local = signers[used] == person
        train, held = used[~local], used[local]
        target = np.eye(203, dtype=np.float32)[y[train]]
        for mode, kernel in kernels(features, train, held, modes):
            for strength in reg:
                scores[(mode, strength)][local] = fit_predict(kernel, target, strength)
        print("validated", person, flush=True)
    return {config: score(logits, y[used]) for config, logits in scores.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--landmarks", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--legacy-predictions", type=Path)
    args = parser.parse_args()
    with args.manifest.open(encoding="utf-8-sig", newline="") as handle:
        clips = list(csv.DictReader(handle))
    vectors = []
    for clip in clips:
        with np.load(args.landmarks / clip["signer"] / f"{clip['source_id']}.npz", allow_pickle=False) as data:
            if int(data["label"]) != int(clip["class_index"]):
                raise ValueError("Landmark label disagrees with manifest")
            vectors.append(features(data["hands"], data["pose"], data["hand_mask"], data["pose_mask"]))
    blocks = [np.stack(batch) for batch in zip(*vectors)]
    y = np.array([int(clip["class_index"]) for clip in clips])
    people = np.array([clip["signer"] for clip in clips])
    base = ("Participant_03", "Participant_04", "Participant_06", "Participant_08", "Participant_10")
    added = ("Participant_07", "Participant_09")
    held = ("Participant_01", "Participant_02", "Participant_05")
    test = np.flatnonzero(np.isin(people, held))
    variants = list(PARTS)
    strengths = (0.05, 0.22)
    cv = cv_score(blocks, y, people, base + added, variants, strengths)
    ranking = lambda config: (cv[config]["top1"], cv[config]["top5"])
    chosen = max((config for config in cv if config[0] in ("full", "movement_weighted", "geometry_weighted")), key=ranking)
    simple = {name: max((config for config in cv if config[0] == name), key=ranking)[1]
              for name in ("single", "dual", "trajectory")}
    configs = dict(simple, **{chosen[0]: chosen[1]})
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"validation": {f"{name}/{reg}": m for (name, reg), m in cv.items()}, "selected": chosen,
              "configs": configs, "legacy_test_signers": held}
    predictions = {}
    for group, fit_group, query in (("five", base, test), ("seven", base + added, test)):
        train = np.flatnonzero(np.isin(people, fit_group))
        target = np.eye(203, dtype=np.float32)[y[train]]
        measured = {}
        for name, gram in kernels(blocks, train, query, configs):
            values = fit_predict(gram, target, configs[name])
            measured[name] = score(values, y[query])
            predictions[f"{group}_{name}"] = values
            if group == "seven" and name == chosen[0]:
                n = len(target)
                system = gram[:n].copy()
                system.flat[::n + 1] += configs[name]
                coefficient = np.linalg.solve(system, target)
                np.savez_compressed(args.out / "dual_motion_model.npz", kernel_name=name, coefficient=coefficient,
                                    **{f"reference_{index}": block[train] for index, block in enumerate(blocks)})
        report[group] = measured
        print(group, measured, flush=True)
    if args.legacy_predictions:
        with np.load(args.legacy_predictions, allow_pickle=False) as previous:
            lookup = {key: i for i, key in enumerate(zip(previous["signer"], previous["y"]))}
            order = [lookup[key] for key in zip(people[test], y[test])]
            legacy = previous["combined"][order]
        def standardized(values):
            return (values - values.mean(axis=1, keepdims=True)) / np.maximum(values.std(axis=1, keepdims=True), 1e-5)
        combined = 0.80 * standardized(predictions[f"seven_{chosen[0]}"]) + 0.20 * standardized(legacy)
        report["legacy_reference"] = score(legacy, y[test])
        report["fixed_legacy_blend"] = score(combined, y[test])
        predictions.update(legacy=legacy, fixed_legacy_blend=combined)
        print("legacy / fixed blend", report["legacy_reference"], report["fixed_legacy_blend"], flush=True)
    predictions.update(test_y=y[test], test_signer=people[test])
    np.savez_compressed(args.out / "predictions.npz", **predictions)
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
