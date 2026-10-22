# Review from Claude, 2026-10-22

For Hermes and Casper. Claude read every file in this project and ran the code.
No Hermes file was edited. This note is the only file Claude added
(plus `software/czapla-data/events.jsonl`, written by running `--demo`).

## 1. Verified

- `python -m unittest discover -s tests`: **110 tests, OK** (Python 3.10, Linux VM).
- `python -m czapla.pipeline --demo`: runs, writes 8 events, 1 alarm.
- Note: CLAUDE.md says Python 3.11+, but it passes on 3.10 too.

## 2. Blocking issue: KrakenSDR cannot receive 2.4 GHz

- KrakenSDR tuning range is 24-1766 MHz (our own `detection-approaches.md` and
  `bom-v1.md` say so). KrakenRF forum, July 2024: the Kraken "can not work in
  these frequency bands" (2.4 / 5.8 GHz), max tuning 1766 MHz.
  https://forum.krakenrf.com/t/can-krakend-sdr-detect-drone-direction/1442
- `spec-v1.md` feature 1, the architecture diagram, `detection-approaches.md`
  ("v1 is 2.4 GHz"), the 2.4 GHz outdoor antenna line in `bom-v1.md`, T-2/T-3
  (Wi-Fi router as test transmitter), the 0.15 m array radius in `assembly.md`
  and the 2.44 GHz demo signal all assume something the hardware can't do.
- A 5-channel coherent downconverter to reach 2.4 GHz is a separate RF project.
  Not v1.

**Proposed fix (Hermes to decide):**
- Point the Kraken at the bands it can hear, which are the FPV and long-range
  links: **868 MHz** (ExpressLRS / Crossfire control links in the EU),
  **433 MHz**, and **1.2-1.3 GHz** analog video. KrakenRF forum confirms 1.2 GHz
  and sub-GHz video links fall inside its range.
- Bench test T-2/T-3 against an 868 MHz transmitter (an ELRS TX module or LoRa
  node) instead of the Wi-Fi router. Recompute array radius for 868 MHz.
- Cover 2.4 / 5.8 GHz consumer drones with **identity receivers** instead
  (next section).

## 3. Merge proposal: two cheap sensor sources, one event schema

Claude's plan (doc linked below) built v1 around **Remote ID + DJI DroneID**
receivers. Hermes' plan built v1 around **KrakenSDR direction finding**.
They cover each other's blind spots:

| Source | Hears | Gives | Cost per node (est.) |
|---|---|---|---|
| Remote ID: 2x ESP32-C5 + Sonoff ZBDongle-P (CC2652P, Sniffle) | Compliant drones on 2.4/5 GHz Wi-Fi and BT5 LR | Serial, position, altitude, pilot/takeoff position | ~400 PLN on top of the Pi |
| DJI DroneID: AntSDR E200 (AD9361) | Most DJI drones, 2.4/5.8 GHz | Model, position, home/pilot point (some models encrypted) | ~2,450 PLN |
| KrakenSDR DF | Sub-GHz control links, 1.2 GHz video (FPV, long range, non-compliant) | Bearing, then position with 2 nodes | ~USD 2,300 landed |

- Add them as new `sensor` values in `czapla.event/1` (`remote_id`, `droneid`,
  `rf_df`). Additive, no schema rename, so it respects the freeze rule.
- `remote_id` events carry a real position, so they can also **validate**
  Kraken bearings in T-3/T-6 for free (fly a Remote ID drone, compare).
- Suggested order: Remote ID bench kit first (cheap, legal, a real demo with a
  real drone in about a week, good for the 14-day buyer test). Kraken only after
  a buyer names a pilot price, per Hermes' gate.

## 4. Funding items not in `research/funding.md`

| Program | What | Deadline / catch |
|---|---|---|
| EUDIS Business Accelerator, cohort 4 | 8-month EU defence accelerator, no equity taken | Apply by **16 Nov 2026**. Needs a company established in the EU. https://tally.so/r/68YyOY |
| PUP start-up grant (jednorazowe środki) | 25-40k PLN in 2026 calls (Trzebnica, Dolnośląskie: 35k) | Only for people registered as unemployed; apply **before** registering any business. Ask PUP Bolesławiec |
| NATO DIANA | EUR 100k contract funding + accelerator | 2027 cohort closed 3 Jul 2026; next call likely mid-2027. Needs a company in a NATO country |
| PARP STEP fund for critical technologies | PLN 500M pot, defence named a priority | Call announced Oct, applications from Nov 2026 (likely the same window as FENG/STEP in our file) |

Conflict to note: the PUP grant assumes a JDG started with the grant; the plan
here assumes a sp. z o.o. for FENG/EDF/POLNORIS. Casper should decide which
comes first.

## 5. What Claude has made (private links, Casper can open them)

- Project plan doc: https://claude.ai/artifact/DPtE56cbHcEzUNGe3PcG3j
  (roadmap, node design, shopping list with prices, funding, pricing, risks)
- Landing page + 3D node model: https://claude.ai/artifact/Umib9L9RcErfi14HvCsWsc

**The landing page breaks this project's honesty rules** (`CLAUDE.md`,
`README.md`): it describes the node as if built, lists prices and a pre-sale
offer, and shows a dashboard illustration. Claude will rewrite it as
"in development, pilot waitlist", with estimates labelled, before anyone sees it.

## 6. Open decisions for Casper

1. **Name.** Hermes uses CZAPLA. Casper asked Claude for a spiritual name with
   `.si` or `.com`; Claude used AJNA (ajna.si). One name across both.
2. **Pre-sale.** Casper wants deposits now; Hermes' rules say no promises
   before the test plan passes. Middle option: waitlist + letters of intent now,
   refundable deposits only after T-1 to T-6 pass.
3. **Pricing.** A Remote-ID-only tier could sell low (Claude's 490 PLN/month
   idea); a Kraken DF system fits Hermes' PLN 10-30k pilot + 1,500-4,000/month.
   Likely two tiers, decided after Phase 2 per `business/model.md`.
4. **Who owns what.** Suggestion: Hermes owns `software/`, research and outreach;
   Claude owns the landing page, the visuals and the Remote ID node software.

## 7. Casper's decisions, 2026-10-22 evening (also in `ops/decisions.md`)

1. **Names.** Ecosystem **SKARVIS** (sky + Jarvis). **HERMES** = the detection
   node (it brings the message). **CASPER** = future interceptor, research only,
   never on the public page as a product. CZAPLA can stay as the folder and
   Python package name; public material says SKARVIS / HERMES.
   Watch: Elbit Systems sells military "Hermes" drones; fine for a sensor, avoid
   for a drone.
2. **Pre-sale.** Pilot list + non-binding LOIs now. Refundable deposits only after
   T-1 to T-6 pass. No prices on the public page.
3. **Hardware.** Buy now: Remote ID kit + one KrakenSDR set. KrakenSDR listens on
   433/868 MHz and 1.2 GHz, not 2.4 GHz (see section 2). AntSDR and node 2 wait.

## 8. Two landing pages exist now

- Hermes: `web/index.html`, Polish, CZAPLA, plain.
- Claude: designed SKARVIS page with an interactive 3D HERMES node and a brand
  board, English, rewritten tonight to follow this folder's honesty rules
  (pilot list, targets labelled "not measured", no prices).
- Proposal: one page. Claude's design, Hermes' Polish copy, SKARVIS names.
  Hermes to send its final Polish text; Claude to merge and publish.

## 9. Suggested split from here

- **Hermes:** software (`software/`), retune DoA and the demo to 868 MHz,
  rewrite T-2/T-3 for an 868 MHz test transmitter, research, outreach list.
- **Claude:** landing page and visuals, Remote ID node service
  (`sensor: "remote_id"` events into `czapla.event/1`), plan doc.
- **Casper:** order hardware, PUP/company decision, first 10 buyer calls.
