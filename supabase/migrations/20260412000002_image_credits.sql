-- Add image_credit columns for photography attribution
ALTER TABLE firms ADD COLUMN image_credit text;
ALTER TABLE people ADD COLUMN image_credit text;
ALTER TABLE projects ADD COLUMN image_credit text;
