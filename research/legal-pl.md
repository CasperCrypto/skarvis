# Polish law — what we may build, and who may use it

Compiled 2026-10-22 from primary-ish sources (see `sources.md`). This is an
engineering brief, not legal advice. Before selling anything, a Polish lawyer
checks it. Re-check before every claim made to a buyer.

## The one rule that defines the product

**Passive reception needs no radio permit. Transmission does.**

- **Art. 145 ustawy Prawo komunikacji elektronicznej (PKE)**: devices *intended
  exclusively for reception* do not require a radio permit. (Source: UKE BIP,
  "Urządzenia niewymagające pozwolenia", citing art. 145 PKE, formerly art. 144
  Prawa telekomunikacyjnego.)
- Everything else — jammers, spoofers — requires a permit in principle and is
  otherwise lawful only through the narrow route below.

**Consequence for us:** the entire v1 product (RF detection, Remote ID receive,
acoustic, radar receive, classification, alerting, evidence) is on the legal
side of that line. Do not cross it.

## The narrow route to effectors (why we are not building them)

**Art. 6zj ustawy o zarządzaniu kryzysowym**, inserted by Ustawa z 29 maja 2026
(Dz.U. 2026 poz. 815):

- An **IK operator** may decide to allow the use of telecom-disrupting devices
  (zakłócających) by **SUFO** personnel.
- Before that, it must notify the interior minister, the **UKE President** and the
  relevant MON unit of: device name and type, frequency bands, radiated power,
  antenna characteristics, installation height, coordinates, and the affected
  sectors.
- Use is limited to the strictly necessary time, with minimisation of the impact
  on telecom services.
- After actual use, the same authorities are notified immediately and may order
  it stopped.
- **This is explicitly not a general radio permit and not consent to permanently
  jam spectrum.** It is a situational operational basis for an IK operator.

Only entities with IK status have this route. A site without IK status has no
equivalent legal basis for jamming at all.

## Who may physically neutralise a drone

- **Art. 36 ustawy o ochronie osób i mienia** (amended): a qualified security
  worker may use means and devices intended to neutralise unmanned aircraft.
- **Art. 11 pkt 16 ustawy o środkach przymusu bezpośredniego i broni palnej**:
  UAS neutralisation is a statutory case of using direct coercion.
- **Art. 156ze ust. 1 Prawa lotniczego**: a UAS may be destroyed, immobilised or
  taken control of only where its operation:
  - endangers or may endanger life or health of people or animals,
  - creates or may create a threat to a protected object, device or area,
  - causes justified suspicion of use as a means of terrorist attack,
  - threatens or disturbs air traffic safety,
  - is conducted against a prohibition in force in the relevant geographic zone.
- Principles that always apply: necessity, proportionality, minimisation of harm,
  and stopping the moment the goal is achieved.
- "A drone is over the object" is **not** by itself a legal premise. The operator
  must qualify one of the five grounds.

## Obligations on the operator (our customers' clock)

From gov.pl/rcb FAQ:

- Entry in the IK register is decided by the RCB director against criteria in a
  Council of Ministers resolution; sector membership alone is not enough.
- Up to 30 days may pass between entry and the operator being informed.
- From the day of being **informed**: 6 months for the threat analysis, then 6 months
  to implement solutions across six areas, 15 months to submit a declaration that
  the protection documentation is complete.
- The coordinator of IK protection (and a deputy) must be appointed within 30 days.
- Anti-drone means belong in the protection plan (or an annex), covering at
  minimum: drone/FPV threat scenarios, possible consequences, observation and
  neutralisation sectors, sensor and effector types, integration with technical
  security systems, SUFO roles, alarm thresholds, escalation procedure, decision
  authority, the notification chain to Police/ABW/PSP/ULC/UKE, incident
  documentation rules, and custody of wreckage, payload, recordings, logs and RF traces.

## What this means commercially

1. Sensors are the easy legal half — anyone can deploy passive detection.
2. The **documentation, workflow and evidence trail** is what a site is measured
   against and what nobody is selling cheaply.
3. We can therefore sell to sites that are *not* IK-registered too (airports,
   logistics, industry) on the same detection plus procedure offer, without
   touching effectors at all.
4. An IK operator is a better customer later, because they can legally go further —
   so we design the software so an effector stage could be added by someone else.

## Watch list — laws and guidance that could change the plan

- Prawo lotnicze amendment of 24 Jan 2025 (Dz.U. 2025 poz. 179), in force
  26 Feb 2025 — current drone regime, insurance obligation from 13 Nov 2025 for
  250 g to 20 kg drones (fine up to PLN 4,000).
- ULC President's guidelines no. 7/2024 — operations over power stations and
  similar require the manager's consent (PSE requires applications 5 days ahead).
- EU Action Plan on Drone and Counter-Drone Security (Feb 2026) plus the
  planned **Drone Security Package 2026** — could add registration/identification
  duties and an "EU trusted" equipment label. That label could become a
  procurement requirement, so track it.
- Polish AI act implementation bill (adopted by the Council of Ministers
  31 Mar 2026) — high-risk AI obligations may touch classification systems used
  in critical-infrastructure management. Unresolved in the draft per PTI.
  **Flag: our classifier could land in high-risk territory. Check before launch.**
