-- ============================================================
-- Phase 2G: Entity relationships table
-- ============================================================

create type relationship_type as enum (
  'subsidiary',
  'partner',
  'successor',
  'spin_off',
  'acquired_by',
  'collaboration',
  'other'
);

create table entity_relationships (
  id                uuid primary key default gen_random_uuid(),
  from_entity_id    uuid not null,
  from_entity_type  entity_type not null,
  to_entity_id      uuid not null,
  to_entity_type    entity_type not null,
  relationship      relationship_type not null,
  start_year        int,
  end_year          int,
  notes             text,
  created_at        timestamptz not null default now(),
  unique (from_entity_id, from_entity_type, to_entity_id, to_entity_type, relationship)
);

create index idx_entity_rel_from on entity_relationships(from_entity_id, from_entity_type);
create index idx_entity_rel_to on entity_relationships(to_entity_id, to_entity_type);
