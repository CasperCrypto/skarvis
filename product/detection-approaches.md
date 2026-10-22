# Detection approaches — what we can and cannot see

Version 1, 2026-10-22. This file exists so nobody in this project overpromises.
Read it before writing any buyer-facing material.

## The physical truth about drones and radio

A drone is detectable by radio **only if it has a radio link that is transmitting
while it flies**. That is true for almost all consumer and industrial drones
(control link plus video downlink, typically 2.4 GHz and 5.8 GHz, some 900 MHz and
433/868 MHz). It is **not** true for fibre-optic guided FPV drones, which carry no
radio at all — and those are now a real and growing share of the military threat
picture. That single fact is why the whole market moved back to radar and EO/IR.

## Sensor by sensor

| Sensor | Sees | Blind to | Cost in our plan | Legal |
|---|---|---|---|---|
| **Passive RF** (2.4/5.8 GHz) | Emitting drones; can locate the operator too | Fibre-optic FPV; silent drones; drones in a crowded band | KrakenSDR USD 749 + antennas USD 249 | **No permit needed** (receive-only, art. 145 PKE) |
| **Remote ID receive** | Compliant drones: serial, position, operator location | Anything not broadcasting (most hostile drones) | ~USD 40 receiver | No permit (receive-only) |
| **Acoustic** | Propeller signature incl. tethered/silent drones | Wind, traffic, industrial noise; short range | Mic array ~USD 100-300 DIY | No permit (no RF) |
| **Passive radar** (DVB-T illuminator) | Physical object, regardless of emissions | Needs a strong illuminator; heavy compute; hard | KrakenSDR can do it; compute is the cost | No transmit |
| **Active radar** | Physical object, all drone types | Birds vs drones needs micro-Doppler; cost | **EUR 30k+** — out of budget | Permits/type approval territory |
| **EO/IR camera** | Visual confirmation, human judgement | Night/weather; needs pointing at the right place | ~USD 200-2,000 | Privacy/GDPR once recording |

## What v1 therefore is, honestly

**A passive RF detection and direction system.** It sees the majority of real-world
nuisance and criminal drone activity over a site (the drones people actually fly).
It does not see fibre-optic FPV. It will be noisier in a Wi-Fi-dense environment
until the classifier and the whitelist are tuned.

## Known technical traps

1. **2.4 GHz is a crowded band.** Wi-Fi, Zigbee, Bluetooth, cameras, microwaves.
   Energy detection alone will fire constantly. DoA plus a drone-specific
   signature (frequency-hopping pattern, video carrier shape) is what turns energy
   into a credible detection. Budget engineering time for this, not for the radio.
2. **5.8 GHz is above the stock KrakenSDR tuner's comfortable range**
   (R820T2 spec: 24 MHz-1766 MHz). Reaching 5.8 GHz needs a downconverter or a
   different receiver — an extra cost and an extra failure mode. **v1 is 2.4 GHz.**
3. **8-bit ADC.** The KrakenSDR is 8-bit and overloads near strong transmitters.
   On an industrial site with its own radio gear, front-end filtering and gain
   control matter more than the software.
4. **Coherence is the whole trick.** Five dongles on a hub cannot do direction
   finding; the KrakenSDR's shared clock and noise-source calibration is what makes
   MUSIC/interferometry possible. Do not "save money" by substituting dongles.
5. **Indoor antennas are not outdoor antennas.** The Krakentenna set is explicitly
   not outdoor-rated and is magnet-mount for a car roof. Outdoor permanent
   installation needs different antennas and a weatherproof enclosure — budget and
   substitute, do not improvise on a customer roof.
6. **Multipath.** Signals bounce off buildings and tanks and steel sheds. A single
   node's bearing can be off by tens of degrees in a bad RF environment. Two nodes
   and time-correlation are how you survive it.

## The upgrade path (v2 and beyond), in the order that adds the most detection per zloty

1. **Remote ID decode** — cheap, legal, adds identification for compliant drones.
2. **Cheap IP camera on alert trigger** — human confirmation; turns "bearing 137°"
   into "here is the picture". Also the thing a security officer trusts most.
3. **Acoustic sensor** — catches silent/tethered drones at short range; needs
   careful calibration to be worth anything on an industrial site.
4. **GNSS interference detection** — detects jamming/spoofing near a site. Cheap in
   L1, and a genuine requirement for some buyers.
5. **Third-party radar via API** — integrate someone else's EUR 30k radar rather
   than build one. This is the honest answer to fibre-optic FPV.
6. **Multi-site management** — only after one site works.

## The line we never cross

No transmit. No jamming. No spoofing. No GNSS interference. No capture. No kinetic.
The 29 May 2026 amendment permits some of that, but only for SUFO personnel of an
IK operator, after notifying MSWiA/UKE/MON, and only situationally. It is not our
business to build, and it is not a capability we can legally offer to the civil
customers we are targeting. See `research/legal-pl.md`.
