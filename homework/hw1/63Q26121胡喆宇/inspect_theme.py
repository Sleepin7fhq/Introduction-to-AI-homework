# -*- coding: utf-8 -*-
import zipfile, re
z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')
for t in ['ppt/theme/theme1.xml', 'ppt/theme/theme2.xml', 'ppt/theme/theme3.xml']:
    xml = z.read(t).decode('utf-8')
    fn = 'D:/AI/pptdemo/' + t.split('/')[-1]
    open(fn, 'w', encoding='utf-8').write(xml)
    print('==== %s (%d bytes) ====' % (t, len(xml)))
    m = re.search(r'<a:fontScheme.*?</a:fontScheme>', xml, re.S)
    if m:
        fs = m.group(0)
        def lat(name):
            if not name:
                return 'NONE'
            mm = re.search(r'typeface="([^"]*)"', name.group(0))
            return mm.group(1) if mm else '?'
        major = re.search(r'<a:majorFont>.*?</a:majorFont>', fs, re.S)
        minor = re.search(r'<a:minorFont>.*?</a:minorFont>', fs, re.S)
        print('major latin:', lat(major), '| minor latin:', lat(minor))
        ea = re.findall(r'<a:ea typeface="([^"]*)"', fs)
        print('ea typefaces:', ea)
    mc = re.search(r'<a:clrScheme.*?</a:clrScheme>', xml, re.S)
    if mc:
        # find each color entry
        for tag in ['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink']:
            seg = re.search(r'<a:%s>(.*?)</a:%s>' % (tag, tag), mc.group(0), re.S)
            if seg:
                val = re.search(r'val="([0-9A-Fa-f]{6})"', seg.group(1))
                last = re.search(r'lastClr="([0-9A-Fa-f]{6})"', seg.group(1))
                sysc = re.search(r'<a:sysClr[^>]*val="([^"]*)"', seg.group(1))
                print('  %-8s val=%s lastClr=%s sysClr=%s' % (tag, val.group(1) if val else None, last.group(1) if last else None, sysc.group(1) if sysc else None))
