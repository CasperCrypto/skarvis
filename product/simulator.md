# Simulator and trainer (working name SKARVIS Trener)

Version 0, 2026-10-28. Built and working on synthetic data. Read
`product/portfolio.md` for why it exists.

## The one-sentence product

A scenario simulator that runs scripted drones, people, animals and vehicles
through the real SKARVIS detection pipeline, and a Polish operator console that
turns the run into an exercise: alarms arrive, the operator acknowledges,
verifies and decides, and the debrief shows what was right, what was wrong, and
what the system never saw.

## The rule that matters most

**A simulator number is a property of its assumptions, never of the product.**
Every range, signal level, bearing error and false-positive rate comes from the
scenario file. No simulator result goes into a pitch, a grant application or
the landing page as performance. The run file, the event records
(`synthetic: true`) and every screen of the console say "SYMULACJA".

## What exists

| Piece | Path | Does |
|---|---|---|
| Scenario engine | `software/czapla/sim.py` | Moves actors, models what each sensor would report, runs the real classifier, baseline, policy, fusion and event store, scores the outcome |
| Demo scenario | `software/czapla/scenarios/podstacja.json` | Fictional 300 × 200 m substation, two HERMES nodes, ground sensors on the south fence, nine actors, one site emitter |
| Trainer console | `web/site/trener/` | Polish playback console: drill and instructor modes, alarm queue, verification, decisions, debrief, copyable exercise record |
| Tests | `software/tests/test_sim.py` | Blind spots are reported, ground truth never reaches a record, findings F-2, F-3, F-5 stay visible |

Run it:

```bash
cd software
python -m czapla.sim                                            # summary + event log
python -m czapla.sim --no-store --out ../web/site/trener/runs/podstacja.js   # file for the console
```

Then open `web/site/trener/index.html` (or double-click `web/preview-sim.bat`).

## Sensor models and their assumptions

| Sensor | Model | Assumption to replace with a measurement |
|---|---|---|
| Remote ID receiver | Decodes any Remote ID drone within range; position from the broadcast ± 3 m | Range 1000 m (T-1 bench, then field) |
| KrakenSDR direction finder | Hears links inside its configured bands and within 24-1766 MHz; free-space SNR from a reference; bearing = truth + Gaussian error | 30 dB SNR at 100 m; 8° bearing error (T-2, T-3, T-6) |
| Thermal array | Pixel footprint from range and field of view (MLX90640 geometry), size noise 10 %, blob quantised to pixels | Size noise and minimum fill (T-G1) |
| Ground radar | Speed and limb cadence with noise, 90 % detection per second when moving | All of it; and decision D1 |
| PIR | Presence when a warm object moves in range, 80 % per second | Detection rate |
| Camera analytics | People and vehicles labelled at ~0.85; an animal gives a false "person" in 12 % of frames | False-person rate (T-G3 measures the real one) |

Not modelled: terrain, buildings, multipath, weather, interference, other
drones' links, realistic flight dynamics (straight segments at constant speed),
track association (the simulator uses its own truth to group ground
observations).

## What it found in our own pipeline

See the table in `product/portfolio.md` (F-1 to F-6). Two need a decision by
the owner of `software/` (Hermes):

- **F-2, cooldown bucket.** Proposal: after T-5 has measured how far real
  hopping links move between scans, set `AlarmPolicy.cooldown_bucket_mhz` to
  cover one hopping band (25 MHz in the demo). Write the reason into
  `hardware/results.md` as the policy rule requires.
- **F-3, baseline that keeps learning.** Proposal: learn the baseline during
  installation (supervised: "no drones now"), freeze it, and re-learn only on
  an operator's command; or keep learning but never mark a frequency persistent
  while its bearing or SNR is changing, since a drone moves and a fixed
  transmitter does not. Until then the simulator runs with a frozen baseline
  and says so in the scenario file.

## The operator console

- **Ćwiczenie** (drill): ground truth hidden. Each alarm needs "Potwierdź
  odbiór", optionally "Weryfikuj" (answers after 8 s of simulated time, like a
  camera check or a guard's look), then a decision: threat (procedure started),
  authorised, or false alarm. "Pauza przy alarmie" stops the clock on each new
  alarm.
- **Instruktor**: ground truth on the map (dashed tracks) and on each alarm.
- **Podsumowanie**: decisions scored against truth, time to acknowledge,
  whether the decision followed a verification, the full list of objects
  including undetected ones with the reason, and the scenario's assumptions.
  "Kopiuj raport z ćwiczenia" copies a plain-text record with a signature line.

## Lines this product does not cross

- No attack, strike or weapon scenarios. No countermeasure training. CASPER
  stays out.
- **No evasion training in anything public.** A mode where a user flies a drone
  around a site's sensors and learns where they are blind teaches exactly the
  wrong people. Red-team use is for a site's own staff and its integrator, on
  that site's scenario, under contract.
- No real site in a shared scenario without the site's written consent: a
  scenario file is a map of a site's blind spots.

## Roadmap (each step only if the previous one was used by someone)

| Step | What | Gate |
|---|---|---|
| v0 (done) | Engine, demo scenario, console, findings | Tests green |
| v1 | Scenario library (airport edge, warehouse, water plant), scenario editor in the browser, Polish exercise report as a printable page | A security officer who is not Casper runs a drill unaided |
| v2 | Measured sensor parameters from `hardware/results.md` replace assumptions; site-specific scenarios for pilot customers | HERMES phase 2 done |
| v3 | Realistic drone trajectories from PX4 or ArduPilot SITL (free, open source); optional flight mode with a USB transmitter for site staff | A paying customer asks for it |

## Flight lab: moved out of SKARVIS (2026-10-29)

Casper decided the 3D environment to build, fly and test drones is a
separate project, not part of SKARVIS and not linked to its sensors. It is
open source, browser first (three.js) with an Unreal Engine 5 client later on
the same physics. Its plan is in `ventures/drone-world.md` and its code in the public repository
https://github.com/CasperCrypto/drone-world. The trainer above stays what it is:
alarm-handling drills for the people who protect a site.
