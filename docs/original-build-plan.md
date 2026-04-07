# Claude Code Build Plan — Architecture, Design & Technology Directory

*Complete local build sequence. Each section is a Claude Code session or task.*
*Prerequisites: VS Code, Claude Code, Docker Desktop, Node.js 20+, Python 3.11+*

---

## Phase 0 — Environment Setup (Day 1, ~1 hour)

Run these yourself before starting Claude Code sessions:

```bash
# 1. Install core tools
brew install supabase/tap/supabase   # Supabase CLI
brew install typesense/tap/typesense-server  # or use Docker

# 2. Create project directory
mkdir arch-directory && cd arch-directory
git init

# 3. Start Supabase local stack (first run downloads ~2-3GB of Docker images)
supabase init
supabase start
# Save the output — you'll need the API URL, anon key, and service role key

# 4. Start Typesense locally
docker run -d -p 8108:8108 \
  -v /tmp/typesense-data:/data \
  typesense/typesense:27.1 \
  --data-dir /data \
  --api-key=xyz --enable-cors

# 5. Create Next.js app
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir
cd web && npm install @supabase/supabase-js typesense instantsearch.js
cd ..

# 6. Create Python environment for scrapers
python -m venv scrapers/.venv
source scrapers/.venv/bin/activate
pip install crawlee[beautifulsoup] httpx feedparser anthropic supabase \
  instructor splink[duckdb] unidecode
```

---

## Phase 1 — Database Schema & Core Data Model (Day 1)

### Session 1.1 — Create the full database schema

**Prompt for Claude Code:**
```
I'm building a directory covering architecture, design, AND technology.
Create Supabase migration files for the complete schema.

The directory has these entity types:

- firms (architecture firms, design studios, tech labs/companies)
- people (architects, designers, researchers, technologists)
- projects (built works, designs, research projects, tech products)
- awards (Pritzker, WAF, Venice Biennale, RIBA, etc.)
- publications (articles from Dezeen, Designboom, MIT Tech Review, etc.)
- typologies (residential, cultural, commercial, computational, etc.)
- style_tags (brutalist, biophilic, timber-first, parametric, AI-driven, etc.)
- sources (press mentions, publications, academic papers)

Junction tables for many-to-many: firm_typologies, firm_styles,
project_typologies, award_recipients, entity_sources, firm_people.

Each firm needs: slug, canonical_name, display_name, country, city,
founded_year, size_range, website, description (LLM-generated),
climate_zone, urban_rural,
sector ENUM ('architecture','design','technology','multidisciplinary').

IMPORTANT — canonical_name vs display_name:
- display_name: the original name as found ("Zaha Hadid Architects")
- canonical_name: normalized form for matching — lowercase, stripped
  of legal suffixes (Inc, Ltd, GmbH, BV, AG, SARL, Pty Ltd),
  & → and, punctuation removed, transliterated to ASCII.
  This is what deduplication and matching runs against.

Each person needs: slug, name, canonical_name (normalized),
current_firm_id, role, title, education, nationality,
bio (LLM-generated), sector.

Entity resolution tables (critical for data quality):
- entity_aliases: entity_id, entity_type ('firm','person'),
  alias (text), alias_normalized (text). Stores all known name
  variants (e.g., "ZHA", "Zaha Hadid ZHA Studio" all point to
  the canonical Zaha Hadid Architects record).
  UNIQUE constraint on (entity_type, alias_normalized).
  GIN index on alias_normalized using pg_trgm for fuzzy lookups.
- entity_merges: survivor_id, merged_id, entity_type, merged_at,
  merge_reason (text). Audit trail for when duplicates are merged.
  The merged_id record gets a 'merged_into' field pointing to
  survivor_id (for URL redirects on old slugs).

Source provenance table:
- field_provenance: entity_id, entity_type, field_name (text),
  value (text), source_id (FK to sources), confidence (float 0-1),
  extracted_at (timestamptz), is_current (boolean).
  Tracks WHERE each data point came from and when. When sources
  conflict, highest confidence wins. Enables "show sources" on
  entity pages and data quality auditing.

Pipeline support tables:
- ingest_cursors: source_name (PK), last_cursor (text),
  last_run_at (timestamptz), entity_count (int), status (text),
  errors (jsonb). Tracks per-source progress for resumable runs.
- enrichment_queue: entity_id, entity_type, status
  ENUM ('pending','processing','done','failed'), attempts (int),
  last_error (text), created_at, enriched_at.

Enable required Postgres extensions:
- pg_trgm (trigram similarity for fuzzy name matching)
- fuzzystrmatch (levenshtein, metaphone, soundex)
- unaccent (accent-insensitive matching)
- pgvector (embedding-based semantic matching — used later for
  blocking/candidate generation in entity resolution)

Create the migration file at supabase/migrations/001_initial_schema.sql.
Include indexes for:
- country, city, typology, style_tag, and sector (SEO filter pages)
- GIN index on canonical_name using pg_trgm (fuzzy name matching)
- GIN index on entity_aliases.alias_normalized using pg_trgm
- HNSW index on name_embedding vector column (pgvector, 384 dims)
  for semantic similarity blocking

All writes must use upserts (ON CONFLICT DO UPDATE) so every
script is idempotent and safe to re-run.

Also create supabase/seed.sql with 15 sample entities across all
three sectors:
- 5 architecture firms (MVRDV, BIG, Zaha Hadid Architects, etc.)
- 5 design studios (Pentagram, IDEO, etc.)
- 5 tech/research entities (MIT Media Lab, ETH Zurich DFAB, etc.)
Include realistic data so I can test the frontend immediately.
```

**Then run:**
```bash
supabase db reset  # applies migrations + seed
```

### Session 1.2 — Generate TypeScript types from the schema

**Prompt:**
```
Generate TypeScript types from my Supabase schema. Create a file at
web/src/lib/database.types.ts that exports all table types. Also create
web/src/lib/supabase.ts with the Supabase client configured for local
development (http://localhost:54321).

Use environment variables NEXT_PUBLIC_SUPABASE_URL and
NEXT_PUBLIC_SUPABASE_ANON_KEY. Create the .env.local file with the
local Supabase credentials.
```

---

## Phase 2 — Next.js Frontend Foundation (Days 1-2)

### Session 2.1 — Layout, homepage, and navigation

**Prompt:**
```
Build the Next.js App Router layout for a directory called [YOUR_NAME]
covering architecture, design, and technology.

Create:
1. app/layout.tsx — minimal, clean layout with navigation. Top nav with
   links: Architecture, Design, Technology, People, Awards, Search.
   Use Tailwind. Keep it minimal and fast — think Brutalist web design
   meets modern directory. No heavy UI library.

2. app/page.tsx — homepage with:
   - Hero: "The global directory of architecture, design & technology"
   - Search bar (just the UI for now, we'll wire Typesense later)
   - Three sector cards: Architecture, Design, Technology — each
     showing count and linking to their section
   - Quick stats (X firms, Y projects, Z awards — hardcoded for now)
   - Featured filter links: "Sustainable firms", "Pritzker winners",
     "Firms in Netherlands", "Computational design labs", etc.

3. app/globals.css — clean typography, minimal color palette.
   Think: lots of whitespace, strong typography, fast-loading.

This is an SEO-first site. Every page must be server-rendered.
No client-side-only content for anything Google needs to see.
```

### Session 2.2 — Entity pages (firms)

**Prompt:**
```
Create the firm detail page at app/[sector]/firms/[slug]/page.tsx.

The [sector] param is one of: architecture, design, technology.

This page should:
1. Fetch firm data from Supabase by slug (server component)
2. If the slug belongs to a merged entity (merged_into is set),
   return a 301 redirect to the canonical entity's slug.
   This preserves SEO juice from old URLs.
3. Display: display_name, sector, location, founded year,
   description, typologies, style tags, notable projects, awards,
   key people (principals/founders), source links.
   Show "Also known as: ZHA, Zaha Hadid ZHA Studio" from aliases.
4. Include full Schema.org Organization markup in JSON-LD,
   including "alternateName" array from aliases
5. Generate dynamic metadata (title, description, canonical URL)
6. If entity has fewer than 3 data points (thin content),
   add <meta name="robots" content="noindex"> until enriched
7. Use ISR with revalidate = 86400 (daily)
8. Include generateStaticParams that pre-renders the seed data firms

Also create app/[sector]/firms/page.tsx — the firms listing page with:
- Grid/list of all firms for that sector
- Server-side pagination (12 per page)
- Basic filtering by country (from URL params)

Create a reusable FirmCard component at components/FirmCard.tsx.

Use the Supabase types from lib/database.types.ts. Fetch data using
the Supabase client in server components.
```

### Session 2.3 — Filter combination pages (SEO pages)

**Prompt:**
```
These filter combination pages are the core SEO strategy. Each URL
combination becomes a crawlable page targeting a specific search query.

Create dynamic routes:
1. app/[sector]/firms/[country]/page.tsx
   — "Architecture firms in [country]"
2. app/[sector]/firms/[country]/[typology]/page.tsx
   — "Sustainable architecture firms in Netherlands"
3. app/design/studios/page.tsx — all design studios
4. app/design/studios/[city]/page.tsx — studios by city
5. app/technology/labs/page.tsx — research labs and tech entities
6. app/technology/labs/[focus]/page.tsx — e.g., "computational design labs"
7. app/people/[role-filter]/page.tsx — architects, designers, researchers
8. app/people/[role-filter]/[award-filter]/page.tsx — "Pritzker winners"

Each page needs:
- Unique title and meta description generated from the filter params
- Schema.org ItemList markup
- Canonical URL
- Breadcrumb navigation
- ISR with revalidate = 3600 (hourly)
- generateStaticParams for the most common combinations

The trick: use Supabase queries that join through the junction tables.
For example, /architecture/firms/netherlands/sustainable joins firms →
firm_typologies → typologies WHERE country = 'Netherlands' AND
typology.slug = 'sustainable' AND sector = 'architecture'.

Also create app/sitemap.ts that generates a dynamic sitemap from the
database — list all firms, all filter combinations with data, all people.
```

### Session 2.4 — People, projects, awards pages

**Prompt:**
```
Create the remaining entity type pages following the same pattern as firms:

1. app/people/[slug]/page.tsx — Person detail (Schema.org Person markup)
   Show: name, role, current firm, education, bio, notable projects,
   awards, publications/press mentions. For principals/founders,
   show their firm association prominently.

2. app/projects/[slug]/page.tsx — Project detail (Schema.org CreativeWork)
   Works for built projects, design projects, and research/tech projects.

3. app/awards/page.tsx — Awards listing grouped by organization
   Include: Pritzker, WAF, Venice Biennale Golden Lion, RIBA Gold Medal,
   AIA Gold Medal, Design of the Year, Turing Award (for tech crossover)

4. app/awards/[slug]/page.tsx — Award detail showing all recipients by year

Each page: server component, ISR, full Schema.org, dynamic metadata,
generateStaticParams for seed data.

For projects, show the firm, location, year, typology, and link to the
source publication.
```

---

## Phase 3 — Search with Typesense (Day 2-3)

### Session 3.1 — Typesense indexing script

**Prompt:**
```
Create a script at scripts/index-typesense.ts that:

1. Connects to local Supabase and fetches all firms with their
   typologies and style tags (joined)
2. Creates a Typesense collection called "entities" with schema:
   - name (string, facet)
   - slug (string)
   - entity_type (string, facet) — firm, person, project
   - sector (string, facet) — architecture, design, technology
   - country (string, facet)
   - city (string, facet)
   - typologies (string[], facet)
   - style_tags (string[], facet)
   - description (string)
   - founded_year (int32, optional)
   - size_range (string, facet, optional)
3. Indexes all firms, people, and projects into Typesense
4. Can be run with: npx tsx scripts/index-typesense.ts

Use the typesense-js client library. Connect to localhost:8108
with api key "xyz" (my local instance).

The script must be idempotent — safe to re-run. Use upsert mode.
```

### Session 3.2 — Search UI with InstantSearch

**Prompt:**
```
Build the search interface using Typesense InstantSearch adapter.

Create app/search/page.tsx with:
1. A search box with instant results (search-as-you-type)
2. Faceted filters sidebar: Sector, Country, Typology, Style, City
3. Results grid showing entity cards (FirmCard, PersonCard, etc.)
4. Facet counts showing how many results per filter value
5. URL-based state (filters reflected in URL for shareability + SEO)

Use react-instantsearch and typesense-instantsearch-adapter packages.
The search page should work as a client component (search is interactive)
but the initial state should be server-rendered for SEO.

Also add the search box to the main layout/navigation so it's
available on every page.

Connect to local Typesense at http://localhost:8108 with search-only
API key. Create a .env.local entry for NEXT_PUBLIC_TYPESENSE_HOST
and NEXT_PUBLIC_TYPESENSE_SEARCH_KEY.
```

---

## Phase 4 — Scraping Pipeline (Days 3-5)

> **Architecture note: simple scripts, not an agent framework.**
>
> Each scraper is a standalone Python script. Reliability comes from:
> - **Idempotent upserts** — every write uses ON CONFLICT DO UPDATE,
>   so re-running is always safe
> - **Per-source cursors** — the `ingest_cursors` table tracks where
>   each scraper left off, enabling resumable runs
> - **`pipeline.py` orchestrator** — a thin wrapper that runs all
>   scrapers in sequence with try/except per source, so one failure
>   doesn't block the rest
> - **Enrichment queue** — `WHERE enriched_at IS NULL` means enrichment
>   always picks up where it left off
>
> This is simpler, more debuggable, and easier to extend than an
> agentic framework. Adding a new source = one new script +
> registering it in the pipeline's source list.

### Session 4.0 — Pipeline orchestrator, shared utilities, and entity resolution

**Prompt:**
```
Create the scraper infrastructure. This is the foundation that
every scraper builds on — get this right and everything downstream
is clean.

1. scrapers/shared/db.py — Supabase client configured from env vars.
   Include a helper function `upsert_entity(table, data, conflict_key)`
   that wraps upsert logic so every scraper writes the same way.

2. scrapers/shared/cursors.py — Functions to read/update the
   ingest_cursors table:
   - get_cursor(source_name) -> last_cursor value or None
   - update_cursor(source_name, cursor, count, status, errors=None)
   This is how scrapers resume from where they left off.

3. scrapers/shared/normalize.py — Name normalization pipeline.
   This is CRITICAL for entity resolution. Create a function
   `normalize_name(name: str) -> str` that applies these steps
   in order:
   a. Strip leading/trailing whitespace
   b. Lowercase
   c. Remove legal suffixes: Inc, Corp, LLC, Ltd, GmbH, AG, KG,
      SA, SARL, Pty Ltd, BV, NV, Co, Company, LLP, LP
   d. Normalize symbols: & → and, + → and
   e. Strip all punctuation except hyphens and spaces
   f. Transliterate non-ASCII to ASCII (use unidecode library)
   g. Collapse multiple spaces to single space
   h. Strip trailing/leading whitespace again

   Also create `generate_slug(name: str) -> str` that builds on
   normalize_name but replaces spaces with hyphens.

   And `generate_aliases(name: str) -> list[str]` that returns
   common variants: the full name, any obvious acronym (first
   letters of multi-word names), and the name without common
   words like "architects", "studio", "design", "lab", "group".

4. scrapers/shared/resolver.py — The entity resolution module.
   This is how we prevent "ZHA" and "Zaha Hadid Architects" from
   becoming separate records. Every scraper calls this BEFORE
   inserting. The function:

   `resolve_entity(name: str, entity_type: str, hints: dict = None)
    -> (entity_id | None, confidence: float, match_type: str)`

   The resolution cascade (try each step, stop on first match):
   a. Exact match: normalize_name(input) == canonical_name
      → confidence 1.0, match_type='exact'
   b. Alias match: normalize_name(input) found in entity_aliases
      → confidence 1.0, match_type='alias'
   c. Trigram similarity: pg_trgm similarity > 0.7 on canonical_name
      → confidence = similarity score, match_type='trigram'
   d. Trigram on aliases: pg_trgm similarity > 0.7 on alias_normalized
      → confidence = similarity score, match_type='trigram_alias'
   e. Hint-boosted match: if hints include country, city, or website
      domain, combine with trigram results above 0.5 and boost
      confidence when hints match
      → confidence = boosted score, match_type='hint_boosted'

   Decision logic:
   - confidence >= 0.85 → auto-match, return entity_id
   - confidence 0.6-0.85 → flag for LLM review (insert into a
     review_queue table: candidate_name, matched_entity_id,
     confidence, match_type, resolved boolean)
   - confidence < 0.6 → no match, create new entity

   When creating a new entity, also:
   - Generate and insert aliases via generate_aliases()
   - Store provenance (which source first mentioned this entity)

5. scrapers/shared/utils.py — Other shared helpers:
   - extract_entity_names(text, known_entities) -> list of matches
   - rate_limit_sleep(seconds) -> async-aware rate limiter

6. scrapers/pipeline.py — The orchestrator. A simple script that:
   - Takes optional --sources flag to run specific scrapers
     (default: all)
   - Runs each source scraper in sequence inside try/except
   - Logs success/failure per source with entity counts
   - Prints a summary table at the end
   - Usage: python scrapers/pipeline.py
            python scrapers/pipeline.py --sources rss,archdaily

All scrapers import from shared/ and follow the same pattern.
Connect to local Supabase using SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
from environment.
```

### Session 4.1 — RSS feed ingestion (all sectors)

**Prompt:**
```
Create scrapers/rss_ingest.py that:

1. Polls RSS feeds from these sources across all three sectors:

   Architecture:
   - ArchDaily: https://feeds.feedburner.com/Archdaily
   - Dezeen: https://www.dezeen.com/feed/

   Design:
   - Designboom: https://www.designboom.com/feed/
   - It's Nice That: https://www.itsnicethat.com/rss

   Technology:
   - MIT Technology Review: https://www.technologyreview.com/feed/
   - Wired (design/arch section): https://www.wired.com/feed/category/design/latest/rss

2. For each new entry:
   - Extract title, URL, published date, author
   - Classify sector based on source feed
   - Try to identify firm/studio/lab names mentioned (regex +
     known entity matching against our database)
   - Store in the sources/publications table via upsert
   - If a new entity name is detected, insert into the enrichment
     queue as a candidate for LLM processing

3. Use feedparser library. Use the ingest_cursors table to track
   last-seen entry per feed (via shared/cursors.py).

4. Idempotent — safe to run multiple times.

Connect to local Supabase using shared/db.py.
```

### Session 4.2 — OpenAlex academic data ingestion

**Prompt:**
```
Create scrapers/openalex_ingest.py that:

1. Queries the OpenAlex API for academic works related to:
   - Architecture (concept ID or topic filter)
   - Urban design, sustainable building, computational design
   - Design research, interaction design, material science
   - Architectural technology, smart buildings, digital fabrication
   Filter for recent works (last 5 years) with 10+ citations

2. For each work, extract:
   - Title, authors, institutions, year, citation count, DOI
   - Topics/concepts assigned by OpenAlex

3. For each author with institution affiliation:
   - Upsert a person record (type: researcher, appropriate sector)
   - Link to their institution (upsert as a firm with sector)
   - Store the publication as a source

4. Use the OpenAlex API at https://api.openalex.org
   Add mailto parameter for polite pool access
   Paginate through results (per_page=100, cursor-based)
   Rate limit: 1 request per second
   Use ingest_cursors to track pagination position

5. Target: ingest ~2,000 research entities in the first run.

This gives us the interdisciplinary research layer across
architecture, design, and technology.
```

### Session 4.3 — ArchDaily firm crawler

**Prompt:**
```
Create scrapers/archdaily_crawler.py using Crawlee (Python) with
BeautifulSoupCrawler.

The crawler should:

1. Start from ArchDaily's office/firm listing pages
   (https://www.archdaily.com/search/offices)
2. For each firm page, extract:
   - Firm name
   - Location (country, city)
   - Website URL
   - Project count
   - List of project names and URLs
   - Any awards mentioned
   - The firm's description/bio text
   - Principal/founder names if visible on the page

3. Upsert into Supabase firms table (sector='architecture')
4. For any principal names found, upsert into people table
   with firm association via firm_people junction table
5. Create slug from firm name (lowercase, hyphenated)
6. Handle pagination on the search results
7. Respect rate limiting — max 1 request per 2 seconds
8. Use ingest_cursors for resume capability

Use Crawlee's built-in request queue and session management.
Target: first 500 firms for initial build.

Important: check robots.txt first and respect it. Include a
reasonable User-Agent header.
```

### Session 4.4 — Designboom crawler

**Prompt:**
```
Create scrapers/designboom_crawler.py using httpx + BeautifulSoup.

Designboom covers both architecture and design, so this crawler
should extract entities from both sectors.

The crawler should:

1. Crawl Designboom's architecture section
   (https://www.designboom.com/architecture/)
   and design section (https://www.designboom.com/design/)

2. For each article/project page, extract:
   - Project/article title
   - Firm or studio name
   - Designer/architect names
   - Location
   - Category/section (architecture or design)
   - Published date
   - Brief description

3. Upsert firms with appropriate sector classification
4. Upsert people mentioned as designers/architects
5. Store article as a source linked to the entities
6. Handle pagination, rate limit 1 req per 2 seconds
7. Use ingest_cursors for resume capability

Target: 200 entities from each section (400 total).
Respect robots.txt.
```

### Session 4.5 — MIT Technology Review & tech source crawler

**Prompt:**
```
Create scrapers/tech_ingest.py that covers technology sources.

This is particularly important for the technology vertical of
the directory. The crawler should:

1. Crawl MIT Technology Review's relevant sections:
   - Look for articles about architecture technology,
     computational design, smart cities, digital fabrication,
     AI in design, sustainable tech, material innovation
   - Use their search/topic pages to find relevant content

2. For each article, extract:
   - Title, author, published date, URL
   - Companies/labs/institutions mentioned
   - People/researchers mentioned
   - Technology topics and keywords

3. For identified entities:
   - Upsert firms/labs with sector='technology' or
     'multidisciplinary'
   - Upsert people with appropriate roles (researcher,
     technologist, etc.)
   - Store articles as sources

4. Also query Google Scholar (via Scholarly library or
   SerpAPI if available) for:
   - Top-cited papers in "computational design"
   - Top-cited papers in "digital fabrication architecture"
   - Top-cited papers in "sustainable building technology"
   Extract author and institution data from results.

5. Rate limit: 1 request per 3 seconds for web scraping,
   respect robots.txt
6. Use ingest_cursors for resume capability

Target: 300 technology entities.
```

### Session 4.6 — Wikipedia awards & events data scraper

**Prompt:**
```
Create scrapers/awards_ingest.py that extracts structured award
and event data from Wikipedia.

Scrape these pages:

Architecture awards:
1. https://en.wikipedia.org/wiki/Pritzker_Architecture_Prize (laureates)
2. https://en.wikipedia.org/wiki/RIBA_Royal_Gold_Medal (recipients)
3. https://en.wikipedia.org/wiki/AIA_Gold_Medal (recipients)

Events and festivals:
4. https://en.wikipedia.org/wiki/List_of_World_Architecture_Festival_winners
   (WAF shortlists and winners)
5. Venice Biennale Architecture — scrape the page for Golden Lion
   winners, national pavilion winners, and participating architects/firms
   across recent editions
6. Venice Biennale Art — extract design-related participants

Design awards:
7. https://en.wikipedia.org/wiki/Design_Museum#Designs_of_the_Year
   (or the separate Designs of the Year page)

For each award/event:
- Award name, organization, year, category
- Winner firm name and/or person name
- Project name if applicable
- Prestige tier (1=lifetime/top prize, 2=category winner, 3=shortlist)

Match winners against existing entities using shared/resolver.py
(resolve_entity with country hints when available). This ensures
"Zaha Hadid", "ZHA", and "Zaha Hadid Architects" all resolve to
the same canonical record. Create new records only when confidence
is below 0.6.

Store in awards and award_recipients tables via upsert.

Use httpx + BeautifulSoup. Parse wiki tables for structured data.
```

### Session 4.7 — Firm website principal extraction

**Prompt:**
```
Create scrapers/principals_ingest.py that extracts founder and
principal data from firm websites.

This replaces LinkedIn scraping with a ToS-compliant approach:

1. Query Supabase for all firms that have a website URL but
   no associated people (principals/founders).

2. For each firm website:
   - Fetch the "About", "Team", "People", or "Leadership" page
     (try common URL patterns: /about, /team, /people, /studio,
     /office, /who-we-are)
   - Extract names and titles of principals, founders, partners,
     and directors
   - Look for education/background info if visible

3. Upsert extracted people into the people table with:
   - role = their title (Principal, Founder, Partner, Director)
   - Link to the firm via firm_people junction table
   - sector matching the firm's sector

4. Fallback: if the website doesn't have a clear team page,
   check if press/source articles mention the firm's principals
   (query the sources table for articles about this firm and
   extract names from those)

5. Rate limit: 1 request per 3 seconds (be polite to firm sites)
6. Use ingest_cursors, log failures gracefully

Target: extract principals for as many firms as possible.
This is important for the People section of the directory.
```

---

## Phase 5 — LLM Enrichment Pipeline (Days 5-7)

### Session 5.1 — Enrichment pipeline

**Prompt:**
```
Create scrapers/enrich.py — the LLM enrichment pipeline.

This script:

1. Fetches entities from the enrichment_queue where
   status = 'pending' OR (status = 'failed' AND attempts < 3)

2. For each entity, gathers all available text from Supabase:
   - Entity description from scraping
   - Source article titles/snippets mentioning this entity
   - Project names and descriptions
   - Award associations

3. Sends to Claude API using the **Instructor** library
   (pip install instructor) for structured extraction with
   Pydantic validation and automatic retries on parse failure.

   Define a Pydantic model for the enrichment response:

   class EntityEnrichment(BaseModel):
       primary_typology: Literal["residential", "cultural",
           "commercial", "institutional", "industrial",
           "urban_planning", "landscape", "interior", "mixed_use",
           "computational", "digital_fabrication", "material_science",
           "sustainability", "interaction_design", "graphic_design",
           "product_design"]
       secondary_typologies: list[str]
       style_tags: list[str]  # e.g., "brutalist", "timber-first",
           # "biophilic", "parametric", "AI-driven"
       climate_context: Literal["tropical", "arid", "temperate",
           "continental", "polar", "N/A"]
       urban_rural: Literal["urban", "suburban", "rural", "mixed", "N/A"]
       known_aliases: list[str]  # ALL known name variants,
           # abbreviations, and former names for this entity
       summary: str  # 150-word professional directory description,
           # third person, factual tone

   Use instructor.from_anthropic() to wrap the Anthropic client.
   The response is guaranteed to be valid — Instructor handles
   retries and validation automatically. No manual JSON parsing.

4. Parse the validated response and update the entity in Supabase:
   - Set description = summary
   - Insert typology and style_tag associations
   - Insert each known_alias into entity_aliases table
     (normalize each alias before storing)
   - Update enrichment_queue: status='done', enriched_at=now()

5. On failure: update enrichment_queue: status='failed',
   attempts += 1, last_error = error message

6. Use Claude claude-haiku-4-5-20251001 model by default
7. Process in batches with asyncio + Semaphore(5)
8. Automatically picks up where it left off (query by status)

Usage: python scrapers/enrich.py --model haiku --limit 100
       python scrapers/enrich.py --model sonnet --limit 50

Use ANTHROPIC_API_KEY from environment variable.
```

### Session 5.2 — LLM-assisted deduplication resolution

**Prompt:**
```
Create scrapers/resolve_duplicates.py — the second-pass dedup system
that handles the ambiguous matches the resolver couldn't auto-decide.

This script does two things:

PART 1 — Resolve the review queue:
1. Fetch all unresolved entries from review_queue (entities that
   the resolver flagged with confidence 0.6-0.85 during ingestion)
2. For each candidate pair, gather context from Supabase:
   - Both entities' names, aliases, locations, descriptions,
     linked sources, awards
3. Send to Claude via Instructor with this Pydantic model:

   class DedupeDecision(BaseModel):
       is_same_entity: bool
       confidence: float  # 0-1
       reasoning: str  # one sentence explaining why
       canonical_name: str | None  # if same, which name to keep
       aliases_to_add: list[str]  # name variants to preserve

4. If is_same_entity == True and confidence > 0.8:
   - Merge: update all references from merged_id to survivor_id
   - Add the merged entity's name to survivor's aliases
   - Insert into entity_merges for audit trail
   - Set merged entity's merged_into = survivor_id
   - Mark review_queue entry as resolved
5. If ambiguous (confidence < 0.8): skip, flag for manual review

PART 2 — Splink probabilistic dedup scan:
6. Run Splink (v4+, DuckDB backend) on the full firms table
   to find duplicate clusters the resolver might have missed:
   - Export firms with canonical_name, country, city, website
   - Configure Splink comparisons:
     * NameComparison on canonical_name (Jaro-Winkler levels)
     * ExactMatch on country
     * LevenshteinAtThresholds on city (threshold 2)
     * Columns to compare on website domain (extract domain from URL)
   - Block on first 3 chars of canonical_name + country
   - Run EM estimation (no training data needed)
   - Predict at match probability > 0.7
   - Cluster predictions
7. Insert any new candidate pairs into review_queue for
   LLM resolution (Part 1 above)

Usage:
  python scrapers/resolve_duplicates.py --resolve-queue
  python scrapers/resolve_duplicates.py --splink-scan
  python scrapers/resolve_duplicates.py --all

Run this AFTER enrichment (aliases from enrichment improve matching)
and periodically after adding new data sources.
```

### Session 5.3 — Batch enrichment for scale

**Prompt:**
```
Create scrapers/enrich_batch.py that uses the Anthropic Batch API
for 50% cost savings on large enrichment runs.

The Batch API works differently:
1. Create a batch of message requests (up to 10,000 per batch)
2. Submit the batch
3. Poll for completion (can take up to 24 hours)
4. Retrieve results

The script should:
1. Fetch all entities from enrichment_queue with status='pending'
2. Create a JSONL file with all the enrichment requests
3. Submit to the Anthropic Batch API
4. Save the batch ID for later retrieval
5. Have a separate "collect" command that checks batch status
   and processes results when ready

Usage:
  python scrapers/enrich_batch.py submit --model haiku --limit 1000
  python scrapers/enrich_batch.py status --batch-id <id>
  python scrapers/enrich_batch.py collect --batch-id <id>

This is for the big enrichment runs (1000+ entities).
Use the per-entity enrichment script for small batches and testing.
```

---

## Phase 6 — Polish & SEO (Days 7-9)

### Session 6.1 — Dynamic sitemaps

**Prompt:**
```
Enhance the sitemap generation at app/sitemap.ts.

Create multiple sitemap indexes by content type:
1. app/sitemap.ts — sitemap index pointing to sub-sitemaps
2. app/firms-sitemap.xml/route.ts — all firm pages (all sectors)
3. app/filter-sitemap.xml/route.ts — all filter combination pages
4. app/people-sitemap.xml/route.ts — all people pages
5. app/projects-sitemap.xml/route.ts — all project pages

Each sitemap entry needs:
- URL
- lastModified (from updated_at in database)
- changeFrequency (weekly for entities, daily for listings)
- priority (1.0 for homepage, 0.8 for entities, 0.6 for filters)

Query Supabase to generate these dynamically. For filter combinations,
only generate sitemaps for combinations that actually have data
(don't create empty pages).

Also create app/robots.ts with proper robots.txt that references
the sitemap index.
```

### Session 6.2 — Performance optimization

**Prompt:**
```
Optimize the Next.js app for Core Web Vitals:

1. Add next/image for any images with proper width/height/alt
2. Add loading="lazy" for below-fold content
3. Ensure all fonts are loaded with next/font (use Inter or similar)
4. Add proper caching headers for static assets
5. Review all pages for unnecessary client-side JavaScript —
   move everything possible to server components
6. Add a loading.tsx skeleton for each route group
7. Ensure no layout shift (add explicit dimensions to all elements)

Also create a simple performance test:
- Run `next build` and check the output for any pages marked as
  "lambda" that should be "static"
- All entity pages should show as ISR (static with revalidation)
- Filter pages should show as ISR

Review the build output and fix any pages that aren't being
statically generated as expected.
```

### Session 6.3 — Analytics and ad preparation

**Prompt:**
```
Add analytics and prepare for ad monetization:

1. Create app/components/Analytics.tsx — Google Analytics 4 setup
   (use next/script with afterInteractive strategy)
   Use NEXT_PUBLIC_GA_ID environment variable

2. Create a placeholder ad component at components/AdSlot.tsx
   that renders a div with data attributes for ad placement:
   - In-list ads (between every 6th entity in listings)
   - Sidebar ads on entity pages
   - Banner ad below navigation
   For now, just render placeholder divs with comments explaining
   where AdSense code will go

3. Add Open Graph and Twitter Card meta tags to all pages
   (use Next.js Metadata API)

4. Create a newsletter signup component (just the UI + a Supabase
   table to store emails). Simple form: email input + submit button.
   Store in a newsletter_subscribers table.
```

---

## Phase 7 — Integration Testing & Data Pipeline (Days 9-10)

### Session 7.1 — End-to-end pipeline test

**Prompt:**
```
Create a test script at scripts/test-pipeline.sh that runs the
entire data pipeline end-to-end:

1. Reset the database: supabase db reset
2. Run the full pipeline: python scrapers/pipeline.py
   (this runs all scrapers in sequence via the orchestrator)
3. Run LLM enrichment: python scrapers/enrich.py --model haiku --limit 20
4. Run dedup resolution: python scrapers/resolve_duplicates.py --all
5. Run data quality: npx tsx scripts/data-quality.ts
6. Index Typesense: npx tsx scripts/index-typesense.ts
7. Build Next.js: cd web && npm run build

Print a summary at the end:
- Total firms, people, projects, awards in database (by sector)
- Total enriched entities
- Entity resolution stats: auto-matched, LLM-resolved, merged,
  still pending review
- Total aliases in entity_aliases table
- Data quality score (from data-quality.ts output)
- Total Typesense documents
- Next.js build status and page count
- Any errors encountered per source

This validates the entire system works before deployment.
```

### Session 7.2 — Data quality checks

**Prompt:**
```
Create scripts/data-quality.ts that checks for common issues:

1. Firms without descriptions (un-enriched)
2. Firms without any typology tags
3. Duplicate detection using pg_trgm:
   - Run trigram similarity self-join on firms.canonical_name
     with threshold 0.5 to find likely duplicates
   - Cross-check against entity_aliases (some "dupes" may
     already be resolved aliases)
   - Report clusters of similar names with similarity scores
4. Orphaned records (people not linked to any firm)
5. Awards without matched recipients
6. Filter combinations that would generate empty pages
7. Slugs that conflict with Next.js route params
8. Entities with very short descriptions (<50 words)
9. Sector distribution — ensure all three sectors have content
10. People without firm associations
11. Unresolved review_queue entries (dedup candidates pending)
12. Entities without any aliases (enrichment may have missed them)
13. Source provenance gaps: entities where key fields have no
    source attribution in field_provenance
14. Thin content check: entity pages that would have fewer than
    3 data points displayed — flag as noindex candidates

Output a report showing counts for each issue category
and the top 10 worst offenders for each.

This helps identify data quality issues before going live.
```

---

## Phase 8 — Deployment Prep (Day 10)

### Session 8.1 — Environment configuration for production

**Prompt:**
```
Create the deployment configuration:

1. .env.production.local.example with all required env vars:
   - NEXT_PUBLIC_SUPABASE_URL
   - NEXT_PUBLIC_SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_ROLE_KEY
   - NEXT_PUBLIC_TYPESENSE_HOST
   - NEXT_PUBLIC_TYPESENSE_SEARCH_KEY
   - TYPESENSE_ADMIN_KEY
   - ANTHROPIC_API_KEY
   - NEXT_PUBLIC_GA_ID
   - NEXT_PUBLIC_SITE_URL

2. vercel.json with:
   - Build settings
   - Cron job for daily pipeline run (vercel.json crons)
   - Headers for caching static assets

3. A deployment checklist at DEPLOY.md with step-by-step:
   - Create Supabase cloud project
   - Run supabase db push to apply migrations
   - Create Typesense Cloud cluster
   - Run indexing script against cloud Typesense
   - Deploy to Vercel
   - Configure Cloudflare DNS
   - Submit sitemap to Google Search Console
   - Apply for AdSense

4. Update all Supabase/Typesense connection code to use env vars
   that work both locally and in production.
```

---

## Expanding Content Later

The pipeline is designed for easy expansion:

**To add a new source:**
1. Create `scrapers/new_source_ingest.py` following the same pattern
   (import shared/db.py, shared/cursors.py, use upserts)
2. Register it in `scrapers/pipeline.py`'s source list
3. Run `python scrapers/pipeline.py --sources new_source`
4. New entities automatically enter the enrichment queue
5. Run `python scrapers/enrich.py` to process them
6. Run `npx tsx scripts/index-typesense.ts` to update search

No schema changes, no frontend changes, no deployment needed.
The filter pages automatically show new content because they
query the database dynamically.

---

## Execution Notes

### Budget Management

Your $100 Anthropic subscription covers both Claude Code development
AND API calls for enrichment. To manage this:

- Claude Code sessions (development): ~$30-50 over the build
- LLM enrichment with Haiku (2-5K entities): ~$15-30
- Testing and iteration: ~$20-30

### Session Order Matters

Follow this order because each phase builds on the previous:
1. Schema first — everything depends on the data model
2. Frontend second — you need to see your data to validate it
3. Search third — depends on data being in the database
4. Scrapers fourth — now you're filling the database with real data
5. Enrichment fifth — transforms raw data into the valuable layer
6. Polish sixth — only optimize what's already working
7. Test seventh — validate the complete system
8. Deploy last — push what works

### When to Deviate

- If Claude Code generates something that doesn't work, debug it in
  the same session before moving to the next
- If the schema needs changes after you start building pages, create
  a new migration (never edit existing ones)
- If you hit API rate limits during enrichment, let it run overnight
  with a lower rate
