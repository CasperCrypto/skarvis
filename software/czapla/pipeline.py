"""Pipeline: wire sensing, classification, policy, storage and reporting together.

Does:
    One function that takes a spectrum or a set of raw detections and runs the whole
    chain: detect -> classify -> alarm decision -> persist -> report. Plus a --demo
    mode that runs entirely on synthetic signals with no hardware, which is how the
    logic is developed and tested before the radio exists.

Does NOT do:
    Touch hardware directly. Capture lives on the node; this module receives what
    the node produced, so it runs identically on a laptop with synthetic input.

Run:
    python -m czapla.pipeline --demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .baseline import BaselineTracker
from .classifier import classify
from .detector import find_candidates, noise_floor_db, power_spectrum_db
from .events import EventStore, make_event, make_position
from .fusion import fuse_all
from .policy import AlarmPolicy, AlarmState, Whitelist, parse_iso

DEFAULT_STORE = os.path.join(os.getcwd(), "czapla-data")


def synthesise_wifi_like(
    n_samples: int = 4096, sample_rate_hz: float = 20e6, carrier_hz: float = 2437e6
) -> list[float]:
    """A narrowband-ish carrier plus noise. Used to exercise the chain in --demo.

    This is a TEST SIGNAL, not a drone recording. It proves the software runs end
    to end; it proves nothing about detection performance. Real validation needs a
    real transmitter (see hardware/test-plan.md T-2).
    """
    import math
    import random

    rng = random.Random(1337)
    out: list[float] = []
    for i in range(n_samples):
        t = i / sample_rate_hz
        carrier = 0.35 * math.sin(2.0 * math.pi * (carrier_hz % sample_rate_hz) * t)
        noise = 0.05 * rng.gauss(0.0, 1.0)
        out.append(carrier + noise)
    return out


def process_detections(
    detections: list[dict],
    store: EventStore,
    policy: AlarmPolicy | None = None,
    whitelist: Whitelist | None = None,
    baseline: "BaselineTracker | None" = None,
    state: AlarmState | None = None,
) -> list[dict]:
    """Classify, decide, persist. Returns the alarm decisions in order.

    Pass a long-lived AlarmState to keep cooldowns across calls (a running node,
    a replay, the simulator); by default each call starts fresh. A detection
    that carries ts_utc is judged and stored at that time instead of "now".

    If a baseline tracker is supplied, its occupancy history is consulted first:
    a frequency that has been present in nearly every recent scan is treated as
    fixed infrastructure and is not classified as drone-like, whatever its other
    features look like. That is the only thing that separates a Wi-Fi access point
    from a drone video downlink in a single snapshot.
    """
    state = state or AlarmState(policy or AlarmPolicy(), whitelist or Whitelist())
    decisions: list[dict] = []

    for det in detections:
        freq_mhz = det["freq_hz"] / 1e6
        persistent = baseline.is_persistent(freq_mhz) if baseline is not None else False

        if persistent:
            verdict = {
                "label": "other",
                "score": 0.0,
                "confidence": 0.5,
                "version": "baseline-persistence-gate",
                "features": {"baseline_persistent": True},
                "disclaimer": (
                    "frequency present continuously in the recent baseline, "
                    "treated as fixed infrastructure"
                ),
            }
        else:
            verdict = classify(
                snr_db=det["snr_db"],
                freq_hz=det["freq_hz"],
                width_hz=det.get("width_hz", 0.0),
                freq_hop_count=det.get("freq_hop_count", 1),
            )

        ts_utc = det.get("ts_utc")
        decision = state.evaluate(
            {
                "freq_hz": det["freq_hz"],
                "snr_db": det["snr_db"],
                "confidence": verdict["confidence"],
                "classification": verdict["label"],
            },
            node_id=det.get("node_id", "unknown"),
            when=parse_iso(ts_utc) if ts_utc else None,
        )
        event = make_event(
            node_id=det.get("node_id", "unknown"),
            freq_hz=det["freq_hz"],
            snr_db=det["snr_db"],
            confidence=verdict["confidence"],
            classification=verdict["label"],
            bearing_deg=det.get("bearing_deg"),
            bearing_sigma_deg=det.get("bearing_sigma_deg"),
            width_hz=det.get("width_hz"),
            node_position=det.get("node_position"),
            evidence=det.get("evidence", {}),
            alarm=bool(decision["alarm"]),
            ts_utc=ts_utc,
            extra={
                "classifier": verdict["version"],
                "classifier_score": verdict["score"],
                "classifier_features": verdict["features"],
                "alarm_reason": decision["reason"],
                "baseline_persistent": persistent,
            },
        )
        store.append(event)
        decisions.append({"event": event, "decision": decision, "verdict": verdict})

    if baseline is not None:
        baseline.observe([d["freq_hz"] / 1e6 for d in detections])

    return decisions


def process_spectrum(
    samples: list[float],
    sample_rate_hz: float,
    center_freq_hz: float,
    node_id: str,
    store: EventStore,
    min_snr_db: float = 6.0,
    node_position: dict | None = None,
    bearing_deg: float | None = None,
    bearing_sigma_deg: float | None = None,
    baseline: "BaselineTracker | None" = None,
) -> list[dict]:
    """Full chain from raw samples: spectrum -> candidates -> classify -> persist."""
    spectrum = power_spectrum_db(samples, sample_rate_hz, center_freq_hz)
    candidates = find_candidates(spectrum, min_snr_db=min_snr_db)
    detections = [
        {
            "node_id": node_id,
            "freq_hz": c["freq_hz"],
            "snr_db": c["snr_db"],
            "width_hz": c["width_hz"],
            "bearing_deg": bearing_deg,
            "bearing_sigma_deg": bearing_sigma_deg,
            "node_position": node_position,
        }
        for c in candidates
    ]
    return process_detections(detections, store, baseline=baseline)


def demo(store_root: str = DEFAULT_STORE) -> int:
    """Run the chain on synthetic signals. No hardware, no network."""
    store = EventStore(store_root)
    sample_rate_hz = 20e6
    samples = synthesise_wifi_like(sample_rate_hz=sample_rate_hz)
    spectrum = power_spectrum_db(samples, sample_rate_hz, 2437e6)

    print("CZAPLA — demo (SYNTHETIC SIGNAL, no hardware, no real detection)")
    print(f"noise floor: {noise_floor_db(spectrum):.1f} dB")
    candidates = find_candidates(spectrum)
    print(f"candidate peaks: {len(candidates)}")
    for c in candidates[:5]:
        print(f"  {c['freq_hz'] / 1e6:10.3f} MHz  SNR {c['snr_db']:5.1f} dB  width {c['width_hz'] / 1e6:.2f} MHz")

    decisions = process_detections(
        [
            {
                "node_id": "demo-node-01",
                "freq_hz": c["freq_hz"],
                "snr_db": c["snr_db"],
                "width_hz": c["width_hz"],
                "freq_hop_count": 1,
                "bearing_deg": 137.5,
                "bearing_sigma_deg": 6.0,
                "node_position": {"lat": 51.2631, "lon": 15.5672, "alt_m": 18.0},
            }
            for c in candidates
        ],
        store,
    )

    print(f"\nevents written: {len(decisions)} -> {store.events_path}")
    for d in decisions:
        v = d["verdict"]
        print(
            f"  {v['label']:10s} score {v['score']:.2f} conf {v['confidence']:.2f} "
            f"alarm={d['decision']['alarm']} ({d['decision']['reason']})"
        )

    if len(decisions) >= 1:
        print("\nsample event JSON:")
        print(json.dumps(decisions[0]["event"], ensure_ascii=False, indent=2)[:900])
    return 0


def demo_fusion(store_root: str = DEFAULT_STORE) -> int:
    """Two synthetic nodes with bearings that should intersect. No hardware."""
    ref_lat, ref_lon = 51.2631, 15.5672
    store = EventStore(store_root)

    # node-01 is 300 m east of the reference; node-02 is 300 m north.
    from .geometry import latlon_to_local, local_to_latlon

    e1, n1 = 300.0, 0.0
    e2, n2 = 0.0, 300.0
    lat1, lon1 = local_to_latlon(e1, n1, ref_lat, ref_lon)
    lat2, lon2 = local_to_latlon(e2, n2, ref_lat, ref_lon)
    # A target due north-east of the origin: bearings from each node point at it.
    target_e, target_n = 500.0, 500.0
    import math

    b1 = math.degrees(math.atan2(target_e - e1, target_n - n1)) % 360.0
    b2 = math.degrees(math.atan2(target_e - e2, target_n - n2)) % 360.0

    detections = [
        {
            "node_id": "node-01",
            "freq_hz": 2437e6,
            "snr_db": 18.0,
            "width_hz": 1.5e6,
            "bearing_deg": b1,
            "bearing_sigma_deg": 5.0,
            "node_position": {"lat": lat1, "lon": lon1},
            "ts_utc": "2026-10-22T12:00:00Z",
        },
        {
            "node_id": "node-02",
            "freq_hz": 2437.5e6,
            "snr_db": 16.0,
            "width_hz": 1.5e6,
            "bearing_deg": b2,
            "bearing_sigma_deg": 5.0,
            "node_position": {"lat": lat2, "lon": lon2},
            "ts_utc": "2026-10-22T12:00:02Z",
        },
    ]

    print("CZAPLA — fusion demo (SYNTHETIC bearings, no hardware)")
    for r in fuse_all(detections, ref_lat, ref_lon):
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if r.get("fused"):
            record = make_position(
                sources=r["sources"],
                lat=r["lat"],
                lon=r["lon"],
                confidence=r["confidence"],
                cep_m=r["cep_estimate_m"],
                extra={"synthetic": True},
            )
            store.append(record)
            print(f"position record written: {record['position_id']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CZAPLA detection pipeline")
    parser.add_argument("--demo", action="store_true", help="synthetic single-node run")
    parser.add_argument("--demo-fusion", action="store_true", help="synthetic two-node run")
    parser.add_argument("--store", default=DEFAULT_STORE, help="event store root directory")
    args = parser.parse_args(argv)

    if args.demo_fusion:
        return demo_fusion(args.store)
    if args.demo:
        return demo(args.store)

    parser.print_help()
    print("\nNothing runs without --demo (no hardware capture is implemented in v1).")
    return 2


if __name__ == "__main__":
    sys.exit(main())
