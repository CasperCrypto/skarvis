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

## Flight lab (requested 2026-10-29, not started)

What Casper asked for: a realistic 3D environment where people pilot drones,
upload drone models, build drones from parts and test them. This is a
different product from the trainer above (which drills the people who protect
a site). Nothing of it is built. This section is the plan and the decision
(D6 in `product/portfolio.md`).

### What "hyper-realistic" actually takes

- **Looks are the easy part to buy.** Unreal Engine 5 gives photoreal scenes
  on a desktop PC with a gaming graphics card; three.js (already used on our
  site) gives good-looking scenes in any browser, phone included.
- **Flight is the hard part.** Thrust and torque per motor and propeller,
  battery voltage sag, drag, wind, and above all the flight controller. Testing
  a drone means testing its real firmware, not our imitation of it.
- **So we do not write a flight engine.** Run the real open-source autopilot
  (ArduPilot or PX4) in software-in-the-loop, let an existing physics backend
  fly it, and draw the result in Unreal or three.js. ArduPilot SITL already
  accepts external physics through a JSON interface; PteroSim is an Unreal
  Engine 5 simulator built on exactly that. PX4 ships with Gazebo. Microsoft's
  AirSim is archived; its successor is Project AirSim. Sources in
  `research/sources.md`.

### Options

| Path | Realism | Runs on | Effort (estimate) | Good for |
|---|---|---|---|---|
| three.js browser lab, our own simplified quadcopter physics | Looks good, flies like a game | Any browser | Weeks for a solid prototype | Demo, the builder UI, public education |
| ArduPilot SITL + our browser 3D view | Real firmware behaviour, simple graphics | PC (Linux or WSL) + browser | Weeks to a few months | Engineering test bench |
| ArduPilot/PX4 SITL + Unreal Engine 5 (PteroSim, Project AirSim) | Real firmware and photoreal scenes | Windows PC with a gaming GPU | Months for at least one experienced Unreal developer | The "hyper-realistic" version |
| PX4 + Gazebo as shipped | Real firmware, robotics-grade physics, plain graphics | Linux | Free, documented | Research and automated tests |

All effort figures are estimates, not quotes.

### "Upload a model" and "build a drone" are two different things

1. **The look**: a glTF/GLB 3D file. Both three.js and Unreal import it.
2. **The flight properties**: mass, frame size, motors (KV), propellers (size,
   pitch), battery (cells, capacity). The builder turns those into
   thrust-to-weight, hover throttle and an estimated flight time, and writes
   autopilot parameters for SITL. The thrust numbers need a real data source
   (motor and propeller test tables); until we have one, every computed figure
   is labelled an estimate.

### Lines the flight lab does not cross

- No payload release, weapons, strike or interceptor (CASPER) content.
- None of our detection-sensor models in anything public: a lab where you
  learn to fly around a site's sensors teaches evasion.
- Flight-training content follows the EU open-category rules; it does not
  replace the ULC exam or the operator's legal duties.

### Market reality

Free (Gazebo, SITL) and cheap (Liftoff, VelociDrone, DRL Simulator) tools
already exist. A Polish flight lab would have to win on something they lack,
for example Polish language, a parts builder with test reports, or exercises
matched to the exams schools teach for. That is unproven. **Gate before
anything beyond a prototype:** five conversations with flight schools or
school programmes, and at least one that would use or pay for it.

### Recommended path

| Stage | What | Gate |
|---|---|---|
| 1 | Browser lab in three.js: fly with keyboard or gamepad, physically based but simplified quadcopter model, parts builder with computed performance, glTF upload for the look, a test course with logged results. Labelled "not a certified simulator". Can be built in this repository. | Casper decides D6 |
| 2 | Connect the stage-1 viewer to ArduPilot SITL, so the drone flies on real firmware | Stage 1 used by someone outside the team |
| 3 | Unreal Engine 5 scenes | A budget and an Unreal developer; a customer who needs photoreal |

Unreal Engine cannot be run in the cloud session where this plan was written
(no Windows PC, no graphics card); stages 1 and 2 can be built there.
