# Ground line (working name SKARVIS Teren): people, animals, vehicles

Version 0, 2026-10-28. Concept plus working software. **No sensor chosen, nothing
bought, nothing measured.** Read `product/portfolio.md` first for why this
exists and what it is not.

## The one-sentence product

A ground-sensing add-on that tells a person or vehicle inside the fence from an
animal or a passer-by outside it, raises an alarm only when two different
sensor types agree, and writes the same evidence record and Polish report as a
drone alarm.

## Why this and not "another camera"

The complaint from sites is false alarms from camera analytics: a fox, a cat or
moving branches become "person detected" at 3 a.m. One sensor type, however
clever, makes the same mistake every night. Two sensor types that measure
different physics (shape from heat, motion from radar or video) rarely make the
same mistake at the same time. That is the design bet. It is a bet until the
tests below produce a number.

## Scope v0 — IN (software, done)

| Piece | File | Does |
|---|---|---|
| Ground record schema | `software/czapla/events.py` (`czapla.ground/1`) | One record per notable change of a ground track: first seen, class changed, alarm |
| Classifier | `software/czapla/ground.py` | Thermal shape, radar speed and limb cadence, camera label → human / animal / vehicle / unknown, one vote per sensor type |
| Alarm policy | `software/czapla/policy.py` (`GroundPolicy`) | Alarm only: person or vehicle, inside the perimeter, confidence ≥ 0.6, two sensor types, cooldown per track |
| Geometry | `software/czapla/geometry.py` | Point-in-perimeter, thermal pixel footprint at range, reference human walking speed and cadence |
| Simulator support | `software/czapla/sim.py` | Synthetic thermal, radar, PIR and camera observations for scenario testing |

## Scope v0 — OUT

- Identifying people (faces, number plates, phones). No personal data by design.
- Tracking across the whole site. v0 classifies objects near the sensors that
  see them.
- Any active response (lights, sirens, locks). Possible later as an output
  to the site's own alarm system; a human still decides.
- Our own radar hardware while the receive-only rule stands (decision D1).

## Sensor options

| Sensor | What it measures | Person vs animal | Limits | Transmits | Source |
|---|---|---|---|---|---|
| PIR | Warm thing moved | No | Presence only | No | — |
| MLX90640 thermal array | 32×24 px heat image, 55°×35° (or 110°×75°) | By shape (height, width, aspect) at short range | A person spans 3 px only up to ~17-23 m (55° model); fog and rain cut range; summer ground near body temperature lowers contrast (estimate) | No | Melexis datasheet |
| Thermal camera (higher resolution) | Same, more pixels | Same, further | Price not checked; image of people may be personal data | No | to research |
| Site's camera analytics | "person" / "vehicle" labels | Labels animals as people sometimes | Night, glare, weather; video is personal data (RODO) | No | — |
| HLK-LD2450 24 GHz | Position and speed, 3 targets | Weak | About 6 m range: an indoor presence sensor, **not** a perimeter sensor | Yes | vendor manual |
| Security radar (e.g. Axis D2110-VE) | Position, speed, class | Yes (vendor classes: human, vehicle, unknown) | 5,600 m² human detection area per manual; range depends on scene and neighbouring radars | Yes | Axis manual |
| Micro-Doppler radar research | Full Doppler spectrogram | Papers report ~75-98% in their own datasets | Learned models; not our data; not our hardware | Yes | van Eeden 2018, Buchman 2022, Manga 2025 |

**Recommended v1 bench kit (when D5 says go):** one MLX90640 (55°) and one PIR
on the Raspberry Pi the HERMES node already has, plus the event feed of one
camera the test site already owns. All passive on our side. Price to be taken
from Botland or TME on the day of ordering; not estimated here.

## How the classifier decides (v0 priors, not fitted)

Each observation becomes evidence for {human, animal, vehicle}:

- **Thermal shape** (only when the sensor can resolve a person at that range):
  tall and narrow → human; low and long → animal; big and wide → vehicle.
- **Radar**: no limb motion and real speed → vehicle; cadence in the human
  walking band (1.3-2.3 Hz from 81-138 steps/min) leans human, capped at 0.7 so
  radar alone never decides; other cadences lean animal.
- **Camera label**: taken at its stated score.
- **PIR**: presence only, counts as a sensor that saw the object.

Each sensor type gets one equal vote, so ten frames from one camera cannot
outvote one thermal sensor. The label is "unknown" unless the top class has at
least half the probability and a 0.2 margin. Confidence drops when sensor types
disagree and when only one type contributed.

## Known failure modes (kept as tests)

1. A person **crawling** looks like an animal to the thermal shape rule.
2. A **walking deer** (or a trotting dog) has a cadence close to a person's.
3. **Two weak sensors can agree on the same mistake**: in the demo scenario a
   deer in a sector without thermal coverage got a false "person" from the
   camera and a human-band cadence from the radar, and alarmed (finding F-6).
   Candidate rule: an alarm needs a shape-capable sensor among the confirming
   types. Not applied until field data shows its cost in missed people.
4. Groups of people and a person leading a dog or pushing a bicycle are not
   modelled at all.
5. Track association uses simulator truth; the real system has to associate
   observations itself, and wrong association is its own error source.

## Tests to add to `hardware/test-plan.md` when hardware is decided

| Test | Do | Record | Fail meaning |
|---|---|---|---|
| T-G1 Thermal shape vs range | Person upright, crouching, crawling at 5/10/15/20/25 m; dog or a person-sized and fox-sized heat target at the same ranges | Class per range | If upright people are not "human" at 15 m, the cheap array is not a perimeter sensor |
| T-G2 Two-sensor confirmation | Walk 20 crossings through a sector with thermal + camera | Alarms, misses, time to alarm | A miss rate above what the site accepts kills the two-sensor rule |
| T-G3 Nuisance run | 7 nights unattended, no planned intrusions | Alarms per night, and what caused each (camera footage) | The number the whole product is sold on; not invented here |
| T-G4 Weather | Same as T-G3 in rain or fog | Change in misses and nuisance alarms | Thermal range collapse is a documented limitation, not a bug |
| T-G5 Outside-the-fence traffic | People and cars on a path or road outside | Alarms (target: none) | Perimeter geometry or position noise too large |

## Legal and privacy

- Passive sensors (thermal, PIR, receiving a camera's events) need no radio
  permit. A radar transmits: licence-exempt short-range-device rules may cover
  it (ERC Recommendation 70-03; annex to be checked in the official text), but
  our own rule is receive-only until Casper decides D1.
- Thermal images at 32×24 px do not show faces. A higher-resolution thermal
  camera or any video recording brings RODO duties (purpose, retention, notice
  signs); the site, as data controller, decides retention.
- Detecting phones or Wi-Fi devices is **not** in scope: EU data protection
  authorities treat MAC addresses with location as personal data (AEPD 2024
  guidance; Article 29 WP opinions). Needs a written legal opinion first.
- The AI-act note in `research/legal-pl.md` applies here too: a classifier used
  in critical-infrastructure protection may count as high-risk. Check before
  launch.
