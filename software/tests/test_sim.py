"""Tests for the scenario simulator.

The simulator is only useful if it is honest about its own blind spots and
never leaks ground truth into the records the pipeline writes. Those are the
properties tested hardest here.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest

from czapla.events import EventStore
from czapla.sim import (
    DEFAULT_SCENARIO,
    Actor,
    MemoryStore,
    ScenarioError,
    load_scenario,
    run_scenario,
    validate_scenario,
)

SCENARIO = load_scenario(DEFAULT_SCENARIO)
RUN = run_scenario(SCENARIO)
ROWS = {r["id"]: r for r in RUN["scorecard"]["actors"]}


class TestScenarioValidation(unittest.TestCase):
    def test_kraken_cannot_be_asked_to_hear_2_4_ghz(self):
        bad = copy.deepcopy(SCENARIO)
        df = next(s for s in bad["sensors"] if s["type"] == "rf_df")
        df["bands_mhz"] = [[2400, 2483]]
        with self.assertRaises(ScenarioError) as ctx:
            validate_scenario(bad)
        self.assertIn("KrakenSDR", str(ctx.exception))

    def test_unknown_sensor_type_rejected(self):
        bad = copy.deepcopy(SCENARIO)
        bad["sensors"].append({"id": "jammer", "type": "jammer"})
        with self.assertRaises(ScenarioError):
            validate_scenario(bad)

    def test_actor_needs_a_path(self):
        bad = copy.deepcopy(SCENARIO)
        bad["actors"][0]["path"] = [[0, 0]]
        with self.assertRaises(ScenarioError):
            validate_scenario(bad)


class TestActor(unittest.TestCase):
    def test_moves_at_constant_speed_and_leaves(self):
        a = Actor({"id": "a", "kind": "human", "speed_mps": 2.0, "start_s": 10,
                   "path": [[0, 0], [0, 100]]})
        self.assertIsNone(a.state(5))
        self.assertAlmostEqual(a.state(20)["north"], 20.0)
        self.assertAlmostEqual(a.state(60)["north"], 100.0)
        self.assertIsNone(a.state(61))

    def test_hold_keeps_a_hovering_drone_in_place(self):
        a = Actor({"id": "d", "kind": "drone", "speed_mps": 10.0, "hold_s": 30,
                   "path": [[0, 0], [100, 0]]})
        st = a.state(25)
        self.assertAlmostEqual(st["east"], 100.0)
        self.assertEqual(st["speed"], 0.0)
        self.assertIsNone(a.state(41))


class TestDemoScenario(unittest.TestCase):
    def test_fibre_optic_drone_is_never_seen(self):
        row = ROWS["fpv-swiatlowod"]
        self.assertFalse(row["detected"])
        self.assertEqual(row["outcome"], "missed")
        self.assertIn("światłowod", row["why_pl"])

    def test_authorised_drone_is_seen_but_does_not_alarm(self):
        row = ROWS["dron-inspekcja"]
        self.assertTrue(row["detected"])
        self.assertFalse(row["alarmed"])

    def test_remote_id_and_868_drones_alarm(self):
        self.assertEqual(ROWS["dron-rid"]["outcome"], "true_alarm")
        self.assertEqual(ROWS["fpv-868"]["outcome"], "true_alarm")
        self.assertGreater(ROWS["fpv-868"]["position_fixes"], 0)

    def test_intruder_alarms_and_fox_does_not(self):
        self.assertEqual(ROWS["intruz"]["outcome"], "true_alarm")
        self.assertFalse(ROWS["lis"]["alarmed"])

    def test_two_sensor_rule_held_a_camera_only_person_on_the_fox(self):
        self.assertGreater(ROWS["lis"]["single_sensor_alarm_held"], 0)

    def test_people_and_cars_outside_the_fence_do_not_alarm(self):
        self.assertTrue(ROWS["spacerowicz"]["detected"])
        self.assertFalse(ROWS["spacerowicz"]["alarmed"])
        self.assertFalse(ROWS["samochod"]["alarmed"])

    def test_site_telemetry_is_learned_as_infrastructure(self):
        self.assertEqual(RUN["scorecard"]["emitters"][0]["outcome"], "correctly_quiet")

    def test_run_is_labelled_synthetic_and_serialisable(self):
        self.assertTrue(RUN["synthetic"])
        self.assertIn("SYMULACJA", RUN["disclaimer_pl"])
        json.dumps(RUN)


class TestRecordsAreHonest(unittest.TestCase):
    def test_every_record_is_stamped_synthetic_and_carries_no_truth(self):
        store = MemoryStore()
        run_scenario(SCENARIO, store=store)
        self.assertGreater(len(store.records), 0)
        schemas = {r["schema"] for r in store.records}
        self.assertEqual(schemas, {"czapla.event/1", "czapla.position/1", "czapla.ground/1"})
        for rec in store.records:
            self.assertTrue(rec["synthetic"])
            self.assertFalse(any("truth" in k for k in rec), rec)

    def test_records_use_simulated_time(self):
        store = MemoryStore()
        run_scenario(SCENARIO, store=store)
        self.assertTrue(all(r["ts_utc"].startswith("2026-10-28T10:") for r in store.records))

    def test_writes_to_a_real_event_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(tmp)
            run_scenario(SCENARIO, store=store)
            self.assertGreater(len(store.read_all()), 0)

    def test_same_seed_same_outcome(self):
        again = run_scenario(SCENARIO)
        self.assertEqual(again["scorecard"], RUN["scorecard"])


class TestDesignFindings(unittest.TestCase):
    """What the simulator found in our own pipeline on 2026-10-28. Kept as tests
    so a fix shows up as a deliberate change, not silently."""

    def test_f2_default_cooldown_bucket_realarms_on_frequency_hopping(self):
        sc = copy.deepcopy(SCENARIO)
        sc["policy"]["air"] = {}
        default_alarms = sum(1 for e in run_scenario(sc)["events"] if e.get("alarm"))
        tuned_alarms = sum(1 for e in RUN["events"] if e.get("alarm"))
        self.assertGreater(default_alarms, tuned_alarms)

    def test_f3_learning_baseline_turns_an_approaching_drone_into_infrastructure(self):
        sc = copy.deepcopy(SCENARIO)
        sc["baseline"]["learn_during_run"] = True
        rows = {r["id"]: r for r in run_scenario(sc)["scorecard"]["actors"]}
        self.assertGreater(rows["fpv-868"]["marked_infrastructure"], 0)
        self.assertEqual(ROWS["fpv-868"]["marked_infrastructure"], 0)

    def test_f5_without_install_warmup_site_telemetry_alarms(self):
        sc = copy.deepcopy(SCENARIO)
        sc["baseline"]["warmup_scans"] = 0
        emitters = run_scenario(sc)["scorecard"]["emitters"]
        self.assertEqual(emitters[0]["outcome"], "false_alarm")


if __name__ == "__main__":
    unittest.main()
