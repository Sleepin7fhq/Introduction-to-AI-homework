# -*- coding: utf-8 -*-
from pptx import Presentation
from PIL import Image
import io, collections

p = Presentation(r'D:\AI\pptdemo\东南大学PPT.pptx')

# 收集最后几页所有图片，按 sha1 去重并保存到临时目录供分析
targets = {}
for idx in range(len(p.slides)-8, len(p.slides)):
    s = p.slides[idx]
    for sh in s.shapes:
        if sh.shape_type == 13:
            img = sh.image
            if img.sha1 not in targets:
                targets[img.sha1] = (img.blob, img.ext)

lines = []
for sha1, (blob, ext) in targets.items():
    im = Image.open(io.BytesIO(blob)).convert('RGBA')
    w, h = im.size
    # 角落像素（判断是否圆形印章/透明背景）
    corners = [im.getpixel((2,2)), im.getpixel((w-3,2)), im.getpixel((2,h-3)), im.getpixel((w-3,h-3))]
    # 颜色分布：统计非透明像素的主要颜色
    rgba = list(im.getdata())
    opaque = [p for p in rgba if p[3] > 128]
    opaque_frac = len(opaque)/len(rgba)
    # 主色调
    from collections import Counter
    def quant(p):
        r,g,b,a = p
        return (r//32*32, g//32*32, b//32*32)
    c = Counter(quant(p) for p in opaque)
    top = c.most_common(4)
    # 是否接近黑白（QR码特征）
    grayish = sum(1 for p in opaque if abs(p[0]-p[1])<16 and abs(p[1]-p[2])<16)
    gray_frac = grayish/len(opaque) if opaque else 0
    lines.append('sha1=%s %dx%d opaque=%.2f gray=%.2f corners=%s top=%s' % (
        sha1[:10], w, h, opaque_frac, gray_frac,
        [tuple(c[:3]) for c in corners], top))

open(r'D:\AI\pptdemo\analyze_images.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('done', len(targets))
