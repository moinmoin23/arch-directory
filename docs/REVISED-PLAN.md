# Revised Plan — Source Strategy & Next Steps

*Updated based on research into architecture × technology data sources
and lessons learned from the MVP build.*

---

## Where we are (status as of session end)

### Completed (Playbook Phases 0–9 equivalent)
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
- ✅ Bonus: Wikipedia awards (Pritzker, RIBA Gold Medal, AIA Gold Medal)
- ✅ Bonus: Venice Biennale Architecture data
- ✅ Bonus: Data quality audit, publish safety, operator dashboard

### Current corpus
| Entity | Total | Published | Draft | Hidden |
|--------|------:|----------:|------:|-------:|
| Firms | 272 | 255 | 4 | 13 |
| People | 1,408 | 133 | 1,275 | 0 |
| Awards | 158 | — | — | — |
| Sources | 1,064 | — | — | — |

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

#### Phase 10 — Replace OpenAlex with CumInCAD (next session)
**Matches: Playbook Phase 7B replacement**

Build `scrapers/cumincad_ingest.py`:
- Scrape/export CumInCAD's BibTeX database (~14K papers)
- Extract authors, institutions, keywords, conference venues
- Use the existing resolver to link authors to institutions
- Use conference keywords to classify sector (digital fabrication,
  parametric design, biomaterials, etc.)
- This replaces the bulk of OpenAlex's role and produces far cleaner data

Expected impact:
- ~5,000–8,000 relevant researchers (replacing 1,275 generic OpenAlex authors)
- ~500+ institutions/labs (pre-filtered to computational architecture)
- Every person has a conference publication link (quality signal)

#### Phase 11 — Archinect firm/people scraping
**Matches: Playbook Stage 3, Prompt A (adapted)**

Build `scrapers/archinect_ingest.py`:
- Scrape Archinect's firm directory (filtered to technology/digital tags)
- Extract firm profiles, people, project mentions
- Link people to firms via firm_people
- This is the practice/industry complement to CumInCAD's academic data

Expected impact:
- ~300–500 firms with descriptions, websites, locations
- ~500–1,000 people with firm affiliations and roles
- Strong overlap with CumInCAD researchers (strengthens existing records)

#### Phase 12 — Niche vertical sources
**Matches: Playbook Stage 3, "focused tech/innovation coverage"**

Add one at a time, in this order:

1. **FabLabs.io API** — global fab lab directory, free API, ~2,500 labs
   Quick win, maps digital fabrication infrastructure.

2. **Materiom** — open biomaterials database, ~100–200 materials
   Covers the biotech-for-architecture vertical specifically.

3. **GitHub topic search** — computational design tool repos
   (COMPAS, Ladybug, etc.) + contributor graphs
   Discovers tool builders and active computational designers.

4. **iGEM teams** — synthetic biology projects relevant to architecture
   Covers bio-digital design crossover.

#### Phase 13 — Search (Playbook Phase 10)
Only after CumInCAD + Archinect data is in and quality-checked.

#### Phase 14 — SEO expansion (Playbook Stage 5)
Only after search is working and data density is proven.

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

## What to clean up before continuing

Before starting Phase 10 (CumInCAD):

1. **Reset the OpenAlex data** — The 1,275 draft people are noise.
   Options:
   a. Delete all OpenAlex-sourced people who are still in draft status
   b. Or keep them but flag as `source=openalex` for later filtering
   Recommendation: option (a) — they add no value to the directory

2. **Register awards + venice scrapers in pipeline.py** — Currently
   standalone scripts, should be part of the pipeline

3. **Commit current state** — Everything since Phase 6 is uncommitted

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
