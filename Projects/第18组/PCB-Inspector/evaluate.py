"""Choose the deployable model on validation images, then evaluate both held-out models."""
import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from faster_coco_eval import COCO, COCOeval_faster
from ultralytics import YOLO

from prepare_data import NAMES


def ground_truth(dataset, split):
    images, annotations, truth = [], [], {}
    paths = sorted((dataset / "images" / split).glob("*.jpg"))
    for img_id, path in enumerate(paths, 1):
        images.append(dict(id=img_id, width=640, height=640, file_name=path.name))
        truth[path.stem] = []
        for line in (dataset / "labels" / split / (path.stem + ".txt")).read_text().splitlines():
            c, x, y, w, h = map(float, line.split())
            x1,y1,x2,y2 = [round(v*640) for v in (x-w/2,y-h/2,x+w/2,y+h/2)]
            bw, bh = x2-x1, y2-y1
            annotations.append(dict(id=len(annotations)+1,image_id=img_id,category_id=int(c)+1,
                                    bbox=[x1,y1,bw,bh],area=bw*bh,iscrowd=0))
            truth[path.stem].append([x1,y1,x2,y2,int(c)])
    coco = COCO()
    coco.dataset = dict(images=images,annotations=annotations,
                        categories=[dict(id=i+1,name=n) for i,n in enumerate(NAMES)])
    coco.createIndex()
    return paths,truth,coco


def collect(model, paths):
    cached, dets = {}, []
    for img_id, path in enumerate(paths, 1):
        res = model.predict(path, conf=0.001, iou=0.7, imgsz=640, device=0, verbose=False)[0]
        rows = sorted(res.boxes.data.cpu().tolist(),key=lambda r:-r[4])
        cached[path.stem] = rows
        for x1,y1,x2,y2,score,cat in rows:
            dets.append(dict(image_id=img_id,category_id=int(cat)+1,bbox=[x1,y1,x2-x1,y2-y1],score=score))
    return cached,dets


def metrics(coco, dets, small):
    ev = COCOeval_faster(coco,coco.loadRes(dets),"bbox")
    ev.params.areaRng = [[0,1e10],[0,small]]
    ev.params.areaRngLbl = ["all","study-small"]
    ev.evaluate()
    ev.accumulate()
    p = ev.eval["precision"]  # IoU, recall, category, area, max-detections
    def avg(arr):
        return float(np.mean(arr[arr>=0]))
    return dict(map=avg(p[:,:,:,0,-1]),ap50=avg(p[0,:,:,0,-1]),small_ap50=avg(p[0,:,:,1,-1]),
                per_class=[avg(p[0,:,i,0,-1]) for i in range(6)])


def iou(a,b):
    inter = max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def match(truth, preds, threshold, small, details=False):
    tp=fp=fn=hits=small_n=0
    cases={}
    for key, gt in truth.items():
        taken=set()
        errors=[]
        for box in preds[key]:
            if box[4] < threshold:
                break
            overlaps=[(iou(box,g),i) for i,g in enumerate(gt) if i not in taken and int(box[5])==g[4]]
            overlap,idx=max(overlaps,default=(0,-1))
            if overlap>=0.5:
                taken.add(idx)
                tp+=1
            else:
                fp+=1
                errors.append(box)
        missed=[g for i,g in enumerate(gt) if i not in taken]
        fn+=len(missed)
        for i,g in enumerate(gt):
            if (g[2]-g[0])*(g[3]-g[1])<=small:
                small_n+=1
                hits+=i in taken
        if details and (missed or errors):
            cases[key]=dict(missed=missed,false_positives=errors)
    return dict(tp=tp,fp=fp,fn=fn,f1=2*tp/max(1,2*tp+fp+fn),small_recall=hits/max(1,small_n),
                small_n=small_n,small_hits=hits),cases


def latency(model, files, threshold):
    pictures = []
    for idx in np.linspace(0,len(files)-1,60,dtype=int):
        with Image.open(files[idx]) as im:
            pictures.append(im.convert("RGB"))
    delays=[]
    for i,im in enumerate(pictures[:10]+pictures):
        torch.cuda.synchronize()
        start=time.perf_counter()
        res=model.predict(im,device=0,conf=threshold,iou=0.7,imgsz=640,verbose=False)[0]
        res.boxes.data.cpu()
        torch.cuda.synchronize()
        if i>=10:
            delays.append(1000*(time.perf_counter()-start))
    return dict(median_ms=float(np.median(delays)),p95_ms=float(np.percentile(delays,95)),n=len(delays))


def main():
    parser=argparse.ArgumentParser()
    for name in ("dataset","runs","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    small=json.loads((args.dataset/"stats.json").read_text())["small_area_px2"]
    variants=["baseline","p2"]
    stats={v:{} for v in variants}
    weights={v:args.runs/v/"weights/best.pt" for v in variants}
    for split in ("val","test"):
        files,truth,coco=ground_truth(args.dataset,split)
        for v in variants:
            model=YOLO(weights[v])
            if split=="val":
                stats[v]["params"]=sum(p.numel() for p in model.model.parameters())
                stats[v]["bytes"]=weights[v].stat().st_size
            pred,dets=collect(model,files)
            s=metrics(coco,dets,small)
            if split=="val":
                # Choose the lowest threshold in an exact F1 tie.
                candidates=range(5,96,5)
                threshold=max(candidates,key=lambda n:match(truth,pred,n/100,small)[0]["f1"])/100
                stats[v]["threshold"]=threshold
                stats[v]["latency"]=latency(model,files,threshold)
            oper,cases=match(truth,pred,stats[v]["threshold"],small,True)
            stats[v][split]=dict(**s,**oper)
            if split=="test":
                (out/f"errors-{v}.json").write_text(json.dumps(cases),encoding="utf8")
                retained={k:[b for b in boxes if b[4]>=stats[v]["threshold"]] for k,boxes in pred.items()}
                (out/f"detections-{v}.json").write_text(json.dumps(retained),encoding="utf8")
            print(split,v,stats[v][split],flush=True)
        if split=="val":
            top=max(stats[v]["val"]["small_ap50"] for v in variants)
            eligible=[v for v in variants if stats[v]["val"]["small_ap50"]>=top-0.005]
            winner=min(eligible,key=lambda v:stats[v]["latency"]["p95_ms"])
            (out/"release.json").write_text(json.dumps(dict(variant=winner,threshold=stats[winner]["threshold"]),indent=2))
            shutil.copy2(weights[winner],out/"pcb.pt")
    (out/"metrics.json").write_text(json.dumps(stats,indent=2))


if __name__=="__main__":
    main()

