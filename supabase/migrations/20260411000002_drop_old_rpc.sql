-- Drop the old upsert_entity_with_aliases overload (9 params)
-- so PostgREST can resolve to the new one (11 params) unambiguously.
DROP FUNCTION IF EXISTS upsert_entity_with_aliases(text, text, text, text, text, text, text, text, jsonb);
