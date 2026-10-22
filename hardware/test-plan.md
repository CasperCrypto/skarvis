# Test plan — how we prove it works, and how we prove it doesn't

Version 1, 2026-10-22. Every test has a **pass threshold and a fail meaning**. A
test that cannot fail is not a test. Results go in `results.md`.

## Purpose

This document is the project's honesty mechanism. Grant applications and buyers
will ask for measured numbers; without this, the only thing we have is opinion.

## Rules

- Every measurement is recorded with date, conditions and the exact setup.
- Estimates are marked as estimates until measured.
- A failed test is a result. It gets written down, not deleted.
- If a threshold turns out to be unrealistic, change the threshold **in writing,
  with the reason** — never quietly.

## T-1 — Receiver and channel integrity (bench)

**Do:** confirm all five channels produce data and coherence calibration completes.
**Pass:** calibration completes and phase offsets are stable across three runs.
**Fail meaning:** hardware or power problem; nothing else can be trusted until fixed.

## T-2 — Known-transmitter detection (bench, indoors)

**Do:** listen at the Wi-Fi router's channel frequency. Detect its energy.
**Pass:** detected, SNR recorded, and detection is repeatable across 10 captures.
**Fail meaning:** if a strong known transmitter 10 m away cannot be detected,
either the band or the gain is wrong — find it before any outdoor work.
**Record:** SNR in dB, and the noise floor.

## T-3 — Bearing accuracy against a known direction (bench, indoors)

**Do:** router at a known true bearing relative to the array; measure the estimated
bearing. Repeat at 8 array yaw angles, 5 captures each.
**Pass:** mean absolute error ≤ 15° (estimate; adjust only with written reason).
**Also record:** the spread (standard deviation) — spread matters more than mean for
a security product.
**Fail meaning:** if error is huge but consistent, calibration/geometry bug
(fixable). If random, multipath or SNR problem (harder).

## T-4 — Bearing stability over time (bench)

**Do:** transmitter fixed, array fixed, 30 captures over 30 minutes.
**Pass:** standard deviation ≤ 10° (estimate).
**Fail meaning:** an alarm built on this bearing would jitter; would need temporal
smoothing before it is usable.

## T-5 — False positive baseline in a real RF environment

**Do:** put the node in an ordinary indoor space with Wi-Fi, then outdoors on a
mast with no drone present, and run unattended for 24 hours.
**Record:** the number of "detections" per hour.
**Pass threshold is not invented here:** this test exists to produce the number.
The product is only viable if that number can be driven low by classification and
whitelisting. **How low is acceptable depends on the alarm design** — one false
alarm per shift is unusable; one per week is tolerable.
**Fail meaning:** if 24 hours produces continuous alarms and no classifier helps,
passive RF in this environment cannot carry this product alone.

## T-6 — Two-node triangulation (outdoor, the key test)

**Do:** two nodes 100-300 m apart, a real drone flying known GPS tracks (from the
pilot's log or a phone tracker), estimate positions, compare.
**Pass:** circular error probable (CEP) ≤ 100 m at 500 m range (estimate — replace
with the measured number). State the number, whatever it is.
**Also record:** maximum usable detection range, and how that changes with drone
heading and altitude.
**Fail meaning:** if CEP is hundreds of metres, the product is a **direction alarm,
not a locator**, and the landing page must say exactly that. That is still sellable;
a false claim is not.

## T-7 — Alarm latency, end to end

**Do:** from drone transmit start to alarm visible in the UI.
**Pass:** ≤ 5 s (estimate).
**Fail meaning:** if it is 30 s, the value proposition changes from "react" to
"record", and the pitch must change with it.

## T-8 — Event log and acknowledgement

**Do:** generate 100 events, acknowledge in the UI, restart, verify persistence.
**Pass:** no lost events, acknowledgements persist, evidence files resolve.
**Fail meaning:** a product that loses its own records cannot be sold to a site with
a documentation obligation.

## T-9 — Polish incident report

**Do:** generate the report from a real event.
**Pass:** a Polish-speaking security officer can read it and file it without
explanation. Get one to check it if possible.
**Fail meaning:** it is a data dump, not a document. The report is a core sellable
feature — it must look like something a site can file.

## T-10 — Installability by someone else

**Do:** someone who is not Casper installs node 1 from the written instructions.
**Pass:** done in under one hour, working, without a phone call.
**Fail meaning:** every install costs Casper's time, which caps the business.

## T-11 — Power and weather endurance

**Do:** outdoor node, 7 days, unattended, in rain and a cold night.
**Pass:** no dropouts, no water ingress, no thermal shutdown.
**Fail meaning:** a mast product that dies in October is not a product in Poland.

## Reporting

Fill in `results.md` as: test id, date, setup, raw numbers, pass/fail, conclusion,
and what changes as a result. When all of T-1 to T-9 have results, the honest
capability statement writes itself — and that statement is what goes on the landing
page, into grant applications, and into the first buyer conversation.
