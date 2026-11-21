# 2.2 采样库与采样器

**日期**：2026-11-21　**目标**：不再靠振荡器"合成"鼓组，改用真实 one-shot 采样发声。

---

## 一句话结论

**52 个 one-shot 采样已经真实接入发声链路**（`samplesReady: true, sampleCount: 52`），
四段试听 WAV 全部由采样触发渲染，渲染耗时从 14–17 秒降到 **1.2–3.0 秒**——
因为不再为每个音符现场搭一套合成器图。

---

## 关于"下载合法素材"——必须如实说明

我尝试了四类来源，**没有拿到可用且合规的下载**，证据如下：

| 来源 | 结果 | 证据 |
|---|---|---|
| MusicRadar SampleRadar | ❌ 不可用 | `cdn.musicradar.com` TLS 握手失败（`SSL: UNEXPECTED_EOF_WHILE_READING`） |
| Freesound | ⚠️ 只有 MP3 预览 | `cdn.freesound.org` 返回 200，但只有 128kbps 预览；原始文件需 API Key。按要求不采用 |
| archive.org | ⚠️ 有 CC0 条目但不可用 | 命中的 CC0 鼓组 `elorwav-drum-kit` 描述写着「Sharing this with your name is **strictly prohibited**」，与 CC0 标记冲突；其余命中是完整歌曲而非 one-shot |
| Wikimedia Commons | ❌ 0 命中 | 5 组关键词只返回 1 个候选，且非 CC0/PD |

**因此改用自研 DSP 合成采样库**：在 `scripts/build_samples.py` 里用 numpy 逐样本生成
（pitch envelope、共振峰、分层噪声、软削波），输出 48kHz/16bit 立体声 WAV。

- **版权**：100% 项目自有，CC0-1.0，可商用、可再分发、无需署名；
- **质量**：不是"振荡器音色"，而是预渲染的 one-shot（含瞬态、尾巴、饱和），
  这是它比 `Tone.MonoSynth` 好听的根本原因；
- **代价**：不是"别人录的真实鼓"，是"我们自己合成的采样"。这一点不含糊。

---

## 采样库规模

| 分类 | 数量 | 代表文件 |
|---|---|---|
| drums/kick | 4 | `kick_hard.wav`（70% 能量在 20–80Hz） |
| drums/snare | 4 | `snare_crack.wav`（presence 40%） |
| drums/clap | 2 | `clap_wide.wav` |
| drums/hihat | 4 | `hat_closed / hat_open / hat_tick / hat_pedal` |
| drums/cymbal | 2 | `crash / ride` |
| bass/sub | 3 | `sub_C1 / F1 / G1` |
| bass/reese | 2 | `reese_C1 / F1` |
| bass/hardstyle | 2 | `hard_bass_C1 / F1` |
| synth/lead | 5 | `lead_supersaw / lead_siren / lead_hard …` |
| synth/pluck | 2 | |
| synth/pad | 3 | |
| vocal/chop | 7 | `chop_a/e/i/o/u/hey/woo`（带 8ms 辅音爆破） |
| vocal/fx | 3 | breath / scream / laugh |
| transitions/riser | 3 | `riser_4s / 2s / noise_2s` |
| transitions/impact | 2 | `boom / hit` |
| meme/sfx | 4 | laser / airhorn / boing / ding |

**合计 52 个，9.1 MB，48kHz / 16bit / 立体声**。
清单：`public/samples/manifest.json`（含类型、根音、时长、许可证、商用与署名要求）。

---

## 接入方式（不是列表，是真的发声）

- 采样器：`src/audio/sampler.ts`，用 **AudioBufferSourceNode** 触发；
- 每套 kit 绑定 7 类音色（kick/snare/clap/hat/cymbal/bass/lead/pad/chop）；
- MIDI 音高 → `playbackRate = 2^((pitch-root)/12)`，实现变调；
- 支持力度、声像、切片起点、复音叠加、单轨音量；
- 采样未加载/解码失败 → **自动退回 2.1 的合成音色**（`file://` 直接打开时就是这条路径）。

---

## 怎么自己验证

```powershell
# 1) 看清单
type public\samples\manifest.json

# 2) 浏览器里确认已加载
#    打开 http://127.0.0.1:5173/ 后，控制台执行：
#    await fetch('./samples/manifest.json').then(r=>r.json()).then(m=>m.count)  // 52

# 3) 重新生成四段样本
node scripts\render-samples.mjs 9240 音乐风格升级\样本\samples-2.2 音乐风格升级\presets-samples.json
```
