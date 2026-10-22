"""Tests for the event schema, durable store and the Polish report."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from czapla.events import (
    EventStore,
    SchemaError,
    make_event,
    make_position,
    validate_event,
    validate_position,
)
from czapla.report import (
    DISCLAIMER_PL,
    LIMITATIONS_PL,
    render_report_html,
    render_report_text,
    report_filename,
)
from czapla import SCHEMA_EVENT, SCHEMA_POSITION


class TestEventSchema(unittest.TestCase):
    def test_make_event_is_valid(self):
        event = make_event(
            node_id="node-01",
            freq_hz=2437e6,
            snr_db=18.0,
            confidence=0.8,
            classification="drone_like",
            bearing_deg=137.5,
            bearing_sigma_deg=6.0,
        )
        self.assertEqual(event["schema"], SCHEMA_EVENT)
        self.assertEqual(event["band_mhz"], 2437.0)
        validate_event(event)

    def test_missing_field_rejected(self):
        bad = {"schema": SCHEMA_EVENT, "event_id": "x", "ts_utc": "now"}
        with self.assertRaises(SchemaError):
            validate_event(bad)

    def test_wrong_schema_rejected(self):
        event = make_event(
            node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
            classification="unknown",
        )
        event["schema"] = "something/else"
        with self.assertRaises(SchemaError):
            validate_event(event)

    def test_bad_classification_rejected(self):
        event = make_event(
            node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
            classification="drone_like",
        )
        event["classification"] = "definitely_a_drone"
        with self.assertRaises(SchemaError):
            validate_event(event)

    def test_confidence_out_of_range_rejected(self):
        event = make_event(
            node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
            classification="unknown",
        )
        event["confidence"] = 1.5
        with self.assertRaises(SchemaError):
            validate_event(event)

    def test_extra_cannot_overwrite_reserved_field(self):
        with self.assertRaises(SchemaError):
            make_event(
                node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
                classification="unknown", extra={"event_id": "hijack"},
            )

    def test_extra_is_added_when_safe(self):
        event = make_event(
            node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
            classification="unknown", extra={"classifier": "v1"},
        )
        self.assertEqual(event["classifier"], "v1")


class TestPositionSchema(unittest.TestCase):
    def test_make_position_valid(self):
        record = make_position(
            sources=["node-01", "node-02"], lat=51.26, lon=15.56, confidence=0.8
        )
        self.assertEqual(record["schema"], SCHEMA_POSITION)
        validate_position(record)

    def test_single_source_rejected(self):
        with self.assertRaises(SchemaError):
            make_position(sources=["node-01"], lat=51.0, lon=15.0, confidence=0.5)

    def test_lat_out_of_range_rejected(self):
        with self.assertRaises(SchemaError):
            make_position(
                sources=["a", "b"], lat=120.0, lon=15.0, confidence=0.5
            )


class TestEventStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="czapla-test-")
        self.store = EventStore(self.tmp)

    def test_append_and_read_back(self):
        event = make_event(
            node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
            classification="unknown",
        )
        self.store.append(event)
        records = self.store.read_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_id"], event["event_id"])

    def test_append_is_additive_not_destructive(self):
        for i in range(5):
            self.store.append(
                make_event(
                    node_id=f"n{i}", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
                    classification="unknown",
                )
            )
        self.assertEqual(len(self.store.read_all()), 5)

    def test_read_all_on_empty_store(self):
        self.assertEqual(self.store.read_all(), [])

    def test_bad_record_is_rejected_and_not_written(self):
        with self.assertRaises(SchemaError):
            self.store.append({"schema": "nope"})
        self.assertEqual(self.store.read_all(), [])

    def test_lines_are_valid_json(self):
        self.store.append(
            make_event(
                node_id="n", freq_hz=2437e6, snr_db=10.0, confidence=0.5,
                classification="unknown",
            )
        )
        with open(self.store.events_path, encoding="utf-8") as fh:
            for line in fh:
                json.loads(line)

    def test_evidence_is_written_and_path_returned(self):
        path = self.store.write_evidence("node-01", "frame.iq16", b"\x00\x01\x02")
        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"\x00\x01\x02")

    def test_evidence_text_mode(self):
        path = self.store.write_evidence("node-01", "notes.txt", "brak zakłóceń")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "brak zakłóceń")


class TestReport(unittest.TestCase):
    def _event(self):
        return make_event(
            node_id="node-01",
            freq_hz=2437e6,
            snr_db=18.4,
            confidence=0.83,
            classification="drone_like",
            bearing_deg=137.5,
            bearing_sigma_deg=6.0,
            width_hz=1.2e6,
        )

    def test_html_is_polish_and_contains_the_event(self):
        html = render_report_html(self._event())
        self.assertIn("Raport incydentu", html)
        self.assertIn("2437.00 MHz", html)
        self.assertIn("137.5", html)
        self.assertIn('<html lang="pl">', html)

    def test_html_carries_the_legal_disclaimer(self):
        html = render_report_html(self._event())
        self.assertIn("nie neutralizuje", html)
        self.assertIn("156ze", html)

    def test_html_carries_limitations(self):
        html = render_report_html(self._event())
        self.assertIn("światłowodem", html)

    def test_text_report_has_disclaimer(self):
        text = render_report_text(self._event())
        self.assertIn(DISCLAIMER_PL[:40], text)
        self.assertIn(LIMITATIONS_PL[:40], text)

    def test_report_includes_position_when_given(self):
        position = {
            "lat": 51.264, "lon": 15.57, "cep_m": 65.0,
            "sources": ["node-01", "node-02"], "confidence": 0.8, "acknowledged": True,
        }
        html = render_report_html(self._event(), position)
        self.assertIn("51.264", html)
        self.assertIn("node-02", html)
        self.assertIn("potwierdzone", html)

    def test_unacknowledged_shows_as_not_confirmed(self):
        html = render_report_html(self._event())
        self.assertIn("niepotwierdzone", html)

    def test_filename_is_stable(self):
        name = report_filename(self._event())
        self.assertTrue(name.startswith("raport-"))
        self.assertTrue(name.endswith(".html"))


if __name__ == "__main__":
    unittest.main()
