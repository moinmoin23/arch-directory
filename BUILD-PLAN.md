# Architecture, Design & Technology Directory — Build Plan

## Current Status

### Completed
- [x] **Phase 0** — Environment setup (2026-04-07)
- [x] **Phase 1** — Minimal schema (2026-04-07)

### Completed
- [x] **Phase 2** — Generate types and data access layer (2026-04-07)

### In Progress
- [ ] **Phase 3** — Frontend foundation

### Upcoming
- [ ] Phase 3 — Frontend foundation
- [ ] Phase 4 — Firm and people pages
- [ ] Phase 5 — Awards and source pages
- [ ] Phase 6 — Ingestion foundation
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
