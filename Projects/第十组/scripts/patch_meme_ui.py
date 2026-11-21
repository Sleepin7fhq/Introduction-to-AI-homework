# -*- coding: utf-8 -*-
"""梗卡显示来源与置信度。"""
import io

P = r'D:\AI\aihw\src\components\MemeRave.tsx'
s = io.open(P, encoding='utf-8').read()

old = """              <div className="mc-tags">
                {c.tags.slice(0, 3).map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>"""

new = """              <div className="mc-tags">
                {c.tags.slice(0, 3).map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
                {c.confidence && (
                  <span className={'conf-tag ' + c.confidence}>
                    {c.confidence === 'high' ? '已核实' : c.confidence === 'medium' ? '部分核实' : '待核实'}
                  </span>
                )}
                {c.sources && c.sources.length > 0 && (
                  <span className="tag dim">
                    {String(c.sources[0]).replace(/^https?:\\/\\//, '').split('/')[0]}
                  </span>
                )}
              </div>"""

assert old in s, 'MemeRave block not found'
s = s.replace(old, new)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('MemeRave.tsx patched')

C = r'D:\AI\aihw\src\styles.css'
c = io.open(C, encoding='utf-8').read()
if '.conf-tag' not in c:
    c = c.replace(""".tag {
  font-size: 9px;""", """.conf-tag {
  font-size: 9px;
  border-radius: 4px;
  padding: 1px 5px;
  border: 1px solid #2c3a48;
  color: #9aa8bd;
}
.conf-tag.high {
  border-color: #1d4a3a;
  color: #5eead4;
}
.conf-tag.low {
  border-color: #4a3a1d;
  color: #f5b942;
}
.tag.dim {
  opacity: 0.65;
}
.tag {
  font-size: 9px;""")
    io.open(C, 'w', encoding='utf-8', newline='\n').write(c)
    print('styles.css patched')
else:
    print('styles.css already has conf-tag')
