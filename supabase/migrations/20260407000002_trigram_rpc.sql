-- RPC function for trigram similarity matching used by the resolver.
-- Searches either firms or people by canonical_name similarity.

create or replace function match_entity_trigram(
  search_name text,
  search_type text,    -- 'firms' or 'people'
  threshold float default 0.5
)
returns table(id uuid, canonical_name text, similarity float)
language plpgsql stable
as $$
begin
  if search_type = 'firms' then
    return query
      select f.id, f.canonical_name,
             similarity(f.canonical_name, search_name)::float as similarity
      from firms f
      where f.merged_into is null
        and similarity(f.canonical_name, search_name) > threshold
      order by similarity desc
      limit 5;
  elsif search_type = 'people' then
    return query
      select p.id, p.canonical_name,
             similarity(p.canonical_name, search_name)::float as similarity
      from people p
      where similarity(p.canonical_name, search_name) > threshold
      order by similarity desc
      limit 5;
  end if;
end;
$$;
