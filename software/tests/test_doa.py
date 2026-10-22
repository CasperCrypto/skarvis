"""Tests for direction of arrival.

The DoA is the single piece of maths that can silently produce a confident wrong
answer, so it is tested by generating phases from a known bearing and checking the
estimator recovers it — across the whole circle and with noise added.
"""

from __future__ import annotations

import random
import unittest

from czapla.doa import (
    array_element_angles,
    bearing_sigma_from_confidence,
    doa_from_phases,
    expected_phases_deg,
)

FREQ_HZ = 2437e6
RADIUS_M = 0.15


class TestArrayGeometry(unittest.TestCase):
    def test_uniform_circular_array(self):
        angles = array_element_angles(5)
        self.assertEqual(len(angles), 5)
        self.assertAlmostEqual(angles[0], 0.0, places=9)
        self.assertAlmostEqual(angles[1], 72.0, places=9)
        self.assertAlmostEqual(angles[4], 288.0, places=9)

    def test_needs_three_elements(self):
        with self.assertRaises(ValueError):
            array_element_angles(2)

    def test_expected_phases_length_and_bounds(self):
        phases = expected_phases_deg(45.0, FREQ_HZ, RADIUS_M)
        self.assertEqual(len(phases), 5)
        # Phase magnitude cannot exceed 2*pi*r/lambda (in degrees).
        import math

        k = 2.0 * math.pi * RADIUS_M * FREQ_HZ / 299_792_458.0
        limit = math.degrees(k) + 1e-6
        for p in phases:
            self.assertLessEqual(abs(p), limit)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            expected_phases_deg(0.0, 0.0, RADIUS_M)
        with self.assertRaises(ValueError):
            expected_phases_deg(0.0, FREQ_HZ, -1.0)


class TestDoA(unittest.TestCase):
    def test_recovers_known_bearing_across_circle(self):
        for true_bearing in (0.0, 37.0, 90.0, 137.5, 180.0, 254.0, 300.0, 359.0):
            phases = expected_phases_deg(true_bearing, FREQ_HZ, RADIUS_M)
            result = doa_from_phases(phases, FREQ_HZ, RADIUS_M)
            error = abs((result["bearing_deg"] - true_bearing + 180.0) % 360.0 - 180.0)
            self.assertLess(error, 2.0, f"bearing {true_bearing} -> {result['bearing_deg']}")

    def test_high_confidence_on_clean_input(self):
        phases = expected_phases_deg(120.0, FREQ_HZ, RADIUS_M)
        result = doa_from_phases(phases, FREQ_HZ, RADIUS_M)
        self.assertGreater(result["confidence"], 0.8)

    def test_tolerates_phase_noise(self):
        # Real measured phases are noisy; the estimator must degrade, not break.
        rng = random.Random(7)
        true_bearing = 200.0
        base = expected_phases_deg(true_bearing, FREQ_HZ, RADIUS_M)
        noisy = [p + rng.gauss(0.0, 5.0) for p in base]
        result = doa_from_phases(noisy, FREQ_HZ, RADIUS_M)
        error = abs((result["bearing_deg"] - true_bearing + 180.0) % 360.0 - 180.0)
        self.assertLess(error, 25.0, f"noisy estimate off by {error:.1f} deg")

    def test_array_yaw_is_applied(self):
        # With the array physically rotated 90 degrees, the same measured phases
        # must map to a bearing 90 degrees different.
        true_bearing = 40.0
        phases = expected_phases_deg(true_bearing, FREQ_HZ, RADIUS_M, array_yaw_deg=90.0)
        result = doa_from_phases(phases, FREQ_HZ, RADIUS_M, array_yaw_deg=90.0)
        error = abs((result["bearing_deg"] - true_bearing + 180.0) % 360.0 - 180.0)
        self.assertLess(error, 2.0)

    def test_rejects_too_few_elements(self):
        with self.assertRaises(ValueError):
            doa_from_phases([0.0, 10.0], FREQ_HZ, RADIUS_M)

    def test_result_declares_limitations(self):
        result = doa_from_phases(expected_phases_deg(10.0, FREQ_HZ, RADIUS_M), FREQ_HZ, RADIUS_M)
        self.assertIn("azimuth", result["note"])
        self.assertIn("multipath", result["note"])


class TestBearingSigma(unittest.TestCase):
    def test_sigma_grows_as_confidence_falls(self):
        self.assertLess(bearing_sigma_from_confidence(0.95), bearing_sigma_from_confidence(0.3))

    def test_sigma_bounds(self):
        self.assertGreaterEqual(bearing_sigma_from_confidence(1.0), 1.0)
        self.assertLessEqual(bearing_sigma_from_confidence(0.0), 30.0)


if __name__ == "__main__":
    unittest.main()
