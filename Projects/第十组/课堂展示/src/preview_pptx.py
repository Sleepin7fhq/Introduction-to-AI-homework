# -*- coding: utf-8 -*-
"""把 PPTX 的真实形状/文字/图片还原成 HTML，用于在无 PowerPoint 渲染环境时做视觉验收。

支持：矩形 / 圆角矩形 / 文本框 / 图片（含裁剪）/ 视频（渲染其海报帧）。
坐标严格按 EMU 换算，颜色、字号、对齐、行距都从 PPTX 读回。
"""
import base64
import os
import sys

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PX_PER_INCH = 96.0
SLIDE_W_PX = 1280
GAP = 28


def emu_to_px(v):
    return float(v) / 914400.0 * PX_PER_INCH


def color_of(fill):
    try:
        rgb = fill.fore_color.rgb
        return '#%02X%02X%02X' % (rgb[0], rgb[1], rgb[2])
    except Exception:
        return None


def alpha_of(shape):
    try:
        from pptx.oxml.ns import qn
        solid = shape.fill._xPr.find(qn('a:solidFill'))
        srgb = solid.find(qn('a:srgbClr'))
        a = srgb.find(qn('a:alpha'))
        if a is None:
            return 1.0
        return int(a.get('val')) / 100000.0
    except Exception:
        return 1.0


def line_of(shape):
    try:
        c = shape.line.color.rgb
        w = shape.line.width.pt if shape.line.width is not None else 1.0
        return '#%02X%02X%02X' % (c[0], c[1], c[2]), w
    except Exception:
        return None, 0


def escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text_html(shape):
    tf = shape.text_frame
    align_map = {PP_ALIGN.CENTER: 'center', PP_ALIGN.RIGHT: 'right', PP_ALIGN.LEFT: 'left'}
    paras = []
    for p in tf.paragraphs:
        if not p.runs:
            continue
        align = align_map.get(p.alignment, 'left')
        spacing = p.line_spacing if p.line_spacing else 1.0
        segs = []
        for r in p.runs:
            fs = r.font.size.pt if r.font.size else 18
            col = '#E6EDF7'
            try:
                c = r.font.color.rgb
                col = '#%02X%02X%02X' % (c[0], c[1], c[2])
            except Exception:
                pass
            weight = '700' if r.font.bold else '400'
            fam = r.font.name or 'Microsoft YaHei'
            segs.append(
                "<span style=\"font-family:'%s',sans-serif;font-size:%.2fpx;color:%s;font-weight:%s;\">%s</span>"
                % (fam, fs * PX_PER_INCH / 72.0, col, weight, escape(r.text))
            )
        paras.append('<div style="text-align:%s;line-height:%.3f;">%s</div>' % (align, spacing, ''.join(segs)))
    anchor = 'flex-start'
    try:
        if tf.vertical_anchor == MSO_ANCHOR.MIDDLE:
            anchor = 'center'
    except Exception:
        pass
    return '<div style="display:flex;flex-direction:column;justify-content:%s;">%s</div>' % (anchor, ''.join(paras))


def movie_poster(shape):
    """从 Movie 形状里取出海报帧图片的 base64。"""
    try:
        from pptx.oxml.ns import qn
        blip = shape._element.find('.//' + qn('a:blip'))
        rId = blip.get(qn('r:embed'))
        part = shape.part.related_part(rId)
        return base64.b64encode(part.blob).decode('ascii'), part.content_type
    except Exception:
        return None, None


def render_slide(slide, index):
    items = []
    for shape in slide.shapes:
        x, y = emu_to_px(shape.left), emu_to_px(shape.top)
        w, h = emu_to_px(shape.width), emu_to_px(shape.height)
        style = 'position:absolute;left:%.2fpx;top:%.2fpx;width:%.2fpx;height:%.2fpx;' % (x, y, w, h)
        name = type(shape).__name__

        if name == 'Movie':
            data, mime = movie_poster(shape)
            if data:
                items.append(
                    '<div style="%soverflow:hidden;">'
                    '<img src="data:%s;base64,%s" style="width:100%%;height:100%%;object-fit:cover;">'
                    '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">'
                    '<div style="width:64px;height:64px;border-radius:50%%;background:rgba(8,11,16,.72);'
                    'border:2px solid #5EEAD4;color:#5EEAD4;font-size:24px;display:flex;'
                    'align-items:center;justify-content:center;">▶</div></div></div>'
                    % (style, mime, data)
                )
            continue

        if name == 'Picture' or shape.shape_type == 13:
            blob = base64.b64encode(shape.image.blob).decode('ascii')
            mime = shape.image.content_type
            cl, cr = shape.crop_left or 0, shape.crop_right or 0
            ct, cb = shape.crop_top or 0, shape.crop_bottom or 0
            inner_w = w / max(1e-6, (1 - cl - cr))
            inner_h = h / max(1e-6, (1 - ct - cb))
            items.append(
                '<div style="%soverflow:hidden;">'
                '<img src="data:%s;base64,%s" style="position:absolute;left:%.2fpx;top:%.2fpx;width:%.2fpx;height:%.2fpx;">'
                '</div>' % (style, mime, blob, -cl * inner_w, -ct * inner_h, inner_w, inner_h)
            )
            continue

        try:
            fill = color_of(shape.fill)
            a = alpha_of(shape)
            lc, lw = line_of(shape)
        except Exception:
            continue
        radius = 0.0
        try:
            if shape.adjustments and len(shape.adjustments) > 0 and shape.adjustments[0]:
                radius = float(shape.adjustments[0]) * min(w, h)
        except Exception:
            pass

        bg = 'rgba(%d,%d,%d,%.3f)' % (
            int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16), a) if fill else 'transparent'
        border = '%.2fpx solid %s' % (max(0.5, lw * PX_PER_INCH / 72.0), lc) if lc else 'none'
        inner = text_html(shape) if shape.has_text_frame and shape.text_frame.text.strip() else ''
        items.append(
            '<div style="%sbackground:%s;border:%s;border-radius:%.1fpx;box-sizing:border-box;padding:0;">%s</div>'
            % (style, bg, border, radius, inner)
        )

    return ('<div class="slide" id="s%d" style="width:%dpx;height:%dpx;">%s</div>'
            % (index, SLIDE_W_PX, int(SLIDE_W_PX * 7.5 / 13.333), ''.join(items)))


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'DSH-Studio-2.0-课堂展示.pptx')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, '.render', 'preview.html')
    prs = Presentation(src)
    slides = [render_slide(s, i) for i, s in enumerate(prs.slides, start=1)]
    h = len(slides) * (int(SLIDE_W_PX * 7.5 / 13.333) + GAP) + GAP
    html = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#05070a;}
.slide{position:relative;margin:%dpx auto;overflow:hidden;background:#080B10;box-shadow:0 0 0 1px #1b2430;}
</style></head><body>%s</body></html>""" % (GAP, ''.join(slides))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)
    print('preview:', out, len(html) // 1024, 'KB', len(slides), 'slides, page height', h)


if __name__ == '__main__':
    main()
