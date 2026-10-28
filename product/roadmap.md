# Roadmap — phases, gates and kill criteria

Version 1, 2026-10-22. Each phase has a **gate**: a thing that must be true before
the next phase gets money or time. Gates are the point of this document.

## Phase 0 — software only, no hardware (this week)

**Do:** build the core software so that it works on simulated and recorded signals.
Everything except the actual radio front end.

**Deliverable:** working `software/` package, passing tests, a simulated detection
flowing through to a Polish incident report.

**Cost:** USD 0.

**Gate:** test suite passes; `--demo` prints a plausible event and writes a report.
If the software cannot be made to work on simulated data, no hardware will save it.

## Phase 1 — one node, bench (2-3 weeks after ordering)

**Do:** order and assemble one KrakenSDR node. Confirm it receives, calibrates
coherently, and estimates a bearing to a known transmitter (a Wi-Fi access point,
then a drone controller indoors).

**Deliverable:** bearing measurements vs ground truth, written to `hardware/results.md`.

**Cost:** ~USD 1,800 (see `hardware/bom-v1.md`). **This is the decision point on
spending.**

**Gates:**
- Bearing error within ±15° indoors at 10-50 m, after calibration. (Estimate — to
  be replaced by the measured number.)
- The detector fires on a real drone controller and does not fire continuously on
  the site's Wi-Fi. If it is constant noise, the concept needs a different
  classifier before any more money goes in.
- **Kill criterion:** if a single node cannot do a stable bearing at all inside
  two weeks of assembly, stop and re-evaluate before buying node two.

## Phase 2 — two nodes, outdoor (3-5 weeks)

**Do:** second node, outdoor mast positions, real drone flights. Measure range,
bearing accuracy, triangulation error and false alarm rate against a real drone
under a real sky.

**Deliverable:** the field test report — the single most valuable asset this project
can own, because it is what every grant application and every buyer asks for.

**Cost:** +~USD 1,800, plus a test drone or access to one.

**Gates:**
- Triangulation circular error under 100 m at 500 m range. (Estimate; the test plan
  measures it. If the real number is 500 m, the product is a "which direction"
  alarm, not a locator — and that must be written on the landing page.)
- False alarms over a 24-hour unattended run: measured, not guessed.

**Kill criterion:** if outdoor false alarms are unusable and the classifier cannot
fix it, the honest conclusion is that this needs radar — which needs capital we do
not have. Stop and revisit the subcontracting route instead of building.

## Phase 3 — pilot-ready (2-3 weeks)

**Do:** operator UI polish, the Polish incident report, the landing page, install
instructions, and a one-page honest capability statement.

**Deliverable:** something that can be demonstrated to a real site.

**Gate:** a person who is not Casper can install it and interpret the UI without help.

## Phase 4 — first paid pilot (target: within 90 days of Phase 2 passing)

**Do:** one real site, one paid pilot. Price in `business/model.md` (estimate:
PLN 10-30k for 90 days). This is the first revenue and the first reference.

**Gate:** a signed pilot. Nothing further is built speculatively before this.

**Kill criterion:** if 20 real conversations produce no paid pilot, the market
answer is no, and the correct move is to sell the software capability as
subcontracting to integrators instead (the `business/outreach/` pack exists for
exactly that fallback).

## Phase 5 — after revenue (grants, company, scale)

Company registration, FENG/STEP (Nov 2026 window), a Norwegian partner for POLNORIS
(17 Dec 2026), EDF SME 2027 as a software partner in a consortium. Detail in
`research/funding.md`.

## Parallel tracks added 2026-10-28 (see `product/portfolio.md`)

They do not change the order above. HERMES phase 1 is still the next spend.

| Track | Now | Gate before money goes in |
|---|---|---|
| Trainer (simulator + operator console) | Built, software only, USD 0. Use it in buyer conversations and to test the pipeline. | v1 only after a security officer who is not Casper runs a drill unaided |
| Ground line (people / animals / vehicles) | Classifier, policy and schema built and tested on synthetic data. No hardware. | HERMES phase 1 passed **and** a buyer asks for ground sensing. Then a passive bench kit and tests T-G1 to T-G5 (`product/perimeter.md`) |

Kill criterion for the ground line: if T-G3 (7 nights unattended) shows the
two-sensor rule does not cut nuisance alarms against the site's own camera
analytics, stop and sell integration only.

## Timeline reality check

- Phase 0: days, free.
- Phases 1-2: 5-8 weeks and ~USD 3,600 — that is roughly 70% of Casper's cash.
- Phase 3-4: 4-6 weeks.
- First revenue realistically: **December 2026 at the earliest**, and only if
  Phases 1-2 do not hit a kill criterion.

If that timeline is too slow for the runway, the correct action is to run Phase 0
in parallel with paid software subcontracting, and let the subcontracting money
fund Phase 1. That is what makes this survivable rather than a gamble.

## What would make me kill the whole project

1. Single-node bearing is unstable, and no amount of calibration fixes it.
2. Outdoor false alarm rate is unusable in an industrial RF environment.
3. Two nodes plus software can only detect at a range so short that a site needs
   dozens of nodes — i.e. the unit economics never work.
4. Nobody will pay even for a pilot after honest conversations.

Each of those is a real possible outcome. The phases are ordered so we learn
which one is true as cheaply as possible.
