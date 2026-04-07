# Architecture, Design & Technology Directory — Build Plan

## Current Status

### Completed
- [x] **Phase 0** — Environment setup (2026-04-07)
- [x] **Phase 1** — Minimal schema (2026-04-07)
- [x] **Phase 2** — Generate types and data access layer (2026-04-07)
- [x] **Phase 3** — Frontend foundation (2026-04-07)

- [x] **Phase 4** — Firm and people detail pages (2026-04-07)

- [x] **Phase 5** — Awards and source pages (2026-04-07)

### In Progress
- [ ] **Phase 6** — Ingestion foundation

### Upcoming
- [ ] Phase 7 — First ingestion sources (RSS + OpenAlex)
- [ ] Phase 8 — Manual review lane
- [ ] Phase 9 — Light enrichment
- [ ] Phase 10 — Basic search
- [ ] Phase 11 — Quality checks and launch prep

---

## Session Log

### Session 1 — Phase 0: Environment Setup (2026-04-07)
- Created repo structure: web/, scrapers/, scripts/, supabase/, docs/
- Initialized Next.js app in web/ (App Router, TypeScript, Tailwind, ESLint)
- Created Python virtual environment and requirements.txt for scrapers
- Created .env.example files for web and scrapers
- Created README with setup instructions
- Pushed to GitHub: moinmoin23/arch-directory

### Session 2 — Phase 1: Minimal Schema (2026-04-07)
- Created migration: `20260407000001_initial_schema.sql`
- Tables: firms, people, sources, awards, firm_people, award_recipients,
  entity_aliases, ingest_cursors, enrichment_queue, review_queue
- ENUMs: sector_type, entity_type, source_type, queue_status, review_status, prestige_tier
- Extensions: pg_trgm, fuzzystrmatch, unaccent
- Indexes: GIN trigram on canonical_name + alias_normalized, btree on slug/sector/country/city
- Auto-update triggers on firms.updated_at and people.updated_at
- Seed data: 10 firms, 8 people, 4 awards, 3 sources, 6 aliases, 7 firm_people links, 4 award_recipients
- Verified: `supabase db reset` clean, trigram fuzzy matching works
- .env.local files configured with local Supabase credentials

### Session 3 — Phase 2: Types & Data Access Layer (2026-04-07)
- Generated TypeScript types from local Supabase via `supabase gen types`
- Created `supabase-server.ts` and `supabase-browser.ts` clients
- Query layer in `lib/queries/`:
  - `firms.ts`: getFirmBySlug, listFirmsBySector, listFirmsByCountry, listFirmsBySectorAndCountry, getFirmAliases, getFirmAwards, countFirmsBySector
  - `people.ts`: getPersonBySlug, listPeople, listPeopleByRole, listPeopleBySector, getPersonAwards, getPersonAliases
  - `awards.ts`: listAwards, getAwardBySlug, listAwardsByOrganization
  - `sources.ts`: listSources, listSourcesByName, listSourcesBySector
  - `index.ts`: barrel exports for all queries and types
- All queries type-safe with generated Supabase types and enum-typed sector params
- Added `npm run db:types` script for regenerating types after schema changes
- `tsc --noEmit` and `next build` both pass clean

### Session 4 — Phase 3: Frontend Foundation (2026-04-07)
- Root layout with nav (Architecture, Design, Technology, People, Awards) and footer
- Homepage: hero, live stats from Supabase (10 firms, 8 people, 4 awards), sector cards, explore links
- Sector pages: /architecture, /design, /technology — each lists firms + notable people
- /people listing page with PersonCard grid
- /awards listing page with award cards
- Reusable components: FirmCard, PersonCard
- Custom globals.css with CSS custom properties (light/dark)
- SEO metadata on all pages (title templates, descriptions)
- All pages server-rendered, verified against live Supabase seed data
- Removed default Next.js boilerplate SVGs
- `tsc --noEmit` and `next build` both pass clean (6 routes)

### Session 5 — Phase 4: Entity Detail Pages (2026-04-07)
- Firm detail: `/[sector]/firms/[slug]` — full page with description, location, website,
  key people, awards, aliases, Schema.org Organization JSON-LD, thin page noindex detection,
  merged entity 301 redirect, breadcrumbs
- Firm listing: `/[sector]/firms` — paginated with country filter via search params
- Person detail: `/people/[slug]` — bio, firm association (prominent), awards, aliases,
  Schema.org Person JSON-LD, breadcrumbs
- Award detail: `/awards/[slug]` — recipients with firm/person links, breadcrumbs
- `generateStaticParams` on all detail pages — 10 firm, 8 people, 4 award pages pre-rendered
- `generateMetadata` on all detail pages for dynamic SEO titles/descriptions
- Verified: JSON-LD renders, people show on firm pages, awards link correctly
- `tsc --noEmit` and `next build` both pass clean

### Session 6 — Phase 5: Awards & Sources (2026-04-07)
- Awards index and detail pages already shipped in Phases 3-4
- Created reusable `SourceList` component for embedding sources on entity pages
- `/sources` listing page showing all tracked publications
- Per playbook: source detail pages deferred as data is still sparse
- Grouping recipients by year deferred — current data has one recipient per award record
- `tsc --noEmit` and `next build` clean

---

## Session Plan

Each session should cover one phase or major milestone:

| Session | Focus | Context |
|---------|-------|---------|
| 1 | Phase 0: Environment setup | Foundation |
| 2 | Phase 1: Minimal schema + Phase 2: Types/data access | Schema |
| 3 | Phase 3-4: Frontend foundation + entity pages | Frontend |
| 4 | Phase 5: Awards pages | Frontend |
| 5 | Phase 6-7: Ingestion foundation + first sources | Pipeline |
| 6 | Phase 8-9: Review lane + light enrichment | Enrichment |
| 7 | Phase 10-11: Search + quality + deploy prep | Launch |

### When to start a new session
- Context shifts to a new subsystem
- Lots of pasted code/files
- Thread becomes messy or contradictory
- You want a cleaner implementation brief
