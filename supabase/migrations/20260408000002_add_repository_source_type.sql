-- Add 'repository' to source_type enum for GitHub repos
alter type source_type add value if not exists 'repository';
