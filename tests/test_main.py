import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main


class PitchParsingTests(unittest.TestCase):
    def test_parse_pitch_uses_a4_reference(self):
        pitch = main.parse_pitch("A4")

        self.assertEqual(pitch.name, "A4")
        self.assertEqual(pitch.midi_number, 69)
        self.assertAlmostEqual(pitch.frequency, 440.0)

    def test_parse_pitch_defaults_to_octave_four(self):
        pitch = main.parse_pitch("C")

        self.assertEqual(pitch.name, "C4")
        self.assertEqual(pitch.midi_number, 60)
        self.assertAlmostEqual(pitch.frequency, 261.625565, places=5)

    def test_parse_pitch_supports_flats_and_unicode_accidentals(self):
        flat = main.parse_pitch("D♭3")
        sharp = main.parse_pitch("F♯4")

        self.assertEqual(flat.name, "Db3")
        self.assertEqual(flat.midi_number, 49)
        self.assertAlmostEqual(flat.frequency, 138.591315, places=5)
        self.assertEqual(sharp.name, "F#4")
        self.assertEqual(sharp.midi_number, 66)

    def test_parse_pitch_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            main.parse_pitch("H4")

    def test_parse_pitch_rejects_non_finite_a4(self):
        with self.assertRaises(ValueError):
            main.parse_pitch("A4", a4=float("nan"))

        with self.assertRaises(ValueError):
            main.parse_pitch("A4", a4=float("inf"))


class ScaleGenerationTests(unittest.TestCase):
    def test_presets_have_expected_sizes(self):
        self.assertEqual(len(main.SCALE_PRESETS["chromatic"].ratios), 12)
        self.assertEqual(len(main.SCALE_PRESETS["major"].ratios), 7)
        self.assertEqual(len(main.SCALE_PRESETS["minor"].ratios), 7)
        self.assertEqual(len(main.SCALE_PRESETS["pythagorean"].ratios), 12)

    def test_major_scale_returns_structured_note_data(self):
        notes = main.just_intonation_scale("C4", preset="major")

        self.assertEqual([note.note_name for note in notes], ["C", "D", "E", "F", "G", "A", "B"])
        self.assertEqual(notes[2].ratio, "5/4")
        self.assertEqual(notes[2].octave_shift, 0)
        self.assertAlmostEqual(notes[2].cents, 386.31371, places=5)
        self.assertAlmostEqual(notes[2].frequency, 327.031956, places=5)

    def test_minor_scale_uses_diatonic_flat_spellings(self):
        notes = main.just_intonation_scale("C4", preset="minor")

        self.assertEqual([note.note_name for note in notes], ["C", "D", "Eb", "F", "G", "Ab", "Bb"])

    def test_major_scale_uses_diatonic_flat_spellings(self):
        notes = main.just_intonation_scale("F4", preset="major")

        self.assertEqual([note.note_name for note in notes], ["F", "G", "A", "Bb", "C", "D", "E"])

    def test_audible_octaves_are_sorted_and_within_range(self):
        notes = main.just_intonation_scale("C4", preset="major")
        audible = main.audible_octaves(notes)

        self.assertGreater(len(audible), len(notes))
        self.assertEqual(audible, sorted(audible, key=lambda note: note.frequency))
        self.assertTrue(all(main.AUDIBLE_MIN_HZ <= note.frequency <= main.AUDIBLE_MAX_HZ for note in audible))
        self.assertTrue(any(note.octave_shift < 0 for note in audible))
        self.assertTrue(any(note.octave_shift > 0 for note in audible))


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.root = main.parse_pitch("C4")
        self.preset = main.get_preset("major")
        self.notes = main.build_scale_notes(self.root, self.preset)

    def test_csv_export_contains_structured_fields(self):
        output = main.format_csv(self.notes)

        self.assertTrue(output.startswith("note_name,ratio,octave_shift,cents,frequency"))
        self.assertIn("E,5/4,0,386.31371", output)

    def test_json_export_contains_metadata_and_notes(self):
        output = main.format_json(self.notes, self.root, self.preset, main.DEFAULT_A4_HZ, "octave")
        payload = json.loads(output)

        self.assertEqual(payload["root"]["name"], "C4")
        self.assertEqual(payload["preset"], "major")
        self.assertEqual(payload["range"], "octave")
        self.assertEqual(payload["notes"][0]["ratio"], "1/1")

    def test_scl_export_uses_scala_pitch_count_and_octave(self):
        output = main.format_scl(self.preset)
        lines = [line for line in output.splitlines() if line and not line.startswith("!")]

        self.assertEqual(lines[0], "5-limit just major scale")
        self.assertEqual(lines[1], "7")
        self.assertEqual(lines[2:], ["9/8", "5/4", "4/3", "3/2", "5/3", "15/8", "2/1"])


class CliTests(unittest.TestCase):
    def test_cli_rejects_invalid_a4(self):
        with redirect_stderr(StringIO()):
            exit_code = main.main(["--root", "A4", "--a4", "0"])

        self.assertEqual(exit_code, 2)

    def test_cli_rejects_nan_a4_without_json_output(self):
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main.main(["--root", "A4", "--a4", "nan", "--format", "json"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("a4 must be finite and > 0", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
