"""Event schema, durable event store, and evidence blobs.

Does:
    Validates, creates and persists detection, position and ground-object
    records as JSONL, and writes evidence files next to them. Append-only: an
    incident record that can be edited after the fact is worthless as evidence.

Does NOT do:
    Any detection, classification or alarm logic. This is storage and schema.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from . import SCHEMA_EVENT, SCHEMA_GROUND, SCHEMA_POSITION

EVENT_REQUIRED = (
    "schema",
    "event_id",
    "ts_utc",
    "node_id",
    "sensor",
    "freq_hz",
    "snr_db",
    "confidence",
    "classification",
)

POSITION_REQUIRED = (
    "schema",
    "position_id",
    "ts_utc",
    "sources",
    "lat",
    "lon",
    "confidence",
)

GROUND_REQUIRED = (
    "schema",
    "ground_id",
    "ts_utc",
    "node_id",
    "track_id",
    "sensors",
    "classification",
    "confidence",
    "alarm",
)

GROUND_CLASSES = ("human", "animal", "vehicle", "unknown")


class SchemaError(ValueError):
    """Raised when a record does not match the frozen v1 schema."""


def new_id() -> str:
    """Short unique id. Sorts roughly by creation time like a ULID."""
    return f"{int(datetime.now(timezone.utc).timestamp() * 1000):013d}-{uuid.uuid4().hex[:8]}"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_event(
    node_id: str,
    freq_hz: float,
    snr_db: float,
    confidence: float,
    classification: str,
    bearing_deg: float | None = None,
    bearing_sigma_deg: float | None = None,
    band_mhz: float | None = None,
    node_position: dict | None = None,
    evidence: dict | None = None,
    sensor: str = "rf",
    width_hz: float | None = None,
    alarm: bool = False,
    extra: dict | None = None,
    ts_utc: str | None = None,
) -> dict:
    """Build a schema-valid detection event.

    ts_utc defaults to now; replay and simulation pass the time the detection
    was actually made.
    """
    event = {
        "schema": SCHEMA_EVENT,
        "event_id": new_id(),
        "ts_utc": ts_utc or utc_iso(),
        "node_id": node_id,
        "sensor": sensor,
        "freq_hz": float(freq_hz),
        "band_mhz": float(band_mhz) if band_mhz is not None else round(freq_hz / 1e6, 3),
        "snr_db": float(snr_db),
        "bearing_deg": bearing_deg,
        "bearing_sigma_deg": bearing_sigma_deg,
        "confidence": float(confidence),
        "classification": classification,
        "width_hz": width_hz,
        "node_position": node_position,
        "evidence": evidence or {},
        "position_estimate": None,
        "alarm": bool(alarm),
    }
    if extra:
        reserved = set(event) | {"schema", "event_id"}
        clashes = reserved & set(extra)
        if clashes:
            raise SchemaError(f"extra would overwrite reserved keys: {sorted(clashes)}")
        event.update(extra)
    validate_event(event)
    return event


def make_position(
    sources: list[str],
    lat: float,
    lon: float,
    confidence: float,
    cep_m: float | None = None,
    alarm: bool = True,
    acknowledged: bool = False,
    extra: dict | None = None,
    ts_utc: str | None = None,
) -> dict:
    """Build a schema-valid fused position record."""
    record = {
        "schema": SCHEMA_POSITION,
        "position_id": new_id(),
        "ts_utc": ts_utc or utc_iso(),
        "sources": list(sources),
        "lat": float(lat),
        "lon": float(lon),
        "cep_m": cep_m,
        "confidence": float(confidence),
        "alarm": bool(alarm),
        "acknowledged": bool(acknowledged),
    }
    if extra:
        reserved = set(record) | {"schema", "position_id"}
        clashes = reserved & set(extra)
        if clashes:
            raise SchemaError(f"extra would overwrite reserved keys: {sorted(clashes)}")
        record.update(extra)
    validate_position(record)
    return record


def make_ground(
    node_id: str,
    track_id: str,
    sensors: list[str],
    classification: str,
    confidence: float,
    east_m: float | None = None,
    north_m: float | None = None,
    inside_perimeter: bool | None = None,
    alarm: bool = False,
    extra: dict | None = None,
    ts_utc: str | None = None,
) -> dict:
    """Build a schema-valid ground-object record (person, animal, vehicle).

    One record per notable change of a ground track: first seen, class changed,
    alarm raised. Positions are metres east/north of the site reference point.
    """
    record = {
        "schema": SCHEMA_GROUND,
        "ground_id": new_id(),
        "ts_utc": ts_utc or utc_iso(),
        "node_id": node_id,
        "track_id": track_id,
        "sensors": sorted(set(sensors)),
        "classification": classification,
        "confidence": float(confidence),
        "east_m": east_m,
        "north_m": north_m,
        "inside_perimeter": inside_perimeter,
        "alarm": bool(alarm),
        "acknowledged": False,
    }
    if extra:
        reserved = set(record)
        clashes = reserved & set(extra)
        if clashes:
            raise SchemaError(f"extra would overwrite reserved keys: {sorted(clashes)}")
        record.update(extra)
    validate_ground(record)
    return record


def validate_event(event: dict) -> None:
    missing = [k for k in EVENT_REQUIRED if k not in event]
    if missing:
        raise SchemaError(f"event missing required fields: {missing}")
    if event["schema"] != SCHEMA_EVENT:
        raise SchemaError(f"wrong schema: {event['schema']!r}")
    if not isinstance(event["sources"] if "sources" in event else [], list):
        raise SchemaError("sources must be a list")
    conf = event["confidence"]
    if not isinstance(conf, (int, float)) or not 0.0 <= float(conf) <= 1.0:
        raise SchemaError("confidence must be a number in [0, 1]")
    if event["classification"] not in ("drone_like", "unknown", "other"):
        raise SchemaError(f"bad classification: {event['classification']!r}")


def validate_position(record: dict) -> None:
    missing = [k for k in POSITION_REQUIRED if k not in record]
    if missing:
        raise SchemaError(f"position missing required fields: {missing}")
    if record["schema"] != SCHEMA_POSITION:
        raise SchemaError(f"wrong schema: {record['schema']!r}")
    if len(record["sources"]) < 2:
        raise SchemaError("a position estimate needs at least two sources")
    lat, lon = float(record["lat"]), float(record["lon"])
    if not -90.0 <= lat <= 90.0:
        raise SchemaError("lat out of range")
    if not -180.0 <= lon <= 180.0:
        raise SchemaError("lon out of range")


def validate_ground(record: dict) -> None:
    missing = [k for k in GROUND_REQUIRED if k not in record]
    if missing:
        raise SchemaError(f"ground record missing required fields: {missing}")
    if record["schema"] != SCHEMA_GROUND:
        raise SchemaError(f"wrong schema: {record['schema']!r}")
    if not isinstance(record["sensors"], list) or not record["sensors"]:
        raise SchemaError("sensors must be a non-empty list")
    if record["classification"] not in GROUND_CLASSES:
        raise SchemaError(f"bad ground classification: {record['classification']!r}")
    conf = record["confidence"]
    if not isinstance(conf, (int, float)) or not 0.0 <= float(conf) <= 1.0:
        raise SchemaError("confidence must be a number in [0, 1]")


class EventStore:
    """Append-only JSONL store plus an evidence directory.

    Layout:
        <root>/events.jsonl              one JSON object per line
        <root>/evidence/<date>/<node>/   raw blobs referenced by evidence paths
    """

    def __init__(self, root: str) -> None:
        self.root = root
        os.makedirs(self.root, exist_ok=True)
        self.events_path = os.path.join(self.root, "events.jsonl")

    def append(self, record: dict) -> None:
        schema = record.get("schema")
        if schema == SCHEMA_EVENT:
            validate_event(record)
        elif schema == SCHEMA_POSITION:
            validate_position(record)
        elif schema == SCHEMA_GROUND:
            validate_ground(record)
        else:
            raise SchemaError(f"unknown schema: {schema!r}")
        # One write call per record keeps lines from interleaving between processes.
        with open(self.events_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.events_path):
            return []
        out: list[dict] = []
        with open(self.events_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def evidence_path(self, node_id: str, name: str, when: datetime | None = None) -> str:
        when = when or datetime.now(timezone.utc)
        day = when.strftime("%Y-%m-%d")
        directory = os.path.join(self.root, "evidence", day, node_id)
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, name)

    def write_evidence(
        self, node_id: str, name: str, payload: bytes | str
    ) -> str:
        path = self.evidence_path(node_id, name)
        mode = "wb" if isinstance(payload, bytes) else "w"
        kwargs = {} if isinstance(payload, bytes) else {"encoding": "utf-8"}
        with open(path, mode, **kwargs) as fh:
            fh.write(payload)
        return path
