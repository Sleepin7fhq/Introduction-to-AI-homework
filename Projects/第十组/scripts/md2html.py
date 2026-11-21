"""把交付报告 Markdown 转成可打印的独立 HTML（图片内联为 base64）。

只为这份报告服务：支持标题、段落、粗体、行内代码、链接、图片、表格、
有序/无序列表、引用块、代码块、分割线。不追求完整 Markdown 兼容。
"""
import base64
import html
import os
import re
import sys


def inline(text):
    text = html.escape(text, quote=False)
    # 图片先于链接处理（两者语法相似）
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: '<img src="%s" alt="%s">' % (m.group(2), m.group(1)),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)),
        text,
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", text)
    return text


def convert(md, image_root):
    lines = md.split("\n")
    out = []
    toc = []
    i = 0
    para = []

    def flush_para():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            del para[:]

    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("```"):
            flush_para()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code), quote=False))
            i += 1
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush_para()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = "h%d-%d" % (level, len(toc))
            if level == 2:
                toc.append((anchor, title))
            out.append('<h%d id="%s">%s</h%d>' % (level, anchor, inline(title), level))
            i += 1
            continue

        if line.strip() == "---":
            flush_para()
            out.append('<hr class="rule">')
            i += 1
            continue

        if line.startswith(">"):
            flush_para()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i][1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(quote)))
            continue

        # 表格：连续以 | 开头的行
        if line.startswith("|"):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            header = cells[0]
            body = [r for r in cells[1:] if not all(re.match(r"^:?-{2,}:?$", c) for c in r)]
            tbl = ['<div class="table-wrap"><table><thead><tr>']
            tbl += ["<th>%s</th>" % inline(c) for c in header]
            tbl.append("</tr></thead><tbody>")
            for r in body:
                tbl.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            tbl.append("</tbody></table></div>")
            out.append("".join(tbl))
            continue

        mo = re.match(r"^(\d+)\.\s+(.*)$", line)
        if mo:
            flush_para()
            items = []
            while i < len(lines):
                mm = re.match(r"^(\d+)\.\s+(.*)$", lines[i].rstrip())
                if not mm:
                    break
                items.append(mm.group(2))
                i += 1
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % inline(x) for x in items))
            continue

        if re.match(r"^[-*]\s+", line):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].rstrip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].rstrip()))
                i += 1
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in items))
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    body = "\n".join(out)

    # 图片转 base64，产出单文件 HTML
    def embed(m):
        src = m.group(1)
        path = os.path.join(image_root, src)
        if not os.path.exists(path):
            print("WARN missing image:", path)
            return m.group(0)
        data = base64.b64encode(open(path, "rb").read()).decode("ascii")
        return '<img src="data:image/png;base64,%s" alt="%s">' % (data, m.group(2))

    body = re.sub(r'<img src="([^"]+)" alt="([^"]*)">', embed, body)
    return body, toc


CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body {
  margin: 0; color: #1b2430;
  font-family: "Microsoft YaHei", "PingFang SC", -apple-system, "Segoe UI", sans-serif;
  font-size: 10.5pt; line-height: 1.75;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.cover {
  min-height: 245mm; display: flex; flex-direction: column; justify-content: center;
  page-break-after: always; padding: 0 6mm;
}
.cover .kicker { font-size: 9pt; letter-spacing: .32em; color: #0e7490; margin-bottom: 10mm; }
.cover h1 { font-size: 30pt; line-height: 1.25; margin: 0 0 6mm; color: #0b1a26; letter-spacing: -.01em; }
.cover .sub { font-size: 13pt; color: #35505f; margin-bottom: 14mm; }
.cover .meta { border-top: 2px solid #0e7490; padding-top: 6mm; font-size: 9.5pt; color: #46606f; }
.cover .meta div { margin: 1.5mm 0; }
.cover .meta b { color: #12252f; display: inline-block; width: 22mm; }
.toc { page-break-after: always; }
.toc h2 { font-size: 15pt; border: none; margin-top: 0; padding: 0; color: #0b1a26; }
.toc ol { padding-left: 6mm; }
.toc li { margin: 2mm 0; font-size: 10.5pt; }
.toc a { color: #1b2430; text-decoration: none; }
h1 { font-size: 19pt; margin: 0 0 5mm; color: #0b1a26; }
h2 {
  font-size: 15pt; margin: 0 0 4mm; padding-bottom: 2mm;
  border-bottom: 1.5px solid #0e7490; color: #0b1a26;
  break-before: page; page-break-before: always;
}
h1 + h2, .cover + h2 { break-before: auto; page-break-before: auto; }
h3 { font-size: 12pt; margin: 6mm 0 2.5mm; color: #12384a; break-after: avoid; }
h4 { font-size: 11pt; margin: 4mm 0 2mm; color: #12384a; }
p { margin: 0 0 3mm; text-align: justify; }
a { color: #0e7490; }
code {
  font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt;
  background: #f1f5f9; border: 1px solid #e2e8ee; border-radius: 3px;
  padding: .5mm 1.2mm; color: #0f4c5c;
}
pre {
  background: #0f1720; color: #dbe7f3; border-radius: 4px;
  padding: 3.5mm 4mm; overflow: auto; break-inside: avoid; margin: 0 0 4mm;
}
pre code { background: none; border: none; color: inherit; padding: 0; font-size: 8.8pt; }
blockquote {
  margin: 0 0 4mm; padding: 3mm 4mm; background: #f0f9fb;
  border-left: 3px solid #0e7490; color: #12384a; font-size: 10.5pt;
  break-inside: avoid;
}
blockquote p { margin: 0; }
.table-wrap { margin: 0 0 4.5mm; break-inside: avoid; }
table { width: 100%; border-collapse: collapse; font-size: 8.6pt; table-layout: auto; }
th, td { border: 1px solid #d7e0e8; padding: 1.4mm 1.8mm; text-align: left; vertical-align: top; word-break: break-word; }
th { background: #eef6f9; color: #0b2b38; font-weight: 600; }
tr:nth-child(even) td { background: #fafcfd; }
ul, ol { margin: 0 0 3.5mm; padding-left: 6mm; }
li { margin: 1.2mm 0; }
hr.rule { border: none; border-top: 1px solid #dfe7ee; margin: 5mm 0; }
img { width: 100%; border: 1px solid #dbe3ea; border-radius: 3px; display: block; margin: 2mm 0; }
em { color: #4b6472; font-style: normal; font-size: 9.5pt; }
/* 屏幕阅读时给 A4 纸张感；打印不受影响（@page 负责页边距） */
@media screen {
  html { background: #e9eef4; }
  body {
    background: #fff; max-width: 210mm; margin: 0 auto;
    padding: 16mm 15mm 24mm; box-shadow: 0 0 24px rgba(15, 40, 60, .12);
  }
  .cover { min-height: auto; padding: 34mm 0 24mm; }
  .toc { page-break-after: auto; }
  h2 { break-before: auto; page-break-before: auto; margin-top: 10mm; }
}
"""


def main():
    md_path, out_path, image_root = sys.argv[1], sys.argv[2], sys.argv[3]
    kicker = sys.argv[4] if len(sys.argv) > 4 else 'DEEPSEEK HARNESS · PROJECT DELIVERY'
    subtitle_text = sys.argv[5] if len(sys.argv) > 5 else 'AI 音乐工作站 · 真实音频生成与可编辑工程'
    md = open(md_path, encoding="utf-8").read()
    # 首个 H1 与紧随的元信息行进封面，正文从第一个 ## 开始
    body_md = md
    lines = md.split("\n")
    title = "交付报告"
    meta_lines = []
    cut = 0
    for idx, ln in enumerate(lines):
        if ln.startswith("# "):
            title = ln[2:].strip()
            continue
        if ln.startswith("**") and "：" in ln:
            meta_lines.append(ln)
            cut = idx + 1
            continue
        if ln.startswith("## "):
            body_md = "\n".join(lines[idx:])
            break

    body, toc = convert(body_md, image_root)
    toc_html = "".join('<li><a href="#%s">%s</a></li>' % (a, inline(t)) for a, t in toc)
    meta_html = "".join("<div>%s</div>" % inline(m.replace("**", "")) for m in meta_lines)

    doc = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%(title)s</title><style>%(css)s</style></head><body>
<section class="cover">
  <div class="kicker">%(kicker)s</div>
  <h1>%(title)s</h1>
  <div class="sub">%(subtitle)s</div>
  <div class="meta">%(meta)s</div>
</section>
<section class="toc"><h2>目录</h2><ol>%(toc)s</ol></section>
%(body)s
</body></html>""" % {
        "title": inline(title),
        "css": CSS,
        "meta": meta_html,
        "toc": toc_html,
        "kicker": inline(kicker),
        "subtitle": inline(subtitle_text),
        "body": body,
    }
    open(out_path, "w", encoding="utf-8").write(doc)
    print("HTML ok: %s (%d bytes, %d 图)" % (out_path, len(doc), doc.count("data:image/png")))


if __name__ == "__main__":
    main()
