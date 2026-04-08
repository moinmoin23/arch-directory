-- ============================================================
-- Publish safety + freshness fields
-- ============================================================
-- Adds quality/publish controls to firms and people tables.
-- These fields enable:
--   1. Hiding thin/irrelevant records from public pages
--   2. Tracking data freshness and source count
--   3. Operator-driven publish decisions

-- ── Firms ───────────────────────────────────────────────────

-- publish_status: controls public visibility
--   'draft'     = not yet reviewed, hidden from public pages
--   'published' = approved for public display
--   'hidden'    = explicitly hidden by operator (irrelevant, junk, etc.)
alter table firms add column if not exists
  publish_status text not null default 'draft';

-- quality_score: 0-100, computed from data completeness
-- Firms need enough data to render a useful page.
alter table firms add column if not exists
  quality_score int not null default 0;

-- source_count: how many sources mention this entity
alter table firms add column if not exists
  source_count int not null default 0;

-- last_seen_at: when any source last referenced this entity
alter table firms add column if not exists
  last_seen_at timestamptz;

-- ── People ──────────────────────────────────────────────────

alter table people add column if not exists
  publish_status text not null default 'draft';

alter table people add column if not exists
  quality_score int not null default 0;

alter table people add column if not exists
  source_count int not null default 0;

alter table people add column if not exists
  last_seen_at timestamptz;

-- ── Indexes ─────────────────────────────────────────────────

create index if not exists idx_firms_publish_status on firms(publish_status);
create index if not exists idx_firms_quality_score on firms(quality_score);
create index if not exists idx_people_publish_status on people(publish_status);
create index if not exists idx_people_quality_score on people(quality_score);

-- ── Seed data: mark the 10 seed firms + 8 seed people as published ──

update firms set publish_status = 'published', quality_score = 80
  where id in (
    'a0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000005',
    'a0000000-0000-0000-0000-000000000006',
    'a0000000-0000-0000-0000-000000000007',
    'a0000000-0000-0000-0000-000000000008',
    'a0000000-0000-0000-0000-000000000009',
    'a0000000-0000-0000-0000-000000000010'
  );

update people set publish_status = 'published', quality_score = 70
  where id in (
    'b0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000003',
    'b0000000-0000-0000-0000-000000000004',
    'b0000000-0000-0000-0000-000000000005',
    'b0000000-0000-0000-0000-000000000006',
    'b0000000-0000-0000-0000-000000000007',
    'b0000000-0000-0000-0000-000000000008'
  );
