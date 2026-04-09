-- ============================================================
-- Phase 2F: Projects and project_entities tables
-- ============================================================

create type project_type as enum (
  'building',
  'installation',
  'research',
  'product',
  'exhibition',
  'other'
);

create table projects (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  display_name  text not null,
  description   text,
  year          int,
  location      text,
  project_type  project_type not null default 'building',
  sector        sector_type,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index idx_projects_slug on projects(slug);
create index idx_projects_year on projects(year);
create index idx_projects_sector on projects(sector) where sector is not null;

create trigger projects_updated_at
  before update on projects
  for each row execute function update_updated_at();

create table project_entities (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references projects(id) on delete cascade,
  entity_id   uuid not null,
  entity_type entity_type not null,
  role        text,
  created_at  timestamptz not null default now(),
  unique (project_id, entity_id, entity_type)
);

create index idx_project_entities_project on project_entities(project_id);
create index idx_project_entities_entity on project_entities(entity_id, entity_type);
