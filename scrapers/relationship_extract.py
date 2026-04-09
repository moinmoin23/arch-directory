"""Extract relationships from existing sources using LLM structured output.

For each source with 2+ entity mentions, sends the title and entity names
to Claude and asks for structured relationship extraction.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/relationship_extract.py --limit 50
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/relationship_extract.py --dry-run --limit 10
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

from scrapers.shared.db import (
    get_client,
    upsert_entity_relationship,
)
from scrapers.shared.rate_limit import RateLimiter
from scrapers.shared.resolver import resolve_entity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Pydantic models ───────────────────────────────────────────────

class ExtractedRelationship(BaseModel):
    subject_name: str = Field(description="Name of the subject entity")
    subject_type: str = Field(description="'firm' or 'person'")
    predicate: str = Field(
        description="Relationship type: 'works_at', 'founded', 'partner_at', "
        "'collaborated_with', 'acquired_by', 'subsidiary_of', 'spin_off_from', "
        "'mentored_by', 'designed', 'led_project'"
    )
    object_name: str = Field(description="Name of the object entity")
    object_type: str = Field(description="'firm' or 'person'")
    year: int | None = Field(default=None, description="Year of the relationship, if mentioned")


class ExtractionResult(BaseModel):
    relationships: list[ExtractedRelationship] = Field(
        default_factory=list,
        max_length=10,
        description="Relationships found in the source. Empty list if none found.",
    )


# ── Prompt ────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are extracting relationships from an article title/description about architecture, design, and technology.

Given the article title and the entities mentioned, identify any relationships between them.

Relationship types:
- works_at: person works at firm
- founded: person founded firm
- partner_at: person is a partner at firm
- collaborated_with: firm collaborated with firm, or person collaborated with person
- acquired_by: firm was acquired by firm
- subsidiary_of: firm is subsidiary of firm
- spin_off_from: firm spun off from firm
- designed: person or firm designed a project
- led_project: person led a project

Rules:
- Only extract relationships you are confident about from the given context.
- Do not invent relationships not implied by the title.
- If no relationships are apparent, return an empty list.
- Use the exact entity names provided.

Article title: {title}

Entities mentioned:
{entities}
"""


# ── Predicate → relationship_type mapping ─────────────────────────

PREDICATE_TO_RELATIONSHIP = {
    "collaborated_with": "collaboration",
    "acquired_by": "acquired_by",
    "subsidiary_of": "subsidiary",
    "spin_off_from": "spin_off",
    "partner_at": "partner",
}

PREDICATE_TO_FIRM_PEOPLE_ROLE = {
    "works_at": "Employee",
    "founded": "Founder",
    "partner_at": "Partner",
}


# ── Main logic ────────────────────────────────────────────────────

def find_sources_with_multiple_entities(db, limit: int) -> list[dict]:
    """Find sources that have 2+ entity_sources links."""
    # Get sources with their linked entities
    result = db.table("entity_sources").select(
        "source_id, entity_id, entity_type"
    ).execute()

    if not result.data:
        return []

    # Group by source_id
    source_entities: dict[str, list[dict]] = {}
    for row in result.data:
        sid = row["source_id"]
        source_entities.setdefault(sid, []).append({
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
        })

    # Filter to sources with 2+ entities
    multi = {sid: entities for sid, entities in source_entities.items() if len(entities) >= 2}

    if not multi:
        return []

    # Fetch source titles
    source_ids = list(multi.keys())[:limit]
    sources = []
    for sid in source_ids:
        src = db.table("sources").select("id, title").eq("id", sid).limit(1).execute()
        if src.data:
            title = src.data[0]["title"]
            # Fetch entity names
            entities = []
            for ent in multi[sid]:
                table = "firms" if ent["entity_type"] == "firm" else "people"
                e = db.table(table).select("id, display_name").eq("id", ent["entity_id"]).limit(1).execute()
                if e.data:
                    entities.append({
                        "id": e.data[0]["id"],
                        "name": e.data[0]["display_name"],
                        "type": ent["entity_type"],
                    })
            if len(entities) >= 2:
                sources.append({"source_id": sid, "title": title, "entities": entities})

    return sources


def extract_and_store(client_ai, db, source: dict, dry_run: bool) -> int:
    """Extract relationships from a single source and store them."""
    entities_text = "\n".join(
        f"- {e['name']} ({e['type']})" for e in source["entities"]
    )

    prompt = EXTRACTION_PROMPT.format(
        title=source["title"],
        entities=entities_text,
    )

    try:
        result = client_ai.chat.completions.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            response_model=ExtractionResult,
        )
    except Exception:
        logger.exception("LLM extraction failed for source: %s", source["title"][:50])
        return 0

    if not result.relationships:
        return 0

    if dry_run:
        for rel in result.relationships:
            logger.info(
                "DRY RUN: %s (%s) -[%s]-> %s (%s)",
                rel.subject_name, rel.subject_type, rel.predicate,
                rel.object_name, rel.object_type,
            )
        return len(result.relationships)

    stored = 0
    entity_lookup = {e["name"].lower(): e for e in source["entities"]}

    for rel in result.relationships:
        # Try to match subject and object to known entities
        subject = entity_lookup.get(rel.subject_name.lower())
        obj = entity_lookup.get(rel.object_name.lower())

        if not subject or not obj:
            # Try resolver for unmatched names
            if not subject:
                r = resolve_entity(rel.subject_name, rel.subject_type)
                if r.entity_id:
                    subject = {"id": r.entity_id, "type": rel.subject_type}
            if not obj:
                r = resolve_entity(rel.object_name, rel.object_type)
                if r.entity_id:
                    obj = {"id": r.entity_id, "type": rel.object_type}

        if not subject or not obj:
            continue

        # Store based on predicate type
        if rel.predicate in PREDICATE_TO_FIRM_PEOPLE_ROLE:
            # Person-firm relationship → firm_people table
            if subject["type"] == "person" and obj["type"] == "firm":
                role = PREDICATE_TO_FIRM_PEOPLE_ROLE[rel.predicate]
                try:
                    db.table("firm_people").upsert(
                        {
                            "firm_id": obj["id"],
                            "person_id": subject["id"],
                            "role": role,
                            "is_current": True,
                            "source": "relationship_extraction",
                        },
                        on_conflict="firm_id,person_id",
                    ).execute()
                    stored += 1
                except Exception:
                    logger.debug("Failed to store firm_people: %s at %s", rel.subject_name, rel.object_name)

        elif rel.predicate in PREDICATE_TO_RELATIONSHIP:
            # Entity-entity relationship → entity_relationships table
            relationship_type = PREDICATE_TO_RELATIONSHIP[rel.predicate]
            upsert_entity_relationship(
                from_entity_id=subject["id"],
                from_entity_type=subject["type"],
                to_entity_id=obj["id"],
                to_entity_type=obj["type"],
                relationship=relationship_type,
                start_year=rel.year,
            )
            stored += 1

        elif rel.predicate in ("designed", "led_project"):
            # These would need a project entity — skip for now unless
            # the object is a firm (collaboration on a project)
            logger.debug("Skipping project-type relationship: %s", rel.predicate)

    return stored


def run(limit: int = 50, dry_run: bool = False) -> int:
    db = get_client()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    raw_client = anthropic.Anthropic(api_key=api_key)
    client_ai = instructor.from_anthropic(raw_client)

    sources = find_sources_with_multiple_entities(db, limit=limit)
    if not sources:
        logger.info("No sources with 2+ entity mentions found")
        return 0

    logger.info("Processing %d sources for relationship extraction (dry_run=%s)", len(sources), dry_run)

    limiter = RateLimiter(min_delay=1.0)
    total = 0

    for source in sources:
        limiter.wait()
        count = extract_and_store(client_ai, db, source, dry_run)
        total += count
        if count:
            logger.info("Source '%s': %d relationships", source["title"][:60], count)

    logger.info("Relationship extraction complete: %d relationships from %d sources", total, len(sources))
    return total


def main():
    parser = argparse.ArgumentParser(description="Extract relationships from sources")
    parser.add_argument("--limit", type=int, default=50, help="Max sources to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    count = run(args.limit, args.dry_run)
    print(f"\nRelationship extraction: {count} relationships processed")


if __name__ == "__main__":
    main()
