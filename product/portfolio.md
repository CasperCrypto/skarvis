# SKARVIS product family: what is possible, what is not

Version 1, 2026-10-28. Written in answer to Casper's question: can SKARVIS also
detect people and other intruders (and tell a person from a cat), and can we
build a virtual environment to train, test and build drones? Sources for every
number are in `research/sources.md`; estimates are marked.

## Short answer

**Yes to both, with conditions, and as one platform rather than three products.**

1. **We do not have a radar.** HERMES is two passive radio receivers: Remote ID
   receivers and a KrakenSDR direction finder. Neither can see a person, a fox
   or a car. A person carrying a phone emits radio, but tracking phones is a
   privacy problem (see "Device detection" below). Detecting people needs new
   sensors.
2. **Telling a person from an animal is a real, solvable feature**, and it is
   exactly what cheap camera analytics get wrong. The design that works is
   confirmation by two different sensor types (for example thermal shape plus
   radar or camera). Nothing about it is measured yet.
3. **A simulator is possible and cheap, because most of it already existed**:
   the detection software ran on simulated signals from day one. It is now a
   scenario engine plus a Polish operator training console. On its first run it
   found six problems in our own pipeline (below), which is the best argument
   for it.
4. **A full flight simulator for learning to fly drones is not where we win.**
   Good ones cost about USD 10-20 (Liftoff, VelociDrone, DRL Simulator) and the
   open-source autopilots ship their own simulators (PX4 and ArduPilot SITL).
   We can integrate those later; we should not rebuild them.

Status does not change: no hardware ordered, no field test, no customer, no
company. Everything built on 2026-10-28 is software tested on synthetic data.

## One platform, three lines

The common core is what is sellable: one event format (`czapla.event/1`,
`czapla.position/1`, now `czapla.ground/1`), one alarm policy with written
reasons, one incident queue, one Polish incident report. A critical
infrastructure operator has to document drone threats **and** physical
protection in the same protection plan, with alarm thresholds, escalation,
integration with technical security systems and incident records
(`research/legal-pl.md`). One evidence trail for air and ground fits that
obligation better than two vendors.

| Line | Working name | What it is | State on 2026-10-28 |
|---|---|---|---|
| Air | **HERMES** | Passive drone detection node (Remote ID + KrakenSDR) | Software built, hardware not ordered |
| Ground | **SKARVIS Teren** (working name) | Person / animal / vehicle classification from 2+ sensor types, alarm inside the perimeter only | Classifier, policy and schema built and unit-tested; no sensor chosen, nothing bought |
| Training and test | **SKARVIS Trener** (working name) | Scenario simulator plus operator training console, Polish | Built: `software/czapla/sim.py`, `web/sim/` |

Names are working names until Casper decides (decision D2).

## Ground line: people, animals, vehicles

Full spec: `product/perimeter.md`. The essentials:

**Sensor options, honestly**

| Sensor | Tells person from animal? | Transmits? | Privacy | Fit |
|---|---|---|---|---|
| PIR motion detector | No, presence only | No | None | Cheap trigger, never an alarm on its own |
| Cheap thermal array (MLX90640, 32×24 px, 55°×35°) | Yes, by shape, **only up to about 17-23 m** (where a 1.3-1.75 m person is still 3 px tall; geometry from the datasheet) | No | Low (no faces at 32×24) | Gate and fence-segment sensor |
| Real thermal camera | Yes, by shape, further | No | Medium | Better, costs more; not priced yet |
| Camera with built-in analytics (often already on site) | Sometimes; false "person" on animals is the known complaint | No | High (video of people: RODO) | Integrate its events, never alarm on it alone |
| Low-power security radar (24/60 GHz) | Partly: speed and limb-motion cadence; papers report high accuracy with learned models | **Yes** | Low | Conflicts with our receive-only rule (decision D1) |
| Phone / Wi-Fi / Bluetooth detection | No | No | **High**: MAC addresses are personal data per EU regulators | Do not build without a lawyer (decision D4) |

**What we built:** `software/czapla/ground.py` scores each sensor's evidence
(thermal shape, radar speed and cadence, camera label) and gives each sensor
type one vote. `GroundPolicy` alarms only on a person or vehicle **inside the
perimeter**, with confidence ≥ 0.6, **seen by two different sensor types**.
Known failure modes are written into the tests: a crawling person looks like an
animal to the thermal shape rule; a walking deer has a cadence close to a
person's.

**Market reality:** perimeter intrusion detection is a mature market. Axis
alone sells a security radar that classifies humans and vehicles over 180°
(manual: 5,600 m² detection area for humans). We will not beat that on
sensors. Our edge is the shared evidence trail with the drone layer, the Polish
protection-plan paperwork, and integrating what a site already owns (its
cameras, its radar) instead of replacing it.

## Training and test line: SKARVIS Trener

Full spec: `product/simulator.md`. Three uses, in order of value:

1. **Test our own software** before hardware exists. It found six problems on
   day one (next section).
2. **Plan a site**: where to put nodes and ground sensors, and which sectors
   stay blind. The demo shows a fibre-optic drone no RF sensor sees, and a deer
   that walks through a sector without thermal coverage and triggers a false
   alarm.
3. **Drill operators**: alarms arrive, the operator acknowledges, verifies,
   decides; the debrief scores the decisions and lists what the system never
   saw. This maps onto the protection-plan duties (escalation procedure,
   decision authority, incident records).

Out of scope, by decision of this document: a flight-physics engine of our own,
a consumer flight-training game, anything that trains attack, evasion of
detection, or countermeasures, and anything about CASPER.

**Government and public interest is real but unverified for us.** Press reports
(search results, not an official MON text) describe a planned civilian
"Dron Legion", a need for "hundreds of thousands" of drone operators, a pilot
"OPW z dronem" in up to 500 schools, and over 560,000 certified operators in
Poland. That is demand for **flight** training, which the existing simulators
and ULC courses serve. Our lane is the other side: people who **protect a
site** from drones. If we want a flight mode later, the route is PX4/ArduPilot
SITL plus a USB transmitter, after HERMES phase 2.

## What the simulator found in our own pipeline (2026-10-28)

All numbers are from the demo scenario, so they describe its assumptions, not
the product. Each finding is a unit test in `software/tests/test_sim.py`.

| # | Finding | Effect in the demo run | Action taken |
|---|---|---|---|
| F-1 | The classifier only knew 2.4/5.8 GHz drone bands. Every KrakenSDR detection (433/868 MHz, 1.2 GHz) was band-gated to "other". | The 868 MHz FPV drone was heard and **never alarmed**. | **Fixed** in `classifier.py`: 433 MHz and 863-870 MHz SRD bands with narrow windows, 1.2 GHz video channels. 915 MHz left out (phone uplink in Poland). |
| F-2 | The alarm cooldown is per 1 MHz bin; a frequency-hopping link moves several MHz between scans. | 14 RF alarms instead of 4. | New `AlarmPolicy.cooldown_bucket_mhz`, **default unchanged** (policy rule: defaults change only with a written reason after T-5). Scenario uses 25 MHz. |
| F-3 | The baseline keeps learning while the system runs, so a drone present for ~30 s becomes "infrastructure". | 144 of 215 detections of the approaching FPV marked infrastructure; the first alarm came at 93 m from the site centre instead of 668 m. | Simulator supports a baseline learned at install and then frozen. **Fix in `baseline.py` is Hermes' call**: proposal in `product/simulator.md`. |
| F-4 | Air alarms have no distance rule. | Remote ID drone alarmed 913 m out, 57 s before entering the 400 m zone. | Open question: early warning or nuisance. Remote ID gives a position, so a zone rule is possible. |
| F-5 | Without a learning period at install, the site's own 433.92 MHz telemetry alarms. | One false alarm incident. | Installation must include a baseline learning period (add to `hardware/assembly.md` when the node exists). |
| F-6 | Two weak sensors can agree on the same mistake. | Deer in a sector without thermal: camera false "person" + radar cadence in the human band = false alarm. | Rule candidate: an alarm needs a shape-capable sensor (thermal) among the confirming types. Not applied; needs field data. |

## Funding: how to use this

- **Tell one story:** one detection-and-evidence platform for critical sites,
  air first. Three unrelated products with no test results read as a lack of
  focus to a reviewer.
- **The simulator is evidence of method, not of performance.** "Our simulator
  found and fixed a defect that would have made the ordered hardware unable to
  raise an alarm" is true and strong. "Our system detects X%" is not true.
- **Possible fits, to verify against each call document:**
  - PARP *DeepTech Goes Dual* (through an accelerator): dual-use platform.
  - POLNORIS (17 Dec 2026, needs a Norwegian research partner): the
    "resilience" priority may fit civil-protection training (Trener) better
    than counter-drone hardware. A hypothesis to test with NCBR.
  - OLiOC civil-protection money (regional, 2027-2031): Trener for municipal
    and crisis teams, later.
  - EDF SME 2027: detection plus sensor fusion, needs TRL 4 (a lab-validated
    prototype) and a consortium.
- Prerequisites are unchanged (`research/funding.md`): a company, a prototype
  with measured results, a first paid pilot.

## What may be said to a buyer now (Polish)

Allowed:
- „Rozwijamy też moduł naziemny: osoba, zwierzę, pojazd. Alarm tylko wtedy,
  gdy obiekt potwierdzą dwa różne typy czujników. Na razie to oprogramowanie
  sprawdzane na danych syntetycznych; sprzętu jeszcze nie ma.”
- „Mamy symulator ćwiczeń dla operatorów. Wszystkie liczby w nim to założenia,
  nie pomiary.”

Not allowed until `hardware/results.md` has measured numbers:
„wykrywamy ludzi”, „eliminujemy fałszywe alarmy”, any percentage, any range,
any mention of MON, Dron Legion or a government partner.

Nothing about the ground line or the trainer goes on the public site yet.

## Decisions for Casper

| # | Decision | Recommendation |
|---|---|---|
| D1 | Keep the receive-only rule for ground sensing, or allow a licence-exempt low-power radar? | **Keep it for v1.** Use passive sensors (thermal, PIR) and **integrate the events of a radar or camera the site already owns** through the API. That gives radar data without us putting a transmitter on a mast. |
| D2 | Public names for the ground line and the trainer. | Keep the working names until a buyer has seen it. (If mythology: Argus, the hundred-eyed watchman, is the obvious one; Hermes is the god who killed him, which a buyer may notice.) |
| D3 | Trainer free or paid? | Free demo for site security staff; paid work is a scenario built from a customer's real site and procedure. No public release with real sensor models. |
| D4 | Detect phones and Wi-Fi devices? | **Not without a written legal opinion.** MAC addresses with location are personal data per EU regulators. |
| D5 | Order of work. | HERMES phase 1 first, unchanged. Trainer: done for now, use it in conversations. Ground: software done; buy ground hardware only after HERMES phase 1 passes **and** a buyer asks for it. |
