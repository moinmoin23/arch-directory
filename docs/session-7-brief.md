# Session 7 Brief — Phase 6: Ingestion Foundation

## Context
Building an architecture/design/technology directory. Phases 0-5 are complete:
- Supabase Postgres with 10 tables (firms, people, sources, awards, etc.)
- Next.js frontend with detail pages, JSON-LD, static generation
- Seed data: 10 firms, 8 people, 4 awards, 3 sources, 6 aliases
- Repo: https://github.com/moinmoin23/arch-directory

## This Session: Phase 6
Build the Python ingestion foundation in `scrapers/`.

### Files to create
1. `scrapers/shared/db.py` — Supabase client + idempotent upsert helpers
2. `scrapers/shared/cursors.py` — Read/update ingest_cursors table
3. `scrapers/shared/normalize.py` — normalize_name, generate_slug, generate_aliases
4. `scrapers/shared/resolver.py` — Conservative entity resolution (exact → alias → trigram → review_queue)
5. `scrapers/pipeline.py` — Orchestrator that runs scrapers in sequence

### Key requirements
- Use `supabase-py` client, configured from env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- All writes must use upserts (idempotent, safe to re-run)
- Cursors enable resumable runs per source
- Resolver must NOT auto-merge — ambiguous cases go to review_queue
- Resolution cascade: exact normalized → alias → trigram similarity > 0.7 → review_queue
- Pipeline: `python scrapers/pipeline.py` or `python scrapers/pipeline.py --sources rss`
- Logging: explicit, human-readable
- Python deps already installed in `scrapers/.venv/`

### Database tables used
- `firms` (canonical_name, slug, sector, etc.)
- `people` (canonical_name, slug, sector, etc.)
- `entity_aliases` (entity_id, entity_type, alias, alias_normalized)
- `ingest_cursors` (source_name PK, last_cursor, last_run_at, entity_count, status, errors)
- `enrichment_queue` (entity_id, entity_type, status, attempts)
- `review_queue` (candidate_name, entity_type, suggested_entity_id, confidence, match_type, status)
- `sources` (title, source_name, url, published_at, author, source_type, sector)

### Env vars (in scrapers/.env)
```
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=<from supabase status output>
```

### Extensions available in Postgres
- pg_trgm (GIN indexes on canonical_name and alias_normalized)
- fuzzystrmatch (levenshtein, soundex)
- unaccent

### Follow the playbook
See `docs/playbook.md` Phase 6 (line 436) for the full prompt.
See `BUILD-PLAN.md` for progress tracker.

### After this session
Phase 7 adds the first two real scrapers: RSS feeds + OpenAlex.
