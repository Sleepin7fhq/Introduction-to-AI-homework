"""plot_kit.py —— 只用 Pillow 的轻量绘图工具（无 matplotlib 依赖）。

所有坐标都用"逻辑像素"书写，内部按 SCALE 倍超采样后再缩小，得到平滑的线条。
"""
import os
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
FONT_DIR = r"C:\Windows\Fonts"
FONT_REG = os.path.join(FONT_DIR, "msyh.ttc")
FONT_BOLD = os.path.join(FONT_DIR, "msyhbd.ttc")

INK = (34, 40, 49)
GRID = (226, 230, 235)
MUTED = (120, 130, 140)
BG = (255, 255, 255)

COLORS = {
    "TD": (192, 57, 43),
    "MC": (41, 98, 168),
    "sparse": (110, 118, 129),
    "proximity": (214, 93, 14),
    "potential": (31, 138, 92),
    "none": (120, 128, 138),
    "expert": (27, 110, 194),
    "good": (31, 138, 92),
    "fair": (214, 158, 14),
    "random": (150, 110, 180),
    "reverse": (192, 57, 43),
}


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, int(size * SCALE))


def canvas(w, h):
    img = Image.new("RGB", (int(w * SCALE), int(h * SCALE)), BG)
    return img, ImageDraw.Draw(img)


def finish(img, path):
    w, h = img.size
    img = img.resize((w // SCALE, h // SCALE), Image.LANCZOS)
    img.save(path)
    return path


def _s(v):
    return int(round(v * SCALE))


def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    start = (lo // step) * step
    ticks = []
    v = start
    while v <= hi + 1e-9:
        if v >= lo - 1e-9:
            ticks.append(v)
        v += step
    return ticks, step


def axes(d, box, xlim, ylim, xlabel="", ylabel="", title="",
         xticks=None, yticks=None, xfmt=None, yfmt=None, grid=True,
         title_size=15, label_size=12, tick_size=11, xlog=False):
    x0, y0, x1, y1 = box
    # 背景与边框
    d.rectangle([_s(x0), _s(y0), _s(x1), _s(y1)], outline=(200, 205, 212), width=_s(1))
    if xticks is None:
        xticks, _ = nice_ticks(xlim[0], xlim[1], 5)
    if yticks is None:
        yticks, _ = nice_ticks(ylim[0], ylim[1], 5)

    def X(v):
        return x0 + (v - xlim[0]) / (xlim[1] - xlim[0]) * (x1 - x0)

    def Y(v):
        return y1 - (v - ylim[0]) / (ylim[1] - ylim[0]) * (y1 - y0)

    f_tick = font(tick_size)
    for t in yticks:
        yy = Y(t)
        if yy < y0 - 1 or yy > y1 + 1:
            continue
        if grid:
            d.line([_s(x0), _s(yy), _s(x1), _s(yy)], fill=GRID, width=_s(1))
        lab = yfmt(t) if yfmt else f"{t:g}"
        w = d.textlength(lab, font=f_tick) / SCALE
        d.text((_s(x0 - 8 - w), _s(yy - tick_size * 0.75)), lab, font=f_tick, fill=MUTED)
    for t in xticks:
        xx = X(t)
        if xx < x0 - 1 or xx > x1 + 1:
            continue
        if grid:
            d.line([_s(xx), _s(y0), _s(xx), _s(y1)], fill=GRID, width=_s(1))
        lab = xfmt(t) if xfmt else f"{t:g}"
        w = d.textlength(lab, font=f_tick) / SCALE
        d.text((_s(xx - w / 2), _s(y1 + 8)), lab, font=f_tick, fill=MUTED)

    if xlabel:
        f = font(label_size)
        w = d.textlength(xlabel, font=f) / SCALE
        d.text((_s((x0 + x1) / 2 - w / 2), _s(y1 + 32)), xlabel, font=f, fill=INK)
    if ylabel:
        f = font(label_size)
        # 竖排：逐字画
        tmp = Image.new("RGBA", (int(200 * SCALE), 40 * SCALE), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((0, 0), ylabel, font=f, fill=INK)
        bbox = td.textbbox((0, 0), ylabel, font=f)
        tmp = tmp.crop(bbox).rotate(90, expand=True)
        d._image.paste(tmp, (_s(x0 - 58), _s((y0 + y1) / 2 - tmp.size[1] / SCALE / 2)), tmp)
    if title:
        f = font(title_size, bold=True)
        w = d.textlength(title, font=f) / SCALE
        d.text((_s((x0 + x1) / 2 - w / 2), _s(y0 - 34)), title, font=f, fill=INK)
    return X, Y


def line(d, X, Y, xs, ys, color, width=2.6, dash=None, alpha=255):
    pts = [(_s(X(x)), _s(Y(y))) for x, y in zip(xs, ys)]
    if len(pts) < 2:
        return
    if dash:
        # 手动画虚线
        on, off = dash
        i = 0
        acc = 0.0
        drawing = True
        while i < len(pts) - 1:
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            seg = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if seg == 0:
                i += 1
                continue
            t0 = 0.0
            while t0 < seg:
                t1 = min(seg, t0 + (on if drawing else off))
                if drawing:
                    p0 = (ax + (bx - ax) * t0 / seg, ay + (by - ay) * t0 / seg)
                    p1 = (ax + (bx - ax) * t1 / seg, ay + (by - ay) * t1 / seg)
                    d.line([p0, p1], fill=color, width=_s(width))
                t0 = t1
                drawing = not drawing
            i += 1
    else:
        d.line(pts, fill=color, width=_s(width), joint="curve")


def band(d, X, Y, xs, lo, hi, color, alpha=30):
    pts = [(_s(X(x)), _s(Y(h))) for x, h in zip(xs, hi)]
    pts += [(_s(X(x)), _s(Y(l))) for x, l in zip(xs[::-1], lo[::-1])]
    overlay = Image.new("RGBA", d._image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon(pts, fill=color + (alpha,))
    d._image.paste(Image.alpha_composite(d._image.convert("RGBA"), overlay).convert("RGB"))


def legend(d, items, x, y, size=12, gap=26, marker_len=26):
    f = font(size)
    yy = y
    for label, color, style in items:
        if style == "line":
            d.line([_s(x), _s(yy + 7), _s(x + marker_len), _s(yy + 7)], fill=color, width=_s(2.6))
        elif style == "dash":
            d.line([_s(x), _s(yy + 7), _s(x + 9), _s(yy + 7)], fill=color, width=_s(2.6))
            d.line([_s(x + 17), _s(yy + 7), _s(x + marker_len), _s(yy + 7)], fill=color, width=_s(2.6))
        elif style == "square":
            d.rectangle([_s(x + 4), _s(yy + 1), _s(x + 18), _s(yy + 15)], fill=color)
        d.text((_s(x + marker_len + 8), _s(yy)), label, font=f, fill=INK)
        yy += gap


def legend_row(d, items, x, y, size=12, marker_len=24, pad=16):
    """一行式图例：自动按文字宽度排布。"""
    f = font(size)
    xx = x
    for label, color, style in items:
        if style == "line":
            d.line([_s(xx), _s(y + 7), _s(xx + marker_len), _s(y + 7)], fill=color, width=_s(2.6))
        elif style == "square":
            d.rectangle([_s(xx + 3), _s(y + 1), _s(xx + 16), _s(y + 14)], fill=color)
        xx += marker_len + 6
        d.text((_s(xx), _s(y)), label, font=f, fill=INK)
        xx += d.textlength(label, font=f) / SCALE + pad


def bars(d, box, values, labels, colors, ylim=None, title="", ylabel="", fmt="{:.2f}",
         value_size=11):
    x0, y0, x1, y1 = box
    n = len(values)
    hi = max(values) * 1.18 if ylim is None else ylim[1]
    lo = 0 if ylim is None else ylim[0]
    X, Y = axes(d, box, (0, n), (lo, hi), title=title, ylabel=ylabel,
                xticks=[], xfmt=lambda v: "")
    f = font(value_size)
    slot = (x1 - x0) / n
    bw = slot * 0.52
    for i, (v, lab, c) in enumerate(zip(values, labels, colors)):
        cx = x0 + slot * (i + 0.5)
        top = Y(v)
        d.rectangle([_s(cx - bw / 2), _s(top), _s(cx + bw / 2), _s(Y(0))], fill=c)
        d.text((_s(cx - d.textlength(fmt.format(v), font=f) / SCALE / 2), _s(top - 22)),
               fmt.format(v), font=f, fill=INK)
        fl = font(11)
        d.text((_s(cx - d.textlength(lab, font=fl) / SCALE / 2), _s(y1 + 8)), lab,
               font=fl, fill=INK)
