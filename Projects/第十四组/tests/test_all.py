"""不依赖 pytest 的自检脚本：python -m tests.test_all 或 python tests/test_all.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from melody_accompanist.arrange import STYLES, arrange
from melody_accompanist.harmonize import harmonize
from melody_accompanist.melody import detect_key, parse_melody
from melody_accompanist.smf import Track, midi_to_melody, read_midi, write_midi
from melody_accompanist.synth import render_wav

TWINKLE = """tempo 100
meter 4/4
C4 C4 G4 G4 | A4 A4 G4:2 | F4 F4 E4 E4 | D4 D4 C4:2
"""


class TestMelody(unittest.TestCase):
    def test_parse(self):
        melody = parse_melody("tempo 90\nmeter 3/4\nC4:1 D4:0.5 R:0.5 E4:1")
        self.assertEqual(len(melody.notes), 3)
        self.assertAlmostEqual(melody.end, 3.0)
        self.assertAlmostEqual(melody.beats_per_bar, 3.0)
        self.assertEqual(melody.time_sig, (3, 4))

    def test_parse_fraction(self):
        melody = parse_melody("C4:1/2 D4:1/2")
        self.assertAlmostEqual(melody.end, 1.0)

    def test_key_c_major(self):
        melody = parse_melody(TWINKLE)
        key, _ = detect_key(melody)
        self.assertEqual(key.name, "C major")

    def test_key_g_major(self):
        melody = parse_melody("G4:2 D5:2 B4:1 G4:1 A4:1 B4:1 C5:1 D5:2 G4:2")
        key, _ = detect_key(melody)
        self.assertEqual(key.name, "G major")


class TestHarmony(unittest.TestCase):
    def test_chart_structure(self):
        melody = parse_melody(TWINKLE)
        harmony = harmonize(melody, chords_per_bar=2)
        self.assertEqual(len(harmony.chart), melody.bars)
        self.assertTrue(all(len(bar) <= 2 for bar in harmony.chart))
        # 结尾应落在主和弦上
        self.assertTrue(harmony.slots[-1].chord.is_tonic)

    def test_conflict_rate_low(self):
        melody = parse_melody(TWINKLE)
        harmony = harmonize(melody, chords_per_bar=2)
        self.assertLess(harmony.stats["conflict_rate"], 0.34)

    def test_phrase_cadence(self):
        melody = parse_melody(TWINKLE)
        harmony = harmonize(melody, chords_per_bar=2, phrase_bars=4)
        chord = harmony.slots[7].chord  # 第 4 小节的最后一个槽
        self.assertEqual(chord.func, "T")


class TestArrangement(unittest.TestCase):
    def test_all_styles(self):
        melody = parse_melody(TWINKLE)
        for style in STYLES:
            result = arrange(melody, style=style, chords_per_bar=2)
            self.assertTrue(result.chords, style)
            self.assertTrue(result.bass, style)
            for note in result.chords + result.bass:
                self.assertTrue(36 <= note.pitch <= 96, (style, note))
                self.assertGreater(note.dur, 0)

    def test_melody_untouched(self):
        melody = parse_melody(TWINKLE)
        result = arrange(melody, style="block")
        self.assertEqual([n.pitch for n in result.melody.notes],
                         [n.pitch for n in melody.notes])


class TestMidiAndWav(unittest.TestCase):
    def test_roundtrip(self):
        melody = parse_melody(TWINKLE)
        result = arrange(melody, style="alberti")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.mid"
            write_midi(path, [
                Track("Melody", 0, 0, melody.notes),
                Track("Chords", 1, 0, result.chords),
                Track("Bass", 2, 32, result.bass),
            ], bpm=melody.bpm, time_sig=melody.time_sig, key=result.key)
            data = read_midi(path)
            self.assertEqual(len(data.tracks), 4)
            recovered = midi_to_melody(data)
            self.assertEqual(sorted(n.pitch for n in recovered.notes),
                             sorted(n.pitch for n in melody.notes))
            self.assertAlmostEqual(recovered.end, melody.end, delta=0.02)

    def test_wav(self):
        melody = parse_melody(TWINKLE)
        result = arrange(melody, style="arpeggio")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.wav"
            seconds = render_wav(path, result)
            self.assertGreater(seconds, 5.0)
            self.assertGreater(path.stat().st_size, 100_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
