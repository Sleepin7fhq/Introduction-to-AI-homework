# -*- coding: utf-8 -*-
import zipfile, io
from PIL import Image

z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')
for name in ['ppt/media/image20.png', 'ppt/media/image27.png', 'ppt/media/image34.png', 'ppt/media/image2.png']:
    im = Image.open(io.BytesIO(z.read(name)))
    print(name, 'mode=', im.mode, 'size=', im.size)
    im = im.convert('RGBA')
    px = im.load()
    w,h = im.size
    # sample corners and center
    pts = {'topleft': px[2,2], 'topright': px[w-3,2], 'botleft': px[2,h-3], 'botright': px[w-3,h-3], 'center': px[w//2,h//2]}
    print('   ', pts)
    # fraction of transparent pixels
    alpha = list(im.getdata())
    transp = sum(1 for p in alpha if p[3] < 16)
    semi = sum(1 for p in alpha if 16 <= p[3] < 240)
    opaque = sum(1 for p in alpha if p[3] >= 240)
    total = len(alpha)
    print('    transparent=%.2f semi=%.2f opaque=%.2f' % (transp/total, semi/total, opaque/total))
