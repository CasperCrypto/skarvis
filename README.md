# CZAPLA — counter-drone detection for infrastructure

**Status: pre-prototype. Nothing built, nothing ordered, no customers.**
Started 2026-10-22. Owner: Casper Poplawski. Research + build: Casper + Hermes + Claude.

## What this is

A **detection-first** C-UAS product for Polish and EU infrastructure sites:
rooftop/mast sensor nodes that detect, classify and track drones, and software
that turns detections into an alarm workflow, an operator record and the
paperwork a site needs for its protection plan.

**Explicitly NOT in scope:** jamming, spoofing, GNSS interference, net capture,
kinetic interceptors, weapons. Those are legally restricted to SUFO personnel of
registered critical-infrastructure operators (see `research/legal-pl.md`), and
building them turns this into an arms business. Detection and evidence only.

## Why this can exist at all

1. Polish law now forces the work: the 29 May 2026 amendment makes
   critical-infrastructure operators document drone threat scenarios,
   response procedures and protection-plan annexes, on a dated clock.
2. Detection hardware is a commodity you can buy (see `hardware/bom-v1.md`),
   so a small team can integrate rather than invent sensors.
3. The expensive incumbents sell systems; nobody sells the cheap
   compliance-and-documentation layer that obligated sites actually get audited on.

## Folder map

| Path | What's in it |
|---|---|
| `CLAUDE.md` | Instructions for Claude Code working in this folder |
| `research/market.md` | Market size, demand drivers, verified numbers |
| `research/legal-pl.md` | Polish law: what's allowed, what isn't, who may do what |
| `research/competitors.md` | Who already sells this and at what price |
| `research/funding.md` | EU/PL grant instruments, rules, deadlines |
| `research/sources.md` | Every source URL used, dated |
| `product/spec-v1.md` | What we build first (v1 scope) |
| `product/architecture.md` | Software architecture |
| `product/detection-approaches.md` | RF vs radar vs acoustic: what we can and can't see |
| `product/roadmap.md` | Phase plan with kill criteria |
| `product/portfolio.md` | SKARVIS product family: air (HERMES), ground, trainer; what is possible, decisions D1-D5 |
| `product/perimeter.md` | Ground line: people / animals / vehicles, sensor options, tests T-G1 to T-G5 |
| `product/simulator.md` | Scenario simulator and operator trainer, assumptions, findings |
| `hardware/bom-v1.md` | Order list with real prices and links |
| `hardware/assembly.md` | How to build the node |
| `hardware/test-plan.md` | How we prove it works (and how we prove it doesn't) |
| `software/` | Working prototype code + tests |
| `web/index.html` | First landing page draft (Hermes, CZAPLA name, kept for reference) |
| `web/site/` | Public SKARVIS site, Polish + English, interactive 3D HERMES node, pilot-list form (see `web/site/README.md`) |
| `web/supabase/` | SQL for the pilot-list table the site writes to |
| `web/sim/` | SKARVIS Trener: Polish operator training console playing simulator runs (synthetic data only) |
| `business/model.md` | Pricing and unit economics |
| `business/outreach/` | Verified target lists, built but NOT sent |

## Status as of 2026-10-22

| Layer | State |
|---|---|
| Software | **Built and passing.** 163 unit tests green (2026-10-28), demos and the simulator run. Stdlib-only. |
| Hardware | **Nothing ordered.** BOM costed, not purchased. |
| Field tests | **None run.** The only verification is against simulated signals. |
| Customer / pilot | **None.** No contact has been made. |
| Company | **Does not exist.** No sp. z o.o. registered. |
| Landing page | `web/site/`, SKARVIS, Polish + English, built 2026-10-22, not yet hosted. States the limitations; every spec labelled as a target. |
| Ground line | **Software only** (2026-10-28): classifier, policy, schema, tested on synthetic data. No sensor chosen. |
| Trainer | **Built** (2026-10-28): scenario simulator + Polish operator console. Synthetic data; its numbers are assumptions, not measurements. |

## The one next action

Agree `hardware/test-plan.md`, then order **node 1 only** (~USD 1,850-2,300 landed)
and run tests T-1 to T-3. The two-node demo (~USD 4,000) is ~70-80% of available
cash and does not get ordered until node 1 passes its gates.

## Rules for this project

- Facts dated. Estimates labelled as estimates.
- No claim of a product, customer or capability that isn't proven in this folder.
- No promises to a buyer before the test plan passes.
- Every hardware purchase has a stated purpose and a kill criterion.
- Outreach material exists in `business/outreach/` but **is not sent** until
  `hardware/results.md` contains measured numbers.
