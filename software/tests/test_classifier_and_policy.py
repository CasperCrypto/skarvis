"""Tests for classification, alarm policy and the whitelist.

The critical property being tested is that the system does NOT alarm on ordinary
Wi-Fi, and that it does alarm on a drone-like signature. A classifier that alarms
on Wi-Fi would make the product unusable in a real building.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from czapla.classifier import (
    CLASSIFIER_VERSION,
    band_affinity_mhz,
    classify,
    width_score,
)
from czapla.policy import AlarmPolicy, AlarmState, Whitelist


class TestBandAffinity(unittest.TestCase):
    def test_on_centre(self):
        self.assertAlmostEqual(band_affinity_mhz(2437.0), 1.0, places=6)

    def test_far_away(self):
        self.assertAlmostEqual(band_affinity_mhz(1000.0), 0.0, places=6)

    def test_decays_with_distance(self):
        # Both must stay inside the 5 MHz full-credit window so the scores diverge.
        self.assertGreater(band_affinity_mhz(2438.0), band_affinity_mhz(2445.0))

    def test_zero_beyond_the_tolerance_window(self):
        # 3000 MHz is not within 20 MHz of any known consumer drone band centre.
        self.assertAlmostEqual(band_affinity_mhz(3000.0), 0.0, places=6)
        # 2430 MHz is 7 MHz from the 2437 centre: outside full credit, still partial.
        self.assertGreater(band_affinity_mhz(2430.0), 0.0)
        self.assertLess(band_affinity_mhz(2430.0), 1.0)


class TestWidthScore(unittest.TestCase):
    def test_narrow_control_link(self):
        # A 50 kHz emission is a narrow control link.
        self.assertGreaterEqual(width_score(50e3), 0.8)

    def test_wide_video_link(self):
        self.assertAlmostEqual(width_score(10e6), 1.0)

    def test_mid_width_is_penalised(self):
        self.assertLess(width_score(4e6), 0.5)


class TestClassify(unittest.TestCase):
    def test_drone_like_signature(self):
        # Strong, in-band, narrow, hopping between channels = a control link.
        result = classify(snr_db=20.0, freq_hz=2437e6, width_hz=0.5e6, freq_hop_count=3)
        self.assertEqual(result["label"], "drone_like")
        self.assertGreater(result["score"], 0.7)

    def test_wifi_access_point_is_not_drone_like(self):
        # On-band and strong, but stationary with a mid width: a Wi-Fi AP.
        result = classify(snr_db=25.0, freq_hz=2437e6, width_hz=4e6, freq_hop_count=0)
        self.assertNotEqual(result["label"], "drone_like")

    def test_off_band_strong_signal_is_gated(self):
        # 900 MHz telemetry is off-band for our drone bands: strong and narrow, but
        # the hard band gate must keep it out of drone_like.
        result = classify(snr_db=25.0, freq_hz=900e6, width_hz=50e3, freq_hop_count=1)
        self.assertNotEqual(result["label"], "drone_like")
        self.assertTrue(result["features"]["band_gated"])

    def test_explains_itself(self):
        result = classify(snr_db=20.0, freq_hz=2437e6, width_hz=50e3, freq_hop_count=3)
        for key in ("snr_score", "band_affinity", "width_score", "hop_score"):
            self.assertIn(key, result["features"])

    def test_admits_weights_are_not_fitted(self):
        result = classify(snr_db=20.0, freq_hz=2437e6, width_hz=0.5e6)
        self.assertEqual(result["version"], CLASSIFIER_VERSION)
        self.assertIn("priors", result["disclaimer"])

    def test_score_always_in_range(self):
        for snr in (-10.0, 0.0, 15.0, 100.0):
            for width in (0.0, 1e6, 2e7):
                result = classify(snr_db=snr, freq_hz=2437e6, width_hz=width)
                self.assertGreaterEqual(result["score"], 0.0)
                self.assertLessEqual(result["score"], 1.0)


class TestWhitelist(unittest.TestCase):
    def test_matches_by_frequency(self):
        wl = Whitelist([{"freq_mhz": 2437.0, "comment": "agreed survey flight"}])
        self.assertIsNotNone(wl.matches(2437.2e6))
        self.assertIsNone(wl.matches(2450.0e6))

    def test_time_window_respected(self):
        now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        wl = Whitelist(
            [
                {
                    "freq_mhz": 2437.0,
                    "from_utc": "2026-10-22T10:00:00+00:00",
                    "to_utc": "2026-10-22T11:00:00+00:00",
                }
            ]
        )
        self.assertIsNone(wl.matches(2437e6, when=now))


class TestAlarmPolicy(unittest.TestCase):
    def _det(self, **over):
        base = {
            "freq_hz": 2437e6,
            "snr_db": 20.0,
            "confidence": 0.9,
            "classification": "drone_like",
        }
        base.update(over)
        return base

    def test_alarms_on_a_good_detection(self):
        state = AlarmState(AlarmPolicy())
        decision = state.evaluate(self._det(), node_id="n1")
        self.assertTrue(decision["alarm"])
        self.assertEqual(decision["reason"], "thresholds_met")

    def test_no_alarm_when_not_drone_like(self):
        state = AlarmState(AlarmPolicy())
        decision = state.evaluate(self._det(classification="other"), node_id="n1")
        self.assertFalse(decision["alarm"])
        self.assertIn("not_classified_drone_like", decision["reason"])

    def test_no_alarm_below_snr(self):
        state = AlarmState(AlarmPolicy())
        decision = state.evaluate(self._det(snr_db=1.0), node_id="n1")
        self.assertFalse(decision["alarm"])
        self.assertIn("below_snr_threshold", decision["reason"])

    def test_no_alarm_below_confidence(self):
        state = AlarmState(AlarmPolicy())
        decision = state.evaluate(self._det(confidence=0.2), node_id="n1")
        self.assertFalse(decision["alarm"])
        self.assertIn("below_confidence_threshold", decision["reason"])

    def test_cooldown_suppresses_the_second_alarm(self):
        policy = AlarmPolicy(cooldown_seconds=60, repeat_alarm_after_seconds=300)
        state = AlarmState(policy)
        t0 = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        first = state.evaluate(self._det(), node_id="n1", when=t0)
        second = state.evaluate(
            self._det(), node_id="n1", when=t0 + timedelta(seconds=10)
        )
        self.assertTrue(first["alarm"])
        self.assertFalse(second["alarm"])
        self.assertTrue(second["suppressed"])
        self.assertIn("cooldown", second["reason"])

    def test_alarm_repeats_after_the_long_window(self):
        policy = AlarmPolicy(cooldown_seconds=60, repeat_alarm_after_seconds=300)
        state = AlarmState(policy)
        t0 = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        state.evaluate(self._det(), node_id="n1", when=t0)
        later = state.evaluate(
            self._det(), node_id="n1", when=t0 + timedelta(seconds=400)
        )
        self.assertTrue(later["alarm"])
        self.assertEqual(later["repeat_of"], 1)

    def test_whitelisted_flight_is_suppressed(self):
        wl = Whitelist([{"freq_mhz": 2437.0, "comment": "authorised inspection"}])
        state = AlarmState(AlarmPolicy(), wl)
        decision = state.evaluate(self._det(), node_id="n1")
        self.assertFalse(decision["alarm"])
        self.assertEqual(decision["reason"], "whitelisted_authorised_flight")

    def test_decision_states_a_human_must_decide(self):
        state = AlarmState(AlarmPolicy())
        decision = state.evaluate(self._det(), node_id="n1")
        self.assertIn("Human decision required", decision["action_note"])
        self.assertIn("does not authorise", decision["action_note"])

    def test_separate_nodes_do_not_share_cooldown(self):
        state = AlarmState(AlarmPolicy())
        t0 = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        a = state.evaluate(self._det(), node_id="n1", when=t0)
        b = state.evaluate(self._det(), node_id="n2", when=t0 + timedelta(seconds=5))
        self.assertTrue(a["alarm"])
        self.assertTrue(b["alarm"])


if __name__ == "__main__":
    unittest.main()
