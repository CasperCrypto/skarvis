# Architecture

Version 1, 2026-10-22. Two layers: the sensing node, and the software that turns
its output into an alarm and a record. Keep them separate — the node should be
replaceable (RF now, radar or acoustic later) without touching the rest.

## Layer diagram

```
   [ 2.4 GHz antenna array, 5 elements ]
                 |
        [ KrakenSDR coherent receiver ]        node, mast-mounted
                 |
        [ Raspberry Pi 5 ]
          - DAQ: coherent IQ capture
          - DoA: MUSIC / correlative interferometry -> bearing
          - detector: energy vs noise floor
                 |
          JSON event, one per line (UDP/HTTP over LAN)
                 |
   ============= LAN / PoE ==============
                 |
        [ CZAPLA core service ]              server or site PC
          - fusion: merge node events over time
          - triangulation: 2+ nodes -> position (or bearing-only if 1 node)
          - classifier: drone-like / other / unknown  (+ confidence)
          - whitelist: known authorised flights
          - alarm policy: thresholds, dedupe, cooldown
                 |
        [ Event store ]  append-only JSONL + raw evidence blobs
                 |
        +--------+---------+---------------+
        |                  |               |
  [ operator UI ]   [ report generator ]  [ outbound API ]
   live map, ACK     PL incident report    webhook/JSON for
   history           for protection plan   integrator PSIM
```

## Why it is split this way

- The node does only what must happen at the antenna: capture, direction, detect.
  Everything else can run anywhere, including on Casper's laptop during development.
- The interface between them is a plain line of JSON. That means a radar or a
  Remote ID receiver can be added as another event source later without a rewrite,
  and an integrator can consume our output without our software.
- No cloud dependency. A site with no internet still gets detection and records.

## Event schema (v1) — freeze this early

One JSON object per line. Additive changes only; never rename a field.

```json
{
  "schema": "czapla.event/1",
  "event_id": "01J...ULID-like",
  "ts_utc": "2026-10-22T14:03:11.482Z",
  "node_id": "node-01",
  "node_position": {"lat": 51.2631, "lon": 15.5672, "alt_m": 18.0},
  "sensor": "rf",
  "band_mhz": 2437.0,
  "bearing_deg": 137.5,
  "bearing_sigma_deg": 6.0,
  "confidence": 0.72,
  "classification": "drone_like",
  "snr_db": 14.2,
  "evidence": {
    "iq_path": "evidence/2026-10-22/node-01/144311.482.iq16",
    "spectrum_png": "evidence/2026-10-22/node-01/144311.482.spectrum.png"
  },
  "position_estimate": null,
  "alarm": false
}
```

Fusion adds a second record type when two nodes agree:

```json
{
  "schema": "czapla.position/1",
  "ts_utc": "...",
  "sources": ["node-01", "node-02"],
  "lat": 51.2640, "lon": 15.5701,
  "cep_m": 65.0,
  "confidence": 0.81,
  "alarm": true,
  "acknowledged": false
}
```

Ground objects (people, animals, vehicles; added 2026-10-28, see
`product/perimeter.md`) use a third record type. Positions are metres east and
north of the site reference point:

```json
{
  "schema": "czapla.ground/1",
  "ground_id": "...",
  "ts_utc": "...",
  "node_id": "straz-poludnie",
  "track_id": "trk-004",
  "sensors": ["camera_ai", "radar_mmwave", "thermal"],
  "classification": "human",
  "confidence": 0.86,
  "east_m": 25.8, "north_m": -99.3,
  "inside_perimeter": true,
  "alarm": true,
  "acknowledged": false
}
```

`classification` is one of `human`, `animal`, `vehicle`, `unknown`. Records made
by the simulator carry `"synthetic": true` and `"sim_scenario"`, so they can
never be mistaken for a detection.

Other additive fields since v1: `sensor: "remote_id"` events carry `rid_serial`
and `rid_position`; a whitelist entry may name a `rid_serial` instead of a
frequency.

## Software modules

| Module | Does | Does NOT do |
|---|---|---|
| `czapla/geometry.py` | Bearing maths, triangulation, unit conversions, earth model | Hold policy or thresholds |
| `czapla/detector.py` | Energy detection over a noise floor, SNR estimate | Classify, locate, alarm |
| `czapla/doa.py` | Direction of arrival from a 5-channel coherent snapshot | Capture samples |
| `czapla/fusion.py` | Merge detections across time and nodes into tracks | Persist anything |
| `czapla/classifier.py` | Score a detection as drone-like using documented features | Claim certainty |
| `czapla/policy.py` | Alarm thresholds, dedupe, cooldown, whitelist | Decide legal grounds |
| `czapla/baseline.py` | Rolling occupancy history per frequency, to tell infrastructure from a drone | Learn a spectrum model, or detect anything |
| `czapla/events.py` | Event schema, JSONL append, evidence blob handling | Alarm logic |
| `czapla/report.py` | Polish incident report for the site's protection file | Send anything |
| `czapla/pipeline.py` | Wire it together; `--demo` runs a simulated detection | Own any of the above |
| `czapla/node_rx.py` | Receive node JSON over LAN, validate schema | Capture RF itself |
| `czapla/ground.py` | Classify a ground object (human / animal / vehicle) from several sensor types | Detect, track, alarm, identify people |
| `czapla/sim.py` | Scenario simulator: synthetic actors and sensor reports through the real pipeline, scorecard, run file for `web/site/trener` | Measure anything; model attack, evasion or countermeasures |

## Dependency policy

Standard library only. Reasons: the Pi and the laptop must behave identically, the
project has no budget for a dependency-maintenance tax, and the maths involved
(FFT, correlative interferometry) is implementable in pure Python at the sample
rates v1 needs. If a real dependency becomes unavoidable, it goes in
`requirements.txt` with a comment naming the reason — and `CLAUDE.md` says so.

## Deployment shapes to support (v1 = first two)

1. **Bench / laptop only** — simulated or recorded IQ, no hardware. What we build and test now.
2. **One node + laptop** — real capture, bearing only, no position.
3. **Two nodes + site PC** — real position estimate. The demo.
4. **Site + operator UI + reports** — the sellable pilot.

## Interfaces we deliberately expose, because integrators ask for them

- Event JSONL stream over LAN (read-only).
- HTTP POST webhook of each `czapla.position/1` record.
- Static file output for evidence (an integrator's VMS can embed it).

## Security and privacy posture (matters for selling)

- Detection data is about aircraft and spectrum, not people. No video in v1.
- No personal data processed in v1. The moment a camera or an operator identity
  enters the record, GDPR and the site's own retention rules apply — flag it then.
- Evidence retention is configurable and documented; default 90 days.
- Node has no inbound shell in production; it pushes, it does not accept.
