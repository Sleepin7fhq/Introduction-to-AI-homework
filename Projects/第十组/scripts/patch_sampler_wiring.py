# -*- coding: utf-8 -*-
"""把采样器接进：Song 携带 kit、播放/渲染前预解码、voices 优先采样。"""
import io
import re

ROOT = r'D:\AI\aihw\src'


def patch(path, pairs, must=True):
    p = ROOT + '\\' + path
    s = io.open(p, encoding='utf-8').read()
    for old, new in pairs:
        if old not in s:
            if must:
                raise SystemExit('NOT FOUND in %s: %s' % (path, old[:60]))
            continue
        s = s.replace(old, new, 1)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched', path)


# 1) bank: isPrepared
patch('audio/sampler.ts', [(
    "  isReady(): boolean {\n    return this.ready;\n  }",
    "  isReady(): boolean {\n    return this.ready;\n  }\n\n  /** 该上下文是否已经解码好素材 */\n  isPrepared(ctx: BaseAudioContext): boolean {\n    const m = this.decoded.get(ctx);\n    return !!m && m.size > 0;\n  }",
)])

# 2) Song 增加 soundKit
patch('music/types.ts', [(
    "  /** 电子乐流派名，如 House / Techno / Trap */\n  genre?: string;",
    "  /** 电子乐流派名，如 House / Techno / Trap */\n  genre?: string;\n  /** 采样套件（决定用哪组 one-shot 发声） */\n  soundKit?: string;",
)])

# 3) 生成时写入 soundKit
patch('music/generate.ts', [(
    "    swing: genre.id === 'trap' ? 0.12 : genre.id === 'dnb' ? 0.02 : 0.06,\n    matched: mood.matched,\n    genre: genre.name,",
    "    swing: genre.id === 'trap' ? 0.12 : genre.id === 'dnb' ? 0.02 : 0.06,\n    matched: mood.matched,\n    genre: genre.name,\n    soundKit: genre.sound?.kit,",
)])

# 4) styles: 每个风格加 kit 字段
patch('music/styles.ts', [(
    "  /** 低频重心：sub 的截止频率 */\n  subHz: number;",
    "  /** 低频重心：sub 的截止频率 */\n  subHz: number;\n  /** 采样套件 id（对应 src/audio/sampler.ts 的 KITS） */\n  kit: string;",
)])

# 5) voices: 优先采样
patch('music/voices.ts', [(
    "export function createVoice(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {\n  if (track.kind === 'drums') return createDrums(track, bus, reverb);",
    "export function createVoice(track: Track, bus: Tone.Gain, reverb: Tone.Reverb): Voice {\n  // 采样库就绪时优先用真实 one-shot；否则自动退回合成音色\n  const bank = getBank();\n  const ctx = Tone.getContext().rawContext as unknown as BaseAudioContext;\n  if (bank.isReady() && bank.isPrepared(ctx)) {\n    return createSampleVoice(track, bus);\n  }\n  if (track.kind === 'drums') return createDrums(track, bus, reverb);",
)])

patch('music/voices.ts', [(
    "import * as Tone from 'tone';\nimport type { Track } from './types';",
    "import * as Tone from 'tone';\nimport type { Track } from './types';\nimport { createSampleVoice, getBank } from '../audio/sampler';",
)])

# 6) 播放器：setSong 时设 kit，play 前解码
patch('music/engine.ts', [(
    "  setSong(song: Song) {\n    const firstLoad = this.song === null;",
    "  setSong(song: Song) {\n    setActiveKit(song.soundKit as never);\n    const firstLoad = this.song === null;",
)])

patch('music/engine.ts', [(
    "  async play() {\n    if (!this.song) return;\n    await this.ensureAudio();",
    "  async play() {\n    if (!this.song) return;\n    await this.ensureAudio();\n    // 采样库：先加载并解码到当前实时上下文（失败则自动退回合成）\n    await ensureSamplesLoaded();\n    await getBank().prepare(Tone.getContext().rawContext as unknown as BaseAudioContext);",
)])

patch('music/engine.ts', [(
    "import * as Tone from 'tone';\nimport type { Song } from './types';",
    "import * as Tone from 'tone';\nimport type { Song } from './types';\nimport { ensureSamplesLoaded, getBank, setActiveKit } from '../audio/sampler';",
)])

# 7) 离线渲染：同样设 kit + 在离线上下文里解码
patch('music/render.ts', [(
    "  const rendered = await Tone.Offline(\n    async () => {",
    "  setActiveKit(song.soundKit as never);\n\n  const rendered = await Tone.Offline(\n    async () => {\n      await ensureSamplesLoaded();\n      await getBank().prepare(Tone.getContext().rawContext as unknown as BaseAudioContext);",
)])

patch('music/render.ts', [(
    "import { createVoice } from './engine';",
    "import { createVoice } from './engine';\nimport { ensureSamplesLoaded, getBank, setActiveKit } from '../audio/sampler';",
)])

print('all wired')
