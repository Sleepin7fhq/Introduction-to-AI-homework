# -*- coding: utf-8 -*-
"""把录屏帧组装成演示 GIF：压缩生成等待，保留操作与播放画面，总长 20-26 秒。"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FRAMES = os.path.join(ROOT, '.render', 'frames')
OUT_GIF = os.path.join(ROOT, '演示视频-20s.gif')
OUT_POSTER = os.path.join(ROOT, '演示视频-封面.png')

W, H = 900, 506
BG = (8, 11, 16)
TEAL = (94, 234, 212)
TEXT = (230, 237, 247)
TEXT3 = (102, 116, 138)


def font(size, bold=False):
    for f in (('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc'),
              'C:/Windows/Fonts/msyh.ttc'):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def card(title, sub, note=None):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 4, W, H], fill=TEAL)
    d.text((60, 44), 'DSH STUDIO 2.0', font=font(13), fill=TEXT3)
    d.text((60, H // 2 - 78), title, font=font(32, True), fill=TEXT)
    d.text((60, H // 2 - 22), sub, font=font(17), fill=TEAL)
    if note:
        d.text((60, H // 2 + 26), note, font=font(13), fill=TEXT3)
    return img


def load_frame(path):
    im = Image.open(path).convert('RGB')
    tw, th = im.size
    target = W / H
    if tw / th > target:
        nw = int(th * target)
        im = im.crop(((tw - nw) // 2, 0, (tw + nw) // 2, th))
    else:
        nh = int(tw / target)
        im = im.crop((0, (th - nh) // 2, tw, (th + nh) // 2))
    return im.resize((W, H), Image.LANCZOS)


def main():
    meta = json.load(open(os.path.join(FRAMES, 'timeline.json'), encoding='utf-8'))
    frames = meta['frames']
    m = meta['marks']
    audio_at = meta.get('audioAt') or m['audioReady']
    print('frames=%d audioAt=%d' % (len(frames), audio_at))
    print('marks:', json.dumps(m, ensure_ascii=False))

    seq = []

    def add_range(t_from, t_to, step_ms, hold_ms, label=''):
        picked = [f for f in frames if t_from <= f['t'] < t_to]
        # 按真实间隔抽样
        last = -1e9
        n = 0
        for f in picked:
            if f['t'] - last >= step_ms:
                seq.append((load_frame(f['file']), hold_ms))
                last = f['t']
                n += 1
        print('  %-14s %5.1f-%5.1fs  frames=%d  dur=%.1fs' % (label, t_from / 1000, t_to / 1000, n, n * hold_ms / 1000.0))

    # 操作段：切页、输入、找、选卡
    add_range(max(0, m['memeTab'] - 250), m['genClick'], 110, 165, '操作')
    # 生成等待：压成 1.2 秒
    for t in (m['genClick'], (m['genClick'] + audio_at) / 2, audio_at - 120):
        near = min(frames, key=lambda f: abs(f['t'] - t))
        seq.append((load_frame(near['file']), 400))
    print('  %-14s compressed to 1.2s' % '生成等待')
    # 播放 AI 音频
    add_range(audio_at, m['audioPlayed'], 110, 165, 'AI 音频播放')
    # 切引擎 + 生成时间轴
    add_range(m['audioPlayed'], m['timelineReady'], 130, 160, '切换引擎')
    # 时间轴播放（播放头在走）
    add_range(m['timelineReady'], m['timelinePlayed'] + 400, 100, 130, '时间轴播放')

    seq.append((card('真实生成 · 真实播放', 'ACE-Step 1.5 在本机 8GB 显卡上生成',
                     '4.45 GB 显存峰值 · 13 秒音频约 10 秒生成'), 4200))

    total = sum(d for _, d in seq) / 1000.0
    print('total frames=%d  duration=%.1fs' % (len(seq), total))

    seq[0][0].save(OUT_POSTER)
    palette = [im.convert('P', palette=Image.ADAPTIVE, colors=128) for im, _ in seq]
    palette[0].save(
        OUT_GIF,
        save_all=True,
        append_images=palette[1:],
        duration=[d for _, d in seq],
        loop=0,
        optimize=True,
        disposal=2,
    )
    print('GIF: %.2f MB  %s' % (os.path.getsize(OUT_GIF) / 1e6, OUT_GIF))


if __name__ == '__main__':
    main()
