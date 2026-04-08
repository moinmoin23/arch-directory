-- ============================================================
-- Atomic entity creation: upsert entity + aliases + enrichment queue
-- in a single transaction. Called from the Python resolver.
-- ============================================================

create or replace function upsert_entity_with_aliases(
  p_entity_type text,         -- 'firm' or 'person'
  p_slug text,
  p_display_name text,
  p_canonical_name text,
  p_sector text,              -- cast to sector_type
  p_country text default null,
  p_city text default null,
  p_website text default null,
  p_aliases jsonb default '[]'::jsonb  -- array of {alias, alias_normalized}
)
returns jsonb
language plpgsql
as $$
declare
  v_entity_id uuid;
  v_alias record;
begin
  if p_entity_type = 'firm' then
    insert into firms (slug, display_name, canonical_name, sector, country, city, website)
    values (p_slug, p_display_name, p_canonical_name, p_sector::sector_type,
            p_country, p_city, p_website)
    on conflict (slug) do update set
      display_name = excluded.display_name,
      canonical_name = excluded.canonical_name,
      updated_at = now()
    returning id into v_entity_id;
  elsif p_entity_type = 'person' then
    insert into people (slug, display_name, canonical_name, sector)
    values (p_slug, p_display_name, p_canonical_name, p_sector::sector_type)
    on conflict (slug) do update set
      display_name = excluded.display_name,
      canonical_name = excluded.canonical_name,
      updated_at = now()
    returning id into v_entity_id;
  else
    raise exception 'Invalid entity_type: %', p_entity_type;
  end if;

  -- Insert aliases (skip duplicates via unique constraint)
  for v_alias in select * from jsonb_to_recordset(p_aliases)
    as x(alias text, alias_normalized text)
  loop
    insert into entity_aliases (entity_id, entity_type, alias, alias_normalized)
    values (v_entity_id, p_entity_type::entity_type, v_alias.alias, v_alias.alias_normalized)
    on conflict (entity_type, alias_normalized) do nothing;
  end loop;

  -- Enqueue for enrichment (skip if already pending/processing via partial index)
  begin
    insert into enrichment_queue (entity_id, entity_type, status)
    values (v_entity_id, p_entity_type::entity_type, 'pending');
  exception when unique_violation then
    -- Already queued, ignore
    null;
  end;

  return jsonb_build_object('id', v_entity_id);
end;
$$;
