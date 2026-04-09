-- ============================================================
-- Phase 3B: Add country_code column for normalized country filtering
-- ============================================================

alter table firms add column country_code char(2);

create index idx_firms_country_code on firms(country_code) where country_code is not null;
