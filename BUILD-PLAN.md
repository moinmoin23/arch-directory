# Architecture, Design & Technology Directory — Build Plan

## Current Status

### Completed
- [x] **Phase 0** — Environment setup (2026-04-07)

### In Progress
- [ ] **Phase 1** — Minimal schema

### Upcoming
- [ ] Phase 2 — Generate types and data access layer
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
