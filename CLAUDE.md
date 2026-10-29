# CLAUDE.md — context for Claude Code

You are helping Casper Poplawski build **CZAPLA**, a detection-first counter-drone
(C-UAS) product for infrastructure sites in Poland and the EU.

## Read these first, in order

1. `README.md` — what the project is and the current status
2. `product/spec-v1.md` — the v1 scope you are building against
3. `product/architecture.md` — how the software is structured
4. `product/detection-approaches.md` — what the sensors can and cannot see
5. `hardware/bom-v1.md` — the hardware being ordered
6. `hardware/test-plan.md` — how we prove it works

## Hard constraints — do not violate these

- **Detect, never defeat.** No jamming, no spoofing, no GNSS interference, no
  net capture, no kinetic anything. Passive receive-only sensing plus software.
  This is a legal constraint, not a preference: see `research/legal-pl.md`.
- **Never invent a capability.** If a feature is not tested, it is not in the
  landing page, the pitch or the spec. Overclaiming to a defence buyer is fatal
  and illegal in procurement contexts.
- **No fake data in the repo.** Every number in a doc needs a source in
  `research/sources.md`. Mark estimates as estimates.
- **Software is stdlib-first.** The prototype must run on a plain Python install
  with no numpy, so it runs on the Raspberry Pi and on Casper's laptop identically.
  If a dependency is genuinely needed, add it to `software/requirements.txt` and
  say why in the commit message.
- **Polish market, Polish language for buyer-facing material.** Code and comments
  in English; anything a Polish security director reads must be in Polish.

## Coding conventions for this repo

- Python 3.11+ target, stdlib only for `software/`.
- Every module has a docstring stating what it does and what it does NOT do.
- Tests in `software/tests/`, runnable with `python -m unittest discover`.
- Physics and geometry constants live in `software/czapla/geometry.py`, never
  hardcoded in logic files.
- Alert/output format is JSON, one event per line, schema in `product/architecture.md`.

## Honest status you must not upgrade

- No hardware has been ordered or built (as of 2026-10-22).
- No field test has been run. The only verification so far is simulated signals.
- No customer, pilot or letter of intent exists.
- The company does not exist yet; no sp. z o.o. is registered.

If you are ever asked to write a website, deck or email that assumes any of the
above is false, stop and flag it instead of writing it.

## Useful commands

```bash
cd software
python -m unittest discover -s tests -v     # run the test suite
python -m czapla.pipeline --demo            # print one simulated detection event
```

## Open technical questions (real, unresolved)

1. Which RF band to listen to first: 2.4 GHz (most consumer drones) vs 433/868 MHz
   (telemetry, longer range, less crowded). Current default: 2.4 GHz, but the
   KrakenSDR's R820T2 tuner is more sensitive lower down — measure both.
2. How to handle fibre-optic FPV drones that emit no RF at all. RF-only cannot
   see them. The v1 answer is "we don't"; the v2 answer is a radar or acoustic
   sensor fusion. Do not pretend otherwise.
3. Whether a 2-node demo is enough to triangulate acceptably, or whether the
   bearing accuracy of a single KrakenSDR node is already sufficient for a
   "which direction is it coming from" alarm. The test plan measures both.

## Update 2026-10-22 evening (added by Claude, read before anything else)

- Read `claude-review-2026-10-22.md` and the last rows of `../../ops/decisions.md`.
- **Public names:** SKARVIS = ecosystem/brand. HERMES = detection node.
  CASPER = future interceptor, research only, never sold or advertised.
  CZAPLA stays as the folder and Python package name.
- **KrakenSDR cannot receive 2.4 or 5.8 GHz** (max 1766 MHz). Its band is
  433/868 MHz and 1.2 GHz. 2.4/5 GHz drones are covered by Remote ID receivers
  (ESP32-C5 x2 + Sonoff ZBDongle-P with Sniffle) as `sensor: "remote_id"` events.
  Anything above that says "v1 is 2.4 GHz" with the Kraken is outdated.
- **Hardware decided:** buy the Remote ID kit + one KrakenSDR set now.
- **Website:** design reference in `web/skarvis-design/*.dc.html` (Claude design
  format: plain HTML with `{{holes}}`, `<sc-for>`, `<sc-if>` and a small logic
  class at the bottom). Rebuild it as a real static site, Polish first, using
  Hermes' Polish copy in `web/index.html`. Keep the honesty rules: pilot list
  and letters of intent only, no prices, every spec labelled as a target until
  `hardware/results.md` has a measured number.

## Update 2026-10-28 (added by Claude)

- **Product family:** read `product/portfolio.md`. SKARVIS now has three lines
  on one platform: HERMES (air), a ground line for people / animals / vehicles
  (working name SKARVIS Teren, software only) and a simulator + operator
  trainer (working name SKARVIS Trener, `software/czapla/sim.py`, `web/site/trener/`).
- **We have no radar.** Do not write that HERMES or the KrakenSDR detects
  people. Ground sensing needs new sensors; the receive-only rule still holds
  for our hardware until Casper decides D1 (integrating a site's own radar
  events is fine).
- **Simulator numbers are assumptions, never performance.** Never quote them to
  a buyer or in a grant application as detection results. Simulated records
  carry `"synthetic": true`.
- **No evasion, attack or countermeasure training** in the trainer, and nothing
  public that shows where a real site's sensors are blind.
- Ground alarms need two different sensor types (`GroundPolicy`). Phone / Wi-Fi
  device detection is out until a written legal opinion exists (RODO).
- Simulator findings F-1 to F-6 are in `product/portfolio.md`; F-1 is fixed,
  F-2 and F-3 wait for the owner of `software/`.
- 2026-10-29: the public site has a platform section (HERMES / Teren / Trener,
  each with its real status tag) and the trainer moved to `web/site/trener/`.
  The flight lab (build, fly, test drones in 3D) is not on the site.
- 2026-10-29, later: the flight lab and the canopy drones are **separate
  projects, not SKARVIS products**, kept in `ventures/` until they get their
  own repositories. Canopy = civilian only (VIP privacy, accident scenes);
  military concealment stays excluded. Neither goes on the SKARVIS site.
- 2026-10-29, latest: Drone World is **open source (MIT), browser first
  (three.js), Unreal Engine 5 later** (Casper's decision, replaces "Unreal
  first"). Code in `ventures/drone-world/`: shared C++ physics in `core/cpp`,
  its line-by-line JS port in `web/src/flight.js`; keep them in step and
  regenerate `core/fixtures/trajectory.json` when either changes. The web
  client is not under the stdlib-only rule (that rule is for `software/`);
  its only dependency is the vendored three.js.
