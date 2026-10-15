# -*- coding: utf-8 -*-
"""
Template analysis for 实践题v1.pptx.

Purpose: before building anything, work out (a) which theme fonts and colours the
东南大学PPT.pptx template defines, and (b) the exact geometry of every picture
placeholder on the layouts. Both matter:

  * the theme colours drive the figure palette (SEU pine green #445437 / blue #2872A1);
  * a PICTURE placeholder is never blank in a saved layout, and an unfilled one
    exports the editor prompt "Double-click to add an Image" into PDF/print
    output - so the geometry tells us where images must be supplied and how large
    they need to be generated.

Run:  python inspect_template.py
"""
import re
import zipfile

from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import PP_PLACEHOLDER

TEMPLATE = r"D:\All_resource\大学\大一\人工智能导论\课件\东南大学PPT.pptx"


def theme_fonts_and_colours(path):
    z = zipfile.ZipFile(path)
    themes = sorted(n for n in z.namelist() if re.match(r"ppt/theme/theme\d+\.xml", n))
    xml = z.read(themes[0]).decode("utf-8")

    print("=" * 74)
    print("THEME")
    print("=" * 74)
    for tag in ("majorFont", "minorFont"):
        m = re.search(rf"<a:{tag}>.*?<a:latin typeface=\"([^\"]*)\"", xml, re.S)
        if m:
            print(f"  {tag:10s}: latin = {m.group(1)!r}")
    scheme = re.search(r"<a:clrScheme.*?</a:clrScheme>", xml, re.S)
    if scheme:
        for name, val in re.findall(
            r"<a:(\w+)>\s*<a:(?:srgbClr val|sysClr[^>]*lastClr)=\"([0-9A-Fa-f]{6})\"",
            scheme.group(0),
        ):
            print(f"  colour {name:12s} = #{val}")


def layout_geometry(path):
    prs = Presentation(path)
    print()
    print("=" * 74)
    print(f"SLIDE SIZE: {Emu(prs.slide_width).inches:.3f} x "
          f"{Emu(prs.slide_height).inches:.3f} in   |  "
          f"{len(prs.slide_layouts)} layouts, {len(prs.slides)} demo slides")
    print("=" * 74)
    for lay in prs.slide_layouts:
        pics = [ph for ph in lay.placeholders
                if ph.placeholder_format.type == PP_PLACEHOLDER.PICTURE]
        if not pics:
            continue
        print(f"\n[{lay.name}]  {len(pics)} picture placeholder(s)")
        for ph in pics:
            w, h = Emu(ph.width).inches, Emu(ph.height).inches
            print(f"   idx={ph.placeholder_format.idx:<3} "
                  f"pos=({Emu(ph.left).inches:5.2f},{Emu(ph.top).inches:5.2f})in  "
                  f"size={w:5.2f}x{h:5.2f}in  aspect={w / h:.3f}")


if __name__ == "__main__":
    theme_fonts_and_colours(TEMPLATE)
    layout_geometry(TEMPLATE)
    print("\nNote: the picture-bearing layouts (图文-1..5) place their picture slots "
          "directly\n      under, or on top of, their own body text boxes, so text and "
          "image cannot\n      coexist there - build_ppt.py accounts for this.")
