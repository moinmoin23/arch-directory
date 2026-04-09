-- ============================================================
-- Phase 2A: Replace N+1 count queries with Postgres RPCs
-- ============================================================

-- Count published firms grouped by country
create or replace function count_firms_by_country()
returns table(country text, count bigint)
language sql stable
as $$
  select f.country, count(*) as count
  from firms f
  where f.publish_status = 'published'
    and f.merged_into is null
    and f.country is not null
  group by f.country
  order by count desc;
$$;

-- Count published firms grouped by sector
create or replace function count_firms_by_sector()
returns table(sector sector_type, count bigint)
language sql stable
as $$
  select f.sector, count(*) as count
  from firms f
  where f.publish_status = 'published'
    and f.merged_into is null
  group by f.sector
  order by f.sector;
$$;

-- Count published people grouped by role
create or replace function count_people_by_role()
returns table(role text, count bigint)
language sql stable
as $$
  select p.role, count(*) as count
  from people p
  where p.publish_status = 'published'
    and p.role is not null
  group by p.role
  order by count desc;
$$;

-- Distinct first letters of published people's names
create or replace function get_people_letters()
returns table(letter text)
language sql stable
as $$
  select distinct upper(left(p.display_name, 1)) as letter
  from people p
  where p.publish_status = 'published'
    and left(p.display_name, 1) ~ '[A-Za-z]'
  order by letter;
$$;

-- Count awards grouped by organization
create or replace function count_awards_by_organization()
returns table(organization text, count bigint)
language sql stable
as $$
  select a.organization, count(*) as count
  from awards a
  where a.organization is not null
  group by a.organization
  order by count desc;
$$;
