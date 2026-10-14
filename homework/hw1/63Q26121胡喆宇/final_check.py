# -*- coding: utf-8 -*-
from pptx import Presentation
from pptx.util import Emu

p = Presentation(r'D:\AI\pptdemo\高考压轴题完整评分解答.pptx')
lines = []
lines.append('opens OK')
lines.append('slides: %d' % len(p.slides))
lines.append('size: %.3f x %.3f in' % (p.slide_width/914400, p.slide_height/914400))
lines.append('masters: %d' % len(p.slide_masters))
lines.append('layouts: %d' % len(p.slide_layouts))
lines.append('--- layouts preserved ---')
for i, l in enumerate(p.slide_layouts):
    lines.append('%d %s' % (i, l.name))
# theme colors check (first master -> theme)
import zipfile
z = zipfile.ZipFile(r'D:\AI\pptdemo\高考压轴题完整评分解答.pptx')
xml = z.read('ppt/theme/theme1.xml').decode('utf-8')
import re
acc1 = re.search(r'<a:accent1><a:srgbClr val="([0-9A-Fa-f]{6})"', xml)
acc2 = re.search(r'<a:accent2><a:srgbClr val="([0-9A-Fa-f]{6})"', xml)
ea = re.search(r'<a:ea typeface="([^"]*)"', xml)
lines.append('theme1 accent1=%s accent2=%s ea=%s (SEU 品牌色/字体)' % (acc1.group(1), acc2.group(1), ea.group(1)))
open(r'D:\AI\pptdemo\final_check.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('done')
