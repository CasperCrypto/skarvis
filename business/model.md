# Model — pricing and unit economics

Version 1, 2026-10-22. **Everything in the price columns is an estimate.** Nothing
here has been tested against a customer. Treat this file as a hypothesis with a
kill date, not as a business plan.

## What we are selling (restated, because it keeps drifting)

Not a sensor. Not a radar. **Detection plus a workflow and a document.**
The hardware is a commodity we assemble; the value is the alarm quality, the
operator record and the Polish incident report a site can file.

## Cost side (measured where possible)

| Item | Cost | Status |
|---|---|---|
| Node hardware, landed incl. VAT | ~USD 2,300 | estimate, from `hardware/bom-v1.md` |
| Node hardware once VAT-registered | ~USD 1,850 | estimate |
| Assembly time | ~4-6 h | estimate |
| Install at site | ~2-4 h | estimate |
| Software | ours | — |
| Annual hosting/management per site | ~USD 200-600 | estimate (a small VPS or the site's own PC) |
| Support | hours | unknown until a pilot runs |

**The number that decides the business is one we do not know yet:** how many nodes
a real site needs to cover its area. If a mid-size industrial site needs 6 nodes,
that is ~USD 11k of hardware at our cost, which changes the entire pricing story.
This must be measured in Phase 2, not guessed.

## Three possible revenue models — pick after Phase 2, not before

### A. System sale (one-off + support)
- Price hypothesis: **PLN 60-150k** per site for a 2-4 node system plus software,
  plus an annual support/support-update fee (estimate).
- Comparable: APS sold 14 SKYctrl sets for PLN 150M (~PLN 10.7M per set) — those are
  military-grade multi-effector systems, so this is **not** our price band; it only
  shows what an institutional buyer will pay for a full system.
- Cash quickly, but lumpy and needs a sales cycle.

### B. Pilot then subscription (recommended first motion)
- Price hypothesis: **PLN 10-30k for a 90-day paid pilot**, then **PLN 1,500-4,000
  per month** per site (estimate).
- Lower barrier, gets a reference, matches the "detection plus document" value, and
  recurring revenue fits Casper's runway problem better than one-off sales.
- Competes against nothing, because nobody is selling the cheap compliance layer.

### C. Subcontracting to integrators (the fallback that also funds the build)
- Sell days or a fixed-scope build to APS / Hertz / Dilectro / Fly Lab / Naftor /
  Saportia / Wasko, or to a SUFO firm.
- Price: **PLN 3,000-6,000 per day**, or **PLN 15-50k** per fixed-scope module
  (estimate; Polish IT contracting for defence-adjacent work).
- Pays in weeks, needs no hardware and no product, and every contract teaches us
  what the buyer actually wants. The target list already exists in
  `business/outreach/` (built, **not sent**).

## Unit economics under model B (the one to test first)

Per site, per year (all figures estimates):

| Line | Amount |
|---|---|
| Pilot fee (once) | PLN 10-30k |
| Subscription | PLN 18-48k |
| Hardware cost (2 nodes, VAT-registered) | −PLN 15k |
| Install (2-4 h) | −PLN 1k |
| Hosting | −PLN 1-3k |
| **Gross margin before support time** | **PLN 12-60k** |

The margin is real but thin at the low end, and it collapses if installs need more
than a few hours or if support is heavy. Which is why T-10 (install by a third
party) is a commercial test, not just an engineering one.

## Break-even framing

To reach Casper's $2,000/month net (~PLN 8,000/month) on subscriptions alone, at
PLN 2,500/month per site (mid estimate) and ~60% margin after hardware amortisation,
the business needs **roughly 5-6 paying sites**. That is a real, achievable number —
and it is also why the subcontracting path (model C) matters: it can cover the
runway while those 5-6 sites are won.

## What would make the model wrong

1. Sites need many more nodes than assumed.
2. The false alarm rate is so high that a site will not pay for it.
3. Sites will only buy from a known name with a service history — in which case
   model C (sell to integrators) is the only viable business, and the product is a
   component, not a brand.
4. Compliance documentation turns out not to be a budget line anyone owns.

## The one pricing rule

**Never quote a price before the scope and the pilot's acceptance criteria are
agreed.** In security procurement an early number becomes the ceiling for the whole
relationship.

## Kill criteria

- No paid pilot after 20 real conversations → the market answer is no; switch to
  model C full-time.
- Pilot delivered but not renewed → the value is not recurring; re-price as a
  one-off system sale or drop.
