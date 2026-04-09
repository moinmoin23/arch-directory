"""Conservative entity resolution.

Cascade:
0. Exact match on wikidata_id (if provided)
1. Exact match on canonical_name
2. Alias match on entity_aliases.alias_normalized
3. Trigram similarity > 0.7 on canonical_name
4. No match → create new entity (or flag to review_queue for ambiguous cases)

No automatic merges. Ambiguous matches (0.6-0.85) go to review_queue.
"""

import logging
from dataclasses import dataclass

from .db import (
    add_to_review_queue,
    get_client,
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
    wikidata_id: str | None = None,
) -> ResolveResult:
    """Resolve a name to an existing entity or create a new one.

    Args:
        name: Display name of the entity.
        entity_type: 'firm' or 'person'.
        sector: Sector for new entities.
        hints: Optional dict with 'country', 'city', 'website' for boosting.
        wikidata_id: Optional Wikidata QID for deterministic matching.

    Returns:
        ResolveResult with entity_id, confidence, and match_type.
    """
    normalized = normalize_name(name)
    table = "firms" if entity_type == "firm" else "people"
    client = get_client()

    # --- Step 0: Deterministic match on wikidata_id ---
    if wikidata_id:
        wk_result = (
            client.table(table)
            .select("id")
            .eq("wikidata_id", wikidata_id)
            .limit(1)
            .execute()
        )
        if wk_result.data:
            entity_id = wk_result.data[0]["id"]
            logger.info("Wikidata match: '%s' (%s) → %s", name, wikidata_id, entity_id)
            return ResolveResult(entity_id=entity_id, confidence=1.0, match_type="wikidata")

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

    # --- Step 4: No match — create new entity atomically ---
    slug = generate_slug(name)
    aliases = [
        {"alias": a, "alias_normalized": normalize_name(a)}
        for a in generate_aliases(name)
    ]

    rpc_params = {
        "p_entity_type": entity_type,
        "p_slug": slug,
        "p_display_name": name,
        "p_canonical_name": normalized,
        "p_sector": sector,
        "p_aliases": aliases,
    }
    if wikidata_id:
        rpc_params["p_wikidata_id"] = wikidata_id
    if hints:
        if hints.get("country"):
            rpc_params["p_country"] = hints["country"]
        if hints.get("city"):
            rpc_params["p_city"] = hints["city"]
        if entity_type == "firm" and hints.get("website"):
            rpc_params["p_website"] = hints["website"]
        if hints.get("openalex_id"):
            rpc_params["p_openalex_id"] = hints["openalex_id"]

    try:
        result = client.rpc("upsert_entity_with_aliases", rpc_params).execute()
        if result.data and isinstance(result.data, dict):
            entity_id = result.data["id"]
        elif result.data and isinstance(result.data, list) and result.data:
            entity_id = result.data[0]["id"] if isinstance(result.data[0], dict) else result.data
        else:
            # Supabase may return the JSONB directly as a string or dict
            entity_id = str(result.data) if result.data else None
    except Exception:
        logger.exception("RPC upsert_entity_with_aliases failed for %s: %s", entity_type, name)
        return ResolveResult(entity_id=None, confidence=0.0, match_type="error")

    if entity_id is None:
        logger.error("Failed to create %s: %s", entity_type, name)
        return ResolveResult(entity_id=None, confidence=0.0, match_type="error")

    logger.info("New %s created: '%s' → %s", entity_type, name, entity_id)
    return ResolveResult(entity_id=entity_id, confidence=0.0, match_type="new")
