# Spec v1 — what we build first

Version 1, 2026-10-22. Scope is deliberately small: prove detection works, and
prove the software produces something a site would pay for. Nothing about
effectors, nothing about interceptors.

## The one-sentence product

A mast-mounted passive sensor node that detects a drone's radio link, says which
direction it is coming from, raises an alarm, and writes an evidence record that
a site can file into its protection documentation.

## v1 scope — IN

| # | Feature | Acceptance test |
|---|---|---|
| 1 | Detect 2.4 GHz drone control/video energy above noise | T-1, T-2 in `hardware/test-plan.md` |
| 2 | Estimate direction of arrival via a 5-element array | T-3, T-4 |
| 3 | Classify energy as drone-like vs other (with a documented, honest error rate) | T-5 |
| 4 | Two-node triangulation to a position on a map | T-6 |
| 5 | Alarm event as JSON: time, bearing, confidence, node, raw evidence pointer | T-7 |
| 6 | Persistent event log + operator acknowledgement | T-8 |
| 7 | One-page Polish PDF/HTML report per incident for a site's file | T-9 |
| 8 | Landing page with an honest pilot offer | Manual review |

## v1 scope — OUT (and why)

- **Jamming / spoofing** — legal, not technical (`research/legal-pl.md`).
- **Interceptors / net capture** — legal and commercial, not our business.
- **Radar sensor** — the cheapest credible radar unit is EUR 30k, which is more
  than the entire project budget. Deferred to v2.
- **EO/IR camera confirmation** — useful but adds a camera, a trigger interface
  and thermal licensing. Deferred; a cheap IP camera with motion alert is the
  v2 first step.
- **GNSS interference detection** — genuinely valuable (spoofing detection is a
  real requirement) and cheap in L1 band. Candidate for v1.5.
- **Fibre-optic FPV detection** — impossible with RF. Explicitly out. Say so in
  every buyer conversation.
- **Remote ID decode** — worth doing (it is receive-only and legal), but it needs
  a second receiver on 2.4 GHz that can parse the broadcast. v1.5.
- **Multi-site central management** — v2. One site, two nodes first.

## Users and what they actually do with it

| User | What they need from v1 |
|---|---|
| Site security officer | An alarm that is not noise. Which direction. A record that it happened. |
| SUFO shift commander | Enough to decide whether to qualify a legal ground and escalate |
| Site manager / compliance | A document for the protection plan file |
| Integrator | An API and a box they can install without us |

## Non-negotiable product constraints

1. **Never a false-confident alarm.** A missed detection is a smaller failure than
   an alarm with no drone. Confidence is reported, not hidden.
2. **Every alarm has raw evidence attached** — the IQ snippet or spectrum
   snapshot that triggered it. No evidence, no alarm.
3. **Offline by default.** Detection must work with no internet. Internet adds
   remote access, not function.
4. **Receive-only.** No transmit path in v1 hardware at all. Documented in the
   BOM so it is provable.
5. **Installable by a non-specialist** in under an hour: mast/clamp, PoE, done.

## Honest limitations to state in writing to any buyer

- RF detection sees only drones with a radio link. Fibre-optic FPV is invisible
  to it. (This is a real and growing threat class.)
- Dense 2.4 GHz environments (warehouse Wi-Fi, cameras, urban) will raise the
  false-positive floor. The test plan measures this rather than assuming it away.
- Bearing accuracy from a single compact array is a direction, not a coordinate.
  A position needs two nodes.
- One node has no range figure until it is measured outdoors against a real drone.

## Definition of done for v1

The test plan runs end to end with results recorded in `hardware/results.md`, and
the software suite passes. Only then does the landing page take a pilot request.
