"""Conservative entity resolution.

Cascade:
1. Exact match on canonical_name
2. Alias match on entity_aliases.alias_normalized
3. Trigram similarity > 0.7 on canonical_name
4. No match → create new entity (or flag to review_queue for ambiguous cases)

No automatic merges. Ambiguous matches (0.6-0.85) go to review_queue.
"""

import logging
from dataclasses import dataclass

from .db import (
    add_to_enrichment_queue,
    add_to_review_queue,
    get_client,
    upsert_alias,
    upsert_firm,
    upsert_person,
)
from .normalize import generate_aliases, generate_slug, normalize_name

logger = logging.getLogger(__name__)


@dataclass
class ResolveResult:
    entity_id: str | None
    confidence: float
    match_type: str  # exact, alias, trigram, new, review


def resolve_entity(
    name: str,
    entity_type: str,
    *,
    sector: str = "architecture",
    hints: dict | None = None,
) -> ResolveResult:
    """Resolve a name to an existing entity or create a new one.

    Args:
        name: Display name of the entity.
        entity_type: 'firm' or 'person'.
        sector: Sector for new entities.
        hints: Optional dict with 'country', 'city', 'website' for boosting.

    Returns:
        ResolveResult with entity_id, confidence, and match_type.
    """
    normalized = normalize_name(name)
    table = "firms" if entity_type == "firm" else "people"
    client = get_client()

    # --- Step 1: Exact match on canonical_name ---
    query = client.table(table).select("id, canonical_name").eq(
        "canonical_name", normalized
    )
    if entity_type == "firm":
        query = query.is_("merged_into", "null")
    result = query.limit(1).execute()
    if result.data:
        entity_id = result.data[0]["id"]
        logger.info("Exact match: '%s' → %s", name, entity_id)
        return ResolveResult(entity_id=entity_id, confidence=1.0, match_type="exact")

    # --- Step 2: Alias match ---
    alias_result = (
        client.table("entity_aliases")
        .select("entity_id")
        .eq("entity_type", entity_type)
        .eq("alias_normalized", normalized)
        .limit(1)
        .execute()
    )
    if alias_result.data:
        entity_id = alias_result.data[0]["entity_id"]
        logger.info("Alias match: '%s' → %s", name, entity_id)
        return ResolveResult(entity_id=entity_id, confidence=1.0, match_type="alias")

    # --- Step 3: Trigram similarity on canonical_name ---
    # Uses pg_trgm's similarity() function via RPC
    trigram_result = client.rpc(
        "match_entity_trigram",
        {
            "search_name": normalized,
            "search_type": table,
            "threshold": 0.5,
        },
    ).execute()

    if trigram_result.data:
        best = trigram_result.data[0]
        similarity = best["similarity"]
        matched_id = best["id"]

        # High confidence — auto-match
        if similarity >= 0.85:
            logger.info(
                "Trigram match (%.2f): '%s' → %s",
                similarity,
                name,
                matched_id,
            )
            return ResolveResult(
                entity_id=matched_id,
                confidence=similarity,
                match_type="trigram",
            )

        # Ambiguous — send to review queue, do NOT auto-match
        if similarity >= 0.6:
            logger.info(
                "Ambiguous trigram (%.2f): '%s' ~ %s → review queue",
                similarity,
                name,
                matched_id,
            )
            add_to_review_queue(
                candidate_name=name,
                entity_type=entity_type,
                suggested_entity_id=matched_id,
                confidence=similarity,
                match_type="trigram",
            )
            return ResolveResult(
                entity_id=None,
                confidence=similarity,
                match_type="review",
            )

    # --- Step 4: No match — create new entity ---
    slug = generate_slug(name)
    new_data = {
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": sector,
    }
    if hints:
        if hints.get("country"):
            new_data["country"] = hints["country"]
        if hints.get("city"):
            new_data["city"] = hints["city"]
        if entity_type == "firm" and hints.get("website"):
            new_data["website"] = hints["website"]

    if entity_type == "firm":
        row = upsert_firm(new_data)
    else:
        row = upsert_person(new_data)

    if row is None:
        logger.error("Failed to create %s: %s", entity_type, name)
        return ResolveResult(entity_id=None, confidence=0.0, match_type="error")

    entity_id = row["id"]

    # Generate and store aliases for the new entity
    for alias in generate_aliases(name):
        upsert_alias(entity_id, entity_type, alias, normalize_name(alias))

    # Add to enrichment queue
    add_to_enrichment_queue(entity_id, entity_type)

    logger.info("New %s created: '%s' → %s", entity_type, name, entity_id)
    return ResolveResult(entity_id=entity_id, confidence=0.0, match_type="new")
