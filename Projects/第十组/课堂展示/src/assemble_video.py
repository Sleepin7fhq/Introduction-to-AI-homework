# -*- coding: utf-8 -*-
"""把录屏帧 + 页面实际播放的 WAV 合成 MP4（H.264 + AAC）。

- 画面：1440x810，30fps，CRF 20
- 声音：直接使用页面里播放的那条 WAV（真实生成音频，不配音）
- 生成等待被压缩成约 1.2 秒，避免干等
"""
import json
import os
import subprocess
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RENDER = os.path.join(ROOT, '.render')
FRAMES = os.path.join(RENDER, 'frames-video')
FFMPEG = os.path.join(RENDER, 'ffmpeg.exe')
OUT = os.path.join(ROOT, '演示视频-20s.mp4')
POSTER = os.path.join(ROOT, '演示视频-封面.png')

W, H = 1440, 810
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
    d.rectangle([0, H - 6, W, H], fill=TEAL)
    d.text((110, 96), 'DSH STUDIO 2.0', font=font(22), fill=TEXT3)
    d.text((110, H // 2 - 120), title, font=font(56, True), fill=TEXT)
    d.text((110, H // 2 - 20), sub, font=font(30), fill=TEAL)
    if note:
        d.text((110, H // 2 + 50), note, font=font(22), fill=TEXT3)
    return img


def main():
    meta = json.load(open(os.path.join(FRAMES, 'timeline.json'), encoding='utf-8'))
    frames = meta['frames']
    m = meta['marks']
    audio_url = meta['audioUrl']
    print('frames=%d' % len(frames))

    # 1) 下载页面实际播放的音频
    wav = os.path.join(RENDER, 'video-audio.wav')
    if not os.path.exists(wav):
        req = urllib.request.Request(audio_url, headers={'User-Agent': 'dsh-studio/2.0'})
        with urllib.request.urlopen(req, timeout=60) as r, open(wav, 'wb') as f:
            f.write(r.read())
    print('audio: %.2f MB' % (os.path.getsize(wav) / 1e6))

    seq = []  # (path, dur_ms)

    intro = os.path.join(RENDER, 'card-intro.jpg')
    card('真实操作录屏', '把「老板画的饼」做成一首 Rave',
         '下面是软件的真实反应，含真实生成的声音').save(intro, quality=95)
    seq.append((intro, 1300))

    def add_range(t_from, t_to, max_fps=30):
        picked = [f for f in frames if t_from <= f['t'] < t_to]
        step = max(1, int(round(1000.0 / max_fps / 33.3)))
        chosen = picked[::step] if step > 1 else picked
        for f in chosen:
            seq.append((f['file'], max(20, int(1000 / max_fps))))
        return len(chosen)

    # 2) 操作段（真实速度）
    n_ops = add_range(max(0, m['memeTab'] - 300), m['genClick'])
    print('ops frames:', n_ops)

    # 3) 生成等待：压缩为 3 帧 × 0.42s
    for t in (m['genClick'] + 200, (m['genClick'] + m['audioReady']) / 2, m['audioReady'] - 100):
        near = min(frames, key=lambda f: abs(f['t'] - t))
        seq.append((near['file'], 420))
    print('generation compressed to 1.26s')

    # 4) 音频播放段（真实速度，保留 12 秒音乐）
    t_play_video = sum(d for _, d in seq) / 1000.0
    n_play = add_range(m['audioReady'], min(m['audioReady'] + 13500, m['playEnd']))
    print('play frames: %d  (playback starts at %.2fs in video)' % (n_play, t_play_video))

    end = os.path.join(RENDER, 'card-end.jpg')
    card('真实生成 · 真实播放', 'ACE-Step 1.5 · 本机 8GB 显卡',
         '4.45 GB 显存峰值 · 13 秒音频约 10 秒生成').save(end, quality=95)
    seq.append((end, 3400))

    total = sum(d for _, d in seq) / 1000.0
    print('planned duration: %.2fs, frames=%d' % (total, len(seq)))

    # 5) concat 清单
    listfile = os.path.join(RENDER, 'concat.txt')
    with open(listfile, 'w', encoding='utf-8') as f:
        for p, d in seq:
            f.write("file '%s'\n" % p.replace('\\', '/'))
            f.write('duration %.3f\n' % (d / 1000.0))
        f.write("file '%s'\n" % seq[-1][0].replace('\\', '/'))

    # 6) 合成
    fade_start = max(0.0, total - 1.4)
    afilter = (
        '[1:a]adelay=%d|%d,volume=0.95,afade=t=in:st=%.2f:d=0.4,'
        'afade=t=out:st=%.2f:d=1.3[a]'
        % (int(t_play_video * 1000), int(t_play_video * 1000),
           t_play_video, fade_start)
    )
    cmd = [
        FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', listfile,
        '-i', wav,
        '-filter_complex', afilter,
        '-map', '0:v', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
        '-vf', 'format=yuv420p,scale=in_range=full:out_range=tv', '-color_range', 'tv', '-r', '30',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-shortest', '-movflags', '+faststart',
        OUT,
    ]
    print('encoding...')
    r = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
    if r.returncode != 0:
        print('FFMPEG FAILED')
        print(r.stderr[-2000:])
        return 1

    # 7) 封面上传 + 探针
    subprocess.run([FFMPEG, '-y', '-ss', '8.5', '-i', OUT, '-frames:v', '1', POSTER],
                   capture_output=True)
    probe = subprocess.run([FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error',
                            '-show_entries', 'format=duration,size:stream=codec_name,width,height,r_frame_rate,channels',
                            '-of', 'default=nw=1', OUT], capture_output=True, text=True)
    print(probe.stdout.strip() if probe.returncode == 0 else '(no ffprobe)')
    print('MP4: %.2f MB  %s' % (os.path.getsize(OUT) / 1e6, OUT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
