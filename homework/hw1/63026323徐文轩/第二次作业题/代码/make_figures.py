# -*- coding: utf-8 -*-
"""
Generate the figures used by 实践题v1.pptx.

Reserve-area panels are generated at the EXACT aspect ratio of the template
placeholder they fill, so they are never stretched or clipped. The panel is
deliberately plain - hairline grey rule, flat pale fill, no rounding, no gradient.

The convergence figure is the real a_n^2/n curve, drawn with the template theme
colours (accent1 pine green #445437 / accent3 blue #2872A1).
"""
import math
import os
from decimal import Decimal, getcontext

from PIL import Image, ImageDraw, ImageFont

getcontext().prec = 45
DPI = 200.0
PNG_DPI = 96            # PowerPoint's native raster DPI; keeps placed size == intended size
MSYH = r"C:\Windows\Fonts\msyh.ttc"
MSYH_BD = r"C:\Windows\Fonts\msyhbd.ttc"

PINE = (0x44, 0x54, 0x37)
BLUE = (0x28, 0x72, 0xA1)
GREY = (0x8A, 0x8A, 0x8A)
LINE = (0xC8, 0xC8, 0xC4)
FILL = (0xF8, 0xF8, 0xF6)
DARK = (0x40, 0x40, 0x40)

BASE = r"D:\All_resource\大学\大一\人工智能导论\作业\第二次作业题\figures"
os.makedirs(BASE, exist_ok=True)


def font(pt, bold=False):
    return ImageFont.truetype(MSYH_BD if bold else MSYH, max(9, int(round(pt * DPI / 72.0))))


def center_text(d, x0, y0, x1, y1, text, f, fill):
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((x0 + (x1 - x0 - (r - l)) / 2 - l, y0 + (y1 - y0 - (b - t)) / 2 - t),
           text, font=f, fill=fill)


def reserve_panel(path, aspect, label="预留图片区域", sub="（此处预留图片）"):
    """Flat panel at the given width/height aspect ratio."""
    W = 1400
    H = max(240, int(round(W / aspect)))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, W - 4, H - 4], fill=FILL, outline=LINE, width=3)
    center_text(d, 0, 0, W, int(H * 0.56), label, font(26, True), PINE)
    center_text(d, 0, int(H * 0.56), W, int(H * 0.90), sub, font(18), GREY)
    img.save(path, dpi=(PNG_DPI, PNG_DPI))
    return path


# ------------------------------------------------------------------ convergence curve
def sequence_ratios(max_n=200000):
    ns, rs = [], []
    a = Decimal(1)
    keep = {1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000,
            10000, 20000, 50000, 100000, 200000}
    for n in range(1, max_n + 1):
        if n in keep:
            ns.append(n)
            rs.append(float((a * a) / Decimal(n)))
        a = a + 1 / a
    return ns, rs


def convergence(path, aspect):
    ns, rs = sequence_ratios()
    W = 1600
    H = int(round(W / aspect))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    L, R, T, B = int(W * 0.155), W - int(W * 0.035), int(H * 0.115), H - int(H * 0.155)
    ymin, ymax = 1.99, 2.10
    logmax = math.log10(200000)

    def X(n):
        return L + (math.log10(n) / logmax) * (R - L)

    def Y(v):
        return B - (v - ymin) / (ymax - ymin) * (B - T)

    for v in (2.00, 2.02, 2.04, 2.06, 2.08, 2.10):
        y = Y(v)
        d.line([L, y, R, y], fill=(0xE6, 0xE6, 0xE6), width=2)
        d.text((L - int(W * 0.085), y - 10), f"{v:.2f}", font=font(15), fill=GREY)
    for n in (1, 10, 100, 1000, 10000, 100000):
        d.text((X(n) - 14, B + 8), f"{n}", font=font(15), fill=GREY)

    for x in range(L, R, 22):
        d.line([x, Y(2.0), x + 11, Y(2.0)], fill=PINE, width=3)
    d.text((L + 16, Y(2.0) + 10), "limit = 2", font=font(16, True), fill=PINE)

    pts = [(X(n), Y(min(max(r, ymin), ymax))) for n, r in zip(ns, rs)]
    d.line(pts, fill=BLUE, width=4, joint="curve")
    for x, y in pts:
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=BLUE)

    d.text((int(W * 0.012), T - int(H * 0.02)), "a_n^2 / n", font=font(17), fill=DARK)
    d.text(((L + R) / 2 - 70, B + int(H * 0.085)), "n  (log scale)",
           font=font(16), fill=DARK)
    d.text((X(1.7) + 8, Y(2.0884) + 8), "n=10: 2.0884", font=font(14), fill=BLUE)
    xk, yk = X(100000), Y(2.000055)
    d.text((X(2000), yk - 60), "n=1e5: 2.000055", font=font(14), fill=BLUE)
    d.line([X(20000), yk - 44, xk - 10, yk - 8], fill=BLUE, width=2)

    d.line([L, B, R, B], fill=(0x9A, 0x9A, 0x9A), width=3)
    d.line([L, T, L, B], fill=(0x9A, 0x9A, 0x9A), width=3)
    img.save(path, dpi=(PNG_DPI, PNG_DPI))
    return path


# ------------------------------------------------------------------ emit
panels = {
    "fig_reserve_1x1.png": 0.987,     # 图文-1 three small squares
    "fig_reserve_1.19.png": 1.190,    # 图文-2 corner slots
    "fig_reserve_1.2.png": 1.199,     # 图文-3 large left slot
    "fig_reserve_1.31.png": 1.314,    # 图文-4 / 图文-5 slots
}
for name, asp in panels.items():
    reserve_panel(os.path.join(BASE, name), asp)

convergence(os.path.join(BASE, "fig_convergence.png"), 0.987)   # fits 图文-1 square slot

print("figures in", BASE)
for f in sorted(os.listdir(BASE)):
    p = os.path.join(BASE, f)
    with Image.open(p) as im:
        print(f"  {f:<26} {im.width}x{im.height}  aspect={im.width/im.height:.3f}")
