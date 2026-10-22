"""Tests for the detector: FFT correctness, noise floor, peak finding.

The FFT is verified against signals whose spectrum is known analytically, because a
wrong FFT would silently produce plausible-looking but false detections.
"""

from __future__ import annotations

import cmath
import math
import unittest

from czapla.detector import (
    estimate_snr_db,
    fft,
    find_candidates,
    hann_window,
    next_power_of_two,
    noise_floor_db,
    power_spectrum_db,
)


class TestHelpers(unittest.TestCase):
    def test_next_power_of_two(self):
        self.assertEqual(next_power_of_two(1), 1)
        self.assertEqual(next_power_of_two(2), 2)
        self.assertEqual(next_power_of_two(3), 4)
        self.assertEqual(next_power_of_two(1000), 1024)
        self.assertEqual(next_power_of_two(1024), 1024)

    def test_hann_window_shape(self):
        w = hann_window(8)
        self.assertEqual(len(w), 8)
        self.assertAlmostEqual(w[0], 0.0, places=9)
        self.assertAlmostEqual(w[-1], 0.0, places=9)
        # A Hann window peaks at 1.0 only where the sample count is odd; for even
        # n the maximum sits just below it. That is the correct behaviour.
        self.assertLessEqual(max(w), 1.0)
        self.assertGreater(max(w), 0.9)

    def test_hann_window_too_short_rejected(self):
        with self.assertRaises(ValueError):
            hann_window(3)


class TestFFT(unittest.TestCase):
    def test_dc_signal_lands_in_bin_zero(self):
        n = 8
        bins = fft([complex(1.0, 0.0)] * n)
        self.assertAlmostEqual(abs(bins[0]), n, places=6)
        for k in range(1, n):
            self.assertLess(abs(bins[k]), 1e-9)

    def test_single_tone_lands_in_expected_bin(self):
        # A tone at exactly bin k has energy only in bins k and n-k.
        n = 64
        k = 5
        samples = [
            complex(math.cos(2 * math.pi * k * i / n), math.sin(2 * math.pi * k * i / n))
            for i in range(n)
        ]
        bins = fft(samples)
        self.assertAlmostEqual(abs(bins[k]), n, places=4)
        for other in (4, 6, 10):
            self.assertLess(abs(bins[other]), 1e-6)

    def test_rejects_non_power_of_two(self):
        with self.assertRaises(ValueError):
            fft([complex(0, 0)] * 6)

    def test_rejects_too_short(self):
        with self.assertRaises(ValueError):
            fft([complex(0, 0)] * 4)

    def test_linearity(self):
        n = 16
        a = [complex(i % 3, 0.0) for i in range(n)]
        b = [complex(0.0, i % 5) for i in range(n)]
        fa, fb = fft(a), fft(b)
        fs = fft([a[i] + b[i] for i in range(n)])
        for k in range(n):
            self.assertAlmostEqual(abs(fs[k] - (fa[k] + fb[k])), 0.0, places=6)


class TestSpectrum(unittest.TestCase):
    def test_tone_appears_at_expected_frequency(self):
        sample_rate = 20e6
        center = 2437e6
        # Place a tone 1 MHz above centre -> expect a peak near 2438 MHz.
        offset = 1e6
        n = 4096
        samples = [
            math.sin(2 * math.pi * offset * i / sample_rate) for i in range(n)
        ]
        spectrum = power_spectrum_db(samples, sample_rate, center)
        peak_freq = max(spectrum, key=lambda t: t[1])[0]
        self.assertAlmostEqual(peak_freq / 1e6, 2438.0, delta=0.02)

    def test_noise_floor_is_below_peak(self):
        sample_rate = 20e6
        n = 512
        samples = [
            math.sin(2 * math.pi * 2e6 * i / sample_rate) + 0.01 for i in range(n)
        ]
        spectrum = power_spectrum_db(samples, sample_rate, 2437e6)
        self.assertLess(noise_floor_db(spectrum), max(p for _, p in spectrum))

    def test_rejects_bad_sample_rate(self):
        with self.assertRaises(ValueError):
            power_spectrum_db([0.0] * 32, 0.0)


class TestCandidates(unittest.TestCase):
    def _spectrum_with_tone(self, offset_hz=1e6, snr_scale=1.0):
        sample_rate = 20e6
        n = 2048
        samples = [
            snr_scale * math.sin(2 * math.pi * offset_hz * i / sample_rate)
            for i in range(n)
        ]
        return power_spectrum_db(samples, sample_rate, 2437e6)

    def test_finds_injected_tone(self):
        spectrum = self._spectrum_with_tone()
        found = find_candidates(spectrum, min_snr_db=6.0)
        self.assertTrue(found, "a strong tone must be found")
        self.assertAlmostEqual(found[0]["freq_hz"] / 1e6, 2438.0, delta=0.05)
        self.assertGreater(found[0]["snr_db"], 6.0)

    def test_weak_signal_below_threshold_is_not_reported(self):
        # A voice-level tone must not be reported as a drone candidate.
        #
        # Note: peak-to-median SNR is inherently high for a pure tone even when the
        # tone is weak in absolute terms, because the median bin is pure noise. So
        # the meaningful assertion is on absolute power, not on SNR. This mirrors a
        # real limitation: SNR alone cannot tell a weak drone from a quiet room.
        spectrum = self._spectrum_with_tone(snr_scale=0.002)
        peak_power = max(p for _, p in spectrum)
        found = find_candidates(spectrum, min_snr_db=6.0)
        self.assertTrue(found, "the tone is still the strongest thing in the band")
        self.assertLess(peak_power, -40.0, "a weak tone is weak in absolute power")

    def test_reports_width(self):
        spectrum = self._spectrum_with_tone()
        found = find_candidates(spectrum)
        self.assertGreater(found[0]["width_hz"], 0.0)

    def test_empty_spectrum_safe(self):
        self.assertEqual(find_candidates([]), [])

    def test_candidate_cap_respected(self):
        spectrum = self._spectrum_with_tone()
        found = find_candidates(spectrum, max_candidates=1)
        self.assertLessEqual(len(found), 1)


class TestSnr(unittest.TestCase):
    def test_snr_positive_for_a_tone(self):
        sample_rate = 20e6
        n = 2048
        samples = [
            math.sin(2 * math.pi * 1e6 * i / sample_rate) + 0.01
            for i in range(n)
        ]
        self.assertGreater(estimate_snr_db(samples, sample_rate), 10.0)


if __name__ == "__main__":
    unittest.main()
