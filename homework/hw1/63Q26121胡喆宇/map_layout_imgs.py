# -*- coding: utf-8 -*-
from pptx import Presentation
from PIL import Image
import io

p = Presentation(r'D:\AI\pptdemo\东南大学PPT.pptx')
lines = []
for li in [0, 8, 15]:
    l = p.slide_layouts[li]
    lines.append('==== LAYOUT %d (%s) pictures ====' % (li, l.name))
    for sh in l.shapes:
        if sh.shape_type == 13:
            try:
                img = sh.image
                im = Image.open(io.BytesIO(img.blob))
                lines.append('  sha1=%s  %dx%d  pos=(%.2f,%.2f) size=(%.2f,%.2f)' % (
                    img.sha1[:10], im.size[0], im.size[1],
                    sh.left/914400, sh.top/914400, sh.width/914400, sh.height/914400))
            except Exception as e:
                lines.append('  err %s' % e)
    # also non-picture shapes that might be logo (autoshape with fill)
open(r'D:\AI\pptdemo\map_layout_imgs.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('done')
