-- RPC: get source counts for a batch of entity IDs
-- Used by listing pages to show "mentioned in X sources" badges

CREATE OR REPLACE FUNCTION get_entity_source_counts(
  p_entity_ids uuid[],
  p_entity_type text
)
RETURNS TABLE(entity_id uuid, source_count bigint)
LANGUAGE sql STABLE
AS $$
  SELECT es.entity_id, count(*) AS source_count
  FROM entity_sources es
  WHERE es.entity_id = ANY(p_entity_ids)
    AND es.entity_type = p_entity_type::entity_type
  GROUP BY es.entity_id;
$$;
