-- ============================================================
-- Phase 3A: Improved search RPC
--   - Raise trigram threshold from 0.2 to 0.35
--   - Weight name matches 2x over description matches
--   - Search entity_aliases for alias-based discovery
--   - Search entity_tags for content matching
--   - Support country_code filtering alongside country text
-- ============================================================

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
  tsq tsquery;
begin
  normalized := lower(trim(query));
  tsq := plainto_tsquery('english', normalized);

  -- Search firms: name (2x weight), aliases, tags, description
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
        similarity(f.canonical_name, normalized) * 2.0,
        coalesce(alias_sim.max_sim * 1.5, 0),
        ts_rank_cd(
          to_tsvector('english', coalesce(f.display_name, '') || ' ' || coalesce(f.short_description, '')),
          tsq
        ),
        case when tag_match.matched then 0.4 else 0 end
      )::float as rank
    from firms f
    left join lateral (
      select max(similarity(ea.alias_normalized, normalized)) as max_sim
      from entity_aliases ea
      where ea.entity_id = f.id and ea.entity_type = 'firm'
    ) alias_sim on true
    left join lateral (
      select exists(
        select 1 from entity_tags et
        join tags t on t.id = et.tag_id
        where et.entity_id = f.id
          and et.entity_type = 'firm'
          and similarity(t.slug, normalized) > 0.3
      ) as matched
    ) tag_match on true
    where f.publish_status = 'published'
      and f.merged_into is null
      and (sector_filter is null or f.sector::text = sector_filter)
      and (country_filter is null or f.country = country_filter or f.country_code = upper(country_filter))
      and (
        similarity(f.canonical_name, normalized) > 0.35
        or coalesce(alias_sim.max_sim, 0) > 0.35
        or tag_match.matched
        or to_tsvector('english', coalesce(f.display_name, '') || ' ' || coalesce(f.short_description, ''))
           @@ tsq
      )
    order by rank desc
    limit result_limit;

  -- Search people: name (2x weight), aliases, tags, bio
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
        similarity(p.canonical_name, normalized) * 2.0,
        coalesce(alias_sim.max_sim * 1.5, 0),
        ts_rank_cd(
          to_tsvector('english', coalesce(p.display_name, '') || ' ' || coalesce(p.bio, '')),
          tsq
        ),
        case when tag_match.matched then 0.4 else 0 end
      )::float as rank
    from people p
    left join lateral (
      select max(similarity(ea.alias_normalized, normalized)) as max_sim
      from entity_aliases ea
      where ea.entity_id = p.id and ea.entity_type = 'person'
    ) alias_sim on true
    left join lateral (
      select exists(
        select 1 from entity_tags et
        join tags t on t.id = et.tag_id
        where et.entity_id = p.id
          and et.entity_type = 'person'
          and similarity(t.slug, normalized) > 0.3
      ) as matched
    ) tag_match on true
    where p.publish_status = 'published'
      and (sector_filter is null or p.sector::text = sector_filter)
      and (
        similarity(p.canonical_name, normalized) > 0.35
        or coalesce(alias_sim.max_sim, 0) > 0.35
        or tag_match.matched
        or to_tsvector('english', coalesce(p.display_name, '') || ' ' || coalesce(p.bio, ''))
           @@ tsq
      )
    order by rank desc
    limit result_limit;
end;
$$;
