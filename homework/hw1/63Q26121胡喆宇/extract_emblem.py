# -*- coding: utf-8 -*-
import zipfile
z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')
# 提取东南大学校徽（image20.png：3301x3301 圆形金绿印章，透明背景）
data = z.read('ppt/media/image20.png')
open(r'D:\AI\pptdemo\seu_emblem.png', 'wb').write(data)
print('extracted', len(data), 'bytes')
