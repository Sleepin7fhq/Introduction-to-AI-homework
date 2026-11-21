# -*- coding: utf-8 -*-
"""生成 DSH Studio 2.2 采样库（one-shot WAV）。

所有素材由本项目 DSP 合成，版权归项目所有，可商用、可再分发。
输出：public/samples/<分类>/<名字>.wav + public/samples/manifest.json
"""
import json
import math
import os
import struct

import numpy as np

SR = 48000
ROOT = r'D:\AI\aihw'
OUT = os.path.join(ROOT, 'public', 'samples')

rng = np.random.default_rng(20261121)


# ---------------------------------------------------------------- DSP 基础
def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env_ad(n, attack, decay, sustain=0.0):
    a = max(1, int(attack * SR))
    d = max(1, n - a)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = sustain + (1 - sustain) * np.exp(-np.arange(d) / max(1e-6, decay * SR))
    return e


def lowpass(x, cutoff, q=0.7):
    """RBJ lowpass biquad，逐样本实现（够快、无 scipy 依赖）。"""
    w0 = 2 * math.pi * cutoff / SR
    alpha = math.sin(w0) / (2 * q)
    b0 = (1 - math.cos(w0)) / 2
    b1 = 1 - math.cos(w0)
    b2 = b0
    a0 = 1 + alpha
    a1 = -2 * math.cos(w0)
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return _lfilter(b, a, x)


def highpass(x, cutoff, q=0.7):
    w0 = 2 * math.pi * cutoff / SR
    alpha = math.sin(w0) / (2 * q)
    b0 = (1 + math.cos(w0)) / 2
    b1 = -(1 + math.cos(w0))
    b2 = b0
    a0 = 1 + alpha
    a1 = -2 * math.cos(w0)
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return _lfilter(b, a, x)


def bandpass(x, freq, q=6.0):
    w0 = 2 * math.pi * freq / SR
    alpha = math.sin(w0) / (2 * q)
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1 + alpha
    a1 = -2 * math.cos(w0)
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return _lfilter(b, a, x)


def _lfilter(b, a, x):
    y = np.zeros_like(x)
    for i in range(len(x)):
        acc = b[0] * x[i]
        if i >= 1:
            acc += b[1] * x[i - 1] - a[1] * y[i - 1]
        if i >= 2:
            acc += b[2] * x[i - 2] - a[2] * y[i - 2]
        y[i] = acc
    return y


def soft_clip(x, drive=1.6):
    return np.tanh(x * drive) / math.tanh(drive)


def normalize(x, peak_db=-1.0):
    m = float(np.max(np.abs(x))) or 1e-9
    return x / m * (10 ** (peak_db / 20))


def fade(x, ms_in=3, ms_out=12):
    n = len(x)
    a = min(int(SR * ms_in / 1000), n // 2)
    b = min(int(SR * ms_out / 1000), n // 2)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a)
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def save(name, x, category, kind, rootNote=None, bpm=None, tags=None, note=''):
    x = np.asarray(x, dtype=np.float64)
    x = normalize(fade(x))
    path = os.path.join(OUT, category, name + '.wav')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = np.clip(x, -1, 1)
    pcm = (pcm * 32767).astype('<i2')
    stereo = np.repeat(pcm[:, None], 2, axis=1).reshape(-1)
    data = stereo.tobytes()
    with open(path, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + len(data)))
        f.write(b'WAVEfmt ')
        f.write(struct.pack('<IHHIIHH', 16, 1, 2, SR, SR * 4, 4, 16))
        f.write(b'data')
        f.write(struct.pack('<I', len(data)))
        f.write(data)
    return {
        'file': '%s/%s.wav' % (category, name),
        'category': category,
        'kind': kind,
        'duration': round(len(x) / SR, 3),
        'sampleRate': SR,
        'channels': 2,
        'rootNote': rootNote,
        'bpm': bpm,
        'tags': tags or [],
        'note': note,
        'source': 'synthesized',
        'author': 'DSH Studio 2.2 (self-made)',
        'license': 'CC0-1.0 (project-generated, no third-party content)',
        'commercialUse': True,
        'attributionRequired': False,
    }


# ---------------------------------------------------------------- 鼓
def kick(name, f_start, f_end, decay, click_amt, drive, note=''):
    t = t_axis(decay + 0.05)
    f = f_end + (f_start - f_end) * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / (decay * 0.42))
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.0035) * click_amt
    click = highpass(click, 2200)
    x = soft_clip(body * 1.35 + click, drive)
    return x, note


def snare(name, tone_hz, noise_decay, tone_decay, bright):
    t = t_axis(max(noise_decay, tone_decay) + 0.05)
    noise = rng.standard_normal(len(t)) * np.exp(-t / noise_decay)
    noise = bandpass(noise, 1800, 1.0)
    body = np.sin(2 * np.pi * tone_hz * t) * np.exp(-t / tone_decay)
    crack = highpass(rng.standard_normal(len(t)) * np.exp(-t / 0.004), 5200) * bright
    return soft_clip(noise * 1.2 + body * 0.8 + crack * 0.6, 1.4), None


def clap(name, spread, decay):
    dur = decay + 0.05
    t = t_axis(dur)
    x = np.zeros(len(t))
    for off, amp in ((0.0, 1.0), (spread, 0.7), (spread * 2.2, 0.5)):
        s = int(off * SR)
        seg = rng.standard_normal(len(t) - s) * np.exp(-np.arange(len(t) - s) / (decay * SR / 3))
        x[s:] += seg * amp
    x = bandpass(x, 1250, 1.4)
    return soft_clip(x * 2.2, 1.2), None


def metallic(dur, base, decay):
    t = t_axis(dur)
    ratios = [1.0, 1.47, 1.83, 2.31, 2.68, 3.04]
    x = np.zeros(len(t))
    for i, r in enumerate(ratios):
        x += np.sign(np.sin(2 * np.pi * base * r * t + i)) * (1.0 / (i + 1))
    x = highpass(x, 6500, 0.8)
    # 方波金属声太刺，低通掉 11k 以上，并把噪声比例降下来
    x = lowpass(x, 11000, 0.7)
    noise = highpass(rng.standard_normal(len(t)), 8000) * 0.22
    y = (x * 0.30 + noise) * np.exp(-t / decay)
    return lowpass(y, 12000, 0.7), None


# ---------------------------------------------------------------- 音高类
def saw(freq, dur, detune_cents=0.0, phase=0.0):
    t = t_axis(dur)
    f = freq * 2 ** (detune_cents / 1200)
    ph = (t * f + phase) % 1.0
    return 2 * ph - 1


def supersaw(freq, dur, voices=7, spread=22):
    x = np.zeros(int(SR * dur))
    for i in range(voices):
        d = -spread + 2 * spread * i / max(1, voices - 1)
        x += saw(freq, dur, d, rng.random())
    return x / voices


def formant_vowel(vowel, dur, f0, consonant=True):
    """共振峰合成元音；开头加 8ms 噪声爆破模拟 /b/ /p/ 的辅音。"""
    F = {
        'a': [(730, 1.0), (1090, 0.55), (2440, 0.25)],
        'e': [(530, 1.0), (1840, 0.45), (2480, 0.2)],
        'i': [(270, 1.0), (2290, 0.35), (3010, 0.2)],
        'o': [(570, 1.0), (840, 0.6), (2410, 0.12)],
        'u': [(300, 1.0), (870, 0.5), (2240, 0.1)],
    }[vowel]
    t = t_axis(dur)
    # 声门脉冲串（带微小抖动，避免机械感）
    jitter = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    src = np.zeros(len(t))
    phase = 0.0
    for i in range(len(t)):
        phase += f0 * jitter[i] / SR
        if phase >= 1.0:
            phase -= 1.0
            src[i] = 1.0
    src = lowpass(src, 4000, 0.7)
    y = np.zeros(len(t))
    for freq, amp in F:
        y += bandpass(src, freq, 12.0) * amp
    y = lowpass(y, 7000, 0.7)
    env = env_ad(len(t), 0.01, dur * 0.35, 0.15)
    y *= env
    if consonant:
        burst = rng.standard_normal(int(0.009 * SR)) * 0.6
        burst = bandpass(burst, 900, 2.0)
        y[:len(burst)] += burst
    return y


# ---------------------------------------------------------------- 过渡 / 音效
def riser(dur, f_from=300, f_to=9000):
    t = t_axis(dur)
    noise = rng.standard_normal(len(t))
    # 用分段带通做扫频
    out = np.zeros(len(t))
    seg = max(1, len(t) // 60)
    for i in range(0, len(t), seg):
        frac = i / len(t)
        f = f_from * (f_to / f_from) ** frac
        part = noise[i:i + seg]
        if len(part) < 8:
            continue
        out[i:i + seg] = bandpass(part, min(f, 16000), 4.0)
    sweep = saw(f_from, dur) * 0.15
    x = out * np.linspace(0.05, 1.0, len(t)) ** 1.6 + sweep * np.linspace(0, 0.4, len(t))
    return x


def impact(dur=1.6):
    t = t_axis(dur)
    f = 90 * np.exp(-t / 0.18) + 38
    phase = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(phase) * np.exp(-t / 0.5)
    noise = lowpass(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.28)
    return soft_clip(boom * 1.4 + noise * 0.7, 1.5)


def airhorn(dur=0.9, f0=233):
    t = t_axis(dur)
    vib = 1 + 0.02 * np.sin(2 * np.pi * 6 * t)
    x = np.zeros(len(t))
    for m, a in ((1, 1.0), (2, 0.6), (3, 0.4), (4, 0.25)):
        x += np.sign(np.sin(2 * np.pi * f0 * m * vib * t)) * a
    x = lowpass(x, 3500, 0.8)
    return x * env_ad(len(t), 0.02, 0.25, 0.4)


def laser(dur=0.35):
    t = t_axis(dur)
    f = 2400 * np.exp(-t / 0.07) + 120
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(phase) + 0.3 * np.sign(np.sin(phase * 2))
    return x * np.exp(-t / 0.12)


def boing(dur=0.5):
    t = t_axis(dur)
    f = 220 * (1 + 0.5 * np.sin(2 * np.pi * 9 * t) * np.exp(-t / 0.25))
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t / 0.3)


def bell(dur=1.2, f0=880):
    t = t_axis(dur)
    x = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.5)
    x += np.sin(2 * np.pi * f0 * 2.76 * t) * 0.4 * np.exp(-t / 0.25)
    x += np.sin(2 * np.pi * f0 * 5.4 * t) * 0.2 * np.exp(-t / 0.12)
    return x


# ---------------------------------------------------------------- 生成
def main():
    os.makedirs(OUT, exist_ok=True)
    entries = []

    def add(name, x, category, kind, **kw):
        entries.append(save(name, x, category, kind, **kw))

    # 鼓：kick
    x, _ = kick('kick_deep', 118, 44, 0.55, 0.20, 1.5)
    add('kick_deep', x, 'drums/kick', 'kick', tags=['deep', 'techno'])
    x, _ = kick('kick_punch', 150, 52, 0.32, 0.35, 1.8)
    add('kick_punch', x, 'drums/kick', 'kick', tags=['punch', 'edm'])
    x, _ = kick('kick_hard', 190, 46, 0.62, 0.45, 2.6)
    add('kick_hard', x, 'drums/kick', 'kick', tags=['hardstyle'])
    x, _ = kick('kick_808', 95, 40, 0.95, 0.12, 1.2)
    add('kick_808', x, 'drums/kick', 'kick', tags=['808', 'trap'])

    # snare
    x, _ = snare('snare_crack', 185, 0.14, 0.07, 0.9)
    add('snare_crack', x, 'drums/snare', 'snare', tags=['crack'])
    x, _ = snare('snare_body', 165, 0.2, 0.1, 0.5)
    add('snare_body', x, 'drums/snare', 'snare', tags=['fat'])
    x, _ = snare('snare_rim', 320, 0.05, 0.03, 1.4)
    add('snare_rim', x, 'drums/snare', 'snare', tags=['rim'])
    x, _ = snare('snare_trap', 200, 0.24, 0.06, 0.7)
    add('snare_trap', x, 'drums/snare', 'snare', tags=['trap'])

    # clap
    x, _ = clap('clap_wide', 0.012, 0.14)
    add('clap_wide', x, 'drums/clap', 'clap', tags=['wide'])
    x, _ = clap('clap_tight', 0.008, 0.09)
    add('clap_tight', x, 'drums/clap', 'clap', tags=['tight'])

    # hat / cymbal
    x, _ = metallic(0.12, 420, 0.028)
    add('hat_closed', x, 'drums/hihat', 'hat', tags=['closed'])
    x, _ = metallic(0.55, 380, 0.15)
    add('hat_open', x, 'drums/hihat', 'hat', tags=['open'])
    x, _ = metallic(0.08, 520, 0.018)
    add('hat_tick', x, 'drums/hihat', 'hat', tags=['tick'])
    x, _ = metallic(0.3, 300, 0.07)
    add('hat_pedal', x, 'drums/hihat', 'hat', tags=['pedal'])
    x, _ = metallic(2.2, 240, 0.7)
    add('crash', x, 'drums/cymbal', 'cymbal', tags=['crash'])
    x, _ = metallic(1.2, 380, 0.35)
    add('ride', x, 'drums/cymbal', 'cymbal', tags=['ride'])

    # bass
    for name, hz, note in (('sub_C1', 32.70, 'C1'), ('sub_F1', 43.65, 'F1'), ('sub_G1', 49.00, 'G1')):
        t = t_axis(1.2)
        x = np.sin(2 * np.pi * hz * t) + 0.12 * np.sin(2 * np.pi * hz * 2 * t)
        x *= env_ad(len(t), 0.005, 0.9, 0.55)
        add(name, soft_clip(x, 1.3), 'bass/sub', 'bass', rootNote=note, tags=['sub'])

    for name, hz, note in (('reese_C1', 32.70, 'C1'), ('reese_F1', 43.65, 'F1')):
        x = saw(hz, 1.0, -9) + saw(hz, 1.0, 11) + 0.5 * saw(hz * 0.5, 1.0)
        x = lowpass(x, 520, 1.2)
        x *= env_ad(len(x), 0.008, 0.7, 0.7)
        add(name, soft_clip(x, 2.0), 'bass/reese', 'bass', rootNote=note, tags=['reese'])

    for name, hz, note in (('hard_bass_C1', 32.70, 'C1'), ('hard_bass_F1', 43.65, 'F1')):
        x = saw(hz, 0.6, 0) + 0.6 * saw(hz, 0.6, 14) + 0.3 * np.sign(np.sin(2 * np.pi * hz * t_axis(0.6)))
        x = lowpass(x, 800, 2.2)
        x *= env_ad(len(x), 0.004, 0.28, 0.25)
        add(name, soft_clip(x, 3.2), 'bass/hardstyle', 'bass', rootNote=note, tags=['hardstyle', 'distorted'])

    # 主音
    lead_specs = [
        ('lead_supersaw_C4', 261.63, 'C4', supersaw(261.63, 0.9, 7, 24), 5200),
        ('lead_saw_C4', 261.63, 'C4', saw(261.63, 0.6, 0) + 0.4 * saw(261.63, 0.6, 8), 4200),
        ('lead_square_C4', 261.63, 'C4', np.sign(np.sin(2 * np.pi * 261.63 * t_axis(0.5))), 3200),
        ('lead_hard_C4', 261.63, 'C4', supersaw(261.63, 0.7, 5, 30), 3800),
        ('lead_siren_C4', 261.63, 'C4', saw(261.63, 1.0, 0), 2600),
    ]
    for name, hz, note, raw, cut in lead_specs:
        x = lowpass(raw, cut, 1.1)
        t = t_axis(len(x) / SR)
        x *= env_ad(len(x), 0.006, len(t) * 0.4, 0.35)
        drive = 2.2 if 'hard' in name or 'siren' in name else 1.4
        add(name, soft_clip(x, drive), 'synth/lead', 'lead', rootNote=note, tags=['lead'])

    # pluck / pad
    for name, hz, note in (('pluck_C4', 261.63, 'C4'), ('pluck_marimba_C4', 523.25, 'C5')):
        t = t_axis(0.35)
        x = np.sin(2 * np.pi * hz * t) * np.exp(-t / 0.12)
        x += 0.4 * np.sin(2 * np.pi * hz * 3 * t) * np.exp(-t / 0.05)
        add(name, x, 'synth/pluck', 'pluck', rootNote=note, tags=['pluck'])

    for name, hz, note, cut in (('pad_warm_C3', 130.81, 'C3', 1000), ('pad_dark_C3', 130.81, 'C3', 620),
                                ('pad_wide_C3', 130.81, 'C3', 1400)):
        x = supersaw(hz, 3.0, 5, 28)
        x = lowpass(x, cut, 0.8)
        x *= env_ad(len(x), 0.8, 1.6, 0.75)
        add(name, x, 'synth/pad', 'pad', rootNote=note, tags=['pad'])

    # 人声切片（带辅音爆破）
    for v in ('a', 'e', 'o', 'i', 'u'):
        add('chop_' + v, formant_vowel(v, 0.42, 174.6), 'vocal/chop', 'vocal',
            rootNote='F3', tags=['chop', 'vowel', v])
    add('chop_hey', formant_vowel('e', 0.3, 220.0), 'vocal/chop', 'vocal', rootNote='A3', tags=['chop', 'hey'])
    add('chop_woo', formant_vowel('u', 0.55, 196.0), 'vocal/chop', 'vocal', rootNote='G3', tags=['chop', 'woo'])

    # 人声 fx
    t = t_axis(0.8)
    add('fx_breath', highpass(rng.standard_normal(len(t)), 1200) * env_ad(len(t), 0.2, 0.3, 0.2),
        'vocal/fx', 'fx', tags=['breath'])
    add('fx_scream', soft_clip(formant_vowel('a', 0.7, 320.0), 4.0), 'vocal/fx', 'fx', tags=['scream'])
    add('fx_laugh', np.concatenate([formant_vowel('a', 0.12, 260.0) for _ in range(4)]),
        'vocal/fx', 'fx', tags=['laugh'])

    # 过渡
    add('riser_4s', riser(4.0), 'transitions/riser', 'riser', tags=['riser', 'long'])
    add('riser_2s', riser(2.0, 400, 12000), 'transitions/riser', 'riser', tags=['riser', 'short'])
    add('riser_noise_2s', riser(2.0, 150, 8000), 'transitions/riser', 'riser', tags=['noise'])
    add('impact_boom', impact(1.8), 'transitions/impact', 'impact', tags=['boom'])
    add('impact_hit', soft_clip(impact(1.2) + metallic(1.2, 200, 0.4)[0] * 0.4, 1.6),
        'transitions/impact', 'impact', tags=['hit'])

    # meme sfx
    add('sfx_laser', laser(), 'meme/sfx', 'fx', tags=['laser'])
    add('sfx_airhorn', airhorn(), 'meme/sfx', 'fx', tags=['airhorn'])
    add('sfx_boing', boing(), 'meme/sfx', 'fx', tags=['boing'])
    add('sfx_ding', bell(), 'meme/sfx', 'fx', tags=['ding'])

    manifest = {
        'version': '2.2.0',
        'sampleRate': SR,
        'generatedAt': '2026-11-21',
        'license': 'CC0-1.0 (self-generated; no third-party audio)',
        'note': '全部 one-shot 由本项目 DSP 合成，可商用、可再分发、无需署名。',
        'count': len(entries),
        'samples': entries,
    }
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total = sum(os.path.getsize(os.path.join(OUT, e['file'])) for e in entries)
    print('samples: %d  total %.1f MB' % (len(entries), total / 1e6))
    cats = {}
    for e in entries:
        cats[e['category']] = cats.get(e['category'], 0) + 1
    for k in sorted(cats):
        print('  %-22s %d' % (k, cats[k]))


if __name__ == '__main__':
    main()
