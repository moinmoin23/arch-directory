-- ============================================================
-- Entity-to-source junction table
-- Links entities (firms, people) to the sources that mention them.
-- ============================================================

create table entity_sources (
  id          uuid primary key default gen_random_uuid(),
  entity_id   uuid not null,
  entity_type entity_type not null,
  source_id   uuid not null references sources(id) on delete cascade,
  mention_type text not null default 'mention',
    -- Values: 'subject', 'author', 'author_affiliation', 'repository_owner', 'mention'
  confidence  float not null default 1.0,
  created_at  timestamptz not null default now(),
  unique (entity_id, entity_type, source_id)
);

create index idx_entity_sources_entity on entity_sources(entity_id, entity_type);
create index idx_entity_sources_source on entity_sources(source_id);
