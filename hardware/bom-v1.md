# Bill of materials — v1 prototype

Version 1, 2026-10-22. **Nothing in this file has been ordered.** Prices are what
the seller published on this date, in the seller's currency. VAT and duty are
estimates and labelled as such.

## Decision context before you read the list

- Single complete node ≈ **USD 1,730-1,880**.
- Two nodes (the minimum for a position estimate) ≈ **USD 3,300-3,700**.
- That is roughly **65-75% of Casper's ~USD 5k cash**. This is why Phase 0 is
  software-only and free, and why the order only happens after the test plan is
  agreed and the software runs on simulated data.

## Node core — buy this (verified prices, 2026-10-22)

| Item | Qty | Unit | Line | Source | Why this exact part |
|---|---|---|---|---|---|
| **KrakenSDR** 5-channel coherent SDR | 1 | USD 749.00 | USD 749.00 | krakenrf.com/product-page/krakensdr | Only cheap way to get 5 phase-coherent channels — required for direction finding and passive radar. 24 MHz-1766 MHz. |
| **Krakentenna matched set of five** | 1 | USD 249.00 | USD 249.00 | krakenrf.com/product-page/krakentenna-set-of-five | Length-matched with a VNA so phase error stays small. **Not outdoor-rated** — see substitutions below. |
| **Outdoor antenna set, 2.4 GHz** (5×, N/SMA) | 1 set | est. USD 150-300 | USD 150-300 | local RF/radio shops | Replaces the magnet set for permanent outdoor use. Estimate. |
| **Raspberry Pi 5, 8 GB** | 1 | ~USD 80-90 | ~USD 85 | local | Runs KrakenDAQ. Pi 5 is what the vendor's software targets. |
| **NVMe SSD + HAT, or 128 GB A2 microSD** | 1 | ~USD 40-60 | ~USD 50 | local | IQ capture and evidence files are big; a card alone is slow. |
| **Powered USB hub (5 V, min 3 A)** | 1 | ~USD 25-35 | ~USD 30 | local | The KrakenSDR draws real current; an unpowered hub causes dropouts. |
| **USB-C PSU + data cable** | 1 | ~USD 25 | ~USD 25 | local | Not included with the KrakenSDR. |
| **IP66/IP67 enclosure, DIN rail, glands** | 1 | ~USD 80-150 | ~USD 110 | local | Mast-mounted electronics need real weather protection. |
| **Mast / roof mount, clamps, poles** | 1 | ~USD 70-150 | ~USD 100 | local | Also sets the array's height, which sets its horizon. |
| **PoE injector or 12 V power run** | 1 | ~USD 30-50 | ~USD 40 | local | One cable up the mast is the goal. |
| **Cabling, connectors, lightning/surge protection** | 1 | ~USD 50-100 | ~USD 75 | local | Surge protection is not optional on a mast. |
| **RTL-SDR V4 dongle** (second receiver) | 1 | ~USD 40 | USD 40 | rtl-sdr.com / local | Band survey and later Remote ID work. Cheap and useful. |

**Node subtotal: ~USD 1,853 (mid-range estimates).**

## Shipping, tax, duty (estimates)

| Item | Estimate | Note |
|---|---|---|
| Shipping from KrakenRF (US) to Poland | ~USD 60-120 | Estimate. International, insured. |
| Import duty | 0-5% | Estimate. Radio equipment often low/zero duty but confirm the HS code. |
| **VAT 23%** | ~USD 300-380 | Estimate on the imported goods plus the Polish purchases. Not recoverable until the company is VAT-registered. |
| **Total single node, landed: ~USD 2,200-2,400 (estimate)** | | |

Revised honest figure: budget **USD 2,300 for one node**, **USD 4,000+ for two** once
VAT is paid as a private person. The VAT point is a real argument for registering
the company (or at least VAT) before ordering, if a contract is in sight.

## Two-node demo (the real target)

| | |
|---|---|
| Node 1 | ~USD 2,300 (landed, incl. VAT) |
| Node 2 | ~USD 1,700-2,000 (no second laptop/Pi dev kit needed) |
| **Total** | **~USD 4,000-4,300 (estimate)** |

## Deliberately NOT bought in v1

| Item | Why not |
|---|---|
| Active radar (EUR 30k+) | More than the whole budget. Integrate someone else's later via API. |
| EO/IR thermal camera | Adds cost, trigger interface and privacy/retention obligations. v2. |
| Jammer / any transmit device | Illegal for our use case and not our product. See `research/legal-pl.md`. |
| Downconverter for 5.8 GHz | Extra cost and failure mode. v1 is 2.4 GHz only. |
| Test drone | Do not buy yet. Borrow or borrow-fly first; a drone is a separate budget line and needs its own legal review (insurance from 13 Nov 2025 for 250 g-20 kg). |
| GNSS antenna/receiver for interference detection | Genuinely valuable, but v1.5. |

## Ordering checklist — do not skip

1. Test plan in `hardware/test-plan.md` agreed **before** any order.
2. Software running and tested on simulated data (Phase 0 gate passed).
3. Confirm current KrakenSDR price and stock — it sold out before and scalper
   listings (USD 1,271-1,273) are not the maker's price.
4. Confirm the outdoor antenna substitution and that the chosen enclosure fits the
   antenna connectors.
5. Confirm the laptop can run the KrakenDAQ stack (Linux preferred; the Pi runs it
   natively, so worst case the Pi is the capture host and the laptop is the UI).
6. Decide VAT: private purchase pays 23% irrecoverably.
7. Buy node 1 only. Node 2 after Phase 1 gates pass.

## Where to buy

- KrakenSDR + Krakentenna: **krakenrf.com** directly (also Crowd Supply). Not Amazon
  — listings there claiming to be KrakenSDR at odd prices are suspect.
- Pi, hub, enclosure, mounting hardware: local Polish electronics supplier
  (Botland, TME, or a local shop) — faster and cheaper than importing.

## Before ordering, verify these three facts yourself

1. KrakenSDR price and stock today.
2. That an outdoor-rated 2.4 GHz antenna set with SMA connectors exists at the
   price estimated here.
3. The current Polish VAT/duty treatment of an SDR receiver imported from the US.
