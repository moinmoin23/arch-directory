# Architecture, Design & Technology Directory — Project Build Playbook

A practical build plan from **day-one setup** to the **full vision**.

This document is designed to be used with a coding assistant such as Claude Code or ChatGPT. Each phase includes:
- objective
- scope
- deliverables
- risks to avoid
- copy-paste prompts

---

## 1. Product goal

Build a high-quality, SEO-friendly directory covering:
- architecture firms
- design studios
- technology labs / research groups / relevant companies
- notable people
- projects
- awards
- publications and source references

The strategic idea is strong: structured entities, searchable profiles, source-backed enrichment, and expansion across architecture, design, and technology. The original plan also correctly emphasized SSR/SEO, idempotent ingestion, and a reusable pipeline architecture. fileciteturn7file0

The biggest correction in this playbook is sequencing: the original plan front-loaded advanced schema, SEO matrix pages, search, multiple scrapers, enrichment, and deduplication too early. Here, the project is re-ordered so the **core data loop** is proven first. fileciteturn7file0

---

## 2. Build principles

### Principle 1 — Prove the core loop first
Before building advanced SEO, vector search, or automated deduplication, prove this loop:

**ingest -> normalize -> store -> review -> publish -> search**

### Principle 2 — Data quality beats feature count
A smaller clean directory is better than a larger messy one.

### Principle 3 — Manual review before automated merges
Use manual review for ambiguous identity matches first. Automated merging comes later.

### Principle 4 — SEO pages should follow data density
Do not generate large numbers of combinatorial pages until content quality and coverage are strong.

### Principle 5 — Enrichment should improve records, not define identity
LLM enrichment can summarize and classify, but should not be the first system deciding entity identity.

---

## 3. Technical direction

### Recommended MVP stack
- **Frontend:** Next.js App Router + TypeScript + Tailwind
- **Database:** Supabase Postgres
- **Search:** Postgres search first, Typesense later if needed
- **Scrapers / ingestion:** Python 3.11+
- **LLM enrichment:** Anthropic API or equivalent
- **Deployment:** Vercel for site, Supabase Cloud for DB

### Defer until later
- pgvector
- Splink-based probabilistic dedupe
- field-level provenance everywhere
- automated LLM-assisted merge execution
- wide SEO filter matrix
- large-scale scheduled crawling

These capabilities appear in the original plan, but they should come after the data loop and review workflow are already working. fileciteturn7file0

---

# PART I — INITIAL MVP

## 4. MVP target

### MVP objective
Launch a lean, useful directory that:
- has clean entity pages
- supports basic browsing by sector
- ingests from 2–3 dependable sources
- includes light enrichment
- has a simple manual review lane
- can be deployed and indexed

### MVP success criteria
- 200–500 clean entities total
- 100–300 firms/labs/studios
- 50–150 people
- a small awards layer
- strong firm pages and people pages
- pages render correctly and index cleanly
- duplicate rate low enough for manual review

---

## 5. MVP phase order

1. Environment setup
2. Minimal schema
3. Seed data
4. Frontend foundation
5. Firm and people pages
6. One ingestion loop
7. Review queue / manual review
8. Light enrichment
9. Basic search
10. Quality checks
11. Deployment

This deliberately changes the original sequencing, which placed search and complex SEO earlier than the real data pipeline. fileciteturn7file0

---

## 6. Phase 0 — Environment setup

### Goal
Create a clean local workspace and confirm the stack runs end to end.

### Deliverables
- repo initialized
- Next.js app created
- Supabase local or cloud dev environment ready
- Python scraper environment ready
- environment variable files created

### Prompt
```text
Set up a new project for an SEO-first directory covering architecture, design, and technology.

Use this stack:
- Next.js App Router
- TypeScript
- Tailwind CSS
- Supabase Postgres
- Python 3.11 for ingestion scripts

Please do the following:
1. Create the project structure for:
   - web/
   - scrapers/
   - docs/
   - scripts/
   - supabase/
2. Initialize a Next.js app in web/ using TypeScript, Tailwind, ESLint, and App Router.
3. Create a Python virtual environment plan for scrapers and a requirements file.
4. Create .env.example files for both web and scrapers.
5. Add a README with setup instructions for local development.
6. Add npm and Python commands for common tasks.

Keep everything minimal, explicit, and easy to debug.
```

---

## 7. Phase 1 — Minimal schema

### Goal
Create only the tables needed to support the MVP.

### Keep in MVP
- firms
- people
- sources
- awards
- firm_people
- award_recipients
- ingest_cursors
- enrichment_queue
- review_queue
- optional entity_aliases

### Defer from original plan
- entity_merges until merge workflow is real
- field_provenance
- pgvector columns and indexes
- deeply polymorphic shared entity system

The original schema was ambitious and useful long term, but too heavy for first implementation. It also referenced a `review_queue` later in the workflow without establishing it in the initial schema section, so this playbook adds that early and explicitly. fileciteturn7file0

### Prompt
```text
Create the MVP Supabase schema for a structured directory covering architecture, design, and technology.

Create SQL migration files for these tables only:
- firms
- people
- sources
- awards
- firm_people
- award_recipients
- ingest_cursors
- enrichment_queue
- review_queue
- entity_aliases (lightweight version)

Schema goals:
1. firms should include:
   - id
   - slug
   - display_name
   - canonical_name
   - sector
   - country
   - city
   - website
   - founded_year
   - short_description
   - merged_into (nullable)
   - created_at / updated_at
2. people should include:
   - id
   - slug
   - display_name
   - canonical_name
   - role
   - sector
   - current_firm_id (nullable)
   - bio
   - created_at / updated_at
3. sources should store:
   - title
   - source_name
   - url
   - published_at
   - author
   - source_type
4. awards should support:
   - award_name
   - organization
   - category
   - year
   - prestige_tier
5. review_queue should support ambiguous identity matching:
   - candidate_name
   - entity_type
   - suggested_entity_id
   - confidence
   - match_type
   - status
   - notes
6. entity_aliases should support alternate names for firms and people.
7. Add practical indexes on slug, canonical_name, sector, country, city.
8. Keep migrations simple and easy to evolve.
9. Also create seed.sql with 25 realistic sample records across firms, people, awards, and sources.

Do not add pgvector, field-level provenance, or probabilistic dedupe tables yet.
```

---

## 8. Phase 2 — Generate types and data access layer

### Goal
Make database access type-safe and boring.

### Deliverables
- generated TypeScript types
- Supabase server and browser clients
- small query helper layer

### Prompt
```text
Generate TypeScript database types from the current Supabase schema and create a clean data access layer for the Next.js app.

Please create:
1. web/src/lib/database.types.ts
2. web/src/lib/supabase-server.ts
3. web/src/lib/supabase-browser.ts
4. web/src/lib/queries/
   - firms.ts
   - people.ts
   - awards.ts
   - sources.ts

Requirements:
- use environment variables
- support server components first
- keep query functions small and readable
- include helper functions for:
  - getFirmBySlug
  - listFirmsBySector
  - listFirmsByCountry
  - getPersonBySlug
  - listPeopleByRole
  - listAwards

Add a short README note explaining how the query layer is organized.
```

---

## 9. Phase 3 — Frontend foundation

### Goal
Create an SEO-first frontend with strong defaults.

### Deliverables
- root layout
- homepage
- navigation
- sector landing pages

### Prompt
```text
Build the frontend foundation for an SEO-first directory covering architecture, design, and technology.

Create:
1. app/layout.tsx
2. app/page.tsx
3. app/architecture/page.tsx
4. app/design/page.tsx
5. app/technology/page.tsx
6. app/globals.css

Requirements:
- use Next.js App Router
- server-render everything possible
- minimal visual style with strong typography and lots of whitespace
- homepage should include:
  - hero statement
  - short explanation of the directory
  - three sector cards
  - high-level stats
  - links into key sections
- add metadata defaults for SEO
- keep the design elegant and fast, not flashy

Do not build interactive client-heavy search yet.
```

---

## 10. Phase 4 — Firm and people pages

### Goal
Ship the core entity page templates.

### Deliverables
- firm detail page
- people detail page
- sector firm listings
- reusable cards
- metadata and structured data

The original plan placed a great deal of emphasis on rich firm pages and structured metadata; that should stay, but the broad filter-page matrix should wait. fileciteturn7file0

### Prompt A — firm pages
```text
Create the core firm pages for the directory.

Build:
1. app/[sector]/firms/page.tsx
2. app/[sector]/firms/[slug]/page.tsx
3. components/FirmCard.tsx

Requirements for firm detail page:
- fetch by slug using a server component
- if merged_into is set, redirect permanently to the canonical slug
- display:
  - display_name
  - sector
  - country / city
  - founded_year
  - website
  - short_description
  - key people
  - linked awards
  - linked sources
  - aliases if present
- include Schema.org Organization JSON-LD
- generate dynamic metadata
- detect thin pages and mark them as noindex when appropriate
- keep the layout minimal and readable

Requirements for listing pages:
- server-side pagination
- basic filter by country through search params
- strong headings and metadata for SEO
```

### Prompt B — people pages
```text
Create the people pages for the directory.

Build:
1. app/people/page.tsx
2. app/people/[slug]/page.tsx
3. components/PersonCard.tsx

Requirements:
- server-rendered pages
- show person name, role, sector, current firm, bio, awards, and related sources
- prominently show their relationship to a firm when available
- add Schema.org Person JSON-LD
- create metadata per person page
- support listing by role or sector through search params

Keep the implementation simple and SEO-friendly.
```

---

## 11. Phase 5 — Awards and source pages

### Goal
Add enough surrounding content to enrich firm and people records.

### Deliverables
- awards index
- award detail page
- optional source/publication page template

### Prompt
```text
Add supporting content pages for awards and sources.

Build:
1. app/awards/page.tsx
2. app/awards/[slug]/page.tsx
3. app/sources/[slug]/page.tsx (if source detail pages make sense with current data)

Requirements:
- server-rendered pages
- award pages should show recipients grouped by year when possible
- link awards back to firms and people
- use clean metadata and structured page copy
- avoid overbuilding if the data is still sparse

If source detail pages are too thin, create a reusable source section component for entity pages instead of a full route.
```

---

## 12. Phase 6 — Ingestion foundation

### Goal
Build a small, dependable ingestion architecture.

### Deliverables
- shared DB helpers
- cursor helpers
- normalization helpers
- basic resolver
- pipeline orchestrator

The original plan correctly recognized the importance of shared normalization, idempotent upserts, and resumable ingestion. Keep those ideas. But the more advanced match cascade and later auto-merge flow should be simplified for the MVP. fileciteturn7file0

### Prompt
```text
Create the ingestion foundation for the directory as a small Python pipeline.

Please create:
1. scrapers/shared/db.py
2. scrapers/shared/cursors.py
3. scrapers/shared/normalize.py
4. scrapers/shared/resolver.py
5. scrapers/pipeline.py

Requirements:
- db.py should expose a consistent client and helper functions for idempotent upserts
- cursors.py should read and update ingest_cursors
- normalize.py should include:
  - normalize_name(name)
  - generate_slug(name)
  - generate_aliases(name)
- resolver.py should use a conservative identity strategy:
  1. exact normalized match
  2. alias match
  3. simple trigram-style similarity threshold
  4. otherwise send ambiguous cases to review_queue
- pipeline.py should run selected scrapers or all scrapers in sequence
- keep logging explicit and human-readable
- prioritize reliability over cleverness

Do not implement automatic merges in the MVP resolver.
```

---

## 13. Phase 7 — First ingestion sources

### Goal
Start with sources that are structured and lower-maintenance.

### Recommended MVP sources
- RSS feeds
- OpenAlex

### Delay from the original plan
- ArchDaily firm crawler
- Designboom crawler
- firm website people extraction
- Wikipedia awards scraping
- broader tech site crawling

Those may be valuable later, but they increase fragility early. The original plan included all of them in the initial build sequence, which makes execution risk much higher. fileciteturn7file0

### Prompt A — RSS ingestion
```text
Create scrapers/rss_ingest.py for the MVP.

Scope:
- poll a curated set of RSS feeds across architecture, design, and technology
- extract title, url, author, published date, and source name
- classify content into sector based on source
- try to identify obvious firm or lab names from titles using database-backed matching
- store each item in sources via idempotent upsert
- add candidate entities to enrichment_queue only when the signal is reasonably strong
- use ingest_cursors for resuming safely

Requirements:
- keep the parser clean and easy to extend
- avoid brittle scraping logic
- add logging for counts and failures
```

### Prompt B — OpenAlex ingestion
```text
Create scrapers/openalex_ingest.py for the MVP research layer.

Scope:
- query OpenAlex for recent, relevant works in architecture, design research, computational design, digital fabrication, material systems, and related technology
- extract:
  - work title
  - authors
  - institutions
  - year
  - citation count
  - topics
  - doi or source URL when available
- upsert institutions as firms/labs where appropriate
- upsert authors as people where affiliation data is good enough
- store the publication as a source
- use ingest_cursors for pagination and resume behavior

Requirements:
- prioritize clean data over volume
- rate-limit politely
- make the first run modest in scope
- log unresolved identity cases to review_queue rather than forcing matches
```

---

## 14. Phase 8 — Manual review lane

### Goal
Create a lightweight operator workflow for ambiguous identity matches.

### Deliverables
- review queue scripts or admin page
- review commands to accept/reject candidates
- manual alias addition

This is one of the most important changes from the original plan. The original document moved toward LLM-assisted dedupe and merge execution relatively quickly. This playbook inserts a human review lane first. fileciteturn7file0

### Prompt
```text
Build a lightweight review workflow for ambiguous identity matches.

Create either:
- a minimal admin page in Next.js, or
- a CLI workflow in Python/TypeScript,
for reviewing entries in review_queue.

The review workflow should allow me to:
1. see candidate_name and suggested existing entity
2. inspect basic context:
   - aliases
   - country / city
   - recent sources
   - short descriptions
3. accept a match
4. reject a match
5. create a new entity
6. add an alias manually

Requirements:
- do not implement full automated merging yet
- optimize for speed and clarity
- make it easy to review 20–50 cases in one session
```

---

## 15. Phase 9 — Light enrichment

### Goal
Use LLMs to improve page quality, not to replace data judgment.

### Deliverables
- enrichment script
- structured validation
- summaries, tags, aliases

The original plan’s enrichment queue concept is good and should remain, but the MVP enrichment scope should be narrow and recoverable. fileciteturn7file0

### Prompt
```text
Create a lightweight LLM enrichment pipeline for the MVP.

Build scrapers/enrich.py with these responsibilities:
1. fetch entities from enrichment_queue with pending status
2. gather available context from sources and existing entity fields
3. send context to the model for structured enrichment
4. return only:
   - short professional summary
   - 1 primary category or typology
   - up to 5 tags
   - likely aliases
5. validate the response with a typed schema
6. update the relevant entity and mark enrichment status
7. retry failed cases up to a safe limit

Important constraints:
- enrichment must not automatically merge entities
- enrichment should improve presentation and discoverability
- keep prompts factual and concise
- design the script so it can resume where it left off
```

### Prompt for enrichment prompt design
```text
Write the internal model prompt for directory enrichment.

The prompt should instruct the model to:
- produce a factual third-person summary
- avoid hype and marketing language
- avoid making unsupported claims
- infer aliases only when strongly justified
- keep classifications broad enough to be reliable
- return structured output that can be validated

Also provide 3 example input/output pairs.
```

---

## 16. Phase 10 — Basic search

### Goal
Make the content navigable once real records exist.

### Recommendation
Start with Postgres search or trigram search. Add Typesense only if needed.

This changes the original plan, which introduced Typesense before the ingestion pipeline was fully proven. fileciteturn7file0

### Prompt A — database-backed search first
```text
Add a simple MVP search experience without introducing extra infrastructure yet.

Build:
1. app/search/page.tsx
2. a server-side search query layer for firms and people

Requirements:
- support searching by name, alias, country, city, and short description
- use Postgres full-text and/or trigram-based matching
- return grouped results by entity type
- support search params in the URL
- keep the page fast and readable
- server-render the first result set for SEO and usability

Do not build a heavy client-side search experience yet.
```

### Prompt B — Typesense upgrade, only after MVP data is healthy
```text
Upgrade the search stack to Typesense now that the dataset is stable.

Please create:
1. a Typesense indexing script
2. a search collection schema for firms, people, awards, and optionally projects
3. a search page with faceting by:
   - sector
   - country
   - city
   - category / typology
4. an indexing command that can be rerun safely

Requirements:
- keep the sync between database and search index straightforward
- only index fields that clearly improve retrieval
- document how to reindex after data changes
```

---

## 17. Phase 11 — Quality checks and launch prep

### Goal
Create enough operational discipline to launch confidently.

### Deliverables
- data quality script
- thin page detection
- build verification
- sitemap and robots

The original plan’s quality-checking ideas are useful, but they should come in before wide deployment and before complex SEO page generation. fileciteturn7file0

### Prompt A — data quality
```text
Create a data quality script for the MVP directory.

The script should check for:
1. firms without descriptions
2. people without firm associations
3. duplicate-like names above a similarity threshold
4. broken slugs or duplicate slugs
5. awards with missing recipient links
6. entities with very little displayable data
7. sectors with weak content coverage
8. unresolved review_queue items

Output:
- counts by issue type
- top offenders per issue
- a short summary score or readiness signal

Keep the script practical and easy to run locally.
```

### Prompt B — sitemap, robots, metadata cleanup
```text
Prepare the MVP site for indexing.

Please create or improve:
1. app/sitemap.ts
2. app/robots.ts
3. metadata generation across key routes

Requirements:
- include homepage, sector pages, firm pages, people pages, and award pages
- exclude thin or empty pages
- use canonical URLs consistently
- keep generation simple and reliable
```

### Prompt C — deployment prep
```text
Prepare the project for first deployment.

Please create:
1. DEPLOY.md
2. .env.production.example
3. a launch checklist

Checklist should include:
- database migration application
- environment variable setup
- build verification
- sitemap submission
- analytics verification
- smoke-test URLs

Keep the deployment process simple and repeatable.
```

---

# PART II — CONTINUED DEVELOPMENT TOWARD THE FULL VISION

## 18. After MVP: the expansion order

Once the MVP loop is working, expand in this order:

1. operator workflow and merge system
2. richer entity graph
3. broader ingestion sources
4. better search and recommendations
5. larger SEO matrix
6. advanced enrichment and dedupe
7. provenance and trust tooling
8. scaled operations and monetization

---

## 19. Stage 1 — Proper merge and review workflow

### Goal
Move from manual review only to a durable identity-management system.

### Deliverables
- entity_merges
- merge commands/UI
- audit trail
- reversible merge logic if possible

### Prompt
```text
Now that the MVP is stable, add a proper identity merge workflow.

Please implement:
1. entity_merges table
2. merge action support in the review workflow
3. alias preservation when records are merged
4. merged_into redirects for canonical entity pages
5. audit notes on why a merge happened

Requirements:
- do not lose source links or award links during merges
- make merges explicit and inspectable
- document edge cases and rollback approach
```

---

## 20. Stage 2 — Richer entity graph

### Goal
Add more depth to each record type.

### Add next
- projects
- publications
- typologies
- style tags
- more source relationships
- people-to-project links
- firm-to-project links

### Prompt
```text
Expand the directory from the MVP schema into a richer entity graph.

Add support for:
- projects
- publications
- typologies
- style tags
- people-to-project relationships
- firm-to-project relationships
- project-to-source relationships

Requirements:
- create migrations incrementally
- do not break existing pages
- add new pages only when enough data exists
- keep the graph understandable and queryable
```

---

## 21. Stage 3 — Additional ingestion sources

### Goal
Broaden coverage carefully.

### Add one at a time
- ArchDaily directory / office pages
- Designboom architecture + design coverage
- selected Wikipedia award tables
- firm website people extraction
- focused tech/innovation coverage

The original plan included all of these early, but they are better treated as controlled expansions after the MVP. fileciteturn7file0

### Prompt A — ArchDaily / office sources
```text
Add a new ingestion source for architecture firms from structured or semi-structured office pages.

Requirements:
- respect robots.txt and site terms
- extract only fields that are consistently available
- use the existing resolver before creating new records
- send uncertain matches to review_queue
- keep the source adapter isolated so it can fail without breaking the rest of the pipeline

Also document the parser assumptions and known failure modes.
```

### Prompt B — firm website people extraction
```text
Add a people extraction source from firm websites.

Requirements:
- only run for firms with websites and weak people coverage
- try common team/about/leadership pages
- extract names and titles conservatively
- do not invent people from weak signals
- send ambiguous results to review_queue
- rate-limit politely and log failures clearly
```

### Prompt C — awards ingestion expansion
```text
Expand the awards ingestion layer.

Requirements:
- ingest structured award recipients where tables are reliable
- connect awards to firms, people, and optionally projects
- preserve source URLs for traceability
- use the resolver with conservative thresholds
- avoid overfitting to messy source pages
```

---

## 22. Stage 4 — Better search, faceting, and recommendations

### Goal
Improve discovery once the dataset is broad enough.

### Deliverables
- richer search schema
- facets
- related entities
- curated landing pages

### Prompt
```text
Improve search and discovery now that the dataset is larger and cleaner.

Please implement:
1. faceted search by sector, country, city, category, award, and organization type
2. related entities on detail pages:
   - related firms
   - related people
   - related awards or sources
3. stronger ranking for exact names and aliases
4. documentation for search indexing and rebuilds

Keep ranking explainable and avoid black-box complexity where possible.
```

---

## 23. Stage 5 — Full SEO program

### Goal
Expand crawlable landing pages only when content density is there.

### Add after data density improves
- country pages
- country + typology pages
- city pages
- labs-by-focus pages
- award-winner pages
- role pages

The original plan treated these filter combinations as a major core tactic from the start. This playbook delays them until enough data exists to avoid thin pages. fileciteturn7file0

### Prompt
```text
Expand the SEO landing page system now that content coverage is strong.

Add dynamic routes for:
- firms by country
- firms by country + category
- design studios by city
- technology labs by research focus
- people by role
- award winners by award

Requirements:
- generate pages only for combinations with meaningful content
- noindex sparse pages
- generate clean metadata and breadcrumbs
- use sitemaps for only high-value routes
- avoid producing thin or duplicate pages
```

---

## 24. Stage 6 — Advanced enrichment and deduplication

### Goal
Scale data improvement more intelligently.

### Add here
- batch enrichment
- duplicate cluster scans
- LLM-assisted candidate review
- maybe embeddings for candidate generation

This is where the original plan’s more advanced dedupe and batch-enrichment ideas belong. They are scaling systems, not starting systems. fileciteturn7file0

### Prompt A — duplicate clustering
```text
Add an advanced duplicate discovery workflow for mature data.

Requirements:
- identify likely duplicate clusters using name, alias, location, and website signals
- propose candidate pairs or clusters for review
- keep auto-merge thresholds conservative
- preserve auditability
- do not execute destructive merges without an explicit review path
```

### Prompt B — batch enrichment
```text
Add a batch enrichment workflow for large pending queues.

Requirements:
- submit enrichment jobs in batches
- track batch status
- collect results safely
- reconcile failures cleanly
- make sure the batch workflow uses the same validation schema as single-item enrichment
```

### Prompt C — embeddings for candidate generation, only if justified
```text
Evaluate whether embeddings are now justified for candidate generation in identity resolution.

Please do the following:
1. assess current duplicate failure modes
2. decide whether trigram + aliases + metadata are no longer enough
3. if embeddings are justified, design a minimal candidate-generation workflow
4. keep final merge decisions explainable and reviewable

Do not add vector infrastructure unless it materially improves the review workload.
```

---

## 25. Stage 7 — Source provenance and trust layer

### Goal
Make records more inspectable and defensible.

### Add later
- field provenance
- confidence tracking
- source-backed field comparison
- visible “why this data exists” explanations

The original plan’s field provenance idea is useful, but most valuable once multiple sources are disagreeing regularly. fileciteturn7file0

### Prompt
```text
Add a provenance layer for mature records.

Please implement support for:
- field-level source attribution for key entity fields
- confidence tracking per field value
- current vs historical values when sources conflict
- UI support for showing source references on entity pages

Requirements:
- start with only a few important fields
- keep writes manageable
- design for auditing and trust, not for theoretical completeness
```

---

## 26. Stage 8 — Operations, analytics, and monetization

### Goal
Stabilize the system and prepare for growth.

### Deliverables
- scheduled jobs
- job monitoring
- analytics
- newsletter capture
- ad-ready placements
- sponsor or premium research options later

### Prompt
```text
Prepare the directory for sustained operation and monetization.

Please add:
1. scheduled pipeline jobs with safe retry behavior
2. job summaries and failure alerts
3. analytics setup
4. newsletter capture
5. placeholder ad slots that do not degrade UX
6. documentation for routine maintenance tasks

Requirements:
- keep the site performance-first
- avoid intrusive monetization patterns
- document operational runbooks clearly
```

---

# PART III — EXECUTION SUPPORT

## 27. Weekly build schedule (suggested)

### Week 1
- setup
- schema
- seed data
- type generation
- frontend foundation
- firm and people pages

### Week 2
- ingestion foundation
- RSS ingestion
- OpenAlex ingestion
- review workflow
- first quality checks

### Week 3
- light enrichment
- basic search
- sitemap and metadata cleanup
- deploy MVP

### Week 4+
- add richer entity graph
- add new ingestion sources one by one
- expand SEO pages carefully
- improve search and discovery
- build merge tooling and advanced dedupe

---

## 28. Decision rules during the build

### When to simplify
Simplify if any phase requires:
- too many migrations before real data exists
- complex matching rules before review workflow exists
- too many source-specific crawlers at once
- too many dynamic page types before data density is proven

### When to expand
Expand only when:
- the current phase is stable
- data quality is good enough to trust downstream pages
- the operator workflow can handle ambiguity
- a new system reduces real pain instead of adding theoretical elegance

---

## 29. Final guidance for using these prompts

Use these prompts one phase at a time.

For each phase:
1. run the prompt
2. inspect the generated code carefully
3. test before moving forward
4. create migrations incrementally
5. do not stack three unfinished systems at once

### Good working pattern
- one schema change
- one UI layer
- one ingestion source
- one quality pass
- then move on

That cadence gives you the best chance of actually shipping.

---

## 30. Short version of the roadmap

### MVP
- setup
- minimal schema
- seed data
- firm and people pages
- RSS + OpenAlex ingestion
- review queue
- light enrichment
- basic search
- quality checks
- deploy

### Full vision
- merge system
- richer entity graph
- broader sources
- stronger search
- larger SEO matrix
- advanced dedupe
- provenance
- scaled operations

---

## 31. Closing note

The original plan contains a strong long-term vision: a structured, multi-sector directory with ingestion, enrichment, search, and SEO leverage. That vision is worth keeping. The main adjustment is execution order: prove the clean data loop first, then scale the sophistication. fileciteturn7file0
