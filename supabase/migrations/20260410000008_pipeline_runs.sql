-- ============================================================
-- Phase 5C: Pipeline run logging table
-- ============================================================

create table pipeline_runs (
  id          uuid primary key default gen_random_uuid(),
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  sources_run jsonb not null default '[]',
  total_entities int not null default 0,
  failures    int not null default 0,
  summary     jsonb,
  webhook_sent boolean not null default false
);

create index idx_pipeline_runs_started on pipeline_runs(started_at desc);
