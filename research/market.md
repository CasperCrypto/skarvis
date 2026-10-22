# Market

Compiled 2026-10-22. All figures sourced in `sources.md`. Estimates labelled.

## Size and growth

| Metric | Value | Source |
|---|---|---|
| Counter-drone market | USD 6.64B (2025) → USD 20.31B (2030) | MarketsandMarkets, 25.1% CAGR |
| Drone detection segment alone | USD ~2,026M in 2026 | Fortune Business Insights, 14.8% CAGR |
| Capital into C-UAS startups | USD 1.2B across 15 rounds, Q1 2025 → Q1 2026 | nexi.fund |
| Single largest sector exit | D-Fend Solutions → Motorola, USD 1.5B (announced 1 Jun 2026) | droneintelligence.ai |

## The demand trigger is legal, not just geopolitical

This is the important part and the reason the timing works.

- **Ustawa z 29 maja 2026** (Dz.U. 2026 poz. 815) amended the crisis-management
  act, the protection-of-persons act and the direct-coercion act.
- A critical-infrastructure (IK) operator who is informed of its entry in the IK
  register has **6 months** to complete a threat analysis, then **6 months** to
  implement safeguards across six areas (physical, technical, personnel, cyber,
  legal, continuity), and **15 months** to declare full documentation. Source:
  gov.pl/rcb FAQ (see `legal-pl.md`).
- Protection plans must include drone scenarios, alarm thresholds, escalation
  procedure and the notification chain.
- Fines under art. 6zzr apply to entities also on the *critical entities*
  register; a plain IK operator without that status is not in that penalty
  chapter. Read: obligation exists, enforcement is soft for plain IK — so sell on
  the audit/documentation argument and the security-director's own risk, not on
  fear of a fine.

## Poland-specific demand, verified

- **SAN programme signed 30 Jan 2026**: ~PLN 15bn net (≈USD 3.7-3.8bn / EUR 3.56bn),
  consortium PGZ + Kongsberg (NOK 16bn to Kongsberg) + APS as key subcontractor.
  18 battery modules, 52 firing platoons, 18 command platoons, 703 vehicles.
  ~60% of value to Polish industry. IOC before end-2026, full delivery in 24 months.
  Financed largely by the EU SAFE instrument.
- **Tarcza Wschód (Eastern Shield)**: minimum PLN 10bn, anti-drone layer is part of it.
- **KINMA** (Kinetic and Non-Kinetic Anti-Drone Module) still in development; MON has
  not published cost.
- **Budget lines already visible**: PLN 175M for drone traffic management, and a
  significant part of PLN 4bn for capitalising Polish defence companies for
  anti-drone technology.
- **APS sold 14 SKYctrl sets for PLN 150M in 2022** (≈PLN 10.7M per set, urgent
  operational need). By Aug 2026 those systems no longer met needs (FPV swarms,
  heavy jamming) and the 1st Regional Logistics Base **cancelled the repair and
  technical-support tender on 20 Aug 2026**. Live gap in support/modernisation.

## Buyer segments, in order of how fast they can pay an unknown supplier

| Segment | Who | Why they buy | Speed |
|---|---|---|---|
| Systems integrators / resellers | Dilectro, Fly Lab, Naftor, Saportia, Wasko | They win the tender, need software capacity they don't have in-house | Weeks — they subcontract |
| SUFO / security firms | Stekop, Sign Polska, Nastawnia-class | They must now operate anti-drone tools and write protection plans | Weeks-months |
| C-UAS makers | APS, Hertz Systems, PGZ companies | They have backlogs and support gaps | Weeks (as subcontractor) |
| IK operators | Emitel, PSE, Orlen group, airports | Legally obliged, budget in 2027 | Months |
| Military / MON | via PGZ only | Programme of record | Years |

## What is NOT true about this market (kill these assumptions early)

- **It is not empty.** APS (Gdynia) and Hertz Systems (Zielona Góra) are
  established, hold national contracts, and APS supplies the C2 layer.
- **Detection hardware is not a differentiator.** It is sold at list price by
  several vendors (see `competitors.md`).
- **Interceptors are not a small-team product.** They are legally restricted and
  militarily procured.
- **"Everyone focuses on military drones" is wrong.** Civil detection is a crowded
  segment already served by Dedrone, DroneShield, Aaronia and Polish integrators.
  The unserved gap is the cheap documentation-and-workflow layer for obligated
  sites, not the sensor itself.
