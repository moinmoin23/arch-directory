"""Lightweight LLM enrichment — adds summaries and tags to entities.

Enrichment is additive only: it fills empty fields, never overwrites
existing data. This makes it safe to run on published entities too.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich.py --limit 10
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich.py --limit 50 --type firm
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich.py --dry-run --limit 5
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import anthropic
import instructor
from pydantic import BaseModel, Field

sys.path.insert(0, ".")

from scrapers.shared.db import get_client, upsert_alias
from scrapers.shared.normalize import normalize_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Pydantic response models ────────────────────────────────────────

class FirmEnrichment(BaseModel):
    summary: str = Field(
        description="1-2 sentence factual description. Third person, no hype."
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 descriptive tags (e.g., 'parametric design', 'sustainable architecture')",
    )
    aliases: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Known abbreviations or alternate names. Only include if confident.",
    )


class PersonEnrichment(BaseModel):
    summary: str = Field(
        description="1-2 sentence factual bio. Third person, no hype."
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 descriptive tags about their work focus",
    )


# ── Enrichment logic ────────────────────────────────────────────────

FIRM_PROMPT = """You are enriching entries for a professional directory of architecture, design, and technology firms/institutions.

Given the entity name and any available context, produce:
1. A factual 1-2 sentence summary suitable for a directory listing
2. Up to 5 descriptive tags
3. Known abbreviations or alternate names (only if confident)

Rules:
- Be factual and concise. No marketing language.
- If you don't know enough, write a minimal but accurate summary.
- Do not invent facts. If unsure about founding year, location, etc., omit them.
- Tags should be broad categories (e.g., "computational design", "sustainable architecture")
- Only include aliases you are confident about.

Entity name: {name}
Sector: {sector}
Country: {country}
City: {city}
"""

PERSON_PROMPT = """You are enriching entries for a professional directory of architecture, design, and technology.

Given the person's name and any available context, produce:
1. A factual 1-2 sentence bio suitable for a directory listing
2. Up to 5 descriptive tags about their work focus

Rules:
- Be factual and concise. No marketing language.
- If you don't know enough about this person, say so briefly.
- Do not invent credentials, affiliations, or achievements.
- Tags should describe their research/work area.

Person name: {name}
Sector: {sector}
"""


def enrich_firm(client_ai, db, firm: dict, dry_run: bool) -> bool:
    """Enrich a single firm. Returns True if updated."""
    prompt = FIRM_PROMPT.format(
        name=firm["display_name"],
        sector=firm.get("sector", ""),
        country=firm.get("country", "") or "unknown",
        city=firm.get("city", "") or "unknown",
    )

    try:
        result = client_ai.chat.completions.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
            response_model=FirmEnrichment,
        )
    except Exception:
        logger.exception("LLM call failed for firm: %s", firm["display_name"])
        return False

    if dry_run:
        logger.info("DRY RUN firm '%s': %s", firm["display_name"], result.summary[:80])
        return True

    # Additive update: only fill empty fields
    update = {}
    if not firm.get("short_description") and result.summary:
        update["short_description"] = result.summary

    if update:
        db.table("firms").update(update).eq("id", firm["id"]).execute()

    # Add new aliases (won't duplicate due to upsert)
    for alias in result.aliases:
        normalized = normalize_name(alias)
        if len(normalized) >= 2:
            upsert_alias(firm["id"], "firm", alias, normalized)

    logger.info("Enriched firm: %s (summary=%d chars, %d aliases)",
                firm["display_name"], len(result.summary), len(result.aliases))
    return True


def enrich_person(client_ai, db, person: dict, dry_run: bool) -> bool:
    """Enrich a single person. Returns True if updated."""
    prompt = PERSON_PROMPT.format(
        name=person["display_name"],
        sector=person.get("sector", ""),
    )

    try:
        result = client_ai.chat.completions.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
            response_model=PersonEnrichment,
        )
    except Exception:
        logger.exception("LLM call failed for person: %s", person["display_name"])
        return False

    if dry_run:
        logger.info("DRY RUN person '%s': %s", person["display_name"], result.summary[:80])
        return True

    update = {}
    if not person.get("bio") and result.summary:
        update["bio"] = result.summary

    if update:
        db.table("people").update(update).eq("id", person["id"]).execute()

    logger.info("Enriched person: %s (bio=%d chars)",
                person["display_name"], len(result.summary))
    return True


def run(limit: int, entity_type: str | None, dry_run: bool):
    db = get_client()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    raw_client = anthropic.Anthropic(api_key=api_key)
    client_ai = instructor.from_anthropic(raw_client)

    # Fetch pending enrichment queue items
    query = db.table("enrichment_queue").select(
        "id, entity_id, entity_type"
    ).eq("status", "pending")

    if entity_type:
        query = query.eq("entity_type", entity_type)

    queue_items = query.order("created_at").limit(limit).execute()

    if not queue_items.data:
        logger.info("No pending enrichment items")
        return

    logger.info("Processing %d enrichment items (dry_run=%s)", len(queue_items.data), dry_run)
    now = datetime.now(timezone.utc).isoformat()

    success = 0
    failed = 0

    for item in queue_items.data:
        eid = item["entity_id"]
        etype = item["entity_type"]

        if etype == "firm":
            entity = db.table("firms").select("*").eq("id", eid).limit(1).execute()
            if not entity.data:
                continue
            ok = enrich_firm(client_ai, db, entity.data[0], dry_run)
        else:
            entity = db.table("people").select("*").eq("id", eid).limit(1).execute()
            if not entity.data:
                continue
            ok = enrich_person(client_ai, db, entity.data[0], dry_run)

        if ok:
            success += 1
            if not dry_run:
                db.table("enrichment_queue").update({
                    "status": "done",
                    "enriched_at": now,
                }).eq("id", item["id"]).execute()
        else:
            failed += 1
            if not dry_run:
                db.table("enrichment_queue").update({
                    "status": "failed",
                    "attempts": item.get("attempts", 0) + 1,
                    "last_error": "LLM call failed",
                }).eq("id", item["id"]).execute()

    logger.info("Done: %d success, %d failed", success, failed)


def main():
    parser = argparse.ArgumentParser(description="LLM enrichment pipeline")
    parser.add_argument("--limit", type=int, default=10, help="Max entities to enrich")
    parser.add_argument("--type", choices=["firm", "person"], default=None, help="Entity type filter")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    args = parser.parse_args()
    run(args.limit, args.type, args.dry_run)


if __name__ == "__main__":
    main()
