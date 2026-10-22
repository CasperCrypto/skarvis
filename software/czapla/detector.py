"""Energy detection: spectrum, noise floor, candidate signals.

Does:
    A radix-2 FFT, a windowed power spectrum, a robust noise-floor estimate, and
    peak picking to find candidate narrowband signals above that floor.

Does NOT do:
    Decide that something is a drone. It reports candidate energy with an SNR.
    Classification is classifier.py; alarm policy is policy.py.
"""

from __future__ import annotations

import cmath
import math

MIN_FFT_SIZE = 8
HANN_WINDOW_MIN_SIZE = 4


def next_power_of_two(n: int) -> int:
    """Smallest power of two >= n (the FFT below requires power-of-two length)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    p = 1
    while p < n:
        p <<= 1
    return p


def hann_window(n: int) -> list[float]:
    """Hann window. Reduces spectral leakage so a weak carrier is not buried."""
    if n < HANN_WINDOW_MIN_SIZE:
        raise ValueError("window needs at least 4 samples")
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


def fft(samples: list[complex]) -> list[complex]:
    """Iterative radix-2 Cooley-Tukey FFT. Length must be a power of two.

    Written out rather than imported because this package is stdlib-only so the
    same code runs on the Pi node and on a laptop.
    """
    n = len(samples)
    if n < MIN_FFT_SIZE or (n & (n - 1)) != 0:
        raise ValueError("fft length must be a power of two and >= 8")

    data = list(samples)
    # Bit-reversal permutation.
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            data[i], data[j] = data[j], data[i]

    length = 2
    while length <= n:
        angle = -2j * math.pi / length
        wlen = cmath.exp(angle)
        half = length >> 1
        for start in range(0, n, length):
            w = 1 + 0j
            for k in range(start, start + half):
                u = data[k]
                v = data[k + half] * w
                data[k] = u + v
                data[k + half] = u - v
                w *= wlen
        length <<= 1
    return data


def power_spectrum_db(
    samples: list[float], sample_rate_hz: float, center_freq_hz: float = 0.0
) -> list[tuple[float, float]]:
    """Windowed power spectrum as (frequency_hz, power_db) for the positive half.

    sample_rate_hz must be >= 2x the highest frequency of interest (Nyquist).
    center_freq_hz is the receiver's tuned frequency, added so the returned
    frequencies are absolute rather than baseband offsets.
    """
    if len(samples) < MIN_FFT_SIZE:
        raise ValueError("need at least 8 samples")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")

    n = next_power_of_two(len(samples))
    padded = list(samples) + [0.0] * (n - len(samples))
    window = hann_window(len(padded))
    buffered = [complex(padded[i] * window[i], 0.0) for i in range(n)]
    bins = fft(buffered)

    out: list[tuple[float, float]] = []
    for k in range(n // 2):
        mag = abs(bins[k]) / n
        power = mag * mag
        db = 10.0 * math.log10(power + 1e-20)
        freq = center_freq_hz + (k * sample_rate_hz / n)
        out.append((freq, db))
    return out


def noise_floor_db(spectrum: list[tuple[float, float]]) -> float:
    """Median power in dB — robust to whatever is transmitting.

    A mean would be dragged up by the very signal we are trying to find, which
    raises the floor and hides weak drones. Median does not.
    """
    if not spectrum:
        raise ValueError("empty spectrum")
    values = sorted(p for _, p in spectrum)
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])


def find_candidates(
    spectrum: list[tuple[float, float]],
    min_snr_db: float = 6.0,
    max_candidates: int = 8,
    neighbour_bins: int = 2,
) -> list[dict]:
    """Peaks at least min_snr_db above the noise floor.

    A peak is only kept if it is the local maximum within neighbour_bins, which
    stops a single wide carrier being reported eight times.
    """
    if not spectrum:
        return []
    floor = noise_floor_db(spectrum)
    powers = [p for _, p in spectrum]
    n = len(powers)
    candidates: list[dict] = []

    for i in range(n):
        snr = powers[i] - floor
        if snr < min_snr_db:
            continue
        lo = max(0, i - neighbour_bins)
        hi = min(n, i + neighbour_bins + 1)
        if powers[i] < max(powers[lo:hi]):
            continue
        # Occupied width: contiguous bins above (floor + half the peak's SNR).
        half = floor + snr / 2.0
        left = i
        while left > 0 and powers[left - 1] > half:
            left -= 1
        right = i
        while right < n - 1 and powers[right + 1] > half:
            right += 1
        candidates.append(
            {
                "freq_hz": round(spectrum[i][0], 3),
                "power_db": round(powers[i], 2),
                "snr_db": round(snr, 2),
                "width_hz": round(spectrum[right][0] - spectrum[left][0], 3),
            }
        )

    candidates.sort(key=lambda c: c["snr_db"], reverse=True)
    return candidates[:max_candidates]


def estimate_snr_db(samples: list[float], sample_rate_hz: float) -> float:
    """Peak-to-median SNR of a raw sample block. Convenience wrapper."""
    spectrum = power_spectrum_db(samples, sample_rate_hz)
    floor = noise_floor_db(spectrum)
    return round(max(p for _, p in spectrum) - floor, 2)
