# -*- coding: utf-8 -*-
"""让离线渲染钩子回传采样库状态，便于验证"真的用了采样"。"""
import io

P = r'D:\AI\aihw\src\App.tsx'
s = io.open(P, encoding='utf-8').read()

old_import = "import { renderSongToWav } from './music/render';"
new_import = "import { renderSongToWav } from './music/render';\nimport { getBank } from './audio/sampler';"
assert old_import in s
s = s.replace(old_import, new_import, 1)

old_ret = "      return { name, bytes: blob.size, bars, tempo: res.song.tempo, tracks: res.song.tracks.length };"
new_ret = ("      const bank = getBank();\n"
           "      return {\n"
           "        name,\n"
           "        bytes: blob.size,\n"
           "        bars,\n"
           "        tempo: res.song.tempo,\n"
           "        tracks: res.song.tracks.length,\n"
           "        kit: res.song.soundKit ?? null,\n"
           "        samplesReady: bank.isReady(),\n"
           "        sampleCount: bank.manifest?.count ?? 0,\n"
           "      };")
assert old_ret in s
s = s.replace(old_ret, new_ret, 1)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('App hook now reports sample status')
