"""命令行入口：python -m route_a.cli 输入.mid --style block --wav 输出.wav"""

from __future__ import annotations

import argparse
from pathlib import Path

from music21 import key as m21key

from .analysis import KeyInfo, detect_key
from .auto import suggest as auto_suggest
from .bass import add_passing_tones, choose as choose_bass_note
from .config import (BUNDLED_IRS, ENSEMBLES, IR_DIR, SOUNDFONT,
                     SOUNDFONT_ALIASES)
from .counter import make_counter
from .drums import PATTERNS as DRUM_PATTERNS, make_drums
from .dynamics import apply as apply_humanize
from .expression import build as build_expression
from .harmony import Harmonization, harmonize, try_modulate
from .instruments import INSTRUMENTS, parse_spec, profile_for
from .io import Melody, NoteEvent, describe_parts, load_melody
from .mixer import BALANCE_LABELS, volumes_for
from .render import ExtraTrack, export_midi, export_stems, render_wav, write_chart
from .texture import STYLE_DESC, STYLES, make_texture
from .variation import add_phrase_fills, avoid_melody
from .voicing import choose_bass, count_parallels, voice

SUPPORTED = {".mid", ".midi", ".xml", ".musicxml"}
BUSY_STYLES = {"alberti", "arp16", "scale", "sync", "pop", "stride", "march", "guitar", "bossa"}


def parse_key(text: str) -> m21key.Key:
    raw = text.strip()
    low = raw.lower()
    if low.endswith("minor"):
        return m21key.Key(raw.split()[0], "minor")
    if low.endswith("major"):
        return m21key.Key(raw.split()[0], "major")
    if raw.endswith("m") and len(raw) > 1:
        return m21key.Key(raw[:-1], "minor")
    return m21key.Key(raw, "major")


def arrange(melody: Melody, key_info: KeyInfo, style: str = "block",
            chords_per_bar: int = 1, phrase_bars: int = 4,
            modulate: bool = True, simple: bool = False):
    harmony = harmonize(melody, key_info, chords_per_bar=chords_per_bar,
                        phrase_bars=phrase_bars, simple=simple)
    if modulate:
        modulated = try_modulate(melody, key_info, harmony,
                                 phrase_bars=phrase_bars, simple=simple)
        if modulated is not None:
            harmony = modulated
    chord_notes = []
    bass_notes = []
    voicings: list[tuple[int, ...]] = []
    prev_voicing = None
    parallels = 0

    choices: list[tuple[int, str]] = []
    prev_bass = None
    for index, slot in enumerate(harmony.slots):
        assert slot.chord is not None
        next_chord = harmony.slots[index + 1].chord if index + 1 < len(harmony.slots) else None
        pitch, label = choose_bass_note(slot.chord, prev_bass, next_chord,
                                        final=index == len(harmony.slots) - 1)
        choices.append((pitch, label))
        prev_bass = pitch
    inversions = sum(1 for _, label in choices if label != "root")

    for slot, (bass, _label) in zip(harmony.slots, choices):
        assert slot.chord is not None
        in_slot = [n.pitch for n in melody.notes if n.end > slot.start and n.start < slot.end]
        floor = min(in_slot) if in_slot else None
        center = 58.0 if not in_slot else max(50.0, min(66.0, sum(in_slot) / len(in_slot) - 12))
        voicing = voice(slot.chord, prev_voicing, center=center, melody_floor=floor)
        if prev_voicing:
            fifths, octaves = count_parallels(prev_voicing, voicing)
            parallels += fifths + octaves
        velocity = 64 + (4 if slot.index == 0 else 0)
        c_events, b_events = make_texture(style, slot, voicing, bass, velocity,
                                          beats_per_bar=melody.beats_per_bar,
                                          key_pcs=harmony.key.pcs)
        chord_notes.extend(c_events)
        bass_notes.extend(b_events)
        voicings.append(voicing)
        prev_voicing = voicing

    bass_notes, passing = add_passing_tones(bass_notes, melody, melody.beats_per_bar)
    harmony.stats["inversions"] = float(inversions)
    harmony.stats["passing_tones"] = float(passing)
    return harmony, chord_notes, bass_notes, voicings, parallels


_LAYER_ROLE = {
    "pad": "sustain", "block": "sustain",
    "arpeggio": "move", "arp16": "move", "guitar": "move",
    "scale": "move", "alberti": "move",
    "sync": "rhythm", "pop": "rhythm", "stride": "rhythm",
    "march": "rhythm", "bossa": "rhythm",
}
_LAYER_BAND = {"sustain": (43, 55), "move": (58, 70), "rhythm": (52, 64)}


def _layer_role(style: str) -> str:
    return _LAYER_ROLE.get(style, "move")


def _tone_pcs(chord, role: str) -> list[int]:
    root = chord.root_pc
    pcs = set(chord.pcs)
    third = (root + 3) % 12 if (root + 3) % 12 in pcs else (
        (root + 4) % 12 if (root + 4) % 12 in pcs else root)
    fifth = (root + 7) % 12 if (root + 7) % 12 in pcs else (
        (root + 6) % 12 if (root + 6) % 12 in pcs else root)
    seventh = (root + 10) % 12 if (root + 10) % 12 in pcs else (
        (root + 11) % 12 if (root + 11) % 12 in pcs else fifth)
    if role == "sustain":
        return [root, fifth]
    if role == "rhythm":
        return [root, third]
    return [third, seventh] if seventh != third else [third, fifth]


def _pick_in_band(pc: int, lo: int, hi: int, target: float) -> int | None:
    options = [p for p in range(lo, hi + 1) if p % 12 == pc]
    if not options:
        return None
    return min(options, key=lambda p: abs(p - target))


def _clashes(pitch: int, start: float, end: float, melody: Melody) -> bool:
    for note in melody.notes:
        if note.start < end - 1e-6 and note.end > start + 1e-6:
            # 同度/小二度才算撞；八度重复是正常配器手法
            if abs(pitch - note.pitch) <= 1:
                return True
    return False


def make_layer_tracks(melody: Melody, harmony: Harmonization,
                      voicings: list[tuple[int, ...]], styles: list[str],
                      octave: int = 0, max_layers: int = 2,
                      constrain: bool = True,
                      primary_style: str = "block",
                      instruments: list[str | None] | None = None,
                      fallback_program: int | None = None) -> list[ExtraTrack]:
    """把额外织体做成独立轨道，并按“乐器档案 + 配器规则”约束。

    * 乐器音域：越界自动折叠；长笛/小号/贝斯等单音乐器只取一个音；
    * 发声方式：弦乐/人声把流动音型改成持续音，吉他/钢琴保持拨奏；
    * 音区分工、和弦音子集、旋律避让、节奏互补同前。
    """
    tracks: list[ExtraTrack] = []
    primary_role = _layer_role(primary_style)
    instr_list = list(instruments or [])

    for i, layer_style in enumerate(styles[:max_layers]):
        explicit = instr_list[i] if i < len(instr_list) else None
        profile = profile_for(layer_style, explicit)
        role = _layer_role(layer_style)

        band_lo = max(_LAYER_BAND[role][0], profile.low)
        band_hi = min(_LAYER_BAND[role][1], profile.high)
        if band_hi - band_lo < 6:
            band_lo = max(profile.low, band_hi - 12)
        if band_hi - band_lo < 6:
            band_hi = min(profile.high, band_lo + 12)
        max_notes = min(2, profile.max_notes)

        notes: list[NoteEvent] = []
        prev = (band_lo + band_hi) / 2

        for slot in harmony.slots:
            if slot.chord is None:
                continue
            in_slot = [n.pitch for n in melody.notes
                       if n.end > slot.start and n.start < slot.end]
            lo, hi = band_lo, band_hi
            if in_slot and constrain:
                floor = min(in_slot)
                hi = min(hi, floor - 3)
                if hi - lo < 6:
                    hi = min(band_hi, lo + 6)

            picked = []
            for pc in _tone_pcs(slot.chord, role)[:max_notes]:
                pitch = _pick_in_band(pc, lo, hi, prev)
                if pitch is None:
                    pitch = _pick_in_band(pc, profile.low, profile.high, prev)
                if pitch is not None and pitch not in picked:
                    picked.append(pitch)
                    prev = pitch
            if not picked:
                continue
            voicing = tuple(sorted(picked))

            if profile.sustain and role == "move":
                events = [NoteEvent(p, slot.start, max(0.8, slot.length * 0.9), 52)
                          for p in voicing]
            else:
                events, _ = make_texture(layer_style, slot, voicing,
                                         bass=36 + slot.chord.root_pc,
                                         velocity=56 if explicit else 52,
                                         beats_per_bar=melody.beats_per_bar,
                                         key_pcs=harmony.key.pcs)
            for ev in events:
                pitch = ev.pitch + octave
                while pitch < profile.low:
                    pitch += 12
                while pitch > profile.high:
                    pitch -= 12
                if not (profile.low <= pitch <= profile.high):
                    continue
                if constrain and _clashes(pitch, ev.start, ev.end, melody):
                    for delta in (-12, 12, -24, 24):
                        candidate = pitch + delta
                        if (profile.low <= candidate <= profile.high
                                and not _clashes(candidate, ev.start, ev.end, melody)):
                            pitch = candidate
                            break
                    else:
                        continue
                dur = ev.dur
                if profile.pluck:
                    dur = min(dur, 0.45)
                elif profile.sustain and role == "rhythm":
                    dur = max(dur, slot.length * 0.6)
                velocity = ev.velocity * profile.velocity - 4 - i * 3
                notes.append(NoteEvent(pitch, ev.start, dur,
                                       max(1, min(127, int(round(velocity))))))

        if profile.density < 0.75 and role == "rhythm":
            notes = notes[::2]
        if constrain and primary_role == "move" and role == "move":
            # 两层都在跑：叠层隔一个音留一个，保留音型轮廓但不抢拍
            notes = notes[::2]
        elif constrain and primary_role == "rhythm" and role == "rhythm":
            notes = [n for n in notes if int(round(n.start)) % 2 == 0]

        if explicit:
            program = profile.program
        elif fallback_program is not None:
            program = fallback_program
        else:
            program = profile.program
        name = f"Layer {layer_style}" + (f":{explicit}" if explicit else "")
        tracks.append(ExtraTrack(name, notes, channel=4 + i, program=program,
                                 gain=profile.gain, instrument=profile.key))
    return tracks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="route-a",
        description="路线 A：music21 + 规则/DP + FluidSynth，给旋律配伴奏。",
    )
    parser.add_argument("input", help="输入旋律：.mid / .midi / .xml / .musicxml")
    parser.add_argument("-o", "--output", default=None, help="输出 MIDI 路径")
    parser.add_argument("--wav", default=None, help="输出 WAV 路径；不传则按默认名生成")
    parser.add_argument("--no-wav", action="store_true", help="只出 MIDI，不渲染 WAV")
    parser.add_argument("--style", default="block", choices=STYLES,
                        help="伴奏织体：" + " / ".join(STYLES))
    parser.add_argument("--chords-per-bar", type=int, default=1, choices=(1, 2),
                        help="每小节换几个和弦")
    parser.add_argument("--phrase-bars", type=int, default=4, help="乐句长度（小节）")
    parser.add_argument("--no-modulate", action="store_true",
                        help="关闭尾部乐句的自动转调")
    parser.add_argument("--harmony", default="rich", choices=("rich", "simple"),
                        help="和声模式：rich（副属/V7）/ simple（只留 I ii IV V vi）")
    parser.add_argument("--ensemble", default="piano", choices=tuple(ENSEMBLES),
                        help="音色组：piano / strings / band")
    parser.add_argument("--humanize", default="off", choices=("off", "light", "strong"),
                        help="乐句力度曲线 + 微时序")
    parser.add_argument("--expression", default="light", choices=("off", "light", "strong"),
                        help="随旋律起伏的 CC11 表情自动化")
    parser.add_argument("--balance", default="orchestral",
                        choices=("orchestral", "pop", "flat"),
                        help="轨道音量平衡：orchestral / pop / flat")
    parser.add_argument("--drums", action="store_true",
                        help="增加一轨 GM 鼓（MIDI 通道 10）")
    parser.add_argument("--drum-pattern", default="auto", choices=DRUM_PATTERNS,
                        help="鼓型：auto/pop/ballad/bossa/waltz")
    parser.add_argument("--counter", action="store_true",
                        help="增加一轨副旋律（MIDI 通道 4）")
    parser.add_argument("--layer", action="append", default=[], metavar="STYLE[:INSTR]",
                        help="额外叠一层，可写 pad:strings 指定乐器；最多两层")
    parser.add_argument("--layer-octave", type=int, default=0, choices=(-12, 0, 12),
                        help="叠加层的八度位移")
    parser.add_argument("--reverb", default="off",
                        choices=("off", "light", "medium", "hall"),
                        help="混响：off/light/medium/hall")
    parser.add_argument("--reverb-mix", type=float, default=None,
                        help="混响湿声比例 0–1，默认按档位")
    parser.add_argument("--reverb-engine", default="ir", choices=("ir", "freeverb"),
                        help="混响引擎：ir（合成脉冲）/ freeverb（Freeverb 算法）")
    parser.add_argument("--soundfont", default=None,
                        help="自定义 SF2/SF3 路径，或 fluid / musescore")
    parser.add_argument("--ir", default=None,
                        help="厅堂 IR：hall / opera / church，或 WAV 路径")
    parser.add_argument("--stems", action="store_true",
                        help="额外导出每个轨道的干声 WAV（分轨混音）")
    parser.add_argument("--no-variation", action="store_true",
                        help="关闭乐句末尾加花")
    parser.add_argument("--no-avoid", action="store_true",
                        help="关闭伴奏避让旋律（默认开启）")
    parser.add_argument("--auto", action="store_true",
                        help="根据旋律自动选择织体/和声/音色/叠层/混响等全部参数")
    parser.add_argument("--key", default="auto", help="指定调，如 'C'、'Am'、'G major'")
    parser.add_argument("--track", type=int, default=None, help="多轨 MIDI 指定 part 序号")
    parser.add_argument("--list-parts", action="store_true",
                        help="只列出文件里的 part（含音数、中位音高），用来决定 --track")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.input)
    if not source.exists():
        print(f"找不到输入文件: {source}")
        return 2

    suffix = source.suffix.lower()
    if suffix not in SUPPORTED:
        print(f"不支持的输入格式: {suffix or '(无扩展名)'}")
        if suffix in (".txt", ".csv"):
            print("  .txt 是本工具输出的和弦谱，不是旋律输入。")
            print("  请改拖同名的 .mid 文件（例如 ode_to_joy - 副本.mid）。")
        print("  支持: .mid / .midi / .xml / .musicxml")
        return 2

    if args.list_parts:
        try:
            parts = describe_parts(source)
        except Exception as exc:  # noqa: BLE001
            print(f"读取失败: {source.name}\n  {exc}")
            return 2
        for part in parts:
            print(f"[{part['index']}] {part['name'] or '(未命名)':20s} "
                  f"notes={part['notes']:4d}  median_pitch={part['median']:.0f}")
        return 0

    try:
        melody = load_melody(source, track=args.track)
    except Exception as exc:  # noqa: BLE001
        print(f"读取失败: {source.name}")
        print(f"  {exc}")
        return 2
    if args.style == "waltz" and abs(melody.beats_per_bar - 3.0) > 1e-6:
        print("提示：waltz 只适用于 3/4 拍，本首已自动退化为 block。")
    if args.key and args.key.lower() != "auto":
        key_info = KeyInfo(m21=parse_key(args.key), confidence=1.0, alternatives=[])
    else:
        key_info = detect_key(melody)
        if key_info.confidence < 0.55:
            hint = " / ".join(key_info.alternatives[:2])
            print(f"提示: 调性置信度较低（{key_info.confidence:.2f}），"
                  f"候选: {hint or '无'}；可用 --key 指定")

    if args.auto:
        plan = auto_suggest(melody, key_info)
        args.style = plan.style
        args.chords_per_bar = plan.chords_per_bar
        args.phrase_bars = plan.phrase_bars
        args.harmony = plan.harmony
        args.ensemble = plan.ensemble
        args.humanize = plan.humanize
        args.balance = plan.balance
        args.reverb = plan.reverb
        args.reverb_engine = plan.reverb_engine
        args.counter = plan.counter
        args.drums = plan.drums
        args.drum_pattern = plan.drum_pattern
        args.ir = plan.ir
        args.soundfont = plan.soundfont
        args.layer = [f"{style}:{instr}" if instr else style
                      for style, instr in plan.layers]
        args.layer_octave = 0
        print("自动配置:")
        for reason in plan.reasons:
            print(f"  - {reason}")
        print(f"  参数: {plan.style} / {plan.harmony} / {plan.ensemble} / "
              f"reverb {plan.reverb} / ir {plan.ir} / sf {plan.soundfont} / "
              f"layer {args.layer}")

    harmony, chord_notes, bass_notes, voicings, parallels = arrange(
        melody, key_info, style=args.style,
        chords_per_bar=args.chords_per_bar, phrase_bars=args.phrase_bars,
        modulate=not args.no_modulate, simple=args.harmony == "simple")

    try:
        layer_specs = [parse_spec(spec, STYLES) for spec in args.layer]
    except ValueError as exc:
        print(f"叠层参数错误: {exc}")
        print("  写法：--layer pad:strings，或只写 --layer pad")
        return 2
    layer_styles = [style for style, _ in layer_specs]
    layer_instruments = [instr for _, instr in layer_specs]
    ensemble = ENSEMBLES[args.ensemble]

    extras: list[ExtraTrack] = []
    if args.counter:
        counter_notes = make_counter(melody, harmony, phrase_bars=args.phrase_bars)
        extras.append(ExtraTrack("Counter", counter_notes, channel=3))
    if args.drums:
        drum_notes = make_drums(melody, harmony, pattern=args.drum_pattern, style=args.style)
        extras.append(ExtraTrack("Drums", drum_notes, channel=9, is_drum=True))
    if layer_styles:
        extras.extend(make_layer_tracks(melody, harmony, voicings, layer_styles,
                                        octave=args.layer_octave,
                                        primary_style=args.style,
                                        instruments=layer_instruments,
                                        fallback_program=ensemble["layer"]))

    for extra in extras:
        if extra.name == "Counter":
            extra.program = ensemble["counter"]

    if not args.no_avoid:
        chord_notes = avoid_melody(chord_notes, melody)
        bass_notes = avoid_melody(bass_notes, melody)
        for extra in extras:
            if not extra.is_drum:
                extra.notes = avoid_melody(extra.notes, melody)
    if not args.no_variation:
        chord_notes = add_phrase_fills(chord_notes, melody, harmony,
                                       phrase_bars=args.phrase_bars, style=args.style)

    if args.humanize != "off":
        chord_notes = apply_humanize(chord_notes, melody, melody.bpm,
                                     phrase_bars=args.phrase_bars, level=args.humanize)
        bass_notes = apply_humanize(bass_notes, melody, melody.bpm,
                                    phrase_bars=args.phrase_bars, level=args.humanize)
        for extra in extras:
            extra.notes = apply_humanize(extra.notes, melody, melody.bpm,
                                         phrase_bars=args.phrase_bars,
                                         level=args.humanize)

    out_midi = Path(args.output) if args.output else source.with_name(source.stem + "_accomp.mid")
    out_wav = None if args.no_wav else (
        Path(args.wav) if args.wav else out_midi.with_suffix(".wav"))

    volumes = volumes_for(args.balance, counter=args.counter,
                          layers=len(layer_styles), drums=args.drums)
    for extra in extras:
        if extra.name.startswith("Layer"):
            volumes[extra.channel] = min(1.0, volumes.get(extra.channel, 1.0) * extra.gain)
    expressions = build_expression(melody, extras, args.phrase_bars, args.expression)
    export_midi(melody, harmony, chord_notes, bass_notes, out_midi, extras=extras,
                programs=ensemble["primary"], volumes=volumes,
                expressions=expressions)
    chart_path = out_midi.with_name(out_midi.stem + "_chords.txt")
    write_chart(chart_path, harmony)
    if out_wav is not None:
        soundfont = SOUNDFONT
        if args.soundfont:
            if args.soundfont in SOUNDFONT_ALIASES:
                soundfont = SOUNDFONT_ALIASES[args.soundfont]
            else:
                soundfont = Path(args.soundfont)
            if not soundfont.exists():
                print(f"找不到音色库: {soundfont}")
                return 2
        ir_path = None
        if args.ir:
            if args.ir in BUNDLED_IRS:
                ir_path = IR_DIR / BUNDLED_IRS[args.ir]
            else:
                ir_path = Path(args.ir)
            if not ir_path.exists():
                print(f"找不到脉冲响应: {ir_path}")
                return 2
            if args.reverb == "off":
                args.reverb = "medium"
        render_wav(out_midi, out_wav, soundfont=soundfont,
                   reverb=args.reverb, reverb_mix=args.reverb_mix,
                   reverb_engine=args.reverb_engine, ir_path=ir_path)
        if args.stems:
            stem_dir = out_midi.parent / f"{out_midi.stem}_stems"
            stems = export_stems(out_midi, stem_dir, soundfont=soundfont)
            print(f"分轨    : {stem_dir}（{len(stems)} 轨干声）")

    final = harmony.slots[-1].chord
    print(f"输入    : {source}")
    print(f"调性    : {key_info.name}  (相关度 {key_info.confidence:.3f})")
    print(f"拍号/速度: {melody.time_sig[0]}/{melody.time_sig[1]}, {melody.bpm:g} BPM, "
          f"{melody.bars} 小节{'，含弱起' if melody.pickup_beats else ''}")
    print(f"和弦    : {harmony.chart_text()}")
    if harmony.modulation:
        print(f"转调    : {harmony.modulation.text}")
    print(f"和声    : V7 {int(harmony.stats.get('v7', 0))} 处，"
          f"副属 {int(harmony.stats.get('secondary', 0))} 处")
    print(f"低音    : 转位 {int(harmony.stats.get('inversions', 0))} 处，"
          f"经过音 {int(harmony.stats.get('passing_tones', 0))} 个")
    skeleton = getattr(melody, "skeleton", None)
    if skeleton is not None and getattr(skeleton, "chords", None):
        if getattr(skeleton, "polyphonic", False):
            total = matched = 0
            for slot in harmony.slots:
                if slot.chord is None:
                    continue
                root = skeleton.root_at(slot.start)
                if root is None:
                    continue
                total += 1
                matched += int(root == slot.chord.root_pc)
            rate = matched / max(1, total)
            print(f"骨架    : {len(skeleton.chords)} 段，根音吻合 {rate:.0%}")
        else:
            print("骨架    : 单声部输入，跳过和声骨架")
    print(f"模式    : 和声 {args.harmony} / 音色 {ensemble['label']} / "
          f"humanize {args.humanize} / 平衡 {BALANCE_LABELS[args.balance]}")
    print(f"表情    : {args.expression}（CC11 随旋律起伏）")
    print(f"织体    : {args.style}，每小节 {args.chords_per_bar} 个和弦")
    track_names = ["旋律", "和弦", "低音"]
    if args.counter:
        track_names.append("副旋律")
    for layer in args.layer[:2]:
        track_names.append(f"叠层:{layer}")
    if args.drums:
        track_names.append("鼓")
    print(f"轨道    : {' / '.join(track_names)}"
          + (f"（鼓型 {args.drum_pattern}）" if args.drums else ""))
    if sum(1 for s in [args.style, *args.layer] if s in BUSY_STYLES) >= 2:
        print("提示    : 叠加了两种以上密集音型，容易浑浊；建议一密一疏（如 pad + arpeggio）。")
    if args.reverb != "off":
        print(f"混响    : {args.reverb} / {args.reverb_engine}"
              + (f"（wet {args.reverb_mix:.2f}）" if args.reverb_mix is not None else ""))
    if args.soundfont:
        print(f"音色库  : {args.soundfont}")
    if args.ir:
        print(f"厅堂    : {args.ir}")
    print(f"质量    : 强拍冲突 {harmony.stats['conflict_rate'] * 100:.1f}%，"
          f"平行五/八度 {parallels} 处，结尾 {final.symbol if final else '-'}")
    print(f"MIDI    : {out_midi}")
    print(f"和弦谱  : {chart_path}")
    if out_wav is not None:
        print(f"WAV     : {out_wav}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
