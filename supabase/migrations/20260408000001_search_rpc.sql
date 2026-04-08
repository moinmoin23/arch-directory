-- Search RPC: combined full-text + trigram search across firms and people.
-- Returns up to `result_limit` results per entity type, ordered by relevance.

create or replace function search_directory(
  query text,
  result_limit int default 12,
  sector_filter text default null,
  country_filter text default null
)
returns table(
  entity_type text,
  id uuid,
  slug text,
  display_name text,
  sector text,
  country text,
  city text,
  short_description text,
  role text,
  rank float
)
language plpgsql stable
as $$
declare
  normalized text;
  tsquery tsquery;
begin
  -- Normalize the query
  normalized := lower(trim(query));

  -- Build tsquery from plain text (handles multi-word naturally)
  tsquery := plainto_tsquery('english', normalized);

  -- Search firms
  return query
    select
      'firm'::text as entity_type,
      f.id,
      f.slug,
      f.display_name,
      f.sector::text,
      f.country,
      f.city,
      f.short_description,
      null::text as role,
      greatest(
        similarity(f.canonical_name, normalized),
        ts_rank_cd(
          to_tsvector('english', coalesce(f.display_name, '') || ' ' || coalesce(f.short_description, '')),
          tsquery
        )
      )::float as rank
    from firms f
    where f.publish_status = 'published'
      and f.merged_into is null
      and (sector_filter is null or f.sector::text = sector_filter)
      and (country_filter is null or f.country = country_filter)
      and (
        similarity(f.canonical_name, normalized) > 0.2
        or to_tsvector('english', coalesce(f.display_name, '') || ' ' || coalesce(f.short_description, ''))
           @@ tsquery
      )
    order by rank desc
    limit result_limit;

  -- Search people
  return query
    select
      'person'::text as entity_type,
      p.id,
      p.slug,
      p.display_name,
      p.sector::text,
      null::text as country,
      null::text as city,
      p.bio as short_description,
      p.role,
      greatest(
        similarity(p.canonical_name, normalized),
        ts_rank_cd(
          to_tsvector('english', coalesce(p.display_name, '') || ' ' || coalesce(p.bio, '')),
          tsquery
        )
      )::float as rank
    from people p
    where p.publish_status = 'published'
      and (sector_filter is null or p.sector::text = sector_filter)
      and (
        similarity(p.canonical_name, normalized) > 0.2
        or to_tsvector('english', coalesce(p.display_name, '') || ' ' || coalesce(p.bio, ''))
           @@ tsquery
      )
    order by rank desc
    limit result_limit;
end;
$$;
