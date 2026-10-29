"""Tests for the ground classifier, ground alarm policy and ground records.

The point of the ground module is fewer empty alarms, so the tests that matter
most are the ones where a single sensor says "person" and no alarm follows.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from czapla.events import EventStore, SchemaError, make_ground
from czapla.geometry import pixel_footprint_m, point_in_polygon
from czapla.ground import classify_track, radar_evidence, thermal_evidence
from czapla.policy import GroundAlarmState, GroundPolicy

PERSON_THERMAL = {"sensor": "thermal", "height_m": 1.75, "width_m": 0.5, "pixels_tall": 4}
FOX_THERMAL = {"sensor": "thermal", "height_m": 0.4, "width_m": 0.9, "pixels_tall": 3}
CAR_THERMAL = {"sensor": "thermal", "height_m": 1.5, "width_m": 4.4, "pixels_tall": 5}
PERSON_RADAR = {"sensor": "radar_mmwave", "speed_mps": 1.3, "gait_hz": 1.9}
FOX_RADAR = {"sensor": "radar_mmwave", "speed_mps": 2.0, "gait_hz": 3.6}
CAR_RADAR = {"sensor": "radar_mmwave", "speed_mps": 12.0, "gait_hz": None}
CAMERA_PERSON = {"sensor": "camera_ai", "label": "person", "score": 0.85}


class TestThermalShape(unittest.TestCase):
    def test_upright_person_is_human(self):
        ev = thermal_evidence(PERSON_THERMAL)
        self.assertEqual(max(ev, key=ev.get), "human")

    def test_fox_is_animal(self):
        ev = thermal_evidence(FOX_THERMAL)
        self.assertEqual(max(ev, key=ev.get), "animal")

    def test_car_is_vehicle(self):
        ev = thermal_evidence(CAR_THERMAL)
        self.assertEqual(max(ev, key=ev.get), "vehicle")

    def test_too_few_pixels_says_nothing_about_class(self):
        far = dict(PERSON_THERMAL, pixels_tall=1)
        self.assertIsNone(thermal_evidence(far))

    def test_resolution_not_blob_size_decides_if_shape_counts(self):
        # Two pixels tall at 10 m (0.25 m per pixel): a person would be 5+ px,
        # so a small blob there is real evidence of an animal.
        near_fox = {"sensor": "thermal", "height_m": 0.5, "width_m": 0.9,
                    "pixels_tall": 2, "pixel_m": 0.25}
        ev = thermal_evidence(near_fox)
        self.assertEqual(max(ev, key=ev.get), "animal")
        # The same blob at 40 m (1 m per pixel) proves nothing.
        far_blob = dict(near_fox, pixel_m=1.0)
        self.assertIsNone(thermal_evidence(far_blob))

    def test_known_failure_crawling_person_looks_like_an_animal(self):
        # Documented weakness of the shape rule, kept as a test so nobody
        # forgets it and nobody claims otherwise.
        crawling = {"sensor": "thermal", "height_m": 0.45, "width_m": 1.7, "pixels_tall": 3}
        ev = thermal_evidence(crawling)
        self.assertEqual(max(ev, key=ev.get), "animal")

    def test_cheap_thermal_resolution_falls_apart_with_range(self):
        # 32 x 24 px over 55 x 35 deg: a 1.75 m person is > 3 px tall at 20 m,
        # fewer than 2 px at 50 m.
        near = 1.75 / pixel_footprint_m(20.0, 35.0, 24)
        far = 1.75 / pixel_footprint_m(50.0, 35.0, 24)
        self.assertGreater(near, 3.0)
        self.assertLess(far, 2.0)


class TestRadar(unittest.TestCase):
    def test_walking_cadence_leans_human_but_does_not_decide(self):
        ev = radar_evidence(PERSON_RADAR)
        self.assertEqual(max(ev, key=ev.get), "human")
        self.assertLess(ev["human"], 0.8)

    def test_no_cadence_and_speed_is_vehicle(self):
        ev = radar_evidence(CAR_RADAR)
        self.assertEqual(max(ev, key=ev.get), "vehicle")

    def test_stationary_without_cadence_is_uninformative(self):
        self.assertIsNone(radar_evidence({"sensor": "radar_mmwave", "speed_mps": 0.1}))


class TestClassifyTrack(unittest.TestCase):
    def test_person_seen_by_three_sensor_types(self):
        v = classify_track([PERSON_THERMAL, PERSON_RADAR, CAMERA_PERSON, {"sensor": "pir"}])
        self.assertEqual(v["label"], "human")
        self.assertGreaterEqual(v["confidence"], 0.7)
        self.assertEqual(v["sensor_types"], ["camera_ai", "pir", "radar_mmwave", "thermal"])

    def test_camera_false_person_on_a_fox_is_outvoted(self):
        # The case the product exists for: the camera says "person", the
        # thermal shape and the radar cadence say animal.
        v = classify_track([CAMERA_PERSON, FOX_THERMAL, FOX_RADAR])
        self.assertEqual(v["label"], "animal")

    def test_one_sensor_type_reports_lower_confidence(self):
        many_frames = [CAMERA_PERSON] * 10
        single = classify_track(many_frames)
        double = classify_track([CAMERA_PERSON, PERSON_THERMAL])
        self.assertEqual(single["label"], "human")
        self.assertLess(single["confidence"], double["confidence"])

    def test_ten_frames_of_one_sensor_do_not_outvote_another_type(self):
        v = classify_track([CAMERA_PERSON] * 10 + [FOX_THERMAL, FOX_RADAR])
        self.assertEqual(v["label"], "animal")

    def test_pir_only_is_unknown(self):
        v = classify_track([{"sensor": "pir"}] * 5)
        self.assertEqual(v["label"], "unknown")
        self.assertEqual(v["confidence"], 0.0)
        self.assertEqual(v["sensor_types"], ["pir"])

    def test_admits_rules_are_not_fitted(self):
        v = classify_track([PERSON_THERMAL])
        self.assertIn("not fitted", v["disclaimer"])
        self.assertIn("not-fitted", v["version"])


class TestGroundPolicy(unittest.TestCase):
    T0 = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)

    def _verdict(self, label="human", conf=0.85, types=("thermal", "radar_mmwave")):
        return {"label": label, "confidence": conf, "sensor_types": list(types)}

    def test_confirmed_person_inside_alarms(self):
        d = GroundAlarmState().evaluate(self._verdict(), "trk-1", True, when=self.T0)
        self.assertTrue(d["alarm"])
        self.assertIn("Human decision required", d["action_note"])

    def test_single_sensor_type_never_alarms(self):
        d = GroundAlarmState().evaluate(
            self._verdict(types=("camera_ai",)), "trk-1", True, when=self.T0
        )
        self.assertFalse(d["alarm"])
        self.assertIn("not_confirmed_by_second_sensor_type", d["reason"])

    def test_animal_never_alarms(self):
        d = GroundAlarmState().evaluate(self._verdict(label="animal"), "trk-1", True)
        self.assertFalse(d["alarm"])
        self.assertIn("class_not_alarming(animal)", d["reason"])

    def test_outside_perimeter_does_not_alarm(self):
        d = GroundAlarmState().evaluate(self._verdict(), "trk-1", False)
        self.assertIn("outside_perimeter", d["reason"])

    def test_cooldown_per_track(self):
        state = GroundAlarmState(GroundPolicy(cooldown_seconds=120))
        first = state.evaluate(self._verdict(), "trk-1", True, when=self.T0)
        again = state.evaluate(
            self._verdict(), "trk-1", True, when=self.T0 + timedelta(seconds=30)
        )
        other = state.evaluate(
            self._verdict(), "trk-2", True, when=self.T0 + timedelta(seconds=30)
        )
        self.assertTrue(first["alarm"])
        self.assertFalse(again["alarm"])
        self.assertTrue(other["alarm"])


class TestGroundRecord(unittest.TestCase):
    def test_round_trip_through_store(self):
        rec = make_ground(
            "ground-s", "trk-1", ["thermal", "radar_mmwave"], "human", 0.8,
            east_m=3.0, north_m=-90.0, inside_perimeter=True, alarm=True,
            ts_utc="2026-10-28T12:00:00.000Z",
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp)
            store.append(rec)
            back = store.read_all()
        self.assertEqual(back[0]["schema"], "czapla.ground/1")
        self.assertEqual(back[0]["ts_utc"], "2026-10-28T12:00:00.000Z")

    def test_rejects_unknown_class(self):
        with self.assertRaises(SchemaError):
            make_ground("g", "t", ["thermal"], "intruder", 0.5)

    def test_rejects_empty_sensor_list(self):
        with self.assertRaises(SchemaError):
            make_ground("g", "t", [], "human", 0.5)


class TestPerimeterGeometry(unittest.TestCase):
    SQUARE = [[-150, -100], [150, -100], [150, 100], [-150, 100]]

    def test_inside_and_outside(self):
        self.assertTrue(point_in_polygon(0.0, 0.0, self.SQUARE))
        self.assertFalse(point_in_polygon(0.0, -120.0, self.SQUARE))
        self.assertFalse(point_in_polygon(200.0, 0.0, self.SQUARE))

    def test_degenerate_polygon_is_never_inside(self):
        self.assertFalse(point_in_polygon(0.0, 0.0, [[0, 0], [1, 1]]))


if __name__ == "__main__":
    unittest.main()
