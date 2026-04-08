# TektonGraph — Strategic Architecture Review & Implementation Plan

## Context

TektonGraph is an architecture/design/technology directory with 2K published firms, 5.8K published people, 158 awards, 1.9K sources, and 12K aliases across 29 ingest cursors. Phases 0-14 of the playbook are complete. The MVP works end-to-end but has accumulated technical debt and architectural gaps that must be addressed before scaling to 50K+ entities.

A thorough audit of the codebase plus research into modern directory best practices surfaced **25+ concrete issues** across 5 areas: data integrity, query efficiency, schema completeness, search quality, and operational robustness. The user wants **solid, scalable, future-proof development** — not deployment, not quick fixes.

**The playbook's sequencing (§18) is still correct in spirit**: fix operations first, then expand the graph, then improve search, then scale SEO. But the specific implementation priorities need updating based on what the audit found. Below is the revised plan.

### Relationship to existing documentation

- **`docs/playbook.md`** — The master playbook. Part I (§4-§17, MVP phases 0-11) is fully executed. Part II (§18-§26) defines the long-term vision. This plan replaces the playbook as the **active execution plan** while keeping the playbook as the authoritative long-term reference.
- **`BUILD-PLAN.md`** — Stale progress tracker (shows Phase 6 "in progress"). To be deleted.
- **`docs/REVISED-PLAN.md`** — Source strategy revision. Fully executed. To be deleted.
- **`docs/original-build-plan.md`** — Pre-playbook plan. Fully superseded. To be deleted.
- **`docs/session-7-brief.md`** — Session handoff. Completed. To be deleted.

---

## Phase 1: Data Integrity & Pipeline Robustness

**Why first:** Everything downstream — new schema, better search, SEO — depends on trustworthy data. Silent data loss, race conditions, and orphaned records multiply as the corpus grows.

### 1A. Entity-to-source junction table
- **Problem:** `getFirmSources()` in `web/src/lib/queries/firms.ts:115-125` returns ALL sources (hardcoded limit 10). The comment on line 116 acknowledges this: `// For now, return all sources — later we'll add entity_sources junction`
- **Fix:** New migration creating `entity_sources` junction table (entity_id, entity_type, source_id, mention_type, confidence). Update all 7 scrapers to call `link_entity_source()` when matching entities to sources. New helper in `scrapers/shared/db.py`. Fix `getFirmSources()` to join through the junction.
- **Files:** New migration, `scrapers/shared/db.py`, `web/src/lib/queries/firms.ts`, all 7 scraper files

### 1B. Review queue deduplication
- **Problem:** `add_to_review_queue()` in `scrapers/shared/db.py:124-144` inserts blindly — same ambiguous match flagged repeatedly across ingest runs
- **Fix:** Add unique partial index on `(candidate_name, entity_type, suggested_entity_id) WHERE status = 'pending'`. Use upsert in `add_to_review_queue()`.
- **Files:** New migration, `scrapers/shared/db.py`

### 1C. Enrichment queue idempotency
- **Problem:** `add_to_enrichment_queue()` in `scrapers/shared/db.py:100-121` has TOCTOU race (check-then-insert without transaction). Also blocks re-enrichment of `done` entities even if data changed.
- **Fix:** Add unique partial index on `(entity_id, entity_type) WHERE status IN ('pending', 'processing')`. Use `INSERT ... ON CONFLICT DO NOTHING`.
- **Files:** New migration, `scrapers/shared/db.py`

### 1D. Atomic entity creation via RPC
- **Problem:** Entity creation in `scrapers/shared/resolver.py:150-166` is multi-step (upsert entity → generate aliases → enqueue enrichment) with no transaction. If alias insert fails, entity exists but can't be resolved by alias.
- **Fix:** Create a Postgres RPC function `upsert_entity_with_aliases` that wraps the entire sequence atomically. Python resolver calls `client.rpc(...)` instead of 3 separate calls.
- **Files:** New migration, `scrapers/shared/resolver.py`, `scrapers/shared/db.py`

### 1E. Rate limiting & retry with backoff
- **Problem:** Scrapers have ad-hoc or missing rate limiting. `rss_ingest.py` has none; `openalex_ingest.py` has hardcoded `sleep(1)` with no backoff on errors.
- **Fix:** Create `scrapers/shared/rate_limit.py` with a reusable retry decorator (max 3 attempts, exponential backoff on 429/503). Apply to all HTTP-calling scrapers.
- **Files:** New file `scrapers/shared/rate_limit.py`, all 7 scraper files

### Verification
- Run a scraper twice; review_queue should not double entries
- Kill a scraper mid-run; no orphaned entities without aliases
- Simulate a 429 response; scraper retries gracefully

---

## Phase 2: Schema Expansion & Query Layer Cleanup

**Why second:** Phase 1 made the pipeline trustworthy. Now fix how data is read (N+1 queries, dead code) and expand what can be stored (tags, projects, relationships). These changes are additive and safe — existing pages keep working.

### 2A. Fix N+1 count queries
- **Problem:** `getCountriesWithCounts()` (`firms.ts:158-180`), `countFirmsBySector()` (`firms.ts:182-204`), `getRolesWithCounts()`, `getPeopleLetterCounts()` all fetch ALL rows and count in JavaScript
- **Fix:** Create Postgres RPC functions (`count_firms_by_country`, `count_firms_by_sector`, `count_people_by_role`) using `GROUP BY`. Update TypeScript to call RPCs.
- **Files:** New migration, `web/src/lib/queries/firms.ts`, `web/src/lib/queries/people.ts`

### 2B. Remove duplicate query function
- **Problem:** `listFirmsByCountry()` (line 50) and `listFirmsByCountry2()` (line 127) are near-identical; only difference is default perPage and optional sector filter
- **Fix:** Keep `listFirmsByCountry2` (superset), rename to `listFirmsByCountry`, delete original. Update callers.
- **Files:** `web/src/lib/queries/firms.ts`, `web/src/lib/queries/index.ts`, caller pages

### 2C. Add error logging to queries
- **Problem:** All query functions silently return empty arrays on error (e.g., `firms.ts:46`), making failures invisible
- **Fix:** Add `console.error('[module.function]', error.message, error.details)` before returning fallback. Keep graceful fallback behavior.
- **Files:** All files in `web/src/lib/queries/`

### 2D. Tags table + enrichment storage
- **Problem:** `enrich.py` generates tags via LLM (lines 41-44, 57-60) but discards them — no table to store them
- **Fix:** New migration creating `tags` (name, slug, category) and `entity_tags` (entity_id, entity_type, tag_id, source). Update `enrich.py` to upsert tags after LLM call.
- **Files:** New migration, `scrapers/enrich.py`, `scrapers/shared/db.py`

### 2E. Temporal data for firm_people
- **Problem:** `firm_people.is_current` is boolean only — no date ranges for career history
- **Fix:** Add `start_year`, `end_year`, `source` columns. No scraper changes required (future enrichment can populate).
- **Files:** New migration

### 2F. Projects table
- **Problem:** Architecture directory with no project/portfolio data. Currently conflated with `award_recipients.project_name` (text field).
- **Fix:** New migration creating `projects` (slug, display_name, description, year, location, project_type, sector) and `project_entities` junction. No frontend pages yet — schema only.
- **Files:** New migration

### 2G. Entity relationships table
- **Problem:** No way to model "partner of", "acquired by", "spun out from", "mentored by". Only `merged_into` exists.
- **Fix:** New migration creating `entity_relationships` (from/to entity refs, relationship type, temporal data). Enables future enrichment and manual curation.
- **Files:** New migration

### 2H. Regenerate TypeScript types
- After all migrations: `npm run db:types` to regenerate `web/src/lib/database.types.ts`
- Verify: `npm run build` compiles without type errors

### Verification
- `/firms/country` page renders same counts (from RPC vs old JS counting)
- `npm run build` passes
- New tables visible in generated types

---

## Phase 3: Search & Enrichment Quality

**Why third:** Depends on Phase 2's tags table (for enrichment to store tags) and Phase 1's entity_sources (for context in enrichment prompts).

### 3A. Improve search RPC
- **Problem:** Trigram threshold 0.2 in `search_rpc.sql:59,89` returns noise. No rank differentiation between name match vs description match. No alias search.
- **Fix:** New migration replacing `search_directory()`:
  - Raise trigram threshold to 0.35
  - Weight name matches 2x: `similarity(canonical_name, normalized) * 2.0`
  - Join against `entity_aliases` for alias-based discovery
  - Include `entity_tags` content matching
- **Files:** New migration

### 3B. Country normalization
- **Problem:** Country filter is exact text match — "USA" vs "US" vs "United States" fails
- **Fix:** Add `country_code CHAR(2)` to firms. Create one-time script `scripts/normalize_countries.py` to populate ISO codes. Update search RPC to filter on `country_code`.
- **Files:** New migration, new script, search RPC update

### 3C. Enrichment improvements
- **Problem:** Tags generated but discarded (now stored via 2D). Prompts too generic (lines 66-100 of `enrich.py`). No context from existing sources. No few-shot examples.
- **Fix:**
  - Store tags in `entity_tags` after LLM call (depends on 2D)
  - Include entity's linked sources from `entity_sources` in prompt (depends on 1A)
  - Add 2-3 few-shot examples to FIRM_PROMPT and PERSON_PROMPT
  - Add rate limiting between API calls
- **Files:** `scrapers/enrich.py`

### 3D. Quality score threshold adjustment
- **Problem:** Publish threshold is 30/100 in `scripts/quality.py` — a firm with only country + city (35 points) gets published with no description, no website, no people
- **Fix:** Raise to 40. Add graduated scoring: thin description (<50 chars) gets 8 instead of 15 points. Run `--dry-run` first to measure impact.
- **Files:** `scripts/quality.py`

### Verification
- Search for "Zaha Hadid" returns the firm and related people, not noise
- Country filter works for both "US" and "United States"
- Enrichment stores tags visible in `entity_tags` table
- Published entity count drops by only thin/low-quality records

---

## Phase 4: Frontend Robustness & SEO

**Why fourth:** Data layer is now trustworthy, schema expanded, search accurate. Polish the presentation.

### 4A. Error boundaries
- Create `error.tsx` for root app, firm detail, person detail, and search routes
- Create/verify `not-found.tsx` at app root
- **Files:** 4-5 new `error.tsx` files in `web/src/app/`

### 4B. Fix duplicate data fetching
- **Problem:** `getFirmBySlug()` called twice in firm detail page (line 13 for metadata, line 55 for component). Supabase client creates new instance each time, so no de-duplication.
- **Fix:** Wrap `getFirmBySlug` with React `cache()`. Same for `getPersonBySlug` in `people/[slug]/page.tsx`.
- **Files:** `web/src/lib/queries/firms.ts`, `web/src/lib/queries/people.ts` (or the page files)

### 4C. Enhanced JSON-LD
- **Problem:** Firm and person JSON-LD missing `sameAs`, `knowsAbout`, `award`, `member`/`founder` references
- **Fix:** Expand structured data using already-fetched data (awards, people, tags from Phase 2D)
- **Files:** `web/src/app/[sector]/firms/[slug]/page.tsx`, `web/src/app/people/[slug]/page.tsx`

### 4D. BreadcrumbList schema + Open Graph tags
- **Problem:** Visual breadcrumbs exist but no JSON-LD markup. No OG tags for social sharing.
- **Fix:** Add BreadcrumbList JSON-LD to detail pages. Add `openGraph` to `generateMetadata` return.
- **Files:** Detail page files for firms, people, awards

### 4E. ISR caching
- **Problem:** Zero caching — every request hits Supabase. No ISR, no Cache-Control headers.
- **Fix:** Add `export const revalidate = 3600` to detail pages, `1800` to listings. (Verify Next.js 16 API first via `node_modules/next/dist/docs/`.)
- **Files:** `web/next.config.ts`, page files

### Verification
- Trigger a query error; see friendly error page, not Next.js crash screen
- Check OG tags render via social sharing preview tools
- Verify cache headers on responses

---

## Phase 5: Testing & Monitoring

**Why last:** Tests are most valuable after architecture stabilizes. Testing Phase 1-4 code means tests cover real production logic.

### 5A. Python pipeline tests
- Pure function tests for `normalize.py` (normalize_name, generate_slug, generate_aliases)
- Resolver tests with mocked Supabase client
- **Files:** New `scrapers/tests/` directory

### 5B. Frontend component tests
- Add vitest + @testing-library/react (verify Next.js 16 compatibility first)
- Test query functions with mocked responses
- Basic render tests for FirmCard, PersonCard
- **Files:** New test files in `web/src/`

### 5C. Pipeline run logging
- **Problem:** No historical tracking of pipeline runs. No alerting on failure.
- **Fix:** New `pipeline_runs` table (started_at, sources_run JSONB, total_entities, failures). Pipeline writes a summary row after each run. Add `--webhook-url` flag for Slack/Discord notifications.
- **Files:** New migration, `scrapers/pipeline.py`

### 5D. Expanded audit checks
- Entities without `entity_sources` links (depends on 1A)
- `enrichment_queue` items stuck in `processing` > 1 hour
- Firms with `merged_into` pointing to nonexistent target
- Fuzzy duplicate detection via trigram > 0.95 (beyond current exact-match-only check)
- **Files:** `scripts/audit.py`

### Verification
- `pytest scrapers/tests/` passes
- `npm test` in web/ passes
- Pipeline failure triggers webhook notification

---

## Dependency Graph

```
Phase 1 (Pipeline robustness)
    ├── 1A entity_sources ──────────┐
    ├── 1B review queue dedup       │
    ├── 1C enrichment idempotency   │
    ├── 1D atomic entity creation   │
    └── 1E rate limiting            │
                                    │
Phase 2 (Schema + queries)         │
    ├── 2A fix N+1 counts           │
    ├── 2B remove dup functions     │
    ├── 2C error logging            │
    ├── 2D tags table ──────────────┤── needed by 3C
    ├── 2E firm_people dates        │
    ├── 2F projects table           │
    ├── 2G relationships table      │
    └── 2H regenerate types         │
                                    │
Phase 3 (Search + enrichment) ◄────┘
    ├── 3A improved search RPC
    ├── 3B country normalization
    ├── 3C enrichment improvements (needs 1A + 2D)
    └── 3D quality threshold

Phase 4 (Frontend + SEO)
    ├── 4A error boundaries
    ├── 4B fix duplicate fetching
    ├── 4C enhanced JSON-LD (uses 2D tags)
    ├── 4D breadcrumbs + OG tags
    └── 4E ISR caching

Phase 5 (Testing + monitoring)
    ├── 5A Python tests
    ├── 5B Frontend tests
    ├── 5C pipeline run logging
    └── 5D expanded audit checks (uses 1A)
```

Within each phase, sub-tasks are largely independent and can be parallelized.

---

## Future Phases (from playbook Part II, not yet scheduled)

These are valid future work items from the playbook (§19-§26) and research that are **not covered by Phases 1-5 above** but should be done eventually. Listed in recommended order.

### Entity merge workflow (playbook §19)
- `entity_merges` table with audit trail (who merged, why, when)
- Merge commands in review CLI or admin UI
- Alias preservation when records merge
- Reversible merge logic (undo capability)
- Currently 228 draft firms likely contain duplicates among the 2,023 published
- **Prerequisite:** Phase 1 (data integrity) and Phase 2G (entity_relationships)

### Full SEO page matrix (playbook §23)
- City pages, country+typology pages, labs-by-focus pages
- Award-winner pages per year
- Tag-based landing pages (uses Phase 2D tags)
- Only generate pages for combinations with meaningful content density
- **Prerequisite:** Phase 4 (frontend/SEO foundations) and sufficient data density

### Typesense upgrade (playbook §16B)
- If Postgres search (improved in Phase 3A) proves insufficient for UX quality
- Typesense collection schema, indexing script, InstantSearch adapter
- Faceted search by sector, country, city, typology, award
- **Prerequisite:** Phase 3A validated and found wanting

### pgvector semantic search
- Embed entity descriptions using `text-embedding-3-small` (~$0.08 for 8K entities)
- `vector(1536)` column, cosine distance search
- Enables "firms that do sustainable adaptive reuse" style queries
- Also useful as a second entity resolution signal (embedding similarity > 0.92 = strong duplicate signal)
- **Prerequisite:** Phase 3 search improvements validated

### Source provenance and trust layer (playbook §25)
- Field-level source attribution for key entity fields
- Confidence tracking per field value
- Current vs historical values when sources conflict
- UI showing "sourced from 12 publications"
- **Prerequisite:** Phase 1A (entity_sources) and multiple disagreeing sources

### Operations, analytics, and monetization (playbook §26)
- Scheduled pipeline jobs with safe retry behavior (cron or CI-triggered)
- Job summaries and failure alerts (extends Phase 5C)
- Analytics setup (Google Analytics or Plausible)
- Newsletter signup component + `newsletter_subscribers` table
- Placeholder ad slots that don't degrade UX
- Sponsor/premium research tiers
- **Prerequisite:** Deployment (site must be live first)

### Deployment (playbook §17C)
- Vercel for frontend + Supabase Cloud for database
- Environment variable setup, build verification
- Sitemap submission, analytics verification, smoke-test URLs
- **Not scheduled yet** per user preference — focus on system improvement first

### Additional future capabilities (from research)
- **Profile claiming by firms** — firms update their own data. Requires auth system.
- **Image/media management** — logos, project photos, headshots. Add when project pages populated.
- **Conversational search / RAG chat** — Low engagement (<5%). Wait for 20K+ entities.
- **Neo4j / graph database** — Postgres handles 50K+. Revisit at 500K+.
- **Splink probabilistic dedupe** — Phase 1D + 3A cover current scale.
- **Relationship extraction from sources** — Use Claude structured output on 1.9K sources to extract person-firm, project, and collaboration relationships. High ROI once entity_sources (1A) and entity_relationships (2G) exist.

---

## Related documentation

| File | Role |
|------|------|
| `docs/playbook.md` | Long-term vision reference. Part I is historical (MVP build). Part II (§19-§26) is the full vision this plan's "Future Phases" references. |
| `README.md` | Project setup instructions. |
| `web/CLAUDE.md` + `web/AGENTS.md` | AI assistant instructions for frontend work. |

*Previously existing plan files (`BUILD-PLAN.md`, `docs/original-build-plan.md`, `docs/REVISED-PLAN.md`, `docs/session-7-brief.md`) were deleted as superseded by this plan.*

---

## Migration Naming Convention

Existing: `20260407000001` through `20260408000002` (5 migrations). New migrations use `20260409+` in phase order.

## Key Files Referenced

| File | Issues |
|------|--------|
| `scrapers/shared/db.py` | 1A, 1B, 1C, 1D, 2D |
| `scrapers/shared/resolver.py` | 1D |
| `scrapers/enrich.py` | 2D, 3C |
| `web/src/lib/queries/firms.ts` | 1A, 2A, 2B, 2C, 4B |
| `web/src/lib/queries/people.ts` | 2A, 2C |
| `supabase/migrations/20260408000001_search_rpc.sql` | 3A |
| `scripts/quality.py` | 3D |
| `scripts/audit.py` | 5D |
| `scrapers/pipeline.py` | 5C |
