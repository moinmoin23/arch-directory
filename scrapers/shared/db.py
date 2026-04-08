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


def add_to_enrichment_queue(entity_id: str, entity_type: str) -> None:
    """Add an entity to the enrichment queue if not already present."""
    try:
        existing = (
            get_client()
            .table("enrichment_queue")
            .select("id")
            .eq("entity_id", entity_id)
            .eq("entity_type", entity_type)
            .limit(1)
            .execute()
        )
        if not existing.data:
            get_client().table("enrichment_queue").insert(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "status": "pending",
                }
            ).execute()
    except Exception:
        logger.exception("Failed to enqueue entity %s", entity_id)


def add_to_review_queue(
    candidate_name: str,
    entity_type: str,
    suggested_entity_id: str | None,
    confidence: float,
    match_type: str,
) -> None:
    """Add an ambiguous match to the review queue."""
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
    except Exception:
        logger.exception("Failed to add to review queue: %s", candidate_name)
