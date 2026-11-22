"""路线 A 的单元测试：python tests/test_route_a.py"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mido
from music21 import chord as m21chord
from music21 import note as m21note
from music21 import stream as m21stream

from route_a.analysis import detect_key
from route_a.auto import suggest as auto_suggest
from route_a.cli import arrange, make_layer_tracks
from route_a.counter import make_counter
from route_a.dynamics import apply as apply_humanize
from route_a.expression import build as build_expression
from route_a.drums import make_drums
from route_a.harmony import harmonize
from route_a.io import NoteEvent, load_melody
from route_a.io import _extract_line
from route_a.render import ExtraTrack, export_midi, export_stems, render_wav
from route_a.reverb import add_reverb
from route_a.texture import STYLES
from route_a.variation import add_phrase_fills, avoid_melody
from route_a.voicing import count_parallels

DATA = ROOT / "tests" / "data"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


class TestLoad(unittest.TestCase):
    def test_all_ten(self):
        for entry in MANIFEST:
            melody = load_melody(DATA / entry["file"])
            self.assertGreater(len(melody.notes), 8, entry["file"])
            self.assertEqual(f"{melody.time_sig[0]}/{melody.time_sig[1]}", entry["time_sig"])
            self.assertGreaterEqual(melody.bars, 2)

    def test_quantize(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        for note in melody.notes:
            self.assertAlmostEqual(note.start * 4, round(note.start * 4), places=6)


class TestAnalysis(unittest.TestCase):
    def test_key_accuracy(self):
        correct = 0
        for entry in MANIFEST:
            melody = load_melody(DATA / entry["file"])
            info = detect_key(melody)
            correct += info.name == entry["key"]
        self.assertGreaterEqual(correct, 10, f"调性只对了 {correct}/{len(MANIFEST)}")


class TestHarmony(unittest.TestCase):
    def test_final_is_tonic(self):
        for entry in MANIFEST:
            melody = load_melody(DATA / entry["file"])
            result = harmonize(melody, detect_key(melody))
            final = result.slots[-1].chord
            self.assertIsNotNone(final)
            self.assertEqual(final.degree, 1, entry["file"])

    def test_chart_shape(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        result = harmonize(melody, detect_key(melody))
        self.assertEqual(len(result.chart), melody.bars)
        self.assertEqual(len(result.slots), melody.bars)


class TestVoicingAndTexture(unittest.TestCase):
    def test_ranges_and_parallels(self):
        for entry in MANIFEST:
            melody = load_melody(DATA / entry["file"])
            _, _, _, voicings, parallels = arrange(
                melody, detect_key(melody), style="block")
            for voicing in voicings:
                self.assertGreaterEqual(min(voicing), 48)
                self.assertLessEqual(max(voicing), 79)
                self.assertLessEqual(len(voicing), 4)
                self.assertLessEqual(max(voicing) - min(voicing), 19)
            self.assertLessEqual(parallels, 2, entry["file"])

    def test_both_styles(self):
        melody = load_melody(DATA / "09_minor_original.mid")
        for style in STYLES:
            harmony, chords, bass, _, _ = arrange(
                melody, detect_key(melody), style=style)
            self.assertTrue(chords, style)
            self.assertTrue(bass, style)
            for note in chords + bass:
                self.assertTrue(36 <= note.pitch <= 96)
                self.assertGreater(note.dur, 0)

    def test_waltz_three_four(self):
        melody = load_melody(DATA / "07_waltz_pickup.mid")
        _, chords, bass, _, _ = arrange(melody, detect_key(melody), style="waltz")
        self.assertTrue(chords)
        self.assertTrue(bass)


class TestModulation(unittest.TestCase):
    def test_modulation_demo(self):
        melody = load_melody(DATA / "11_modulation_demo.mid")
        harmony, chords, bass, _, _ = arrange(
            melody, detect_key(melody), style="block")
        self.assertIsNotNone(harmony.modulation)
        self.assertEqual(harmony.modulation.target.name, "G major")
        self.assertEqual(harmony.slots[-1].chord.symbol, "G")
        self.assertTrue(chords)
        self.assertTrue(bass)


class TestRender(unittest.TestCase):
    def test_midi_channels_and_wav(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="block")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "t.mid"
            wav = Path(tmp) / "t.wav"
            export_midi(melody, harmony, chords, bass, midi)
            mid = mido.MidiFile(str(midi))
            channels = sorted({m.channel for t in mid.tracks for m in t
                               if not m.is_meta and hasattr(m, "channel")})
            self.assertEqual(channels, [0, 1, 2])
            programs = {(m.channel, m.program) for t in mid.tracks for m in t
                        if m.type == "program_change"}
            self.assertIn((2, 32), programs)

            render_wav(midi, wav)
            with wave.open(str(wav), "rb") as handle:
                seconds = handle.getnframes() / handle.getframerate()
            self.assertGreater(seconds, 5.0)
            self.assertGreater(wav.stat().st_size, 100_000)


class TestExtras(unittest.TestCase):
    def test_counter_no_clash(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        harmony, _, _, _, _ = arrange(melody, detect_key(melody), style="block")
        notes = make_counter(melody, harmony)
        self.assertTrue(notes)
        for note in notes:
            self.assertTrue(55 <= note.pitch <= 67)
            self.assertGreater(note.dur, 0)
        clashes = 0
        for note in notes:
            for m in melody.notes:
                if m.start < note.end and m.end > note.start:
                    if abs(note.pitch - m.pitch) % 12 in (0, 1, 11):
                        clashes += 1
        self.assertLessEqual(clashes, 2)

    def test_drums(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        harmony, _, _, _, _ = arrange(melody, detect_key(melody), style="pop")
        notes = make_drums(melody, harmony, style="pop")
        self.assertTrue(notes)
        for note in notes:
            self.assertTrue(35 <= note.pitch <= 59)
            self.assertGreater(note.dur, 0)

    def test_band_channels(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="pop")
        counter = make_counter(melody, harmony)
        drums = make_drums(melody, harmony, style="pop")
        extras = [ExtraTrack("Counter", counter, channel=3),
                  ExtraTrack("Drums", drums, channel=9, is_drum=True)]
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "band.mid"
            export_midi(melody, harmony, chords, bass, midi, extras=extras)
            mid = mido.MidiFile(str(midi))
            channels = sorted({m.channel for t in mid.tracks for m in t
                               if not m.is_meta and hasattr(m, "channel")})
            self.assertEqual(channels, [0, 1, 2, 3, 9])
            programs = {(m.channel, m.program) for t in mid.tracks for m in t
                        if m.type == "program_change"}
            self.assertNotIn(9, {ch for ch, _ in programs})

    def test_layers(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, voicings, _ = arrange(melody, key_info, style="arpeggio")
        layers = make_layer_tracks(melody, harmony, voicings, ["pad", "guitar"],
                                   primary_style="arpeggio")
        self.assertEqual(len(layers), 2)
        self.assertTrue(all(layer.notes for layer in layers))

        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "layers.mid"
            export_midi(melody, harmony, chords, bass, midi, extras=layers)
            mid = mido.MidiFile(str(midi))
            channels = sorted({m.channel for t in mid.tracks for m in t
                               if not m.is_meta and hasattr(m, "channel")})
            self.assertIn(4, channels)
            self.assertIn(5, channels)

    def test_layer_constraints(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, _, _, voicings, _ = arrange(melody, key_info, style="arpeggio")
        pad = make_layer_tracks(melody, harmony, voicings, ["pad"],
                                primary_style="arpeggio")[0]
        self.assertTrue(pad.notes)
        for note in pad.notes:
            self.assertTrue(31 <= note.pitch <= 67)
            for m in melody.notes:
                if m.start < note.end and m.end > note.start:
                    self.assertGreater(abs(note.pitch - m.pitch), 1)

        # 两层都是密集型时，叠层只保留正拍
        harmony2, _, _, voicings2, _ = arrange(melody, key_info, style="arp16")
        scale = make_layer_tracks(melody, harmony2, voicings2, ["scale"],
                                  primary_style="arp16")[0]
        self.assertTrue(scale.notes)
        for note in scale.notes:
            self.assertAlmostEqual(note.start, round(note.start), places=6)


class TestEnsembleAndDynamics(unittest.TestCase):
    def test_simple_harmony(self):
        melody = load_melody(DATA / "02_ode_to_joy.mid")
        harmony, _, _, _, _ = arrange(melody, detect_key(melody), simple=True)
        for slot in harmony.slots:
            self.assertNotIn("7", slot.chord.symbol)
            self.assertNotIn("/", slot.chord.roman)
        self.assertEqual(harmony.slots[-1].chord.degree, 1)

    def test_ensemble_programs(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="block")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "ens.mid"
            export_midi(melody, harmony, chords, bass, midi, programs=(40, 48, 42))
            mid = mido.MidiFile(str(midi))
            programs = {(m.channel, m.program) for t in mid.tracks for m in t
                        if m.type == "program_change"}
            self.assertIn((0, 40), programs)
            self.assertIn((1, 48), programs)
            self.assertIn((2, 42), programs)

    def test_humanize(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        harmony, chords, bass, _, _ = arrange(melody, detect_key(melody), style="alberti")
        shaped = apply_humanize(chords, melody, melody.bpm, level="strong")
        self.assertEqual(len(shaped), len(chords))
        self.assertTrue(any(abs(a.start - b.start) > 1e-6 for a, b in zip(shaped, chords)))
        self.assertTrue(any(a.velocity != b.velocity for a, b in zip(shaped, chords)))
        for note in shaped:
            self.assertGreaterEqual(note.start, 0.0)
            self.assertTrue(1 <= note.velocity <= 127)


    def test_layer_instruments(self):
        melody = load_melody(DATA / "02_ode_to_joy.mid")
        key_info = detect_key(melody)
        harmony, _, _, voicings, _ = arrange(melody, key_info, style="arpeggio")
        layers = make_layer_tracks(melody, harmony, voicings, ["pad", "arpeggio"],
                                   instruments=["strings", "flute"],
                                   primary_style="arpeggio")
        self.assertEqual(layers[0].program, 48)
        self.assertEqual(layers[1].program, 73)
        for note in layers[0].notes:
            self.assertTrue(48 <= note.pitch <= 84)
        for note in layers[1].notes:
            self.assertTrue(60 <= note.pitch <= 96)

        by_start: dict[float, int] = {}
        for note in layers[1].notes:
            key = round(note.start, 4)
            by_start[key] = by_start.get(key, 0) + 1
        self.assertLessEqual(max(by_start.values(), default=0), 1)


    def test_balance_cc7(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="block")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "mix.mid"
            export_midi(melody, harmony, chords, bass, midi,
                        volumes={0: 1.0, 1: 0.5, 2: 0.8})
            mid = mido.MidiFile(str(midi))
            cc7 = {(m.channel, m.control): m.value for t in mid.tracks for m in t
                   if m.type == "control_change"}
            self.assertEqual(cc7[(0, 7)], 127)
            self.assertEqual(cc7[(1, 7)], 64)
            self.assertEqual(cc7[(2, 7)], 102)


    def test_canon_key(self):
        melody = load_melody(DATA / "08_canon.mid")
        self.assertEqual(detect_key(melody).name, "D major")


class TestMelodyExtraction(unittest.TestCase):
    def test_extract_line_top_voice(self):
        part = m21stream.Stream()
        for offset, pitch in ((0, 72), (1, 74), (2, 76)):
            part.insert(offset, m21note.Note(pitch, quarterLength=1))
        for offset, pitches in ((0, (60, 64, 67)), (1, (60, 65, 69)),
                                (2, (60, 64, 67))):
            part.insert(offset, m21chord.Chord(pitches, quarterLength=1))
        line = _extract_line(part)
        self.assertEqual([n.pitch for n in line], [72, 74, 76])
        self.assertEqual([n.start for n in line], [0.0, 1.0, 2.0])
class TestAuto(unittest.TestCase):
    def test_auto_plan(self):
        for name in ("01_twinkle.mid", "02_ode_to_joy.mid", "07_waltz_pickup.mid"):
            melody = load_melody(DATA / name)
            plan = auto_suggest(melody, detect_key(melody))
            self.assertIn(plan.style, STYLES)
            self.assertIn(plan.chords_per_bar, (1, 2))
            self.assertIn(plan.harmony, ("simple", "rich"))
            self.assertIn(plan.ensemble, ("piano", "strings", "band"))
            self.assertIn(plan.reverb, ("off", "light", "medium", "hall"))
            self.assertIn(plan.ir, ("hall", "opera", "church"))
            self.assertIn(plan.soundfont,
                          ("fluid", "musescore", "generaluser"))
            self.assertLessEqual(len(plan.layers), 2)
            self.assertTrue(plan.reasons)

    def test_auto_waltz(self):
        melody = load_melody(DATA / "07_waltz_pickup.mid")
        plan = auto_suggest(melody, detect_key(melody))
        self.assertEqual(plan.style, "waltz")


class TestVariationAndStems(unittest.TestCase):
    def test_avoid_melody(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        first = melody.notes[0]
        notes = [NoteEvent(first.pitch, first.start, first.dur, 80)]
        out = avoid_melody(notes, melody)
        for note in out:
            for m in melody.notes:
                if m.start < note.end and m.end > note.start:
                    self.assertGreater(abs(note.pitch - m.pitch), 1)

    def test_phrase_fills(self):
        melody = load_melody(DATA / "02_ode_to_joy.mid")
        key_info = detect_key(melody)
        harmony, chords, _, _, _ = arrange(melody, key_info, style="arpeggio")
        filled = add_phrase_fills(chords, melody, harmony, phrase_bars=4, style="arpeggio")
        self.assertGreater(len(filled), len(chords))
        for note in filled[len(chords):]:
            for m in melody.notes:
                if m.start < note.end and m.end > note.start:
                    self.assertGreater(abs(note.pitch - m.pitch), 1)

    def test_stems(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="block")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "stem.mid"
            export_midi(melody, harmony, chords, bass, midi)
            stems = export_stems(midi, Path(tmp) / "stems")
            self.assertEqual(len(stems), 3)
            self.assertTrue(all(path.exists() for path in stems))


class TestBass(unittest.TestCase):
    def test_inversions_and_final(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, _, bass, _, _ = arrange(melody, key_info, style="alberti")
        self.assertGreater(harmony.stats.get("inversions", 0), 0)
        self.assertGreaterEqual(harmony.stats.get("passing_tones", 0), 0)
        final = harmony.slots[-1].chord
        self.assertEqual(bass[-1].pitch % 12, final.root_pc)
        for note in bass:
            self.assertTrue(36 <= note.pitch <= 52)

    def test_passing_tones(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, _, bass, _, _ = arrange(melody, key_info, style="alberti")
        self.assertGreater(harmony.stats.get("passing_tones", 0), 0)
        starts = [note.start for note in bass]
        self.assertEqual(len(starts), len(set(round(s, 4) for s in starts)))


class TestExpression(unittest.TestCase):
    def test_curves(self):
        melody = load_melody(DATA / "02_ode_to_joy.mid")
        extras = [
            ExtraTrack("Counter", [], channel=3),
            ExtraTrack("Layer pad:strings", [], channel=4, instrument="strings"),
            ExtraTrack("Layer arp:piano", [], channel=5, instrument="piano"),
        ]
        curves = build_expression(melody, extras, phrase_bars=4, level="strong")
        for channel in (1, 2, 3, 4, 5):
            self.assertIn(channel, curves)
            values = [value for _, value in curves[channel]]
            self.assertGreater(len(values), 4)
            self.assertGreaterEqual(min(values), 1)
            self.assertLessEqual(max(values), 127)
            self.assertNotEqual(min(values), max(values))
        self.assertEqual(build_expression(melody, extras, level="off"), {})


class TestCustomIR(unittest.TestCase):
    def test_custom_ir(self):
        import numpy as np

        melody = load_melody(DATA / "01_twinkle.mid")
        harmony, chords, bass, _, _ = arrange(melody, detect_key(melody), style="block")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "ir.mid"
            dry = Path(tmp) / "dry.wav"
            wet = Path(tmp) / "wet.wav"
            ir = Path(tmp) / "ir.wav"
            export_midi(melody, harmony, chords, bass, midi)
            render_wav(midi, dry)

            rate = 44100
            n = rate * 2
            data = np.random.default_rng(3).standard_normal((n, 2)) * np.exp(
                -4 * np.arange(n) / rate).reshape(-1, 1)
            pcm = (data / np.max(np.abs(data)) * 0.5 * 32767).astype("<i2")
            with wave.open(str(ir), "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(rate)
                handle.writeframes(pcm.tobytes())

            shutil.copyfile(dry, wet)
            self.assertTrue(add_reverb(wet, "hall", ir_path=ir))
            with wave.open(str(wet), "rb") as handle:
                wet_s = handle.getnframes() / handle.getframerate()
            with wave.open(str(dry), "rb") as handle:
                dry_s = handle.getnframes() / handle.getframerate()
            self.assertGreater(wet_s, dry_s + 1.0)


class TestSkeleton(unittest.TestCase):
    def test_extract(self):
        from route_a.skeleton import extract
        part = m21stream.Stream()
        part.insert(0, m21note.Note(36, quarterLength=4))
        part.insert(0, m21chord.Chord((60, 64, 67), quarterLength=4))
        part.insert(4, m21note.Note(43, quarterLength=4))
        part.insert(4, m21chord.Chord((59, 62, 67), quarterLength=4))
        skeleton = extract(part)
        self.assertTrue(skeleton.bass_notes)
        self.assertEqual(skeleton.bass_notes[0].pitch % 12, 0)
        self.assertEqual(skeleton.final_root_pc, 7)
        self.assertEqual(skeleton.root_at(0), 0)
        self.assertTrue(skeleton.polyphonic)


class TestReverb(unittest.TestCase):
    def test_hall_extends_tail(self):
        import numpy as np

        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="alberti")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "r.mid"
            dry = Path(tmp) / "dry.wav"
            wet = Path(tmp) / "wet.wav"
            export_midi(melody, harmony, chords, bass, midi)
            render_wav(midi, dry)
            shutil.copyfile(dry, wet)
            self.assertTrue(add_reverb(wet, "hall"))

            def info(path):
                with wave.open(str(path), "rb") as handle:
                    frames = handle.getnframes()
                    rate = handle.getframerate()
                    data = np.frombuffer(handle.readframes(frames), dtype="<i2")
                return frames / rate, float(np.max(np.abs(data)) / 32768)

            dry_s, _ = info(dry)
            wet_s, peak = info(wet)
            self.assertGreater(wet_s, dry_s + 1.0)
            self.assertLessEqual(peak, 0.91)

    def test_freeverb_engine(self):
        melody = load_melody(DATA / "01_twinkle.mid")
        key_info = detect_key(melody)
        harmony, chords, bass, _, _ = arrange(melody, key_info, style="alberti")
        outdir = ROOT / "output"
        outdir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outdir) as tmp:
            midi = Path(tmp) / "fv.mid"
            dry = Path(tmp) / "dry.wav"
            wet = Path(tmp) / "wet.wav"
            export_midi(melody, harmony, chords, bass, midi)
            render_wav(midi, dry)
            shutil.copyfile(dry, wet)
            self.assertTrue(add_reverb(wet, "hall", engine="freeverb"))
            with wave.open(str(dry), "rb") as handle:
                dry_s = handle.getnframes() / handle.getframerate()
            with wave.open(str(wet), "rb") as handle:
                wet_s = handle.getnframes() / handle.getframerate()
            self.assertGreater(wet_s, dry_s + 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
