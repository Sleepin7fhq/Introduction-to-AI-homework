# -*- coding: utf-8 -*-
import zipfile, re
z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')
xml = z.read('ppt/slideMasters/slideMaster1.xml').decode('utf-8')
m = re.search(r'<p:txStyles>.*?</p:txStyles>', xml, re.S)
if m:
    txt = m.group(0)
    # pretty: find all runs with sz and colors
    print('=== txStyles (titleStyle/bodyStyle/otherStyle) ===')
    for sec in re.findall(r'<p:(titleStyle|bodyStyle|otherStyle)>.*?</p:\1>', txt, re.S):
        pass
    # simpler: print each <a:p> with lvl and sz/color
    for pm in re.finditer(r'<a:lvl(\d)pPr[^>]*>', txt):
        pass
    # just dump sz and color pairs with context
    for seg in re.findall(r'<p:titleStyle>(.*?)</p:titleStyle>', txt, re.S):
        szs = re.findall(r'sz="(\d+)"', seg)
        cols = re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"|schemeClr val="(\w+)"', seg)
        print('titleStyle: sizes=%s colors=%s' % (szs, cols))
    for seg in re.findall(r'<p:bodyStyle>(.*?)</p:bodyStyle>', txt, re.S):
        szs = re.findall(r'sz="(\d+)"', seg)
        cols = re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"|schemeClr val="(\w+)"', seg)
        print('bodyStyle: sizes=%s colors=%s' % (szs, cols))
    print(txt[:2000])
