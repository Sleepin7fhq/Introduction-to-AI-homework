"""Train controlled YOLO11n baseline and high-resolution P2 variant."""
import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.utils import ROOT

class SharedInitTrainer(DetectionTrainer):
    def get_model(self, cfg=None, weights=None, verbose=True):
        model = super().get_model(cfg, weights=None, verbose=verbose)
        pretrained = YOLO(self.initial_weights).model.state_dict()
        shared = {k: v for k, v in pretrained.items() if int(k.split(".")[1]) < 23}
        missing, unexpected = model.load_state_dict(shared, strict=False)
        assert not unexpected and all(int(k.split(".")[1]) >= 23 for k in missing)
        print(f"Loaded {len(shared)} shared state entries from layers 0 through 22", flush=True)
        return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--variant", choices=["baseline","p2"], required=True)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=8)
    args = parser.parse_args()
    args.runs.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load((ROOT / "cfg/models/11/yolo11.yaml").read_text())
    cfg.update(nc=6, scale="n")
    if args.variant == "p2":
        cfg["head"][-1:] = [[16, 1, "nn.Upsample", [None, 2, "nearest"]],
                             [[-1, 2], 1, "Concat", [1]],
                             [-1, 2, "C3k2", [256, False]],
                             [[25, 16, 19, 22], 1, "Detect", ["nc"]]]
    config = args.runs / f"yolo11n-{args.variant}.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf8")
    trainer = SharedInitTrainer(overrides=dict(model=str(config.resolve()), data=str(args.data.resolve()),
        epochs=args.epochs, batch=args.batch, device=0, imgsz=640, seed=42, deterministic=True,
        optimizer="AdamW", lr0=0.001, workers=2, plots=False, amp=True, cache=False,
        project=str(args.runs.resolve()), name=args.variant, mosaic=0.0, scale=0.15,
        translate=0.05, hsv_h=0, hsv_s=0, hsv_v=0, fliplr=0.5, pretrained=False))
    trainer.initial_weights = str(args.weights.resolve())
    trainer.train()


if __name__ == "__main__":
    main()

