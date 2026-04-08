-- ============================================================
-- Review queue deduplication + enrichment queue idempotency
-- ============================================================

-- Prevent the same ambiguous match from being flagged multiple times
-- while it's still pending review.
create unique index if not exists idx_review_queue_dedup
  on review_queue(candidate_name, entity_type, suggested_entity_id)
  where status = 'pending';

-- Prevent duplicate enrichment queue entries for the same entity
-- while pending or processing.
create unique index if not exists idx_enrichment_queue_active
  on enrichment_queue(entity_id, entity_type)
  where status in ('pending', 'processing');
