# -*- coding: utf-8 -*-
import zipfile, re
from pptx import Presentation

z = zipfile.ZipFile(r'D:\AI\pptdemo\东南大学PPT.pptx')

# 建立 rId -> media 映射需要看每个 part 的 rels；这里直接反向：找哪些 xml 引用了指定媒体
targets = ['image20.png', 'image27.png', 'image34.png', 'image2.png', 'image17.png', 'image29.png', 'image30.png', 'image41.png']
# 遍历所有 rels 文件，建立 (source_part -> rId -> target)
rels_files = [n for n in z.namelist() if n.endswith('.rels')]
# media rId -> filename
lines = []
for rf in rels_files:
    src = rf[:-5]  # remove '.rels'
    xml = z.read(rf).decode('utf-8')
    for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', xml):
        rid, tgt = m.group(1), m.group(2)
        base = tgt.split('/')[-1]
        if base in targets:
            lines.append('%-22s  rId=%s  -> %s' % (src, rid, base))

# 也找 slideN.xml 里哪个 rId 用了哪个 media（反向）
open(r'D:\AI\pptdemo\find_usage.txt', 'w', encoding='utf-8').write('\n'.join(sorted(set(lines))))
print('done', len(lines))
