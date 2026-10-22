# Competitors — who is already selling this

Compiled 2026-10-22. Prices verified the same day unless marked.

## Polish / regional

### Advanced Protection Systems (APS) — Gdynia. The one to respect.
- Products: **FIELDctrl** 3D MIMO radars (Advance, Range, Runway, Ultra SR/LR, Follow),
  **SKYctrl** anti-drone systems (S, L), **CyView C2** suite, APS&MSI Terrahawk Paladin.
- Role in SAN: supplies the **command-and-control (C2) software and sensor
  solutions**. SanView C2 aggregates radars, thermal cameras and acoustic sensors
  into one operational picture, classifies targets (bird vs drone) with AI, and
  manages effectors. It also integrates at platoon level in the SAN architecture.
- Track record: 14 SKYctrl sets sold to the Army in 2022 for **PLN 150M**
  (~PLN 10.7M per set). Plus the SAN subcontract.
- Legal/tender detail: 20 Aug 2026, the 1st Regional Logistics Base **cancelled**
  the tender for repair and technical support of SKYctrl (37-month contract);
  APS's own bid was rejected for not filing evidence on time.
- Open roles (Oct 2026) incl. Java Developer, DevOps Engineer, Product Manager
  Radar & C-UAS, Configuration Manager. They are hiring software people now.
- Site: apsystems.tech | X: @APS_SKYctrl

**Read:** they already own the C2 layer we would otherwise sell. Competing head-on
is a losing play. Subcontracting to them, or selling below them to non-SAN sites
they ignore, are the two viable routes.

### Hertz Systems — Zielona Góra (Hertz Systems Ltd Sp. z o.o.)
- Product: **HAWK** anti-drone system (developed ~15 years). Claims detection of
  everything moving in air, identification and classification, effective against a
  single drone and a swarm; soft-kill and hard-kill neutralisation.
- Claims deployment with Border Guard, police, airports and Ukrainian soldiers.
- Cooperation agreement with PGZ for military anti-drone systems (signed at MSPO Kielce).
- Public estimate from their president: a system covering the whole eastern border
  would cost **from PLN 1bn upward** and take up to 3 years.
- Site: hertzsystems.com | email hertz@hertzsystems.com | R&D at Space Technology
  Park, Nowy Kisielin, Zielona Góra

### PIT-RADWAR (PGZ) — Warsaw / Gdańsk / Wrocław / Kobyłka
- Radar, ESM/ELINT, C2/C4ISR and air-defence systems. In SAN: battery-level
  integration (APS integrates at platoon level).
- Also builds the Polish C2 for Mała Narew (with MBDA, Jelcz, WZU, SOŁA radar).
- Publishes no contact email — form and phone only.
- Their job ads (e.g. C++ developer, "systemy wspomagania dowodzenia") describe
  distributed systems for reconnaissance, planning and fire control, with
  JIRA/Confluence/Git/Jenkins, Boost/GTest/cmake/conan, SOLID/TDD. That is a
  conventional software shop inside a defence prime — i.e. a place where an
  outside contractor could plausibly be used, and where the bar is standard.

### Integrators and resellers (our most realistic first customers)
| Company | Position | Contact |
|---|---|---|
| **Dilectro Enterprise** (Warsaw) | Resells Spanish ASDT C-UAS (SENDES DAU/DAU stationary, SENDESCOPE mobile, SENDES Gate, SJ jammers). Explicitly promotes **cloud/subscription C-UAS** and says it configures, deploys and supports. | kontakt@dilectro.pl, +48 881 726 700 |
| **Fly Lab** (Zielona Góra, Space Technology Park) | Own **SkyPatrol** detection system: drone and operator location, live map, protected zones, event archive and **operator action audit**. Also an own interceptor and BSP docking stations. States it builds dedicated applications and has a dev team. | biuro@flylab.expert, 536 093 047 |
| **Naftor** (Warsaw) | Designs C-UAS from cameras, RF scanners, radars and jammers. Claims "integration with any protection-management platform". Office: Wał Miedzeszyński 630. | sekretariat@naftor.pl, 22 487 57 87 |
| **Saportia** (Radom) | Technical security integrator: CCTV, SSWiN, BMS/SMS/VMS/**PSIM**, anti-drone line, fire systems, IT/OT. Works on critical infrastructure. | biuro@saportia.pl, 48 363 41 41 |
| **Wasko** (Gliwice) | Large Polish systems integrator, network and security; also a Milestone-class VMS reseller. | wasko@wasko.pl |

### Notable: SkyPatrol (Fly Lab) already ships our "differentiator"
Their public feature list includes **"archiwizacja zdarzeń i audyt działań
operatorów"** (event archive and operator-action audit) and an interactive live
map. That is close to the v1 product thesis. Implication: the audit-trail idea is
not novel on its own — it has to be cheaper, faster to deploy, or tied
specifically to the POIK documentation obligation to be worth buying.

## International (prices are the market's answer to "what is a sensor worth")
| Vendor | Product | Price | Note |
|---|---|---|---|
| Dedrone (Axon) | RF-160 | **EUR 14,999** | retail-listed |
| Dedrone | DedroneEye Portable | **USD 12,490** | palm-size, 1.4 kg, 5 km vs DJI Mavic 3, 12h battery, 12,000 RF signals/s, alerts in 1.3-2.1 s |
| DroneShield (ASX:DRO) | DroneSentry-X2 | **USD 24,900** | 4.2 kg, external power, ~17 min setup |
| Aaronia | RTSA Suite + Flyover bundle | **USD 31,500** | RF fingerprinting only |
| Fortem | DroneHunter interceptor | **~USD 160,000** | net capture |
| D-Fend (Motorola) | EnforceAir takeover | acquired for **USD 1.5B**; USD 185M expected 2026 revenue | control-link takeover |
| Generic | standalone radar unit | **EUR 30,000-80,000** | 1-8 km |
| Generic | professional RF sensor | **USD 15,000-60,000** | 1-5 km |
| Generic | PTZ camera with AI classification | **USD 10,000-40,000** | EO + thermal |
| Generic | handheld RF detector | **USD 5,000-15,000** | 2.4/5.8 GHz |
| Generic | Remote ID receiver | **USD 2,000-8,000** | compliant drones only |

**The cheapest commercial C-UAS detector concept** in the market data: "For an
average civilian site (five hectares, mostly cooperative drones), expect a few
thousand euros excl. VAT for an RF detector + annual hub licence" (DECTYR
buyer's guide). That is the price band we must beat or match, because it is what
a civil site will compare us against.

## Where the gap actually is

1. **Price floor.** Everyone sells a sensor at EUR 12-30k. Nothing sits at
   EUR 2-5k with software that produces documentation.
2. **Documentation.** No vendor's public material is about producing the
   protection-plan annex a Polish IK operator must file. They sell hardware.
3. **Effector-free deployment.** Nearly every Polish vendor leads with
   jamming/neutralisation and most civil sites cannot legally use it. A
   detection-plus-evidence system is legally deployable today by anyone.

## Honest competitive risk

- APS or Hertz could ship the same software layer as a bundled feature and
  undercut us to zero, because they already own the customer.
- Fly Lab already has the audit feature.
- A site with a PLN 10M budget will buy a real system from a name it knows.
- Therefore the go-to-market must be the segments the incumbents do not chase:
  obligatorily-protected sites without IK status, mid-size industry, logistics
  and airports, and integrators who need subcontract capacity, not another vendor.
