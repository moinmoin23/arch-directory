-- ============================================================
-- Phase 2E: Add temporal data and source to firm_people
-- ============================================================

alter table firm_people
  add column start_year int,
  add column end_year int,
  add column source text;
