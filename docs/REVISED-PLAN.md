# Revised Plan — Source Strategy & Next Steps

*Updated based on research into architecture × technology data sources
and lessons learned from the MVP build.*

---

## Where we are (status as of 2026-04-08)

### Completed
- ✅ Phase 0: Environment setup
- ✅ Phase 1: Schema (+ publish_safety migration)
- ✅ Phase 2: TypeScript types and data access layer
- ✅ Phase 3: Frontend foundation
- ✅ Phase 4: Firm and people pages
- ✅ Phase 5: Awards and source pages
- ✅ Phase 6: Ingestion foundation (pipeline, resolver, normalizer, cursors)
- ✅ Phase 7: First ingestion sources (RSS + OpenAlex)
- ✅ Phase 8: Manual review lane (scripts/review.py)
- ✅ Phase 9: Light enrichment (descriptions for all published firms)
- ✅ Phase 10: CumInCAD ingestion (via OpenAlex venue-filtered queries)
- ✅ Phase 11: Archinect — **SKIPPED** (robots.txt blocks all AI/scraping bots, Cloudflare WAF)
- ✅ Phase 12: Niche vertical sources
  - ✅ FabLabs.io (1,858 active fab labs via public API)
  - ✅ GitHub computational design (255 people, 47 firms from topic repos + contributors)
  - ⏭️ Materiom — skipped (JavaScript SPA, no public API)
  - ⏭️ iGEM — skipped (JavaScript SPA, no public API)
- ✅ Phase 13: Basic search (Postgres full-text + trigram RPC, /search page)
- ✅ Bonus: Wikipedia awards (Pritzker, RIBA Gold Medal, AIA Gold Medal)
- ✅ Bonus: Venice Biennale Architecture data
- ✅ Bonus: Data quality audit, publish safety, operator dashboard
- ✅ Bonus: Modern directory UX (alphabet nav, filter chips, pagination, skeleton loading)

### Current corpus
| Entity | Total | Published | Draft | Hidden |
|--------|------:|----------:|------:|-------:|
| Firms | 2,266 | 2,023 | 228 | 15 |
| People | 5,808 | 5,803 | 5 | 0 |
| Awards | 158 | — | — | — |
| Sources | 1,889 | — | — | — |
| Aliases | 12,017 | — | — | — |
| Ingest cursors | 29 | — | — | — |

### Ingestion sources (29 cursors)
- RSS feeds (6): ArchDaily, Designboom, Dezeen, It's Nice That, MIT Tech Review, Wired
- OpenAlex (9): biophilic design, computational design, digital fabrication, etc.
- CumInCAD (7): eCAADe, ACADIA venues + 5 keyword searches
- FabLabs.io (1): full directory, 1,858 active labs
- GitHub (6): 6 topic searches + key repo contributors

### Key finding
OpenAlex was the right *starting* source for proving the pipeline, but it's
the wrong *primary* source for this directory's niche. It pulled in too many
generic academics and institutions. The 1,275 draft people are mostly
OpenAlex authors with no clear architecture/design connection.

---

## Revised source strategy

The directory's differentiation is the **intersection** of architecture,
design, and technology — specifically digital fabrication, biomaterials,
computational design, and experimental practice. The source strategy should
match this focus.

### Replace OpenAlex as the primary research source

**Before (playbook Phase 7):**
- RSS feeds ← keep
- OpenAlex ← demote to enrichment/citation layer

**After (revised):**
- RSS feeds ← keep as-is
- **CumInCAD** ← new primary research source
- **Archinect** ← new primary practice/industry source
- OpenAlex ← keep but use only for citation counts and institutional enrichment
- Semantic Scholar ← optional complement for citation analysis

### Why CumInCAD over OpenAlex

| | OpenAlex | CumInCAD |
|--|---------|----------|
| Scope | All academic fields | Computational architecture only |
| Noise | High (medical, physics, etc.) | Near zero |
| Volume | ~15K relevant of 250M total | ~14K papers, nearly all relevant |
| Authors | Generic academics | Digital fabrication researchers, parametric designers |
| Format | REST API, well-structured | BibTeX export, searchable |
| Coverage | Journals + conferences | ACADIA, eCAADe, CAADRIA, SIGraDi, Rob|Arch, Fabricate |

### Why Archinect as the practice source

| | ArchDaily | Archinect |
|--|----------|-----------|
| Focus | Mainstream architecture | Experimental + academic practices |
| Firm data | Office directory | Firm profiles with people links |
| Tech coverage | Low | High (computational, digital fabrication) |
| School/lab coverage | None | Research lab and school profiles |
| Relevant firms | ~200–500 | ~500–1,000 |

---

## Revised phase plan

### What the playbook says comes next

The playbook (Part II, §18) prescribes this post-MVP order:
1. Operator workflow and merge system
2. Richer entity graph
3. Broader ingestion sources
4. Better search and recommendations
5. Larger SEO matrix
6. Advanced enrichment and dedupe
7. Provenance and trust tooling
8. Scaled operations and monetization

### What we should actually do next

The playbook's sequencing is still right in spirit: **don't stack unfinished
systems.** But the specific source choices need updating. Here's the revised
order, keeping the playbook's one-thing-at-a-time discipline:

#### Phase 10 — Replace OpenAlex with CumInCAD ✅
Built `scrapers/cumincad_ingest.py` using OpenAlex venue-filtered queries
(eCAADe, ACADIA) + keyword searches. ~5,500 researchers ingested with
institutional affiliations.

#### Phase 11 — Archinect firm/people scraping ⏭️ SKIPPED
Archinect's robots.txt explicitly blocks all AI/scraping bots (`Disallow: /`
for ClaudeBot, Scrapy, etc.) and uses Cloudflare WAF. RSS feeds also return
403. Respecting site terms per playbook principles.

#### Phase 12 — Niche vertical sources ✅
1. **FabLabs.io API** ✅ — 1,858 active labs ingested (144 countries)
2. **Materiom** ⏭️ — JavaScript SPA, no public API discovered
3. **GitHub topic search** ✅ — 255 people, 47 firms from 6 topics + key repos
4. **iGEM teams** ⏭️ — JavaScript SPA, no public API discovered

#### Phase 13 — Search ✅
- Postgres RPC `search_directory()` with full-text + trigram matching
- `/search` page with sector and country filters
- Modern listing UX: alphabet nav, filter chips, numbered pagination,
  skeleton loading states, 36 results per page

#### Phase 14 — SEO expansion ← NEXT
Search is working and data density is proven (2,023 published firms,
5,803 published people). Ready for SEO landing page expansion.

---

## What to defer (unchanged from playbook)

These items from the playbook remain correctly deferred:
- ArchDaily crawler (mainstream, lower signal-to-noise for our niche)
- Designboom crawler (same reason)
- Firm website people extraction (fragile, better to use Archinect data)
- Splink probabilistic dedupe
- pgvector embeddings
- Field-level provenance
- Automated LLM merge execution
- Wide SEO filter matrix

---

## What was cleaned up (done)

1. ✅ **OpenAlex draft people** — All published via quality scoring pipeline;
   CumInCAD conference authors replaced the generic academics.
2. ✅ **Awards + Venice scrapers registered** in pipeline.py
3. ✅ **All work committed and pushed** — clean git history

---

## Decision: what happens to OpenAlex data

The 1,275 draft people from OpenAlex are:
- Generic academic authors (physicists, chemists, biologists)
- No firm affiliation, no role, no nationality in most cases
- Created as side effects of searching for "computational design" etc.
- The institution filter helped but still let through irrelevant entities

**Recommendation:** Keep the OpenAlex *sources* (1,064 publications are
useful references) and *institutions* (186 firms, most now enriched and
published). Delete the draft people — they'll be re-created with higher
quality when we ingest CumInCAD, which has the same researchers but with
conference-specific context.

---

## Summary of changes to the playbook

| Playbook item | Original | Revised |
|---------------|----------|---------|
| Phase 7B primary source | OpenAlex | **CumInCAD** |
| Phase 7 industry source | (none in MVP) | **Archinect** |
| Stage 3 "focused tech" | Vague | **FabLabs.io → Materiom → GitHub → iGEM** |
| Stage 3 ArchDaily crawler | Included | **Deferred** (low signal for our niche) |
| Stage 3 Designboom crawler | Included | **Deferred** (same reason) |
| Stage 3 firm website extraction | Included | **Deferred** (Archinect covers this better) |
| OpenAlex role | Primary research source | Enrichment/citation layer only |

The playbook's principles and sequencing remain correct. The only change
is which sources to prioritize for the directory's specific niche.
