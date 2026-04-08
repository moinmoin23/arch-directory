"""Shared utilities for the ingestion pipeline."""

from .cursors import get_cursor, update_cursor
from .db import (
    add_to_enrichment_queue,
    add_to_review_queue,
    get_client,
    upsert_alias,
    upsert_firm,
    upsert_person,
    upsert_source,
)
from .normalize import generate_aliases, generate_slug, normalize_name
from .resolver import ResolveResult, resolve_entity

__all__ = [
    "add_to_enrichment_queue",
    "add_to_review_queue",
    "generate_aliases",
    "generate_slug",
    "get_client",
    "get_cursor",
    "normalize_name",
    "resolve_entity",
    "ResolveResult",
    "update_cursor",
    "upsert_alias",
    "upsert_firm",
    "upsert_person",
    "upsert_source",
]
