# Outreach material — BUILT BUT NOT SENT

Status as of 2026-10-22: **nothing has been sent.** Casper's decision was to build
the prototype first and look for money afterwards. These files are the ready-to-use
fallback and the soft-sell channel.

## What is here

| File | Contents |
|---|---|
| `outreach-pack-2026-10-22.txt` | 28 verified email addresses, 5 form-only targets, Polish message templates, DM versions, send sequence, and the list of claims never to make |
| `targets-2026-10-22.csv` | 33 rows: company, tier, email, source URL for that address, second channel, notes |

## Verification state

- Every email was copied from a page that was fetched on 2026-10-22, not guessed
  from a name pattern. The source URL for each is in the CSV.
- MX records were checked per domain. Two domains have **no MX** and will silently
  blackhole mail: `ochrona.orlen.pl` and `grupapgz.pl`. Do not send to those.
- Two addresses existed on pages but their domains have no MX
  (`biuro@karabela.com.pl`, `biuro@armachrona.pl` equivalents) — treat as
  unconfirmed, not dead.

## Why it is worth sending even on the prototype path

Two of these companies are **potential pilot sites or pilot partners**, not just
employers: a SUFO firm protecting an obligated site is exactly the user the
prototype is built for, and an integrator can supply the site and the mast.
A pilot with one of them removes the need for cold outreach later.

## When to send

Only after `hardware/results.md` has real numbers in it. Sending a pitch before the
test plan has produced data would mean claiming a capability that does not exist
yet, which `CLAUDE.md` forbids.
