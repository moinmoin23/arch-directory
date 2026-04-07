-- ============================================================
-- Phase 1: MVP Schema for Architecture, Design & Technology Directory
-- ============================================================

-- Required extensions
create extension if not exists pg_trgm;
create extension if not exists fuzzystrmatch;
create extension if not exists unaccent;

-- ============================================================
-- ENUM types
-- ============================================================

create type sector_type as enum (
  'architecture',
  'design',
  'technology',
  'multidisciplinary'
);

create type entity_type as enum (
  'firm',
  'person'
);

create type source_type as enum (
  'rss',
  'crawl',
  'api',
  'manual',
  'wikipedia'
);

create type queue_status as enum (
  'pending',
  'processing',
  'done',
  'failed'
);

create type review_status as enum (
  'pending',
  'accepted',
  'rejected',
  'skipped'
);

create type prestige_tier as enum (
  '1',  -- lifetime / top prize
  '2',  -- category winner
  '3'   -- shortlist / nominee
);

-- ============================================================
-- Core entity tables
-- ============================================================

create table firms (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  display_name  text not null,
  canonical_name text not null,
  sector        sector_type not null default 'architecture',
  country       text,
  city          text,
  website       text,
  founded_year  int,
  size_range    text,
  short_description text,
  merged_into   uuid references firms(id),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table people (
  id              uuid primary key default gen_random_uuid(),
  slug            text not null unique,
  display_name    text not null,
  canonical_name  text not null,
  role            text,
  title           text,
  sector          sector_type not null default 'architecture',
  current_firm_id uuid references firms(id),
  nationality     text,
  bio             text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table sources (
  id            uuid primary key default gen_random_uuid(),
  title         text not null,
  source_name   text not null,
  url           text unique,
  published_at  timestamptz,
  author        text,
  source_type   source_type not null default 'rss',
  sector        sector_type,
  created_at    timestamptz not null default now()
);

create table awards (
  id              uuid primary key default gen_random_uuid(),
  slug            text not null unique,
  award_name      text not null,
  organization    text,
  category        text,
  year            int,
  prestige        prestige_tier not null default '2',
  created_at      timestamptz not null default now()
);

-- ============================================================
-- Junction / relationship tables
-- ============================================================

create table firm_people (
  id        uuid primary key default gen_random_uuid(),
  firm_id   uuid not null references firms(id) on delete cascade,
  person_id uuid not null references people(id) on delete cascade,
  role      text,
  is_current boolean not null default true,
  unique (firm_id, person_id)
);

create table award_recipients (
  id          uuid primary key default gen_random_uuid(),
  award_id    uuid not null references awards(id) on delete cascade,
  firm_id     uuid references firms(id) on delete set null,
  person_id   uuid references people(id) on delete set null,
  project_name text,
  year        int,
  unique (award_id, firm_id, person_id, year)
);

-- ============================================================
-- Entity resolution
-- ============================================================

create table entity_aliases (
  id                uuid primary key default gen_random_uuid(),
  entity_id         uuid not null,
  entity_type       entity_type not null,
  alias             text not null,
  alias_normalized  text not null,
  created_at        timestamptz not null default now(),
  unique (entity_type, alias_normalized)
);

-- ============================================================
-- Pipeline support tables
-- ============================================================

create table ingest_cursors (
  source_name   text primary key,
  last_cursor   text,
  last_run_at   timestamptz,
  entity_count  int default 0,
  status        text,
  errors        jsonb
);

create table enrichment_queue (
  id            uuid primary key default gen_random_uuid(),
  entity_id     uuid not null,
  entity_type   entity_type not null,
  status        queue_status not null default 'pending',
  attempts      int not null default 0,
  last_error    text,
  created_at    timestamptz not null default now(),
  enriched_at   timestamptz
);

create table review_queue (
  id                  uuid primary key default gen_random_uuid(),
  candidate_name      text not null,
  entity_type         entity_type not null,
  suggested_entity_id uuid,
  confidence          float,
  match_type          text,
  status              review_status not null default 'pending',
  notes               text,
  created_at          timestamptz not null default now(),
  resolved_at         timestamptz
);

-- ============================================================
-- Indexes
-- ============================================================

-- Firms
create index idx_firms_slug on firms(slug);
create index idx_firms_canonical_name on firms using gin (canonical_name gin_trgm_ops);
create index idx_firms_sector on firms(sector);
create index idx_firms_country on firms(country);
create index idx_firms_city on firms(city);
create index idx_firms_merged_into on firms(merged_into) where merged_into is not null;

-- People
create index idx_people_slug on people(slug);
create index idx_people_canonical_name on people using gin (canonical_name gin_trgm_ops);
create index idx_people_sector on people(sector);
create index idx_people_current_firm on people(current_firm_id);

-- Sources
create index idx_sources_source_name on sources(source_name);
create index idx_sources_published_at on sources(published_at);

-- Awards
create index idx_awards_slug on awards(slug);
create index idx_awards_year on awards(year);
create index idx_awards_organization on awards(organization);

-- Entity aliases
create index idx_entity_aliases_entity on entity_aliases(entity_id, entity_type);
create index idx_entity_aliases_normalized on entity_aliases using gin (alias_normalized gin_trgm_ops);

-- Enrichment queue
create index idx_enrichment_queue_status on enrichment_queue(status);
create index idx_enrichment_queue_entity on enrichment_queue(entity_id, entity_type);

-- Review queue
create index idx_review_queue_status on review_queue(status);

-- ============================================================
-- Auto-update updated_at trigger
-- ============================================================

create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger firms_updated_at
  before update on firms
  for each row execute function update_updated_at();

create trigger people_updated_at
  before update on people
  for each row execute function update_updated_at();
