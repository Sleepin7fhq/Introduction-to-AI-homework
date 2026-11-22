"""导出：music21 写 MIDI → 修正通道/音色 → FluidSynth 渲染 WAV。"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import mido
from music21 import key as m21key
from music21 import meter, note, stream, tempo

from .config import FLUIDSYNTH, GAIN, PROGRAMS, SAMPLE_RATE, SOUNDFONT
from .harmony import Harmonization
from .io import Melody, NoteEvent
from .reverb import add_reverb


@dataclass
class ExtraTrack:
    """额外轨道：副旋律、鼓等。"""
    name: str
    notes: list[NoteEvent]
    channel: int
    program: int = 0
    is_drum: bool = False
    gain: float = 1.0
    instrument: str | None = None


def _add_notes(part: stream.Part, events: list[NoteEvent]) -> None:
    for ev in events:
        n = note.Note(ev.pitch, quarterLength=max(ev.dur, 0.05))
        n.volume.velocity = max(1, min(127, ev.velocity))
        part.insert(ev.start, n)


def export_midi(melody: Melody, harmony: Harmonization,
                chord_notes: list[NoteEvent], bass_notes: list[NoteEvent],
                path: str | Path, extras: list[ExtraTrack] | None = None,
                programs: tuple[int, int, int] | None = None,
                volumes: dict[int, float] | None = None,
                expressions: dict[int, list[tuple[float, int]]] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    score = stream.Score()
    melody_part = stream.Part()
    melody_part.partName = "Melody"
    melody_part.insert(0, tempo.MetronomeMark(number=melody.bpm))
    melody_part.insert(0, meter.TimeSignature(f"{melody.time_sig[0]}/{melody.time_sig[1]}"))
    melody_part.insert(0, m21key.Key(harmony.key.m21.tonic.name, harmony.key.m21.mode))
    _add_notes(melody_part, melody.notes)

    chord_part = stream.Part()
    chord_part.partName = "Chords"
    _add_notes(chord_part, chord_notes)

    bass_part = stream.Part()
    bass_part.partName = "Bass"
    _add_notes(bass_part, bass_notes)

    parts = [melody_part, chord_part, bass_part]
    prim = programs or (PROGRAMS.get(0, 0), PROGRAMS.get(1, 0), PROGRAMS.get(2, 32))
    specs = [(0, prim[0], False), (1, prim[1], False), (2, prim[2], False)]

    for extra in extras or []:
        part = stream.Part()
        part.partName = extra.name
        _add_notes(part, extra.notes)
        parts.append(part)
        specs.append((extra.channel, extra.program, extra.is_drum))

    for part in parts:
        score.insert(0, part)

    score.write("midi", fp=str(path))
    _assign_channels(path, specs, volumes or {})
    if expressions:
        _add_expression_track(path, expressions)
    return path


def _add_expression_track(path: Path,
                          expressions: dict[int, list[tuple[float, int]]]) -> None:
    """把各通道的 CC11 表情曲线写成一条独立控制轨。"""
    mid = mido.MidiFile(str(path))
    control = mido.MidiTrack()
    events: list[tuple[int, mido.Message]] = []
    for channel, curve in expressions.items():
        for beat, value in curve:
            tick = max(0, int(round(beat * mid.ticks_per_beat)))
            events.append((tick, mido.Message(
                "control_change", channel=channel, control=11,
                value=max(1, min(127, int(value))), time=0)))
    events.sort(key=lambda item: item[0])
    last = 0
    for tick, message in events:
        message.time = max(0, tick - last)
        last = tick
        control.append(message)
    mid.tracks.append(control)
    mid.save(str(path))


def _assign_channels(path: Path, specs: list[tuple[int, int, bool]],
                     volumes: dict[int, float]) -> None:
    """按轨分配通道、GM 音色与 CC7 音量；鼓轨（通道 9）不发 program change。"""
    mid = mido.MidiFile(str(path))
    for index in range(1, len(mid.tracks)):
        if index - 1 >= len(specs):
            continue
        channel, program, is_drum = specs[index - 1]
        track = mid.tracks[index]
        messages = []
        if channel in volumes:
            value = max(0, min(127, int(round(127 * volumes[channel]))))
            messages.append(mido.Message("control_change", channel=channel,
                                         control=7, value=value, time=0))
        if not is_drum and channel != 9:
            messages.append(mido.Message("program_change", channel=channel,
                                         program=program, time=0))
        for msg in track:
            if not msg.is_meta and hasattr(msg, "channel"):
                msg = msg.copy(channel=channel)
            messages.append(msg)
        track[:] = messages
    mid.save(str(path))


def export_stems(midi_path: str | Path, outdir: str | Path,
                 soundfont: Path = SOUNDFONT) -> list[Path]:
    """把每个非空轨道单独导出成 MIDI + 干声 WAV，方便在 DAW 里分轨混音。"""
    midi_path = Path(midi_path)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    mid = mido.MidiFile(str(midi_path))
    stems: list[Path] = []
    used: set[str] = set()
    role_names = {0: "Melody", 1: "Chords", 2: "Bass", 3: "Counter",
                  4: "Layer1", 5: "Layer2", 9: "Drums"}
    for index, track in enumerate(mid.tracks[1:], start=1):
        if not any(msg.type == "note_on" for msg in track):
            continue
        channel = next((msg.channel for msg in track
                        if not msg.is_meta and hasattr(msg, "channel")), None)
        name = role_names.get(channel, "track")
        for msg in track:
            if msg.is_meta and msg.type == "track_name" and msg.name:
                name = msg.name
                break
        safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name).strip("_")
        safe = safe or f"track{index}"
        while safe in used:
            safe += "_2"
        used.add(safe)

        stem = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        stem.tracks.append(mid.tracks[0])
        stem.tracks.append(track)
        stem_midi = outdir / f"{midi_path.stem}_{safe}.mid"
        stem.save(stem_midi)
        render_wav(stem_midi, stem_midi.with_suffix(".wav"), soundfont=soundfont)
        stems.append(stem_midi.with_suffix(".wav"))
    return stems


def render_wav(midi_path: str | Path, wav_path: str | Path,
               soundfont: Path = SOUNDFONT, gain: float = GAIN,
               reverb: str = "off", reverb_mix: float | None = None,
               reverb_engine: str = "ir", ir_path: str | Path | None = None) -> Path:
    midi_path, wav_path = Path(midi_path), Path(wav_path)
    if not FLUIDSYNTH.exists():
        raise FileNotFoundError(f"找不到 fluidsynth: {FLUIDSYNTH}")
    if not Path(soundfont).exists():
        raise FileNotFoundError(f"找不到 SoundFont: {soundfont}")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    # 注意：FluidSynth 2.6 要求 -F 出现在 soundfont 之前
    cmd = [str(FLUIDSYNTH), "-ni", "-g", f"{gain}", "-r", str(SAMPLE_RATE),
           "-F", str(wav_path), str(soundfont), str(midi_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not wav_path.exists():
        raise RuntimeError(
            "FluidSynth 渲染失败\n命令: " + " ".join(cmd)
            + "\nstdout: " + result.stdout[-800:]
            + "\nstderr: " + result.stderr[-800:]
        )
    _normalize_wav(wav_path)
    add_reverb(wav_path, preset=reverb, mix=reverb_mix, engine=reverb_engine,
               ir_path=ir_path)
    return wav_path


def _normalize_wav(path: Path, target: float = 0.9) -> None:
    """FluidSynth 的 -g 0.8 输出偏小，这里统一峰值归一化到 -1 dB 左右。"""
    import wave

    import numpy as np

    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        data = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    samples = data.astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 1e-4:
        samples = samples * (target / peak)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def write_chart(path: str | Path, harmony: Harmonization) -> Path:
    path = Path(path)
    lines = [f"Key: {harmony.key.name}", "", harmony.chart_text()]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
