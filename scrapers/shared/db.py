"""Supabase client and idempotent upsert helpers."""

import logging
import os
import certifi
from dotenv import load_dotenv
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Load .env from scrapers/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Fix SSL certificate verification on macOS (feedparser uses urllib)
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

_client: Client | None = None


def get_client() -> Client:
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        _client = create_client(url, key)
    return _client


def upsert_firm(data: dict, *, conflict_key: str = "slug") -> dict | None:
    """Upsert a firm record. Returns the upserted row or None on error."""
    try:
        result = (
            get_client()
            .table("firms")
            .upsert(data, on_conflict=conflict_key)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert firm: %s", data.get("slug"))
        return None


def upsert_person(data: dict, *, conflict_key: str = "slug") -> dict | None:
    """Upsert a person record."""
    try:
        result = (
            get_client()
            .table("people")
            .upsert(data, on_conflict=conflict_key)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert person: %s", data.get("slug"))
        return None


def upsert_source(data: dict, *, conflict_key: str = "url") -> dict | None:
    """Upsert a source record."""
    try:
        result = (
            get_client()
            .table("sources")
            .upsert(data, on_conflict=conflict_key)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert source: %s", data.get("url"))
        return None


def upsert_alias(
    entity_id: str, entity_type: str, alias: str, alias_normalized: str
) -> dict | None:
    """Upsert an entity alias."""
    try:
        result = (
            get_client()
            .table("entity_aliases")
            .upsert(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "alias": alias,
                    "alias_normalized": alias_normalized,
                },
                on_conflict="entity_type,alias_normalized",
            )
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert alias: %s", alias)
        return None


def link_entity_source(
    entity_id: str,
    entity_type: str,
    source_id: str,
    mention_type: str = "mention",
) -> None:
    """Link an entity to a source that mentions it. Idempotent via unique constraint."""
    try:
        get_client().table("entity_sources").upsert(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "source_id": source_id,
                "mention_type": mention_type,
            },
            on_conflict="entity_id,entity_type,source_id",
        ).execute()
    except Exception:
        logger.exception("Failed to link entity %s to source %s", entity_id, source_id)


def upsert_tag(name: str, slug: str, category: str | None = None) -> dict | None:
    """Upsert a tag by slug. Returns the tag row."""
    try:
        data: dict = {"name": name, "slug": slug}
        if category:
            data["category"] = category
        result = (
            get_client()
            .table("tags")
            .upsert(data, on_conflict="slug")
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert tag: %s", slug)
        return None


def link_entity_tag(
    entity_id: str, entity_type: str, tag_id: str, source: str = "llm"
) -> None:
    """Link an entity to a tag. Idempotent via unique constraint."""
    try:
        get_client().table("entity_tags").upsert(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "tag_id": tag_id,
                "source": source,
            },
            on_conflict="entity_id,entity_type,tag_id",
        ).execute()
    except Exception:
        logger.exception("Failed to link entity %s to tag %s", entity_id, tag_id)


def upsert_education(
    person_id: str,
    institution_name: str,
    *,
    institution_id: str | None = None,
    degree: str | None = None,
    field: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    source: str | None = None,
) -> None:
    """Upsert an education record. Idempotent via unique constraint."""
    try:
        data: dict = {
            "person_id": person_id,
            "institution_name": institution_name,
        }
        if institution_id:
            data["institution_id"] = institution_id
        if degree:
            data["degree"] = degree
        if field:
            data["field"] = field
        if start_year:
            data["start_year"] = start_year
        if end_year:
            data["end_year"] = end_year
        if source:
            data["source"] = source
        # Use insert with manual conflict handling since the unique index uses COALESCE
        get_client().table("education").insert(data).execute()
    except Exception as e:
        if "duplicate key" in str(e) or "23505" in str(e):
            return  # Already exists
        logger.exception("Failed to upsert education for person %s", person_id)


def upsert_project(
    slug: str,
    display_name: str,
    *,
    year: int | None = None,
    location: str | None = None,
    project_type: str = "building",
    sector: str | None = None,
    wikidata_id: str | None = None,
    country: str | None = None,
    city: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict | None:
    """Upsert a project record. Returns the project row."""
    try:
        data: dict = {
            "slug": slug,
            "display_name": display_name,
            "project_type": project_type,
        }
        if year:
            data["year"] = year
        if location:
            data["location"] = location
        if sector:
            data["sector"] = sector
        if wikidata_id:
            data["wikidata_id"] = wikidata_id
        if country:
            data["country"] = country
        if city:
            data["city"] = city
        if latitude is not None:
            data["latitude"] = latitude
        if longitude is not None:
            data["longitude"] = longitude
        result = (
            get_client()
            .table("projects")
            .upsert(data, on_conflict="slug")
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Failed to upsert project: %s", slug)
        return None


def link_project_entity(
    project_id: str, entity_id: str, entity_type: str, role: str | None = None
) -> None:
    """Link an entity to a project. Idempotent via unique constraint."""
    try:
        data: dict = {
            "project_id": project_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
        }
        if role:
            data["role"] = role
        get_client().table("project_entities").upsert(
            data,
            on_conflict="project_id,entity_id,entity_type",
        ).execute()
    except Exception:
        logger.exception("Failed to link project %s to entity %s", project_id, entity_id)


def upsert_entity_relationship(
    from_entity_id: str,
    from_entity_type: str,
    to_entity_id: str,
    to_entity_type: str,
    relationship: str,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
    notes: str | None = None,
) -> None:
    """Upsert an entity relationship. Idempotent via unique constraint."""
    try:
        data: dict = {
            "from_entity_id": from_entity_id,
            "from_entity_type": from_entity_type,
            "to_entity_id": to_entity_id,
            "to_entity_type": to_entity_type,
            "relationship": relationship,
        }
        if start_year:
            data["start_year"] = start_year
        if end_year:
            data["end_year"] = end_year
        if notes:
            data["notes"] = notes
        get_client().table("entity_relationships").upsert(
            data,
            on_conflict="from_entity_id,from_entity_type,to_entity_id,to_entity_type,relationship",
        ).execute()
    except Exception:
        logger.exception(
            "Failed to upsert relationship %s → %s", from_entity_id, to_entity_id
        )


def add_to_enrichment_queue(entity_id: str, entity_type: str) -> None:
    """Add an entity to the enrichment queue if not already pending/processing.

    Uses the partial unique index idx_enrichment_queue_active to skip
    duplicates without a separate existence check.
    """
    try:
        get_client().table("enrichment_queue").insert(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "status": "pending",
            }
        ).execute()
    except Exception as e:
        # Unique constraint violation from the partial index = already queued
        if "duplicate key" in str(e) or "23505" in str(e):
            return
        logger.exception("Failed to enqueue entity %s", entity_id)


def add_to_review_queue(
    candidate_name: str,
    entity_type: str,
    suggested_entity_id: str | None,
    confidence: float,
    match_type: str,
) -> None:
    """Add an ambiguous match to the review queue.

    Uses the partial unique index idx_review_queue_dedup to skip
    duplicates for the same candidate that's still pending.
    """
    try:
        get_client().table("review_queue").insert(
            {
                "candidate_name": candidate_name,
                "entity_type": entity_type,
                "suggested_entity_id": suggested_entity_id,
                "confidence": confidence,
                "match_type": match_type,
                "status": "pending",
            }
        ).execute()
    except Exception as e:
        if "duplicate key" in str(e) or "23505" in str(e):
            return
        logger.exception("Failed to add to review queue: %s", candidate_name)
