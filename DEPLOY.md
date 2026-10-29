# Putting SKARVIS online

Written 2026-10-29. Two Cloudflare Pages projects built from this GitHub
repository. No build step: the site is plain files.

| Project | What it shows | Build output directory | Who can open it |
|---|---|---|---|
| `skarvis` | Public site (PL + EN) and the Trener demo | `web/site` | Everyone |
| `skarvis-console` | Build console, docs, code | `/` (repository root); console at `/web/admin/` | Only the email addresses you allow (Cloudflare Access) |

Why not GitHub Pages: this repository is private, and GitHub Pages from a
private repository needs a paid GitHub plan; the published site is public
anyway, so it cannot protect the console.
([GitHub docs](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site),
[community thread](https://github.com/orgs/community/discussions/22817))
Cloudflare Pages deploys from private GitHub repositories once you authorise
it ([Cloudflare guide](https://developers.cloudflare.com/pages/get-started/guide/)).

## Before the public site goes live (blocking)

1. Fill the `[UZUPEŁNIĆ]` fields in `web/site/polityka-prywatnosci.html` and
   `[TO FILL IN]` in `web/site/en/privacy.html`: data controller (name or
   company, address) and a contact email. The pilot form collects personal
   data, so the notice must be complete (RODO).
2. After the first deploy, send one test entry through the form and delete
   that row in Supabase (project `skarvis`, table `pilot_signups`).
3. Check that every status tag on the site still matches
   `hardware/results.md`. Nothing measured yet means nothing upgraded.

## Public site: `skarvis`

1. Sign in at dash.cloudflare.com (free plan).
2. Workers & Pages → Create → Pages → Connect to Git. Authorise GitHub and
   pick `CasperCrypto/skarvis`.
3. Production branch: `main`. Framework preset: None. Build command: empty
   (or `exit 0`). Build output directory: `web/site`.
4. Save and Deploy. The site appears at `https://<project>.pages.dev`; every
   push to `main` redeploys it.
5. Later: Custom domains → add the SKARVIS domain once you own it.

This project publishes only `web/site`. The console, the docs, the code and
the outreach lists are not in it.

## Console: `skarvis-console` (private)

**Do not create this project without step 2.** It publishes the whole
repository, including `business/outreach/` contact lists, and the console's
own passphrase is readable in `web/admin/admin.js`. Cloudflare Access is the
real lock; the passphrase screen stays as a second, soft step.

1. Create a second Pages project from the same repository: name
   `skarvis-console`, branch `main`, build output directory `/`.
2. Cloudflare dashboard → Zero Trust → Access → Applications → Add an
   application → Self-hosted:
   - Domain `skarvis-console.pages.dev`, and a second entry
     `*.skarvis-console.pages.dev` so preview deployments are locked too.
   - Policy: Allow, Include → Emails → your own address (and anyone else who
     should see the console).
   - Login method: One-time PIN (a code sent by email). Check it is enabled
     under Zero Trust → Settings → Authentication.
3. Open `https://skarvis-console.pages.dev/web/admin/`. Cloudflare asks for
   your email and sends a code; then the console's passphrase screen.

Third-party guides report that Access is free for up to 50 users; check
Cloudflare's current pricing when you sign up
([guide](https://revdoku.com/blog/how-to-password-protect-a-cloudflare-pages-site/),
[preview URLs](https://israynotarray.com/en/misc/2026/05/13/cloudflare-pages-preview-urls-stay-forever-lock-with-access/)).
If a code never arrives: look in spam, and check the address matches the
policy exactly (Access sends nothing to an address that is not allowed).

## Local preview (unchanged)

- Site: `web/preview-site.bat`, or `python -m http.server 8765 --directory web/site`
- Console: `web/preview-admin.bat` (serves the whole repository locally)
- Trainer only: `web/preview-sim.bat` (opens from disk, no server)
