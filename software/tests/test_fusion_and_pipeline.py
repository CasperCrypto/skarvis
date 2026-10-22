"""Tests for fusion and end-to-end pipeline behaviour.

Fusion is where a wrong answer is most dangerous (a confident position on empty
sky), so the rejection paths are tested as hard as the success path.
"""

from __future__ import annotations

import math
import tempfile
import unittest

from czapla.fusion import fuse_all, fuse_group, group_detections, haversine_m
from czapla.geometry import local_to_latlon
from czapla.pipeline import demo, demo_fusion, process_detections, process_spectrum
from czapla.events import EventStore

REF_LAT, REF_LON = 51.2631, 15.5672


def node_at(east: float, north: float) -> dict:
    lat, lon = local_to_latlon(east, north, REF_LAT, REF_LON)
    return {"lat": lat, "lon": lon}


def bearing_to(east_from: float, north_from: float, east_to: float, north_to: float) -> float:
    return math.degrees(math.atan2(east_to - east_from, north_to - north_from)) % 360.0


class TestGrouping(unittest.TestCase):
    def test_groups_detections_close_in_time_and_frequency(self):
        dets = [
            {"node_id": "a", "freq_hz": 2437e6, "ts_utc": "2026-10-22T12:00:00Z"},
            {"node_id": "b", "freq_hz": 2438e6, "ts_utc": "2026-10-22T12:00:02Z"},
            {"node_id": "c", "freq_hz": 5800e6, "ts_utc": "2026-10-22T12:00:03Z"},
        ]
        groups = group_detections(dets, time_window_s=5.0, freq_tolerance_mhz=20.0)
        sizes = sorted(len(g) for g in groups)
        self.assertEqual(sizes, [1, 2])

    def test_does_not_group_across_time(self):
        dets = [
            {"node_id": "a", "freq_hz": 2437e6, "ts_utc": "2026-10-22T12:00:00Z"},
            {"node_id": "b", "freq_hz": 2437e6, "ts_utc": "2026-10-22T12:05:00Z"},
        ]
        groups = group_detections(dets, time_window_s=5.0)
        self.assertEqual(len(groups), 2)


class TestFusion(unittest.TestCase):
    def _pair(self, target_e: float, target_n: float):
        return [
            {
                "node_id": "node-01",
                "freq_hz": 2437e6,
                "bearing_deg": bearing_to(0.0, 0.0, target_e, target_n),
                "bearing_sigma_deg": 5.0,
                "node_position": node_at(0.0, 0.0),
                "ts_utc": "2026-10-22T12:00:00Z",
            },
            {
                "node_id": "node-02",
                "freq_hz": 2437.5e6,
                "bearing_deg": bearing_to(400.0, 0.0, target_e, target_n),
                "bearing_sigma_deg": 5.0,
                "node_position": node_at(400.0, 0.0),
                "ts_utc": "2026-10-22T12:00:01Z",
            },
        ]

    def test_fuses_two_good_bearings(self):
        result = fuse_group(self._pair(500.0, 700.0), REF_LAT, REF_LON)
        self.assertIsNotNone(result)
        self.assertTrue(result["fused"])
        self.assertEqual(len(result["sources"]), 2)
        truth_lat, truth_lon = local_to_latlon(500.0, 700.0, REF_LAT, REF_LON)
        miss = haversine_m(result["lat"], result["lon"], truth_lat, truth_lon)
        self.assertLess(miss, 5.0, f"fused position off by {miss:.1f} m")

    def test_refuses_with_one_node(self):
        dets = self._pair(500.0, 700.0)[:1]
        result = fuse_group(dets, REF_LAT, REF_LON)
        self.assertFalse(result["fused"])
        self.assertIn("two_distinct_nodes", result["reason"])

    def test_refuses_without_bearing(self):
        dets = self._pair(500.0, 700.0)
        del dets[0]["bearing_deg"]
        result = fuse_group(dets, REF_LAT, REF_LON)
        self.assertFalse(result["fused"])

    def test_refuses_wide_sigma(self):
        dets = self._pair(500.0, 700.0)
        dets[0]["bearing_sigma_deg"] = 40.0
        result = fuse_group(dets, REF_LAT, REF_LON)
        self.assertFalse(result["fused"])
        self.assertIn("two_distinct_nodes", result["reason"])

    def test_refuses_disagreeing_rays(self):
        # Two nodes reporting bearings that cannot both be true of one target.
        dets = [
            {
                "node_id": "node-01", "freq_hz": 2437e6, "bearing_deg": 0.0,
                "bearing_sigma_deg": 2.0, "node_position": node_at(0.0, 0.0),
                "ts_utc": "2026-10-22T12:00:00Z",
            },
            {
                "node_id": "node-02", "freq_hz": 2437e6, "bearing_deg": 0.0,
                "bearing_sigma_deg": 2.0, "node_position": node_at(400.0, 0.0),
                "ts_utc": "2026-10-22T12:00:01Z",
            },
        ]
        result = fuse_group(dets, REF_LAT, REF_LON)
        # Parallel rays -> degenerate geometry, which must be refused, not guessed.
        self.assertFalse(result["fused"])

    def test_fuse_all_returns_only_fixes(self):
        one = self._pair(100.0, 100.0)
        results = fuse_all(one, REF_LAT, REF_LON)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["fused"])

    def test_confidence_is_bounded(self):
        result = fuse_group(self._pair(300.0, -200.0), REF_LAT, REF_LON)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_haversine_sanity(self):
        self.assertAlmostEqual(haversine_m(51.0, 15.0, 51.0, 15.0), 0.0, places=6)
        self.assertGreater(haversine_m(51.0, 15.0, 51.001, 15.0), 100.0)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="czapla-pipe-")
        self.store = EventStore(self.tmp)

    def test_process_detections_writes_events(self):
        dets = [
            {
                "node_id": "n1", "freq_hz": 2437e6, "snr_db": 20.0,
                "width_hz": 0.5e6, "freq_hop_count": 3,
            }
        ]
        decisions = process_detections(dets, self.store)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(len(self.store.read_all()), 1)

    def test_wifi_like_spectrum_does_not_alarm_once_baseline_learns_it(self):
        """The core honesty property: a persistent Wi-Fi carrier must not alarm.

        A single snapshot cannot distinguish a steady Wi-Fi carrier from a drone
        video downlink, so the system is given a baseline period exactly as a real
        install would. After that, the persistent signal must stop alarming while a
        new, transient signal still does.
        """
        from czapla.baseline import BaselineTracker
        from czapla.pipeline import synthesise_wifi_like

        tracker = BaselineTracker(window=10, min_observations=5, occupancy_threshold=0.8)
        samples = synthesise_wifi_like()

        # Baseline phase: the site's Wi-Fi is present in every scan.
        for _ in range(6):
            process_spectrum(
                samples, 20e6, 2437e6, "n1", self.store, baseline=tracker
            )

        # Now a scan of the same persistent carrier must not alarm.
        decisions = process_spectrum(
            samples, 20e6, 2437e6, "n1", self.store, baseline=tracker
        )
        alarms = [d for d in decisions if d["decision"]["alarm"]]
        self.assertEqual(alarms, [], "a learned persistent carrier must not alarm")

    def test_new_signal_still_alarms_after_baseline_learns_the_wifi(self):
        """The gate must not blind the system to genuinely new signals."""
        from czapla.baseline import BaselineTracker
        from czapla.pipeline import synthesise_wifi_like

        tracker = BaselineTracker(window=10, min_observations=5, occupancy_threshold=0.8)
        samples = synthesise_wifi_like()
        for _ in range(6):
            process_spectrum(samples, 20e6, 2437e6, "n1", self.store, baseline=tracker)

        # A new drone-like emission at a different frequency within the band.
        decisions = process_detections(
            [
                {
                    "node_id": "n1",
                    "freq_hz": 2452e6,
                    "snr_db": 22.0,
                    "width_hz": 60e3,
                    "freq_hop_count": 3,
                }
            ],
            self.store,
            baseline=tracker,
        )
        self.assertTrue(decisions[0]["decision"]["alarm"])

    def test_baseline_not_trusted_before_enough_scans(self):
        from czapla.baseline import BaselineTracker

        tracker = BaselineTracker(window=10, min_observations=5)
        tracker.observe([2437.0])
        self.assertFalse(tracker.is_trusted)
        self.assertFalse(tracker.is_persistent(2437.0))

    def test_demo_runs_clean(self):
        code = demo(self.tmp)
        self.assertEqual(code, 0)
        self.assertGreaterEqual(len(self.store.read_all()), 1)

    def test_demo_fusion_writes_a_position(self):
        code = demo_fusion(self.tmp)
        self.assertEqual(code, 0)
        records = self.store.read_all()
        positions = [r for r in records if r["schema"] == "czapla.position/1"]
        self.assertEqual(len(positions), 1)
        self.assertTrue(positions[0]["synthetic"])


if __name__ == "__main__":
    unittest.main()
