from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Optional, Sequence


AUDIBLE_MIN_HZ = 20.0
AUDIBLE_MAX_HZ = 20000.0
DEFAULT_A4_HZ = 440.0
DEFAULT_OCTAVE = 4

NATURAL_SEMITONES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

PITCH_RE = re.compile(r"^\s*([A-Ga-g])([#b♯♭]?)([-+]?\d+)?\s*$")


@dataclass(frozen=True)
class Pitch:
    pitch_class: str
    semitone: int
    octave: int
    midi_number: int
    frequency: float
    prefer_flats: bool = False

    @property
    def name(self) -> str:
        return f"{self.pitch_class}{self.octave}"


@dataclass(frozen=True)
class NoteData:
    note_name: str
    ratio: str
    octave_shift: int
    cents: float
    frequency: float


@dataclass(frozen=True)
class ScalePreset:
    name: str
    description: str
    intervals: tuple[int, ...]
    ratios: tuple[Fraction, ...]


SCALE_PRESETS = {
    "chromatic": ScalePreset(
        name="chromatic",
        description="5-limit just chromatic scale",
        intervals=tuple(range(12)),
        ratios=(
            Fraction(1, 1),
            Fraction(16, 15),
            Fraction(9, 8),
            Fraction(6, 5),
            Fraction(5, 4),
            Fraction(4, 3),
            Fraction(45, 32),
            Fraction(3, 2),
            Fraction(8, 5),
            Fraction(5, 3),
            Fraction(9, 5),
            Fraction(15, 8),
        ),
    ),
    "major": ScalePreset(
        name="major",
        description="5-limit just major scale",
        intervals=(0, 2, 4, 5, 7, 9, 11),
        ratios=(
            Fraction(1, 1),
            Fraction(9, 8),
            Fraction(5, 4),
            Fraction(4, 3),
            Fraction(3, 2),
            Fraction(5, 3),
            Fraction(15, 8),
        ),
    ),
    "minor": ScalePreset(
        name="minor",
        description="5-limit just natural minor scale",
        intervals=(0, 2, 3, 5, 7, 8, 10),
        ratios=(
            Fraction(1, 1),
            Fraction(9, 8),
            Fraction(6, 5),
            Fraction(4, 3),
            Fraction(3, 2),
            Fraction(8, 5),
            Fraction(9, 5),
        ),
    ),
    "pythagorean": ScalePreset(
        name="pythagorean",
        description="Pythagorean chromatic scale",
        intervals=tuple(range(12)),
        ratios=(
            Fraction(1, 1),
            Fraction(256, 243),
            Fraction(9, 8),
            Fraction(32, 27),
            Fraction(81, 64),
            Fraction(4, 3),
            Fraction(729, 512),
            Fraction(3, 2),
            Fraction(128, 81),
            Fraction(27, 16),
            Fraction(16, 9),
            Fraction(243, 128),
        ),
    ),
}


def pitch_class_name(semitone: int, prefer_flats: bool = False) -> str:
    names = FLAT_NAMES if prefer_flats else SHARP_NAMES
    return names[semitone % 12]


def parse_pitch(name: str, default_octave: int = DEFAULT_OCTAVE, a4: float = DEFAULT_A4_HZ) -> Pitch:
    """Parse a pitch like C4, Db3, F♯4, or A into an equal-tempered root."""
    if a4 <= 0:
        raise ValueError("a4 must be > 0")
    if not name or not name.strip():
        raise ValueError("Root note is required.")

    match = PITCH_RE.match(name)
    if not match:
        raise ValueError(f"Invalid pitch {name!r}. Use examples like C4, Db3, F♯4, or A4.")

    letter, accidental, octave_text = match.groups()
    letter = letter.upper()
    accidental = accidental.replace("♯", "#").replace("♭", "b")
    accidental_offset = {"": 0, "#": 1, "b": -1}[accidental]
    octave = int(octave_text) if octave_text is not None else default_octave

    midi_number = (octave + 1) * 12 + NATURAL_SEMITONES[letter] + accidental_offset
    semitone = midi_number % 12
    effective_octave = midi_number // 12 - 1
    prefer_flats = accidental == "b"
    frequency = a4 * (2 ** ((midi_number - 69) / 12))

    return Pitch(
        pitch_class=pitch_class_name(semitone, prefer_flats),
        semitone=semitone,
        octave=effective_octave,
        midi_number=midi_number,
        frequency=frequency,
        prefer_flats=prefer_flats,
    )


def get_preset(name: str) -> ScalePreset:
    try:
        return SCALE_PRESETS[name.lower()]
    except KeyError as exc:
        choices = ", ".join(sorted(SCALE_PRESETS))
        raise ValueError(f"Unknown preset {name!r}. Choose one of: {choices}.") from exc


def ratio_text(ratio: Fraction) -> str:
    return f"{ratio.numerator}/{ratio.denominator}"


def ratio_cents(ratio: Fraction) -> float:
    return 1200.0 * math.log2(float(ratio))


def build_scale_notes(root: Pitch, preset: ScalePreset) -> list[NoteData]:
    notes = []
    for interval, ratio in zip(preset.intervals, preset.ratios):
        cents = ratio_cents(ratio)
        notes.append(
            NoteData(
                note_name=pitch_class_name(root.semitone + interval, root.prefer_flats),
                ratio=ratio_text(ratio),
                octave_shift=0,
                cents=round(cents, 5),
                frequency=root.frequency * float(ratio),
            )
        )
    return notes


def just_intonation_scale(
    root_note: str,
    preset: str = "chromatic",
    a4: float = DEFAULT_A4_HZ,
) -> list[NoteData]:
    """Return one octave of structured just-intonation note data."""
    root = parse_pitch(root_note, a4=a4)
    return build_scale_notes(root, get_preset(preset))


def audible_octaves(
    notes: Sequence[NoteData],
    cent_deviation: float = 0.5,
    freq_min: float = AUDIBLE_MIN_HZ,
    freq_max: float = AUDIBLE_MAX_HZ,
) -> list[NoteData]:
    """Expand structured notes into the audible range while deduplicating close pitches."""
    if cent_deviation <= 0:
        raise ValueError("cent_deviation must be > 0")
    if freq_min <= 0 or freq_max <= 0 or freq_min >= freq_max:
        raise ValueError("freq_min and freq_max must be positive and increasing")

    cents_factor = 1200.0 / cent_deviation
    seen = set()
    results = []

    for note in notes:
        if note.frequency <= 0:
            continue

        k_min = math.ceil(math.log2(freq_min / note.frequency))
        k_max = math.floor(math.log2(freq_max / note.frequency))

        for octave_shift in range(k_min, k_max + 1):
            frequency = note.frequency * (2 ** octave_shift)
            duplicate_key = round(cents_factor * math.log2(frequency))
            if duplicate_key in seen:
                continue

            seen.add(duplicate_key)
            results.append(
                NoteData(
                    note_name=note.note_name,
                    ratio=note.ratio,
                    octave_shift=octave_shift,
                    cents=round(note.cents + (1200.0 * octave_shift), 5),
                    frequency=frequency,
                )
            )

    return sorted(results, key=lambda note: note.frequency)


def generate_notes(
    root_note: str,
    preset: str = "chromatic",
    range_mode: str = "audible",
    a4: float = DEFAULT_A4_HZ,
) -> list[NoteData]:
    base_notes = just_intonation_scale(root_note, preset=preset, a4=a4)
    if range_mode == "octave":
        return base_notes
    if range_mode == "audible":
        return audible_octaves(base_notes)
    raise ValueError("range_mode must be 'audible' or 'octave'")


def note_dicts(notes: Iterable[NoteData]) -> list[dict[str, object]]:
    return [asdict(note) for note in notes]


def format_table(
    notes: Sequence[NoteData],
    root: Pitch,
    preset: ScalePreset,
    a4: float,
    range_mode: str,
) -> str:
    rows = [
        {
            "note": note.note_name,
            "ratio": note.ratio,
            "octave": str(note.octave_shift),
            "cents": f"{note.cents:.5f}",
            "frequency": f"{note.frequency:.5f}",
        }
        for note in notes
    ]
    headers = {
        "note": "Note",
        "ratio": "Ratio",
        "octave": "Octave",
        "cents": "Cents",
        "frequency": "Frequency (Hz)",
    }
    widths = {
        key: max(len(headers[key]), *(len(row[key]) for row in rows))
        for key in headers
    }

    lines = [
        f"Root: {root.name} ({root.frequency:.5f} Hz)",
        f"Preset: {preset.name} - {preset.description}",
        f"A4: {a4:.5f} Hz",
        f"Range: {range_mode}",
        "",
        "  ".join(headers[key].ljust(widths[key]) for key in headers),
        "  ".join("-" * widths[key] for key in headers),
    ]
    lines.extend(
        "  ".join(row[key].ljust(widths[key]) for key in headers)
        for row in rows
    )
    return "\n".join(lines)


def format_csv(notes: Sequence[NoteData]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=("note_name", "ratio", "octave_shift", "cents", "frequency"),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(note_dicts(notes))
    return output.getvalue().rstrip("\n")


def format_json(
    notes: Sequence[NoteData],
    root: Pitch,
    preset: ScalePreset,
    a4: float,
    range_mode: str,
) -> str:
    payload = {
        "root": {
            "name": root.name,
            "frequency": root.frequency,
            "midi_number": root.midi_number,
        },
        "preset": preset.name,
        "description": preset.description,
        "a4": a4,
        "range": range_mode,
        "notes": note_dicts(notes),
    }
    return json.dumps(payload, indent=2)


def format_scl(preset: ScalePreset) -> str:
    lines = [
        "! just-intonation-generator.scl",
        "!",
        preset.description,
        str(len(preset.ratios)),
        "!",
    ]
    lines.extend(ratio_text(ratio) for ratio in preset.ratios[1:])
    lines.append("2/1")
    return "\n".join(lines)


def format_output(
    output_format: str,
    notes: Sequence[NoteData],
    root: Pitch,
    preset: ScalePreset,
    a4: float,
    range_mode: str,
) -> str:
    if output_format == "table":
        return format_table(notes, root, preset, a4, range_mode)
    if output_format == "csv":
        return format_csv(notes)
    if output_format == "json":
        return format_json(notes, root, preset, a4, range_mode)
    if output_format == "scl":
        return format_scl(preset)
    raise ValueError("Unsupported format")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate just-intonation note frequencies.")
    parser.add_argument("--root", help="Root pitch, such as C4, Db3, F♯4, or A4.")
    parser.add_argument(
        "--preset",
        default="chromatic",
        choices=sorted(SCALE_PRESETS),
        help="Scale or tuning preset to generate.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default="table",
        choices=("table", "csv", "json", "scl"),
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--range",
        dest="range_mode",
        default="audible",
        choices=("audible", "octave"),
        help="Generate one octave or expand notes across the audible range.",
    )
    parser.add_argument(
        "--a4",
        type=float,
        default=DEFAULT_A4_HZ,
        help="Reference frequency for A4 in Hz.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root_note = args.root
    if not root_note:
        root_note = input("Please enter root note (e.g., C4, D#, Eb3, A4): ").strip()

    try:
        root = parse_pitch(root_note, a4=args.a4)
        preset = get_preset(args.preset)
        range_mode = "octave" if args.output_format == "scl" else args.range_mode
        base_notes = build_scale_notes(root, preset)
        notes = audible_octaves(base_notes) if range_mode == "audible" else base_notes
        output = format_output(args.output_format, notes, root, preset, args.a4, range_mode)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
