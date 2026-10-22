-- SKARVIS pilot list. Applied 2026-10-22 to the Supabase project "skarvis"
-- (ref xoquclgglhucvyvirmep, region eu-central-1).
--
-- The public website may only INSERT, with the publishable key (role anon).
-- Nobody can read rows with that key; read them in the Supabase dashboard.
-- Personal data under RODO/GDPR: see web/site/polityka-prywatnosci.html.

create table public.pilot_signups (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  lang          text not null default 'pl' check (lang in ('pl', 'en')),
  name          text not null check (char_length(name) between 2 and 120),
  organization  text not null check (char_length(organization) between 2 and 200),
  email         text not null check (char_length(email) <= 254 and email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  phone         text check (phone is null or char_length(phone) <= 40),
  site_type     text not null check (site_type in ('gmina', 'oze', 'logistics', 'critical', 'integrator', 'other')),
  town          text check (town is null or char_length(town) <= 120),
  message       text check (message is null or char_length(message) <= 4000),
  loi_interest  boolean not null default false,
  consent       boolean not null check (consent = true),
  status        text not null default 'new' check (status in ('new', 'contacted', 'loi_sent', 'declined'))
);

comment on table public.pilot_signups is 'SKARVIS pilot-list form submissions from the public website. Personal data under RODO/GDPR: insert-only for anon, read via dashboard only.';

alter table public.pilot_signups enable row level security;

revoke all on public.pilot_signups from anon, authenticated;
grant insert (lang, name, organization, email, phone, site_type, town, message, loi_interest, consent)
  on public.pilot_signups to anon;

create policy "website can add a signup"
  on public.pilot_signups
  for insert
  to anon
  with check (consent = true and status = 'new');

create index pilot_signups_created_at_idx on public.pilot_signups (created_at desc);
