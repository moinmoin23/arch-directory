-- ============================================================
-- Image storage for entities
-- ============================================================

ALTER TABLE firms ADD COLUMN logo_url text;
ALTER TABLE firms ADD COLUMN image_url text;
ALTER TABLE people ADD COLUMN image_url text;
ALTER TABLE projects ADD COLUMN image_url text;
