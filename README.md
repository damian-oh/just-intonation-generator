# Just Intonation Generator

Generate musical note frequencies from simple just-intonation and Pythagorean tuning presets.

The default `chromatic` preset is a 12-note 5-limit just chromatic scale. It is not a major scale. The original ratio set is preserved as:

```text
1/1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8
```

## Features

- Explicit tuning presets: `chromatic`, `major`, `minor`, and `pythagorean`.
- Root pitch parsing for inputs like `C`, `C4`, `Db3`, `A4`, `F♯4`, and `D♭3`.
- Equal-tempered root frequency calculation from configurable `A4`, defaulting to `440 Hz`.
- Structured note data with note name, ratio, octave shift, cents, and frequency.
- Audible range expansion from `20 Hz` to `20 kHz`.
- Export formats: table, CSV, JSON, and Scala `.scl`.

## Usage

No third-party dependencies are required.

```bash
python3 src/main.py --root C4 --preset major --range octave
```

If `--root` is omitted, the script prompts for one interactively.

### Options

```text
--root ROOT                     Root pitch, such as C4, Db3, F♯4, or A4
--preset chromatic|major|minor|pythagorean
--range audible|octave          Default: audible
--format table|csv|json|scl     Default: table
--output PATH                   Write output to a file instead of stdout
--a4 FLOAT                      A4 reference frequency, default: 440.0
```

## Examples

Print one octave of a C just major scale:

```bash
python3 src/main.py --root C4 --preset major --range octave
```

Sample output:

```text
Root: C4 (261.62557 Hz)
Preset: major - 5-limit just major scale
A4: 440.00000 Hz
Range: octave

Note  Ratio  Octave  Cents       Frequency (Hz)
----  -----  ------  ----------  --------------
C     1/1    0       0.00000     261.62557
D     9/8    0       203.91000   294.32876
E     5/4    0       386.31371   327.03196
F     4/3    0       498.04500   348.83409
G     3/2    0       701.95500   392.43835
A     5/3    0       884.35871   436.04261
B     15/8   0       1088.26871  490.54793
```

Export all audible notes for `Db3` as CSV:

```bash
python3 src/main.py --root Db3 --preset chromatic --format csv --output db3-chromatic.csv
```

Export structured JSON:

```bash
python3 src/main.py --root A4 --preset minor --range octave --format json
```

Export a Scala tuning file for synths and tuning tools:

```bash
python3 src/main.py --root C4 --preset pythagorean --format scl --output pythagorean.scl
```

Scala exports use the selected one-octave preset. The `1/1` tonic is implicit in the Scala format, and `2/1` is written as the final octave entry.

## Presets

- `chromatic`: the original 12-note 5-limit just chromatic ratio set.
- `major`: 5-limit just major scale: `1/1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8`.
- `minor`: 5-limit just natural minor scale: `1/1, 9/8, 6/5, 4/3, 3/2, 8/5, 9/5`.
- `pythagorean`: 12-note Pythagorean chromatic scale built from simple powers of `3/2`, octave-reduced into one octave.

## Why Just Intonation?

Just intonation uses simple whole-number ratios to define intervals between notes. Unlike equal temperament, which slightly adjusts intervals so every key is equally usable, just intonation favors harmonically pure intervals relative to a chosen root.
