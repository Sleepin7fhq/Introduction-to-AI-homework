"""Local image inference and batch reports. All coordinates use original image pixels."""
import base64
import csv
import hashlib
import html
import io
from collections import Counter
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
LABELS = ["断路", "短路", "缺口", "毛刺", "多余铜", "针孔"]
COLORS = ["#FF7E65", "#36D6EF", "#F8BE48", "#AD94FF", "#5BDEAC", "#FA88C5"]


def decode_image(data):
    with Image.open(io.BytesIO(data)) as src:
        if src.format not in {"JPEG", "PNG"}:
            raise ValueError("仅支持 JPG 或 PNG 图片")
        if src.width * src.height > 30_000_000:
            raise ValueError("图片超过 3000 万像素")
        return ImageOps.exif_transpose(src).convert("RGB")


def annotated(image, boxes):
    preview = image.copy()
    canvas = ImageDraw.Draw(preview)
    font = ImageFont.load_default(size=max(14, min(32, image.width // 35)))
    for box in boxes:
        c = box["class"]
        xy = box["xyxy"]
        canvas.rectangle(xy, outline=COLORS[c], width=max(2, image.width//280))
        label = f'{c+1}  {box["score"]:.2f}'
        x, y = xy[:2]
        text_box = canvas.textbbox((0,0), label, font=font)
        bw, bh = text_box[2]+7, text_box[3]+5
        x, y = max(0,min(x,image.width-bw)), max(0,y-bh)
        canvas.rectangle((x,y,x+bw,y+bh), fill=COLORS[c])
        canvas.text((x+3,y+1),label,font=font,fill="#121B22")
    return thumbnail(preview)


def thumbnail(image):
    preview = image.copy()
    preview.thumbnail((1000,1000))
    stream = io.BytesIO()
    preview.save(stream, format="JPEG", quality=88)
    return stream.getvalue()


class Detector:
    def __init__(self, weights, device):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.device = device
        self.lock = Lock()
        self.version = f"{Path(weights).stem} / {hashlib.sha256(Path(weights).read_bytes()).hexdigest()[:10]}"

    def detect(self, image, threshold):
        with self.lock:
            result = self.model.predict(image, imgsz=640, conf=threshold, iou=0.7,
                                        device=self.device, verbose=False)[0]
            raw = result.boxes.data.cpu().tolist()
        return [{"xyxy":[round(float(v), 2) for v in row[:4]], "score":float(row[4]),
                 "class":int(row[5])} for row in raw]


def inspect_batch(files, detector, threshold, progress=None):
    rows = []
    for index, (name, payload) in enumerate(files, start=1):
        record = {"id":index, "name":name, "boxes":[], "preview":None, "error":""}
        try:
            image = decode_image(payload)
            boxes = detector.detect(image, threshold)
            record.update(preview=annotated(image, boxes), original=thumbnail(image), boxes=boxes,
                          status="待复检" if boxes else "未检出缺陷")
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, RuntimeError) as exc:
            record.update(status="处理失败",error=str(exc))
        rows.append(record)
        if progress:
            progress(index / len(files))
    return {"id":uuid4().hex[:10], "date":datetime.now().astimezone().isoformat(timespec="seconds"),
            "version":detector.version, "conf":threshold, "rows":rows}


def summary(batch):
    rows = batch["rows"]
    ok = sum(r["status"] == "未检出缺陷" for r in rows)
    failed = sum(r["status"] == "处理失败" for r in rows)
    valid = len(rows)-failed
    counts = Counter(b["class"] for r in rows for b in r["boxes"])
    return {"total":len(rows), "valid":valid, "failed":failed, "review":valid-ok,
            "clear":ok, "rate":ok/valid if valid else None, "counts":[counts[i] for i in range(6)]}


def export_csv(batch):
    file = io.StringIO(newline="")
    writer = csv.writer(file)
    writer.writerow(["批次","时间","模型","阈值","序号","文件","状态","类别","置信度","x1","y1","x2","y2","错误"])
    def cell(value):
        return "'" + value if value.lstrip().startswith(("=","+","-","@")) else value
    for row in batch["rows"]:
        prefix = [batch["id"],batch["date"],batch["version"],batch["conf"],row["id"],cell(row["name"]),row["status"]]
        if not row["boxes"]:
            writer.writerow(prefix+[""]*6+[cell(row["error"])])
        for box in row["boxes"]:
            writer.writerow(prefix+[LABELS[box["class"]],round(box["score"],5),*box["xyxy"],""])
    return file.getvalue().encode("utf-8-sig")


def export_html(batch):
    s = summary(batch)
    rate = f'{s["rate"]:.1%}' if s["rate"] is not None else "无有效结果"
    blocks = []
    esc = html.escape
    for row in batch["rows"]:
        img = ""
        if row["preview"]:
            data = base64.b64encode(row["preview"]).decode()
            img = f'<img alt="检测结果图" src="data:image/jpeg;base64,{data}">'
        lines = "".join(f'<li>{b["class"]+1} · {LABELS[b["class"]]}　{b["score"]:.3f}　{b["xyxy"]}</li>' for b in row["boxes"])
        blocks.append(f'<section><h2>{row["id"]}. {esc(row["name"])}</h2><p>{row["status"]}　{esc(row["error"])}</p>{img}<ul>{lines}</ul></section>')
    freq = "　".join(f'{n} {v}' for n,v in zip(LABELS,s["counts"]))
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>PCB 检测报告</title>
    <style>body{{font:16px/1.6 sans-serif;max-width:950px;margin:3rem auto;padding:1rem;color:#173338}}
    img{{max-width:100%;width:450px}}section{{break-inside:avoid;border-top:1px solid #ddd}} h1{{font-size:32px}}</style>
    <h1>微瑕必究 · 批次检测报告</h1><p>批次 {batch["id"]}　{batch["date"]}<br>模型 {esc(batch["version"])}　置信度阈值 {batch["conf"]:.3f}</p>
    <p>上传 {s["total"]}　成功 {s["valid"]}　失败 {s["failed"]}　待复检 {s["review"]}　未检出缺陷 {s["clear"]}</p>
    <b>图块模拟合格率 {rate}</b><p>未检出缺陷图块数 ÷ 成功检测图块数。每张图代表一个图块。</p><p>{freq}</p>
    {''.join(blocks)}</html>""".encode("utf8")

