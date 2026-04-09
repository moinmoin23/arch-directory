-- ============================================================
-- Enrichment schema: external IDs, education table, project geo
-- ============================================================

-- A1. External identifiers on firms
ALTER TABLE firms ADD COLUMN wikidata_id text;
ALTER TABLE firms ADD COLUMN openalex_id text;
ALTER TABLE firms ADD COLUMN latitude double precision;
ALTER TABLE firms ADD COLUMN longitude double precision;
CREATE UNIQUE INDEX idx_firms_wikidata ON firms(wikidata_id) WHERE wikidata_id IS NOT NULL;

-- A1. External identifiers on people
ALTER TABLE people ADD COLUMN wikidata_id text;
ALTER TABLE people ADD COLUMN openalex_id text;
ALTER TABLE people ADD COLUMN orcid text;
ALTER TABLE people ADD COLUMN birth_year int;
ALTER TABLE people ADD COLUMN death_year int;
CREATE UNIQUE INDEX idx_people_wikidata ON people(wikidata_id) WHERE wikidata_id IS NOT NULL;
CREATE UNIQUE INDEX idx_people_orcid ON people(orcid) WHERE orcid IS NOT NULL;

-- A2. Education table
CREATE TABLE education (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id       uuid NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  institution_id  uuid REFERENCES firms(id) ON DELETE SET NULL,
  institution_name text NOT NULL,
  degree          text,
  field           text,
  start_year      int,
  end_year        int,
  source          text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_education_unique ON education(person_id, institution_name, COALESCE(degree, ''));
CREATE INDEX idx_education_person ON education(person_id);
CREATE INDEX idx_education_institution ON education(institution_id);

-- A3. Geo + wikidata_id on projects
ALTER TABLE projects ADD COLUMN wikidata_id text;
ALTER TABLE projects ADD COLUMN latitude double precision;
ALTER TABLE projects ADD COLUMN longitude double precision;
ALTER TABLE projects ADD COLUMN country text;
ALTER TABLE projects ADD COLUMN city text;
CREATE UNIQUE INDEX idx_projects_wikidata ON projects(wikidata_id) WHERE wikidata_id IS NOT NULL;

-- A4. Update upsert_entity_with_aliases RPC to handle new columns
CREATE OR REPLACE FUNCTION upsert_entity_with_aliases(
  p_entity_type text,
  p_slug text,
  p_display_name text,
  p_canonical_name text,
  p_sector text,
  p_country text DEFAULT NULL,
  p_city text DEFAULT NULL,
  p_website text DEFAULT NULL,
  p_aliases jsonb DEFAULT '[]'::jsonb,
  p_wikidata_id text DEFAULT NULL,
  p_openalex_id text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_entity_id uuid;
  v_alias record;
BEGIN
  IF p_entity_type = 'firm' THEN
    INSERT INTO firms (slug, display_name, canonical_name, sector, country, city, website, wikidata_id, openalex_id)
    VALUES (p_slug, p_display_name, p_canonical_name, p_sector::sector_type,
            p_country, p_city, p_website, p_wikidata_id, p_openalex_id)
    ON CONFLICT (slug) DO UPDATE SET
      display_name = excluded.display_name,
      canonical_name = excluded.canonical_name,
      wikidata_id = COALESCE(firms.wikidata_id, excluded.wikidata_id),
      openalex_id = COALESCE(firms.openalex_id, excluded.openalex_id),
      updated_at = now()
    RETURNING id INTO v_entity_id;
  ELSIF p_entity_type = 'person' THEN
    INSERT INTO people (slug, display_name, canonical_name, sector, wikidata_id, openalex_id)
    VALUES (p_slug, p_display_name, p_canonical_name, p_sector::sector_type,
            p_wikidata_id, p_openalex_id)
    ON CONFLICT (slug) DO UPDATE SET
      display_name = excluded.display_name,
      canonical_name = excluded.canonical_name,
      wikidata_id = COALESCE(people.wikidata_id, excluded.wikidata_id),
      openalex_id = COALESCE(people.openalex_id, excluded.openalex_id),
      updated_at = now()
    RETURNING id INTO v_entity_id;
  ELSE
    RAISE EXCEPTION 'Invalid entity_type: %', p_entity_type;
  END IF;

  -- Insert aliases (skip duplicates via unique constraint)
  FOR v_alias IN SELECT * FROM jsonb_to_recordset(p_aliases)
    AS x(alias text, alias_normalized text)
  LOOP
    INSERT INTO entity_aliases (entity_id, entity_type, alias, alias_normalized)
    VALUES (v_entity_id, p_entity_type::entity_type, v_alias.alias, v_alias.alias_normalized)
    ON CONFLICT (entity_type, alias_normalized) DO NOTHING;
  END LOOP;

  -- Enqueue for enrichment (skip if already pending/processing via partial index)
  BEGIN
    INSERT INTO enrichment_queue (entity_id, entity_type, status)
    VALUES (v_entity_id, p_entity_type::entity_type, 'pending');
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;

  RETURN jsonb_build_object('id', v_entity_id);
END;
$$;
