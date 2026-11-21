# -*- coding: utf-8 -*-
"""两处修正：
1) 镲片合成过于刺耳（方波 7k+ 高通）→ 加低通、降噪声比例；
2) 采样触发缺少乐器级音量配平 → 在采样器里加 TRIM。
"""
import io
import re

# ---- 1) 采样库：镲片柔化 ----
S = r'D:\AI\aihw\scripts\build_samples.py'
s = io.open(S, encoding='utf-8').read()
old = """    x = highpass(x, 7000, 0.8)
    noise = highpass(rng.standard_normal(len(t)), 9000) * 0.5
    return (x * 0.35 + noise) * np.exp(-t / decay), None"""
new = """    x = highpass(x, 6500, 0.8)
    # 方波金属声太刺，低通掉 11k 以上，并把噪声比例降下来
    x = lowpass(x, 11000, 0.7)
    noise = highpass(rng.standard_normal(len(t)), 8000) * 0.22
    y = (x * 0.30 + noise) * np.exp(-t / decay)
    return lowpass(y, 12000, 0.7), None"""
assert old in s
s = s.replace(old, new)
io.open(S, 'w', encoding='utf-8', newline='\n').write(s)
print('build_samples: cymbals softened')

# ---- 2) 采样器：乐器级音量配平 ----
P = r'D:\AI\aihw\src\audio\sampler.ts'
t = io.open(P, encoding='utf-8').read()

anchor = "const KITS: Record<KitId, Kit> = {"
trim = '''/**
 * 乐器级音量配平。
 * 采样都归一化到 -1 dBFS，如果直接按力度触发，五轨叠起来会把限幅器打爆
 * （实测 RMS -7dB、air 20%）。这里按"鼓组内部比例"做一次静态配平。
 */
const TRIM: Record<string, number> = {
  kick: 0.95,
  snare: 0.5,
  clap: 0.42,
  hat: 0.2,
  openhat: 0.18,
  cymbal: 0.22,
  bass: 0.4,
  lead: 0.32,
  chop: 0.26,
  pad: 0.2,
};

const KITS: Record<KitId, Kit> = {'''
assert anchor in t
t = t.replace(anchor, trim, 1)

# play() 增加 trim 参数
old_play = "  function play(file: string, pitch: number, durSec: number, time: number, vel: number, oneShot: boolean) {"
new_play = "  function play(file: string, pitch: number, durSec: number, time: number, vel: number, oneShot: boolean, trim = 1) {"
assert old_play in t
t = t.replace(old_play, new_play, 1)

old_gain = "    const v = Math.max(0.02, Math.min(1, vel));"
new_gain = "    const v = Math.max(0.02, Math.min(1, vel)) * trim;"
assert old_gain in t
t = t.replace(old_gain, new_gain, 1)

# 各分支带 trim
repl = [
 ("play(pickVariant(kit.kick, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.kick, pitch, time), pitch, dur, time, vel, true, TRIM.kick)"),
 ("play(pickVariant(kit.snare, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.snare, pitch, time), pitch, dur, time, vel, true, TRIM.snare)"),
 ("play(pickVariant(kit.clap, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.clap, pitch, time), pitch, dur, time, vel, true, TRIM.clap)"),
 ("play(pickVariant(kit.hatClosed, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.hatClosed, pitch, time), pitch, dur, time, vel, true, TRIM.hat)"),
 ("play(pickVariant(kit.hatOpen, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.hatOpen, pitch, time), pitch, dur, time, vel, true, TRIM.openhat)"),
 ("play(pickVariant(kit.cymbal, pitch, time), pitch, dur, time, vel, true)",
  "play(pickVariant(kit.cymbal, pitch, time), pitch, dur, time, vel, true, TRIM.cymbal)"),
 ("play(kit.bass, pitch, dur, time, vel, false)",
  "play(kit.bass, pitch, dur, time, vel, false, TRIM.bass)"),
 ("play(kit.pad, pitch, Math.max(dur, 0.6), time, vel, false)",
  "play(kit.pad, pitch, Math.max(dur, 0.6), time, vel, false, TRIM.pad)"),
 ("play(pickVariant(kit.chop, pitch, time), pitch, Math.min(dur, 0.35), time, vel, false)",
  "play(pickVariant(kit.chop, pitch, time), pitch, Math.min(dur, 0.35), time, vel, false, TRIM.chop)"),
 ("play(kit.lead, pitch, dur, time, vel, false)",
  "play(kit.lead, pitch, dur, time, vel, false, TRIM.lead)"),
 ("play(kit.pad, pitch, Math.min(dur, 0.5), time, vel, false)",
  "play(kit.pad, pitch, Math.min(dur, 0.5), time, vel, false, TRIM.pad)"),
]
for a, b in repl:
    if a in t:
        t = t.replace(a, b, 1)
    else:
        print('WARN not found:', a[:50])

io.open(P, 'w', encoding='utf-8', newline='\n').write(t)
print('sampler: trims applied')
