"""图形绘制工具库（Pillow）
数学文本约定：
  ^{...}   上标（数学斜体）
  _{...}   下标
  \\dfrac{n}{d}  分式
  $...$    直立体（函数名 ln/cos、常数 e、记号 d 等）
中文字符自动使用微软雅黑，数学字母使用 Cambria（斜体），数字/运算符使用正体。
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)

MATH = "C:/Windows/Fonts/cambria.ttc"
CJK = "C:/Windows/Fonts/msyh.ttc"
CJK_B = "C:/Windows/Fonts/msyhbd.ttc"
TNR = "C:/Windows/Fonts/times.ttf"
CAMBRIA_UP = "C:/Windows/Fonts/cambria.ttc"

# ---------------- 主题配色 ----------------
NAVY = (20, 33, 61)
INK = (30, 41, 59)
MUTED = (100, 112, 133)
RED = (192, 57, 43)
GOLD = (186, 132, 26)
TEAL = (18, 118, 128)
BLUE = (38, 84, 156)
CREAM = (250, 247, 240)
LINE = (214, 208, 196)
WHITE = (255, 255, 255)
PAPER = (253, 251, 246)
GREEN = (58, 118, 78)

FRAC = "\u2221"        # 分式占位符
B = ("\ue000", "\ue001")  # 直立体起止标记

_fc = {}


def fm(size):
    k = ("m", int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(MATH, int(size))
    return _fc[k]


def fc(size, bold=False):
    k = ("c", int(size), bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(CJK_B if bold else CJK, int(size))
    return _fc[k]


def f(_path, size):
    return ImageFont.truetype(_path, int(size))


# ---------------- 字符分类 ----------------
def is_cjk(ch):
    o = ord(ch)
    return (0x3000 <= o <= 0x303F or 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF
            or 0x3400 <= o <= 0x4DBF or 0xFE30 <= o <= 0xFE4F)


def _is_letter(ch):
    o = ord(ch)
    return (ch.isalpha() and o < 0x0250) or 0x0370 <= o <= 0x03FF


def _font_for(text, size, upright):
    """选择字体：中文→雅黑；直立体→Cambria；数学字母→Cambria；数字/运算符→Times
       Times 缺少的数学符号（⇔ ⇒ ≤ 等）自动改用 Cambria。"""
    if not text:
        return f(TNR, size)
    if is_cjk(text[0]):
        return fc(size)
    if upright:
        return f(CAMBRIA_UP, size)
    if _is_letter(text[0]):
        return fm(size)
    fnt = f(TNR, size)
    for ch in text:
        if ch == " ":
            continue
        if not _has(fnt, ch):
            return f(CAMBRIA_UP, size)
    return fnt


_glyph_ok = {}


_NOTDEF = {}


def _has(font, ch):
    """检测字体是否真的含有该字符：缺失字形时 FreeType 统一绘制 .notdef。
    做法：为该字体算出 .notdef 的指纹（大小 + 墨迹计数 + 灰度直方图），
    目标字符指纹与之相同即视为缺字。"""
    key = (font.path, font.size)
    if key not in _NOTDEF:
        try:
            m, off = font.getmask2("\uf8ff", "L", anchor="ls")
            _NOTDEF[key] = (m.size, off, tuple(m.histogram()))
        except Exception:
            _NOTDEF[key] = None
    nd = _NOTDEF[key]
    try:
        m, off = font.getmask2(ch, "L", anchor="ls")
    except Exception:
        return True
    if nd is not None and m.size == nd[0] and off == nd[1] and tuple(m.histogram()) == nd[2]:
        return False
    return True


def _math_font(text, size, upright):
    return _font_for(text, size, upright)


def cwidth(d, text, font):
    b = d.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


# ---------------- 预处理 ----------------
CMDS = [("\\dfrac", FRAC), ("\\tfrac", FRAC), ("\\frac", FRAC),
        ("\\ln", "ln"), ("\\cos", "cos"), ("\\sin", "sin"), ("\\tan", "tan"),
        ("\\log", "log"), ("\\lg", "lg"), ("\\prime", "\u2032"), ("\\sqrt", "\u221a"),
        ("\\to", "\u2192"), ("\\Rightarrow", "\u21d2"), ("\\Leftrightarrow", "\u21d4"),
        ("\\iff", "\u21d4"), ("\\cdot", "\u00b7"), ("\\times", "\u00d7"), ("\\div", "\u00f7"),
        ("\\le ", "\u2264 "), ("\\ge ", "\u2265 "), ("\\ne ", "\u2260 "), ("\\in", "\u2208"),
        ("\\forall", "\u2200"), ("\\exists", "\u2203"), ("\\ell", "\u2113"), ("\\alpha", "\u03b1"), ("\\beta", "\u03b2"),
        ("\\theta", "\u03b8"), ("\\omega", "\u03c9"), ("\\varphi", "\u03c6"), ("\\phi", "\u03c6"),
        ("\\rho", "\u03c1"), ("\\lambda", "\u03bb"), ("\\mu", "\u03bc"), ("\\Delta", "\u0394"),
        ("\\Sigma", "\u03a3"), ("\\pm", "\u00b1"), ("\\sim", "\u223c"), ("\\approx", "\u2248"),
        ("\\forall", "\u2200"), ("\\quad", "\u2003"), ("\\qquad", "\u2003\u2003"),
        ("\\,", "\u2009"), ("\\;", "\u2009"), ("\\ ", " "), ("\\{", "{"), ("\\}", "}")]


def _fmt_sqrt(s):
    """把 \\sqrt{...} 改写成 √ 后紧跟内容（保留括号语义）"""
    out = []
    i = 0
    while i < len(s):
        if s.startswith("\\sqrt", i):
            k = i + 5
            if k < len(s) and s[k] == "{":
                depth = 0
                for j in range(k, len(s)):
                    if s[j] == "{":
                        depth += 1
                    elif s[j] == "}":
                        depth -= 1
                        if depth == 0:
                            out.append("\u221a" + s[k + 1:j])
                            i = j + 1
                            break
                else:
                    out.append("\u221a")
                    i = k
            else:
                out.append("\u221a")
                i = k
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def norm(s):
    if not isinstance(s, str):
        s = str(s)
    s = _fmt_sqrt(s)
    # $ 直立体区段：先切分，再逐段替换命令（避免替换出的 \\ 再次触发转义）
    parts = s.split("$")
    for k in range(len(parts)):
        body = parts[k]
        for a, b in CMDS:
            body = body.replace(a, b)
        parts[k] = body
    if len(parts) > 1:
        merged = [parts[0]]
        for k in range(1, len(parts)):
            merged.append(B[0] + parts[k] + (B[1] if k < len(parts) - 1 else ""))
        parts = merged
    return "".join(parts)


def _match_brace(s, k):
    """s[k] == '{'，返回与之匹配的 '}' 的下标"""
    depth = 0
    for j in range(k, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced braces in: " + s)


def _parse_frac(s, i):
    k = s.index("{", i)
    depth = 0
    for j in range(k, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                num = s[k + 1:j]
                break
    k2 = s.index("{", j)
    depth = 0
    for j2 in range(k2, len(s)):
        if s[j2] == "{":
            depth += 1
        elif s[j2] == "}":
            depth -= 1
            if depth == 0:
                den = s[k2 + 1:j2]
                break
    return num, den, j2 + 1


def _tokens(s, size):
    """切分成 [(kind, text_or_(num,den), dy, font, upright)]"""
    out = []
    i, n = 0, len(s)
    up = False
    while i < n:
        c = s[i]
        if c in B:
            up = (c == B[0])
            i += 1
            continue
        if c == FRAC:
            num, den, i = _parse_frac(s, i)
            out.append(("f", (num, den), 0, None, up))
            continue
        if c in "^_" and i + 1 < n and s[i + 1] == "{":
            j = _match_brace(s, i + 1)
            body = s[i + 2:j]
            dy = -size * 0.40 if c == "^" else size * 0.20
            # 上下标中的字母保持斜体
            out.append(("s", body, dy, None, False))
            i = j + 1
            continue
        # 普通字符：按字体类别分段
        j = i
        cls = "cjk" if is_cjk(c) else ("letter" if _is_letter(c) else "op")
        while j < n and s[j] not in B and s[j] != FRAC and not (
                s[j] in "^_" and j + 1 < n and s[j + 1] == "{"):
            cj = "cjk" if is_cjk(s[j]) else ("letter" if _is_letter(s[j]) else "op")
            if cj != cls:
                break
            j += 1
        text = s[i:j]
        out.append(("t", text, 0, _math_font(text, size, up), up))
        i = j
    return out


def mwidth(d, s, size):
    total = 0
    for kind, payload, dy, fnt, up in _tokens(norm(s), size):
        if kind == "t":
            total += cwidth(d, payload, fnt)
        elif kind == "s":
            total += mwidth(d, payload, size * 0.66)
        else:
            num, den = payload
            total += max(mwidth(d, num, size * 0.8), mwidth(d, den, size * 0.8)) + size * 0.22
    return total


def mtext(d, xy, s, size, color=INK, anchor="ls"):
    """排版并绘制数学富文本；返回右端 x 坐标。
       · 基线由 PIL 的 "ls" 锚点给出（Top=0 坐标系下即真正的基线）
       · 上下标 / 分式各自用局部坐标系偏移，避免嵌套锚点叠加。"""
    S = 2.0                      # 内部用 2 倍精度排版，再整体缩放回去
    sz = size
    x, y = xy
    toks = _tokens(norm(s), sz)

    def sub_width(t):
        tot = 0
        for kind, payload, dy, fnt, up in t:
            if kind == "t":
                tot += cwidth(d, payload, fnt)
            elif kind == "s":
                tot += sub_width(_tokens(payload, sz * 0.66))
            else:
                num, den = payload
                tot += max(sub_width(_tokens(num, sz * 0.8)), sub_width(_tokens(den, sz * 0.8))) + sz * 0.22
        return tot

    W = sum(sub_width([tk]) for tk in toks)
    if anchor[0] == "m":
        x -= W / 2
    elif anchor[0] == "r":
        x -= W

    def draw(toks_, ox, oy, s_):
        for kind, payload, dy, fnt, up in toks_:
            if kind == "t":
                d.text((ox, oy + dy), payload, font=fnt, fill=color, anchor="ls")
                ox += cwidth(d, payload, fnt)
            elif kind == "s":
                draw(_tokens(payload, s_ * 0.66), ox, oy + dy, s_ * 0.66)
                ox += sub_width(_tokens(payload, s_ * 0.66))
            else:
                num, den = payload
                fs = s_ * 0.8
                tn = _tokens(num, fs)
                td = _tokens(den, fs)
                wn, wd = sub_width(tn), sub_width(td)
                bw = max(wn, wd) + s_ * 0.22
                cx = ox + bw / 2
                ly = oy - s_ * 0.30
                d.line([(ox + 3, ly), (ox + bw - 3, ly)], fill=color, width=max(1, int(s_ * 0.05)))
                draw(tn, cx - wn / 2, ly - s_ * 0.12, fs)
                draw(td, cx - wd / 2, ly + s_ * 0.12 + fs * 0.72, fs)
                ox += bw

    draw(toks, x, y, sz)
    return x + W


# ---------------- 画布 ----------------
class Canvas(object):
    def __init__(self, w, h, bg=None, scale=2):
        self.scale = scale
        self.W, self.H = int(w * scale), int(h * scale)
        self.img = Image.new("RGB", (self.W, self.H), bg or PAPER)
        self.d = ImageDraw.Draw(self.img)

    def S(self, v):
        if isinstance(v, (tuple, list)):
            return tuple(self.S(x) for x in v)
        return v * self.scale

    def line(self, pts, color=INK, width=2, joint="curve"):
        if len(pts) < 2:
            return
        self.d.line([self.S(p) for p in pts], fill=color, width=max(1, int(width * self.scale)), joint=joint)

    def rect(self, box, fill=None, outline=None, width=2, radius=0):
        box = self.S(box)
        if radius:
            self.d.rounded_rectangle(box, radius=int(radius * self.scale), fill=fill,
                                     outline=outline, width=int(width * self.scale))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * self.scale))

    def ellipse(self, box, fill=None, outline=None, width=2):
        self.d.ellipse(self.S(box), fill=fill, outline=outline, width=int(width * self.scale))

    def dot(self, p, color=RED, r=5):
        x, y = self.S(p)
        rr = r * self.scale
        self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color)

    def poly(self, pts, fill, outline=None):
        self.d.polygon([self.S(p) for p in pts], fill=fill, outline=outline)

    def m(self, xy, s, size, color=INK, anchor="ls"):
        return mtext(self.d, self.S(xy), s, size * self.scale, color, anchor) / self.scale

    def mw(self, s, size):
        return mwidth(self.d, s, size * self.scale) / self.scale

    def c(self, xy, s, size, color=INK, bold=False, anchor="ls"):
        fnt = fc(size * self.scale, bold)
        s = str(s)
        self.d.text(self.S(xy), s, font=fnt, fill=color, anchor=anchor)
        return self.d.textlength(s, font=fnt) / self.scale

    def save(self, name):
        p = os.path.join(ASSETS, name)
        self.img.save(p, dpi=(300, 300))
        return p
