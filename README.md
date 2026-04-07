# Architecture, Design & Technology Directory

A structured, SEO-first directory covering architecture firms, design studios, technology labs, notable people, projects, and awards.

## Stack

- **Frontend:** Next.js App Router + TypeScript + Tailwind CSS
- **Database:** Supabase (Postgres)
- **Search:** Postgres full-text (MVP), Typesense (later)
- **Scrapers:** Python 3.11+
- **LLM Enrichment:** Anthropic Claude API
- **Deployment:** Vercel + Supabase Cloud

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker Desktop (for Supabase local)
- Supabase CLI: `brew install supabase/tap/supabase`

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/moinmoin23/arch-directory.git
cd arch-directory

# 2. Start Supabase local stack
supabase start
# Save the output credentials

# 3. Set up web environment
cp web/.env.example web/.env.local
# Edit web/.env.local with your Supabase credentials from step 2

# 4. Install web dependencies and run
cd web
npm install
npm run dev
# Open http://localhost:3000

# 5. Set up Python scrapers
cd ../scrapers
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase service role key
```

### Common Commands

```bash
# Web
cd web && npm run dev          # Start dev server
cd web && npm run build        # Production build
cd web && npm run lint         # Lint

# Scrapers
cd scrapers && source .venv/bin/activate
python pipeline.py             # Run all scrapers
python enrich.py               # Run enrichment

# Database
supabase db reset              # Reset and re-seed
supabase migration new <name>  # Create new migration
```

## Project Structure

```
arch-directory/
├── web/                  # Next.js frontend
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # Reusable components
│       └── lib/          # Database types, clients, queries
├── scrapers/             # Python ingestion pipeline
│   ├── shared/           # DB, cursors, normalization, resolver
│   ├── pipeline.py       # Orchestrator
│   └── *.py              # Individual source scrapers
├── scripts/              # Utility scripts (indexing, quality checks)
├── supabase/             # Migrations and seed data
│   ├── migrations/
│   └── seed.sql
├── docs/                 # Additional documentation
├── BUILD-PLAN.md         # Build progress tracker
└── README.md
```

## Build Plan

See [BUILD-PLAN.md](BUILD-PLAN.md) for the phased development plan and session log.
