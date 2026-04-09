-- ============================================================
-- Phase 2D: Tags and entity_tags tables
-- ============================================================

create table tags (
  id        uuid primary key default gen_random_uuid(),
  name      text not null,
  slug      text not null unique,
  category  text,
  created_at timestamptz not null default now()
);

create index idx_tags_slug on tags(slug);
create index idx_tags_category on tags(category) where category is not null;

create table entity_tags (
  id          uuid primary key default gen_random_uuid(),
  entity_id   uuid not null,
  entity_type entity_type not null,
  tag_id      uuid not null references tags(id) on delete cascade,
  source      text not null default 'llm',
  created_at  timestamptz not null default now(),
  unique (entity_id, entity_type, tag_id)
);

create index idx_entity_tags_entity on entity_tags(entity_id, entity_type);
create index idx_entity_tags_tag on entity_tags(tag_id);
