"""Scenario simulator: synthetic drones, people, animals and vehicles through the
real CZAPLA pipeline.

Does:
    Moves scripted actors (drones, people, animals, vehicles) over a site, models
    what each configured sensor would report under STATED ASSUMPTIONS, and pushes
    those reports through the same classifier, baseline, alarm policy, fusion and
    event store the real system uses. Scores the outcome per actor (seen? alarmed?
    how early? right class?) and writes a run file that the browser trainer
    (web/sim) plays back for operator drills.

Does NOT do:
    Measure anything. Every range, SNR, accuracy and false-positive figure comes
    from the scenario file and is an assumption until hardware/results.md has a
    measured value. A simulator score is a property of those assumptions, never of
    the product, and must never be quoted to a buyer as detection performance.
    Flight is straight segments at constant speed; there is no terrain, multipath,
    weather or interference model; ground observations are associated to tracks
    using ground truth, which a real system has to do for itself.
    There is no attack, evasion or countermeasure modelling, by design.

Run:
    python -m czapla.sim                          # built-in demo scenario
    python -m czapla.sim --no-store --out ../web/sim/runs/podstacja.js
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone

from . import SCHEMA_EVENT, SCHEMA_GROUND, SCHEMA_POSITION, __version__
from .baseline import BaselineTracker
from .events import EventStore, make_event, make_ground, make_position
from .events import validate_event, validate_ground, validate_position
from .fusion import fuse_all
from .geometry import (
    KRAKENSDR_MAX_MHZ,
    KRAKENSDR_MIN_MHZ,
    MLX90640_FOV_H_DEG,
    MLX90640_FOV_V_DEG,
    MLX90640_PIXELS_H,
    MLX90640_PIXELS_V,
    latlon_to_local,
    local_to_latlon,
    path_snr_db,
    pixel_footprint_m,
    point_in_polygon,
    unit_to_bearing,
    wrap_180,
)
from .ground import classify_track
from .pipeline import DEFAULT_STORE, process_detections
from .policy import AlarmPolicy, AlarmState, GroundAlarmState, GroundPolicy, Whitelist

SIM_SCHEMA = "skarvis.simrun/1"
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
DEFAULT_SCENARIO = os.path.join(SCENARIO_DIR, "podstacja.json")

AIR_SENSORS = ("remote_id", "rf_df")
GROUND_SENSORS = ("thermal", "radar_mmwave", "pir", "camera_ai")
ACTOR_KINDS = ("drone", "human", "animal", "vehicle")

# Representative 2.4 GHz carrier for broadcast Remote ID records. Illustrative:
# the schema needs a frequency, the decoded message is what matters.
REMOTE_ID_FREQ_HZ = 2437e6

DISCLAIMER_PL = (
    "SYMULACJA. Dane syntetyczne. Zasięgi, poziomy sygnału i dokładności są "
    "założeniami scenariusza, nie pomiarami. Wynik symulacji opisuje założenia, "
    "a nie skuteczność systemu."
)


class ScenarioError(ValueError):
    """Raised when a scenario asks for something the modelled hardware cannot do."""


# --- scenario loading -------------------------------------------------------------


def load_scenario(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        scenario = json.load(fh)
    validate_scenario(scenario)
    return scenario


def validate_scenario(sc: dict) -> None:
    for key in ("name", "duration_s", "site", "sensors", "actors"):
        if key not in sc:
            raise ScenarioError(f"scenario missing {key!r}")
    site = sc["site"]
    for key in ("ref_lat", "ref_lon", "perimeter"):
        if key not in site:
            raise ScenarioError(f"site missing {key!r}")
    if len(site["perimeter"]) < 3:
        raise ScenarioError("perimeter needs at least three corners")

    ids = set()
    for s in sc["sensors"]:
        if s.get("id") in ids:
            raise ScenarioError(f"duplicate sensor id {s.get('id')!r}")
        ids.add(s.get("id"))
        if s.get("type") not in AIR_SENSORS + GROUND_SENSORS:
            raise ScenarioError(f"unknown sensor type {s.get('type')!r}")
        if s["type"] == "rf_df":
            for lo, hi in s.get("bands_mhz", []):
                if lo < KRAKENSDR_MIN_MHZ or hi > KRAKENSDR_MAX_MHZ:
                    raise ScenarioError(
                        f"{s['id']}: band {lo}-{hi} MHz is outside the KrakenSDR "
                        f"tuning range {KRAKENSDR_MIN_MHZ:.0f}-{KRAKENSDR_MAX_MHZ:.0f} MHz"
                    )
    for a in sc["actors"]:
        if a.get("kind") not in ACTOR_KINDS:
            raise ScenarioError(f"unknown actor kind {a.get('kind')!r}")
        if len(a.get("path", [])) < 2:
            raise ScenarioError(f"actor {a.get('id')!r} needs a path of two or more points")
        if a.get("speed_mps", 0) <= 0:
            raise ScenarioError(f"actor {a.get('id')!r} needs a positive speed")


# --- actors -------------------------------------------------------------------------


class Actor:
    """A scripted mover: constant speed along a polyline, optional hover at the end."""

    def __init__(self, spec: dict) -> None:
        self.spec = spec
        self.id = spec["id"]
        self.kind = spec["kind"]
        self.path = [(float(p[0]), float(p[1])) for p in spec["path"]]
        self.speed = float(spec["speed_mps"])
        self.start = float(spec.get("start_s", 0.0))
        self.hold = float(spec.get("hold_s", 0.0))
        self.alt = float(spec.get("altitude_m", 0.0))
        self._seg = [math.dist(a, b) for a, b in zip(self.path, self.path[1:])]
        self.length = sum(self._seg)

    def state(self, t: float) -> dict | None:
        """Position at time t, or None before it appears / after it has left."""
        if t < self.start:
            return None
        travelled = (t - self.start) * self.speed
        moving = True
        if travelled >= self.length:
            if t - self.start - self.length / self.speed > self.hold:
                return None
            travelled, moving = self.length, False
        last = len(self._seg) - 1
        for i, ((a, b), seg) in enumerate(zip(zip(self.path, self.path[1:]), self._seg)):
            if travelled <= seg or i == last:
                f = 1.0 if seg == 0 else min(1.0, travelled / seg)
                return {
                    "east": a[0] + (b[0] - a[0]) * f,
                    "north": a[1] + (b[1] - a[1]) * f,
                    "alt": self.alt,
                    "heading": unit_to_bearing(b[0] - a[0], b[1] - a[1]),
                    "speed": self.speed if moving else 0.0,
                }
            travelled -= seg
        return None


# --- stores -------------------------------------------------------------------------


class MemoryStore:
    """Validating in-memory stand-in for EventStore, for tests and --no-store."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def append(self, record: dict) -> None:
        validators = {
            SCHEMA_EVENT: validate_event,
            SCHEMA_POSITION: validate_position,
            SCHEMA_GROUND: validate_ground,
        }
        validators[record["schema"]](record)
        self.records.append(record)


class SyntheticStore:
    """Stamps every record as synthetic before it reaches the real store.

    A simulated record must never be mistaken for a detection: the stamp travels
    with the record into the event log, the reports and anything an integrator
    reads.
    """

    def __init__(self, inner, scenario_name: str) -> None:
        self.inner = inner
        self.scenario_name = scenario_name

    def append(self, record: dict) -> None:
        record["synthetic"] = True
        record["sim_scenario"] = self.scenario_name
        self.inner.append(record)


class FrozenBaseline:
    """A baseline learned during warm-up and not updated while the scenario runs."""

    def __init__(self, tracker: BaselineTracker) -> None:
        self.tracker = tracker

    def is_persistent(self, freq_mhz: float) -> bool:
        return self.tracker.is_persistent(freq_mhz)

    def observe(self, frequencies_mhz: list[float]) -> None:
        pass


# --- the simulator ------------------------------------------------------------------


def _due(t: float, period: float) -> bool:
    k = t / period
    return abs(k - round(k)) < 1e-6


def _r(x: float | None, digits: int = 1) -> float | None:
    return None if x is None else round(float(x), digits)


class Simulator:
    def __init__(self, scenario: dict, store=None) -> None:
        validate_scenario(scenario)
        self.sc = scenario
        self.rng = random.Random(scenario.get("seed", 1))
        site = scenario["site"]
        self.ref_lat = float(site["ref_lat"])
        self.ref_lon = float(site["ref_lon"])
        self.perimeter = site["perimeter"]
        self.zone_r = float(site.get("airspace_radius_m", 400.0))
        self.step = float(scenario.get("step_s", 1.0))
        self.duration = float(scenario["duration_s"])
        start = scenario.get("start_utc", "2026-01-01T00:00:00Z")
        self.t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))

        self.store = SyntheticStore(store or MemoryStore(), scenario["name"])
        policy = scenario.get("policy", {})
        self.air_state = AlarmState(
            AlarmPolicy(**policy.get("air", {})), Whitelist(scenario.get("whitelist", []))
        )
        self.ground_state = GroundAlarmState(GroundPolicy(**policy.get("ground", {})))
        self.window_s = float(policy.get("ground_window_s", 8.0))
        self.incident_merge_s = float(policy.get("incident_merge_s", 120.0))

        self.sensors = scenario["sensors"]
        self.actors = [Actor(a) for a in scenario["actors"]]
        self.emitters = scenario.get("emitters", [])

        base_cfg = dict(scenario.get("baseline", {}))
        self.warmup_scans = int(base_cfg.pop("warmup_scans", 0))
        self.learn_during_run = bool(base_cfg.pop("learn_during_run", True))
        self.baselines = {
            s["id"]: BaselineTracker(**base_cfg) for s in self.sensors if s["type"] == "rf_df"
        }

        self.frames: list[dict] = []
        self.events: list[dict] = []
        self.incidents: list[dict] = []
        self.obs: dict[str, list[dict]] = {}
        self.track_ids: dict[str, str] = {}
        self.track_last: dict[str, dict] = {}

    # time helpers
    def ts(self, t: float) -> str:
        when = self.t0 + timedelta(seconds=t)
        return when.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def node_pos(self, s: dict) -> dict:
        lat, lon = local_to_latlon(s["east"], s["north"], self.ref_lat, self.ref_lon)
        return {"lat": round(lat, 6), "lon": round(lon, 6), "alt_m": s.get("alt_m")}

    def gauss(self, sigma: float) -> float:
        return self.rng.gauss(0.0, sigma) if sigma > 0 else 0.0

    # geometry helpers
    @staticmethod
    def _look(s: dict, east: float, north: float) -> tuple[bool, float, float]:
        dx, dy = east - s["east"], north - s["north"]
        rng = math.hypot(dx, dy)
        bearing = unit_to_bearing(dx, dy) if rng > 1e-9 else 0.0
        if rng > float(s.get("range_m", 0.0)):
            return False, rng, bearing
        fov = float(s.get("fov_deg", 360.0))
        if fov < 360.0 and abs(wrap_180(bearing - float(s.get("heading_deg", 0.0)))) > fov / 2:
            return False, rng, bearing
        return True, rng, bearing

    # --- run ---------------------------------------------------------------------------

    def run(self) -> dict:
        self._warmup()
        if not self.learn_during_run:
            self.baselines = {k: FrozenBaseline(v) for k, v in self.baselines.items()}
        steps = int(round(self.duration / self.step))
        for i in range(steps + 1):
            t = round(i * self.step, 6)
            states = {a.id: a.state(t) for a in self.actors}
            frame = {"t": t, "actors": [], "tracks": []}
            for a in self.actors:
                st = states[a.id]
                if st is not None:
                    frame["actors"].append(
                        {"id": a.id, "e": _r(st["east"]), "n": _r(st["north"]),
                         "alt": _r(st["alt"])}
                    )
            for s in self.sensors:
                period = float(s.get("period_s", 1.0))
                if not _due(t, period):
                    continue
                if s["type"] == "rf_df":
                    self._scan_rf(s, t, states)
                elif s["type"] == "remote_id":
                    self._scan_remote_id(s, t, states)
                else:
                    self._observe_ground(s, t, states)
            self._fuse(t)
            self._update_tracks(t, frame)
            self.frames.append(frame)
        return self.result()

    def _warmup(self) -> None:
        """Teach each node's baseline the site's own fixed emitters, as at install."""
        for _ in range(self.warmup_scans):
            for s in self.sensors:
                if s["type"] != "rf_df":
                    continue
                freqs = [d["freq_hz"] / 1e6 for d, _ in self._rf_hits(s, -1.0, {})]
                self.baselines[s["id"]].observe(freqs)

    # --- air ---------------------------------------------------------------------------

    def _rf_hits(self, s: dict, t: float, states: dict) -> list[tuple[dict, str]]:
        """What one direction-finding node hears in one scan, with ground truth."""
        sources = [(e, {"east": e["east"], "north": e["north"], "alt": e.get("alt_m", 0.0)})
                   for e in self.emitters]
        for a in self.actors:
            st = states.get(a.id)
            if a.kind == "drone" and st is not None and not a.spec.get("fibre_optic"):
                sources.append((a.spec, st))
        hits = []
        for spec, st in sources:
            links = spec.get("links") or ([spec] if "freq_mhz" in spec else [])
            dist = math.dist((st["east"], st["north"], st["alt"]),
                             (s["east"], s["north"], s.get("alt_m", 0.0)))
            if dist > float(s.get("range_m", 1e9)):
                continue
            for link in links:
                f0 = float(link["freq_mhz"])
                if not any(lo <= f0 <= hi for lo, hi in s.get("bands_mhz", [])):
                    continue
                snr = path_snr_db(float(s["ref_snr_db"]), float(s["ref_dist_m"]), dist)
                snr += float(link.get("power_offset_db", 0.0))
                snr += self.gauss(s.get("snr_sigma_db", 0.0))
                if snr < float(s.get("min_snr_db", 6.0)):
                    continue
                hop = float(link.get("hop_mhz", 0.0))
                freq = f0 + (self.rng.uniform(-hop, hop) if hop else 0.0)
                true_bearing = unit_to_bearing(st["east"] - s["east"], st["north"] - s["north"])
                sigma = float(s.get("bearing_sigma_deg", 10.0))
                hits.append((
                    {
                        "node_id": s["id"],
                        "freq_hz": freq * 1e6,
                        "snr_db": round(snr, 2),
                        "width_hz": float(link.get("width_mhz", 1.0)) * 1e6,
                        "freq_hop_count": int(link.get("hop_count", 1)),
                        "bearing_deg": round((true_bearing + self.gauss(sigma)) % 360.0, 2),
                        "bearing_sigma_deg": sigma,
                        "node_position": self.node_pos(s),
                        "ts_utc": self.ts(t),
                    },
                    spec["id"],
                ))
        return hits

    def _scan_rf(self, s: dict, t: float, states: dict) -> None:
        hits = self._rf_hits(s, t, states)
        decisions = process_detections(
            [d for d, _ in hits], self.store, state=self.air_state, baseline=self.baselines[s["id"]]
        )
        for (det, truth), d in zip(hits, decisions):
            event, decision, verdict = d["event"], d["decision"], d["verdict"]
            view = {
                "t": t,
                "type": "rf",
                "node": s["id"],
                "e": s["east"],
                "n": s["north"],
                "bearing": det["bearing_deg"],
                "sigma": det["bearing_sigma_deg"],
                "freq_mhz": round(det["freq_hz"] / 1e6, 2),
                "snr": det["snr_db"],
                "label": verdict["label"],
                "conf": verdict["confidence"],
                "persistent": event.get("baseline_persistent", False),
                "alarm": decision["alarm"],
                "reason": decision["reason"],
                "_det": det,
                "_truth": truth,
            }
            self.events.append(view)
            if decision["alarm"]:
                self._incident(view, "air", key="rf", title_pl="Emisja radiowa drona (namiar)")

    def _scan_remote_id(self, s: dict, t: float, states: dict) -> None:
        for a in self.actors:
            st = states.get(a.id)
            if a.kind != "drone" or st is None or not a.spec.get("remote_id"):
                continue
            dist = math.dist((st["east"], st["north"], st["alt"]),
                             (s["east"], s["north"], s.get("alt_m", 0.0)))
            if dist > float(s.get("range_m", 0.0)):
                continue
            snr = path_snr_db(
                float(s.get("ref_snr_db", 30.0)), float(s.get("ref_dist_m", 100.0)), dist
            )
            e = st["east"] + self.gauss(s.get("position_sigma_m", 3.0))
            n = st["north"] + self.gauss(s.get("position_sigma_m", 3.0))
            lat, lon = local_to_latlon(e, n, self.ref_lat, self.ref_lon)
            serial = a.spec["remote_id"]
            # The drone declared itself, so the label is not inferred; the
            # confidence is about the decode, not about whether it is honest.
            det = {"freq_hz": REMOTE_ID_FREQ_HZ, "snr_db": snr, "confidence": 0.95,
                   "classification": "drone_like", "rid_serial": serial}
            when = self.t0 + timedelta(seconds=t)
            decision = self.air_state.evaluate(det, node_id=s["id"], when=when)
            event = make_event(
                node_id=s["id"],
                freq_hz=REMOTE_ID_FREQ_HZ,
                snr_db=round(snr, 2),
                confidence=0.95,
                classification="drone_like",
                node_position=self.node_pos(s),
                sensor="remote_id",
                alarm=decision["alarm"],
                ts_utc=self.ts(t),
                extra={
                    "rid_serial": serial,
                    "rid_position": {
                        "lat": round(lat, 6), "lon": round(lon, 6), "alt_m": st["alt"]
                    },
                    "alarm_reason": decision["reason"],
                },
            )
            self.store.append(event)
            view = {
                "t": t,
                "type": "rid",
                "node": s["id"],
                "e": _r(e),
                "n": _r(n),
                "alt": _r(st["alt"]),
                "serial": serial,
                "alarm": decision["alarm"],
                "reason": decision["reason"],
                "whitelisted": decision.get("reason") == "whitelisted_authorised_flight",
                "_truth": a.id,
            }
            self.events.append(view)
            if decision["alarm"]:
                self._incident(
                    view, "air", key=f"rid:{serial}", title_pl=f"Dron z Remote ID {serial}"
                )

    def _fuse(self, t: float) -> None:
        recent = [
            v for v in self.events
            if v["type"] == "rf" and v["t"] == t and v["label"] == "drone_like"
        ]
        if len({v["node"] for v in recent}) < 2:
            return
        for fix in fuse_all([v["_det"] for v in recent], self.ref_lat, self.ref_lon):
            if not fix.get("fused"):
                continue
            record = make_position(
                sources=fix["sources"],
                lat=fix["lat"],
                lon=fix["lon"],
                confidence=fix["confidence"],
                cep_m=fix["cep_estimate_m"],
                alarm=any(v["alarm"] for v in recent),
                ts_utc=self.ts(t),
            )
            self.store.append(record)
            e, n = latlon_to_local(fix["lat"], fix["lon"], self.ref_lat, self.ref_lon)
            truths = [v["_truth"] for v in recent if v["node"] in fix["sources"]]
            self.events.append({
                "t": t,
                "type": "fix",
                "e": _r(e),
                "n": _r(n),
                "cep": _r(fix["cep_estimate_m"]),
                "sources": fix["sources"],
                "conf": fix["confidence"],
                "_truth": max(set(truths), key=truths.count) if truths else None,
            })

    # --- ground ------------------------------------------------------------------------

    def _observe_ground(self, s: dict, t: float, states: dict) -> None:
        for a in self.actors:
            st = states.get(a.id)
            if a.kind == "drone" or st is None:
                continue
            seen, rng, bearing = self._look(s, st["east"], st["north"])
            if not seen:
                continue
            obs = self._ground_model(s, a, st, rng, bearing)
            if obs is None:
                continue
            sigma = float(s.get("position_sigma_m", 1.5))
            obs.update({
                "t": t,
                "sensor_id": s["id"],
                "node": s.get("node", s["id"]),
                "e": st["east"] + self.gauss(sigma),
                "n": st["north"] + self.gauss(sigma),
            })
            self.obs.setdefault(a.id, []).append(obs)

    def _ground_model(
        self, s: dict, a: Actor, st: dict, rng: float, bearing: float
    ) -> dict | None:
        kind, spec, typ = a.kind, a.spec, s["type"]
        moving = st["speed"] > 0.05
        p_detect = float(s.get("p_detect", 1.0))
        if typ == "thermal":
            px_v = pixel_footprint_m(rng, s.get("fov_v_deg", MLX90640_FOV_V_DEG),
                                     s.get("pixels_v", MLX90640_PIXELS_V))
            px_h = pixel_footprint_m(rng, s.get("fov_h_deg", MLX90640_FOV_H_DEG),
                                     s.get("pixels_h", MLX90640_PIXELS_H))
            # Side-on we see the length, head-on the width.
            theta = math.radians(bearing - st["heading"])
            seen_w = abs(spec.get("length_m", 0.5) * math.sin(theta)) + abs(
                spec.get("width_m", 0.5) * math.cos(theta)
            )
            noise = float(s.get("size_sigma", 0.1))
            h = max(0.05, spec.get("height_m", 1.0) * (1 + self.gauss(noise)))
            w = max(0.05, seen_w * (1 + self.gauss(noise)))
            if h * w < float(s.get("min_fill", 0.3)) * px_v * max(px_h, 1e-6):
                return None  # too small at this range to stand out from background
            n_v = max(1, round(h / max(px_v, 1e-6)))
            n_h = max(1, round(w / max(px_h, 1e-6)))
            return {"sensor": "thermal", "height_m": round(n_v * px_v, 3),
                    "width_m": round(n_h * px_h, 3), "pixels_tall": n_v, "pixel_m": round(px_v, 4)}
        if typ == "radar_mmwave":
            if not moving or self.rng.random() > p_detect:
                return None
            gait = spec.get("gait_hz")
            return {
                "sensor": "radar_mmwave",
                "speed_mps": round(abs(st["speed"] + self.gauss(0.2)), 2),
                "gait_hz": round(gait + self.gauss(0.15), 2) if gait else None,
            }
        if typ == "pir":
            if not moving or self.rng.random() > p_detect:
                return None
            return {"sensor": "pir"}
        if typ == "camera_ai":
            if kind in ("human", "vehicle"):
                if self.rng.random() > p_detect:
                    return None
                label = "person" if kind == "human" else "vehicle"
                return {"sensor": "camera_ai", "label": label,
                        "score": round(min(0.99, 0.85 + self.gauss(0.05)), 2)}
            # Animals: most frames nothing, some frames a false "person". This is
            # the camera-only nuisance alarm sites complain about.
            if self.rng.random() < float(s.get("false_person_rate", 0.0)):
                return {"sensor": "camera_ai", "label": "person",
                        "score": round(min(0.9, 0.7 + self.gauss(0.05)), 2)}
            return None
        return None

    def _update_tracks(self, t: float, frame: dict) -> None:
        for actor_id, all_obs in self.obs.items():
            window = [o for o in all_obs if t - self.window_s < o["t"] <= t]
            if not window:
                continue
            latest_t = max(o["t"] for o in window)
            if latest_t < t - 2.0:
                continue  # track lost for now
            verdict = classify_track(window)
            recent = [o for o in window if o["t"] == latest_t]
            e = sum(o["e"] for o in recent) / len(recent)
            n = sum(o["n"] for o in recent) / len(recent)
            inside = point_in_polygon(e, n, self.perimeter)
            tid = self.track_ids.setdefault(actor_id, f"trk-{len(self.track_ids) + 1:03d}")
            decision = self.ground_state.evaluate(
                verdict, tid, inside, when=self.t0 + timedelta(seconds=t)
            )
            frame["tracks"].append({
                "id": tid, "e": _r(e), "n": _r(n), "label": verdict["label"],
                "conf": verdict["confidence"], "sensors": verdict["sensor_types"],
                "inside": inside, "_truth": actor_id,
            })
            last = self.track_last.get(tid)
            changed = (
                last is None
                or last["label"] != verdict["label"]
                or last["inside"] != inside
                or decision["alarm"]
            )
            self.track_last[tid] = {"label": verdict["label"], "inside": inside}
            if not changed:
                continue
            node = recent[0]["node"]
            record = make_ground(
                node_id=node,
                track_id=tid,
                sensors=verdict["sensor_types"],
                classification=verdict["label"],
                confidence=verdict["confidence"],
                east_m=round(e, 1),
                north_m=round(n, 1),
                inside_perimeter=inside,
                alarm=decision["alarm"],
                ts_utc=self.ts(t),
                extra={
                    "classifier": verdict["version"],
                    "classifier_probs": verdict["probs"],
                    "alarm_reason": decision["reason"],
                },
            )
            self.store.append(record)
            view = {
                "t": t,
                "type": "ground",
                "track": tid,
                "e": _r(e),
                "n": _r(n),
                "label": verdict["label"],
                "conf": verdict["confidence"],
                "sensors": verdict["sensor_types"],
                "inside": inside,
                "alarm": decision["alarm"],
                "reason": decision["reason"],
                "_truth": actor_id,
            }
            self.events.append(view)
            if decision["alarm"]:
                label_pl = {"human": "Osoba", "vehicle": "Pojazd"}.get(verdict["label"], "Obiekt")
                self._incident(view, "ground", key=f"track:{tid}",
                               title_pl=f"{label_pl} w obrębie ogrodzenia ({tid})")

    # --- incidents and scoring ---------------------------------------------------------

    def _incident(self, view: dict, domain: str, key: str, title_pl: str) -> None:
        """Group alarms into incidents an operator handles once (system-side rule:
        same key, within incident_merge_s of the incident's last alarm)."""
        for inc in reversed(self.incidents):
            if inc["key"] == key and view["t"] - inc["t_last"] <= self.incident_merge_s:
                inc["t_last"] = view["t"]
                inc["alarm_count"] += 1
                inc["_truths"].append(view.get("_truth"))
                return
        located = view["type"] in ("rid", "ground")
        self.incidents.append({
            "id": f"INC-{len(self.incidents) + 1:03d}",
            "domain": domain,
            "key": key,
            "t_open": view["t"],
            "t_last": view["t"],
            "alarm_count": 1,
            "title_pl": title_pl,
            "evidence_pl": self._evidence_pl(view),
            "ref": view.get("serial") or view.get("track"),
            "e": view.get("e") if located else None,
            "n": view.get("n") if located else None,
            "_truths": [view.get("_truth")],
        })

    @staticmethod
    def _evidence_pl(view: dict) -> str:
        """What the operator is shown when the alarm opens: system data only."""
        sensors_pl = {"thermal": "termowizja", "radar_mmwave": "radar", "pir": "PIR",
                      "camera_ai": "kamera"}
        labels_pl = {"human": "osoba", "vehicle": "pojazd", "animal": "zwierzę",
                     "unknown": "nieznany"}
        if view["type"] == "ground":
            used = ", ".join(sensors_pl.get(x, x) for x in view["sensors"])
            conf = f"{view['conf']:.2f}".replace(".", ",")
            label = labels_pl.get(view["label"], view["label"])
            return f"Klasyfikacja: {label} ({conf}). Czujniki: {used}."
        if view["type"] == "rid":
            return (f"Remote ID {view['serial']}: pozycja z komunikatu drona, "
                    f"wysokość {view['alt']:.0f} m. Numer nie jest na białej liście.")
        freq = f"{view['freq_mhz']:.1f}".replace(".", ",")
        return (f"Emisja {freq} MHz, SNR {view['snr']:.0f} dB, namiar {view['bearing']:.0f}° "
                f"z węzła {view['node']}. Brak Remote ID.")

    def _actor_expected_alarm(self, a: Actor) -> bool:
        if a.kind == "drone":
            return not a.spec.get("authorised", False)
        if a.kind in ("human", "vehicle"):
            # Expected only if the actor really entered the perimeter.
            for i in range(int(self.duration / self.step) + 1):
                st = a.state(i * self.step)
                if st and point_in_polygon(st["east"], st["north"], self.perimeter):
                    return True
        return False

    def _zone_entry(self, a: Actor) -> float | None:
        for i in range(int(self.duration / self.step) + 1):
            t = i * self.step
            st = a.state(t)
            if st and math.hypot(st["east"], st["north"]) <= self.zone_r:
                return t
        return None

    def scorecard(self) -> dict:
        per_actor = []
        alarm_truths = {}
        for inc in self.incidents:
            for truth in inc["_truths"]:
                alarm_truths.setdefault(truth, []).append(inc)

        for a in self.actors:
            seen = [v for v in self.events if v.get("_truth") == a.id and v["type"] != "fix"]
            incs = alarm_truths.get(a.id, [])
            first_alarm = min((i["t_open"] for i in incs), default=None)
            expected = self._actor_expected_alarm(a)
            row = {
                "id": a.id,
                "kind": a.kind,
                "label_pl": a.spec.get("label_pl", a.id),
                "detected": bool(seen),
                "first_detect_s": min((v["t"] for v in seen), default=None),
                "detected_by": sorted({v["type"] if v["type"] != "ground" else "ground"
                                      for v in seen}),
                "alarmed": bool(incs),
                "first_alarm_s": first_alarm,
                "expected_alarm": expected,
            }
            if a.kind == "drone":
                entry = self._zone_entry(a)
                row["zone_entry_s"] = entry
                if first_alarm is not None and entry is not None:
                    row["warning_before_zone_s"] = round(entry - first_alarm, 1)
                fixes = [v for v in self.events if v["type"] == "fix" and v.get("_truth") == a.id]
                errs = []
                for f in fixes:
                    st = a.state(f["t"])
                    if st:
                        errs.append(math.hypot(f["e"] - st["east"], f["n"] - st["north"]))
                row["position_fixes"] = len(fixes)
                row["median_fix_error_m"] = _r(sorted(errs)[len(errs) // 2]) if errs else None
                row["marked_infrastructure"] = sum(
                    1 for v in seen if v["type"] == "rf" and v.get("persistent")
                )
            else:
                labels = [v["label"] for v in seen if v["type"] == "ground"]
                row["labels_seen"] = sorted(set(labels))
                row["final_label"] = labels[-1] if labels else None
                # Moments one sensor type alone said "person"/"vehicle" and the
                # two-sensor rule held the alarm back.
                row["single_sensor_alarm_held"] = sum(
                    1 for v in seen
                    if v["type"] == "ground"
                    and v["label"] in ("human", "vehicle")
                    and "not_confirmed_by_second_sensor_type" in v["reason"]
                )

            if expected and row["alarmed"]:
                outcome = "true_alarm"
            elif expected:
                outcome = "missed"
            elif row["alarmed"]:
                outcome = "false_alarm"
            else:
                outcome = "correctly_quiet"
            row["outcome"] = outcome
            row["why_pl"] = self._why(a, row)
            per_actor.append(row)

        emitter_rows = []
        for em in self.emitters:
            incs = alarm_truths.get(em["id"], [])
            emitter_rows.append({
                "id": em["id"],
                "label_pl": em.get("label_pl", em["id"]),
                "alarmed": bool(incs),
                "outcome": "false_alarm" if incs else "correctly_quiet",
            })

        false_incidents = [
            inc["id"] for inc in self.incidents
            if not any(self._truth_expected(tr) for tr in inc["_truths"])
        ]
        return {
            "assumptions_not_measurements": True,
            "incidents": len(self.incidents),
            "true_alarm_actors": sum(1 for r in per_actor if r["outcome"] == "true_alarm"),
            "missed_actors": [r["id"] for r in per_actor if r["outcome"] == "missed"],
            "false_alarm_incidents": false_incidents,
            "actors": per_actor,
            "emitters": emitter_rows,
        }

    def _truth_expected(self, truth: str | None) -> bool:
        for a in self.actors:
            if a.id == truth:
                return self._actor_expected_alarm(a)
        return False

    def _why(self, a: Actor, row: dict) -> str:
        spec = a.spec
        if a.kind == "drone":
            if spec.get("fibre_optic"):
                return ("Dron sterowany światłowodem nie emituje sygnału radiowego. "
                        "Detekcja RF go nie widzi.")
            if spec.get("authorised") and not row["alarmed"]:
                return ("Lot autoryzowany: numer Remote ID na białej liście, "
                        "zdarzenie zapisane bez alarmu.")
            if row["outcome"] == "missed" and row.get("marked_infrastructure"):
                return ("Wykryty, ale baseline uznał go za stałą infrastrukturę, zanim "
                        "klasyfikator uznał go za drona.")
            if row["outcome"] == "missed" and not row["detected"]:
                return ("Brak Remote ID i brak łącza w pasmach węzłów "
                        "albo poza założonym zasięgiem.")
            if row["outcome"] == "missed":
                return "Wykryty, ale nie spełnił progów alarmu."
            if row["alarmed"]:
                via = " i ".join({"rid": "Remote ID", "rf": "namiar RF"}.get(x, x)
                                 for x in row["detected_by"])
                return f"Alarm na podstawie: {via}."
            return "Bez alarmu."
        if row["outcome"] == "false_alarm":
            return ("Fałszywy alarm: czujniki, które widziały obiekt, wskazały osobę. "
                    "Sprawdź, czy kamera termowizyjna obejmowała ten sektor.")
        if row["outcome"] == "missed":
            if not row["detected"]:
                return "Obiekt poza polem widzenia czujników naziemnych."
            return "Wykryty, ale bez potwierdzenia drugim typem czujnika albo poza ogrodzeniem."
        if row["outcome"] == "true_alarm":
            return "Alarm potwierdzony przez co najmniej dwa typy czujników."
        if row.get("final_label") == "animal" or "animal" in row.get("labels_seen", []):
            return "Rozpoznany jako zwierzę: zapisany, bez alarmu."
        if row["detected"] and not row["expected_alarm"]:
            return "Wykryty poza ogrodzeniem: zapisany, bez alarmu."
        return "Bez alarmu."

    # --- output ------------------------------------------------------------------------

    def result(self) -> dict:
        def public(d: dict) -> dict:
            out = {k: v for k, v in d.items() if not k.startswith("_")}
            if "_truth" in d:
                out["truth"] = d["_truth"]
            return out

        incidents = []
        for inc in self.incidents:
            truths = [x for x in inc["_truths"] if x]
            item = {k: v for k, v in inc.items() if not k.startswith("_") and k != "key"}
            item["truth"] = max(set(truths), key=truths.count) if truths else None
            item["truth_expected_alarm"] = any(self._truth_expected(x) for x in truths)
            incidents.append(item)

        return {
            "schema": SIM_SCHEMA,
            "synthetic": True,
            "generated_by": f"czapla.sim {__version__}",
            "disclaimer_pl": DISCLAIMER_PL,
            "note": (
                "Fields named 'truth' are simulator ground truth for the instructor "
                "view and scoring. The detection pipeline never sees them."
            ),
            "scenario": self.sc,
            "frames": [
                {**f, "tracks": [public(t) for t in f["tracks"]]} for f in self.frames
            ],
            "events": [public(e) for e in self.events],
            "incidents": incidents,
            "scorecard": self.scorecard(),
        }


def run_scenario(scenario: dict, store=None) -> dict:
    """Convenience wrapper: run one scenario, return the run dict."""
    return Simulator(scenario, store=store).run()


def _print_summary(run: dict) -> None:
    sc = run["scorecard"]
    print(f"SKARVIS / CZAPLA simulator — {run['scenario']['name']}")
    print("SYNTHETIC. Every number below follows from the scenario's assumptions;")
    print("none of it is a measurement of the product.\n")
    print(f"incidents raised: {sc['incidents']}   "
          f"false-alarm incidents: {len(sc['false_alarm_incidents'])}   "
          f"missed: {len(sc['missed_actors'])}")
    print()
    for r in sc["actors"]:
        extra = ""
        if r["kind"] == "drone" and r.get("warning_before_zone_s") is not None:
            extra = f"  warning {r['warning_before_zone_s']:+.0f}s vs zone entry"
        if r.get("final_label"):
            extra = f"  labels {','.join(r['labels_seen'])}"
        by = ",".join(r["detected_by"]) or "-"
        print(f"  {r['outcome']:16s} {r['id']:18s} detected_by={by}{extra}")
    for e in sc["emitters"]:
        print(f"  {e['outcome']:16s} {e['id']:18s} (fixed emitter on site)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SKARVIS scenario simulator (synthetic)")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, help="scenario JSON file")
    parser.add_argument("--out", help="write the run (for web/sim) to this JSON file")
    parser.add_argument(
        "--store",
        default=None,
        help="event store directory (default: czapla-data/sim/<run time>)",
    )
    parser.add_argument("--no-store", action="store_true", help="keep records in memory only")
    args = parser.parse_args(argv)

    try:
        scenario = load_scenario(args.scenario)
    except ScenarioError as exc:
        print(f"scenario rejected: {exc}", file=sys.stderr)
        return 2

    store = None
    if not args.no_store:
        root = args.store or os.path.join(
            DEFAULT_STORE, "sim", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
        store = EventStore(root)

    run = run_scenario(scenario, store=store)
    _print_summary(run)
    if store is not None:
        print(f"\nevent log (synthetic records): {store.events_path}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        payload = json.dumps(run, ensure_ascii=False, separators=(",", ":"))
        with open(args.out, "w", encoding="utf-8") as fh:
            # A .js run loads with a plain <script> tag, so the trainer opens
            # straight from disk (file://) with no web server.
            if args.out.endswith(".js"):
                fh.write(f"window.SKARVIS_RUN = {payload};\n")
            else:
                fh.write(payload)
        print(f"run file for the trainer: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
