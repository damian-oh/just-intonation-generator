import math

# Equal-temperament tonic frequencies at A4=440Hz
root_freq_440 = {
    "C": 261.63,
    "C#": 277.18,
    "Db": 277.18,
    "D": 293.66,
    "D#": 311.13,
    "Eb": 311.13,
    "E": 329.63,
    "F": 349.23,
    "F#": 369.99,
    "Gb": 369.99,
    "G": 392.0,
    "G#": 415.30,
    "Ab": 415.30,
    "A": 440.0,
    "A#": 466.16,
    "Bb": 466.16,
    "B": 493.88
}

# Enharmonic equivalents to normalize flat symbols
enharmonics = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#", "CB": "B", "FB": "E", "E#": "F", "B#": "C"}

# Just intonation note ratios for a major scale
ji_ratios_major = [1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8]

def normalize_note(name: str) -> str:
    """
        Normalize a user's note input
        1. Trim spaces
        2. Replace flat symbol with "b"
        3. Convert to uppercase
        4. Map enharmonics
    """
    note = name.strip().replace("♭", "b").upper()

    # Map all flats/enharmonics
    return enharmonics.get(note, note)
    
def just_intonation_scale(root_note: str) -> list:
    """
        Return a list of Just Intonation scale frequencies (one octave) for a given root note
    """

    # Gather the root note
    key = normalize_note(root_note)

    # Validate the input
    if key not in root_freq_440:
        raise ValueError(f"Please input a valid root note: {sorted(root_freq_440.keys())}")
    
    # Gather the root note frequency
    tonic = root_freq_440[key]

    # Return a single octave of a selected key
    return [tonic * ratio for ratio in ji_ratios_major]

def audible_octaves(freqs: list,
                    cent_deviation: float = 0.5) -> list:
    """
        Expand a list of base frequencies into the audible range ([20Hz, 20kHz])
        Remove duplicate notes based on a cent deviation threshold
    """

    if cent_deviation <= 0:
        raise ValueError("cent_deviation must be > 0")

    # Define audible frequency range (20-20kHz)
    freq_min = 20.0
    freq_max = 20000.0

    # Factor for converting cents to a manageable scale
    cents_factor = 1200.0 / cent_deviation

    # Reference frequency for cents (1Hz)
    ref_freq = 1.0

    # A list to store the results
    results = []

    # A set to prevent duplicate notes
    duplicated_notes = set()

    # Iterate through each frequency in the scale
    for freq in freqs:
        # Exclude wrong frequencies
        if freq <= 0:
            continue

        # freq * 2^k >= freq_min <=> k >= log2(freq_min / freq) (min integer k)
        k_min = math.ceil(math.log2(freq_min / freq))
        # freq * 2^k <= freq_max <=> k <= log2(freq_max / freq) (max integer k)
        k_max = math.floor(math.log2(freq_max / freq))

        # Iterate through the range of exponents
        for k in range(k_min, k_max + 1):
            # Octave up/down
            new_freq = freq * (2 ** k)

            # Convert the new frequency to cents relative to 1Hz reference
            cents = round(cents_factor * math.log2(new_freq / ref_freq))

            if cents not in duplicated_notes:
                duplicated_notes.add(cents)

                results.append(new_freq)

    # Return the sorted list of frequencies
    results.sort()
    return results

if __name__ == "__main__":
    root_note = input("Please enter root note (e.g., C, D#, Eb, A): ").strip()

    try:
        scale = just_intonation_scale(root_note)
        notes = audible_octaves(scale)

        print(f"Audible notes: {[round(x, 5) for x in notes]} ({len(notes)} notes)")
    except ValueError as e:
        print(e)