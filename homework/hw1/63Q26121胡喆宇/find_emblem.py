# -*- coding: utf-8 -*-
import zipfile, io
from PIL import Image
from collections import Counter

z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')
lines = []
for name in sorted(z.namelist()):
    if not name.startswith('ppt/media/'):
        continue
    if not name.lower().endswith(('.png', '.jpeg', '.jpg', '.gif')):
        continue
    try:
        blob = z.read(name)
        im = Image.open(io.BytesIO(blob)).convert('RGBA')
        w, h = im.size
        if w*h > 4000*4000:
            continue
        rgba = list(im.getdata())
        # 采样加速
        step = max(1, len(rgba)//20000)
        sample = rgba[::step]
        opaque = [p for p in sample if p[3] > 128]
        if not opaque:
            continue
        # 统计绿/金系像素
        def is_green(p):
            r,g,b = p[0],p[1],p[2]
            return g > r and g > b and g > 60 and g < 160
        def is_gold(p):
            r,g,b = p[0],p[1],p[2]
            return r > 180 and g > 140 and b < 120 and g > b
        green = sum(1 for p in opaque if is_green(p))
        gold = sum(1 for p in opaque if is_gold(p))
        green_f = green/len(opaque)
        gold_f = gold/len(opaque)
        # 角落（判断圆形印章）
        corner = [im.getpixel((2,2)), im.getpixel((w-3,2)), im.getpixel((2,h-3)), im.getpixel((w-3,h-3))]
        corner_white = sum(1 for c in corner if c[3]<128 or (c[0]>230 and c[1]>230 and c[2]>230))
        if green_f > 0.05 or gold_f > 0.08:
            lines.append('%-28s %5dx%-5d green=%.2f gold=%.2f cwhite=%d/4' % (name, w, h, green_f, gold_f, corner_white))
    except Exception as e:
        lines.append('%-28s ERR %s' % (name, e))

open(r'D:\AI\pptdemo\find_emblem.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('done', len(lines))
