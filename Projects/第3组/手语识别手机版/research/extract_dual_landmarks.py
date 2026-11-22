"""Extract both hands and body trajectories from NationalCSL-DP image sequences."""
from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

POSE_IDS = (0, 11, 12, 13, 14, 15, 16, 23, 24)
DETECTORS = None


def initialize(hand_model, pose_model):
    global DETECTORS
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(hand_model)), num_hands=2,
        min_hand_detection_confidence=0.35, min_hand_presence_confidence=0.40))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(pose_model)),
        min_pose_detection_confidence=0.45, min_pose_presence_confidence=0.45))
    DETECTORS = (mp, hands, pose)


def load_image(path):
    from PIL import Image
    mp, _, _ = DETECTORS
    with Image.open(path) as picture:
        rgb = np.array(picture.convert("RGB"))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def choose_hands(candidates, handed, pose_wrists, pose_visibility, previous):
    choice = [-1, -1]
    if not len(candidates):
        return choice
    cost = np.zeros((len(candidates), 2), dtype=np.float64)
    for index, (candidate, category) in enumerate(zip(candidates, handed)):
        wrist = candidate[0, :2]
        for side, word in enumerate(("Left", "Right")):
            if category.category_name != word:
                cost[index, side] += 0.10 * float(category.score)
            if pose_visibility[side] > 0.32:
                cost[index, side] += np.linalg.norm(wrist - pose_wrists[side, :2])
            if np.isfinite(previous[side, 0]):
                cost[index, side] += 0.65 * np.linalg.norm(wrist - previous[side, :2])
    if len(candidates) == 1:
        choice[int(np.argmin(cost[0]))] = 0
    elif (cost[0, 0] + cost[1, 1]) <= (cost[1, 0] + cost[0, 1]):
        choice = [0, 1]
    else:
        choice = [1, 0]
    return choice


def locate_clip(job):
    images, signer, word, label, frame_count, output, length = job
    path = output / signer / f"{word}.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as cache:
            if cache["hands"].shape == (length, 2, 21, 3):
                return int(cache["hand_mask"].sum()), int(cache["pose_mask"].sum())
    pictures = sorted((images / signer / "front" / word).glob("*.jpg"))
    if len(pictures) != frame_count or not pictures:
        raise ValueError(f"Missing source frames in {signer}/{word}")
    _, hands, pose = DETECTORS
    clock = np.linspace(0, len(pictures) - 1, length).round().astype(int)
    frames = {i: load_image(pictures[i]) for i in set(clock)}
    pose_times = np.unique(np.linspace(0, length - 1, min(5, length)).round().astype(int))
    unique_pose = {}
    for i in pose_times:
        frame = clock[i]
        if frame not in unique_pose:
            result = pose.detect(frames[frame]).pose_landmarks
            unique_pose[frame] = (np.array([[result[0][j].x, result[0][j].y, result[0][j].z,
                                            result[0][j].visibility] for j in POSE_IDS], dtype=np.float32)
                                  if result else None)
    body = np.zeros((length, len(POSE_IDS), 4), dtype=np.float32)
    pose_mask = np.zeros(length, dtype=bool)
    found = [(i, unique_pose[clock[i]]) for i in pose_times if unique_pose[clock[i]] is not None]
    if found:
        indices, measured = zip(*found)
        measured = np.stack(measured).reshape(len(found), -1)
        body = np.column_stack([np.interp(np.arange(length), indices, trace) for trace in measured.T])
        body = body.reshape(length, len(POSE_IDS), 4).astype(np.float32)
        pose_mask[:] = (body[:, 1, 3] > 0.30) & (body[:, 2, 3] > 0.30)
    detection = {}
    poses = np.zeros((length, 2, 21, 3), dtype=np.float32)
    hand_mask = np.zeros((length, 2), dtype=bool)
    prior = np.full((2, 3), np.nan, dtype=np.float32)
    for i, frame in enumerate(clock):
        if frame not in detection:
            result = hands.detect(frames[frame])
            candidates = [np.array([[joint.x, joint.y, joint.z] for joint in hand], dtype=np.float32)
                          for hand in result.hand_landmarks]
            handed = [category[0] for category in result.handedness]
            detection[frame] = candidates, handed
        candidates, handed = detection[frame]
        wrists = body[i, 5:7]
        choices = choose_hands(candidates, handed, wrists[:, :3], wrists[:, 3], prior)
        for side, selected in enumerate(choices):
            if selected >= 0:
                poses[i, side] = candidates[selected]
                hand_mask[i, side] = True
                prior[side] = poses[i, side, 0]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, hands=poses, hand_mask=hand_mask, pose=body, pose_mask=pose_mask,
                            label=np.int64(label), frame_indices=clock, source_frames=frame_count)
    temporary.replace(path)
    return int(hand_mask.sum()), int(pose_mask.sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--hand-model", type=Path, required=True)
    parser.add_argument("--pose-model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--frames", type=int, default=12)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    with (args.images / "manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda row: row["signer"] not in {"Participant_07", "Participant_09"})
    if args.limit is not None:
        rows = rows[:args.limit]
    jobs = [(args.images, row["signer"], row["source_id"], int(row["class_index"]), int(row["frames"]),
             args.out, args.frames) for row in rows]
    report = {}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize,
                             initargs=(args.hand_model, args.pose_model)) as pool:
        for i, (job, (hands, pose)) in enumerate(zip(jobs, pool.map(locate_clip, jobs, chunksize=3)), 1):
            values = report.setdefault(job[1], {"clips": 0, "hand_frames": 0, "clips_with_hand": 0, "pose_frames": 0})
            values["clips"] += 1
            values["hand_frames"] += hands
            values["clips_with_hand"] += int(hands > 0)
            values["pose_frames"] += pose
            if i % 100 == 0 or i == len(jobs):
                print(f"Landmarks {i}/{len(jobs)}", flush=True)
    (args.out / "extraction.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report, flush=True)


if __name__ == "__main__":
    main()
