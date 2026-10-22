# Assembly — node 1

Version 1, 2026-10-22. Written **before** the hardware arrives, on purpose, so the
order can be checked against it. Correct anything that turns out wrong — a wrong
assembly doc that nobody fixes is worse than none.

## Pre-flight, before you touch hardware

- [ ] Phase 0 gate passed: `python -m unittest discover` green and `--demo` runs.
- [ ] Test plan (`test-plan.md`) agreed and printed.
- [ ] A known transmitter to test against: the building Wi-Fi router, and ideally a
      drone controller. Note the router's channel (which 2.4 GHz frequency).
- [ ] Decide the array's orientation and write it down. **Every bearing is relative
      to the array's zero mark.** If you do not record the mark, all your bearings
      are meaningless. This is the single most common mistake in DF work.

## Physical build

1. **Array layout.** Five antennas in a circle, evenly spaced. Measure the radius
   and record it — the DoA maths needs the baseline in metres. Typical compact
   array: 5 antennas on a 0.1-0.2 m radius circle for 2.4 GHz. Larger radius =
   sharper bearing but more ambiguity. Start at ~0.15 m.
   - Mark antenna 1 physically with tape. Note which physical direction it points
     (e.g. "antenna 1 = north"). Write it in `results.md`.
2. **Connections.** Antenna 1 → Kraken channel 1, and so on, in the same rotational
   order. Do not skip or reorder channels; coherence calibration assumes a known
   geometry. **Same rotational direction must be used in software** — an antenna
   array wired clockwise but modelled anticlockwise mirrors every bearing.
3. **Power.** Powered USB hub for the KrakenSDR; its own PSU for the Pi. Do not
   power both from one weak supply — brownouts show up as mysterious coherence
   failures, not as obvious reboots.
4. **Enclosure.** Antennas outside, receiver inside, shortest possible coax runs.
   Every extra metre of cheap coax costs signal. Use the outdoor antennas, not the
   magnet-mount set, for anything that stays outside.
5. **Surge protection** on the mast run. A strike takes out the Pi, the receiver and
   the hub together.
6. **Network.** Node gets a static LAN address. Record it.

## Software bring-up, in this order (do not skip steps)

1. **Receiver visible.** Confirm the operating system sees the KrakenSDR and all
   five channels.
2. **Coherence calibration.** Run the vendor's calibration with the noise source.
   Record the phase offsets it reports. **If calibration fails or drifts, stop** —
   nothing downstream will be trustworthy.
3. **Known-transmitter baseline.** With the router transmitting, capture a snapshot
   and compute a bearing. Point the array so the true bearing is known (e.g. router
   due north). Compare. Record the error in degrees.
4. **Repeat 5 times** at different array yaws to check whether the error is
   constant (a calibration/offset problem, fixable) or random (a multipath or SNR
   problem, harder).
5. **Integration with our software.** Feed the capture into `czapla.doa` and confirm
   it produces the same bearing as the vendor tool within a few degrees. If our
   implementation disagrees, ours is wrong — trust the vendor's tool first and debug
   against it.
6. **Full chain.** Confirm one event reaches the store and generates a Polish
   report (test T-7, T-9).

## Common failure modes, and what they look like

| Symptom | Likely cause | Fix |
|---|---|---|
| Bearing is mirrored / off by exactly the array symmetry | Channel order reversed or array modelled in the wrong rotational direction | Check wiring order against the software's assumed geometry |
| Bearing wanders ±40° between captures | Multipath, or a strong local transmitter overloading the 8-bit front end | Reduce gain, add a band filter, change array position, take more snapshots and median |
| Nothing detected at all | Wrong band, wrong gain, or the antenna set is 100-1000 MHz while you are listening at 2437 MHz | Check the antenna spec — this is exactly why the outdoor substitution matters |
| Detections fire constantly | Wi-Fi/Bluetooth energy in the band; the classifier is doing nothing yet | Expected at first. This is what the classifier and whitelist are for — record it as a false-positive baseline |
| Coherence calibration fails | Under-powered hub; heat; one channel dead | Power first, then swap the hub, then check each channel individually |

## What to write down for every session

Date, array radius, array yaw, which physical direction antenna 1 points, gain
setting, band, weather, what was transmitting and where, the measured bearing, the
true bearing, the error, and anything that looked wrong. Untracked sessions are
wasted sessions — the numbers only become a product once they are written down.

## Safety and legal reminders

- Receive-only. Nothing in this build transmits. Do not add a transmit path.
- Do not fly a drone for testing until you have checked the current rules
  (insurance obligation since 13 Nov 2025 for 250 g-20 kg; geographic zones; site
  consents). Test on your own property or a permitted area first.
- Do not mount anything on a site you do not own without written permission, even
  a "just detecting" box.
