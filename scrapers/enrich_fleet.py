"""Tiered enrichment fleet — orchestrates multi-stage entity enrichment.

Routes entities through the right enrichment strategy based on their tier:
  - Stage 1: Drain enrichment queue (LLM enrichment for pending items)
  - Stage 2: Deep web research for top-tier entities
  - Stage 3: LLM enrichment for mid-tier entities
  - Stage 4: Basic LLM bios for long-tail entities

The fleet is designed to be run periodically. It's additive-only and
idempotent — safe to re-run without destroying data.

Usage:
    # Full pipeline (all stages)
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich_fleet.py

    # Specific stage
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich_fleet.py --stage 2

    # Dry run (no writes)
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich_fleet.py --dry-run

    # Custom limits
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/enrich_fleet.py --stage 2 --limit 50
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, ".")

from scrapers.shared.db import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enrich_fleet")


def count_gaps(db) -> dict:
    """Count data gaps to determine what needs enrichment."""
    gaps = {}

    # Firms
    r = db.table("firms").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("merged_into", "null").execute()
    gaps["total_firms"] = r.count or 0

    r = db.table("firms").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("merged_into", "null").is_("short_description", "null").execute()
    gaps["firms_no_desc"] = r.count or 0

    r = db.table("firms").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("merged_into", "null").is_("website", "null").execute()
    gaps["firms_no_website"] = r.count or 0

    r = db.table("firms").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("merged_into", "null").is_("image_url", "null").execute()
    gaps["firms_no_image"] = r.count or 0

    # People
    r = db.table("people").select("id", count="exact").eq(
        "publish_status", "published"
    ).execute()
    gaps["total_people"] = r.count or 0

    r = db.table("people").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("bio", "null").execute()
    gaps["people_no_bio"] = r.count or 0

    r = db.table("people").select("id", count="exact").eq(
        "publish_status", "published"
    ).is_("image_url", "null").execute()
    gaps["people_no_image"] = r.count or 0

    # Queue
    r = db.table("enrichment_queue").select("id", count="exact").eq(
        "status", "pending"
    ).execute()
    gaps["queue_pending"] = r.count or 0

    return gaps


def print_gaps(gaps: dict):
    """Print a summary of data gaps."""
    logger.info("=" * 60)
    logger.info("DATA GAP SUMMARY")
    logger.info("=" * 60)
    logger.info("Firms:  %d total, %d no description, %d no website, %d no image",
                gaps["total_firms"], gaps["firms_no_desc"],
                gaps["firms_no_website"], gaps["firms_no_image"])
    logger.info("People: %d total, %d no bio, %d no image",
                gaps["total_people"], gaps["people_no_bio"], gaps["people_no_image"])
    logger.info("Queue:  %d pending",
                gaps["queue_pending"])
    logger.info("=" * 60)


def stage_1_drain_queue(limit: int, dry_run: bool, entity_type: str | None) -> int:
    """Stage 1: Process pending enrichment queue items via LLM enrichment."""
    logger.info("── STAGE 1: LLM enrichment (drain queue) ──")

    # Import here to avoid loading anthropic SDK unless needed
    from scrapers.enrich import run as enrich_run
    enrich_run(limit=limit, entity_type=entity_type, dry_run=dry_run)
    return 0  # enrich.py logs its own counts


def stage_2_deep_research(
    limit: int, dry_run: bool, entity_type: str | None
) -> int:
    """Stage 2: Deep web research for top-tier entities."""
    logger.info("── STAGE 2: Deep web research (top tier) ──")

    from scrapers.deep_research import run as research_run

    total = 0
    types = [entity_type] if entity_type else ["firm", "person"]

    for etype in types:
        count = research_run(
            entity_type=etype,
            limit=limit,
            dry_run=dry_run,
            tier="top",
            min_confidence=0.3,
        )
        total += count

    return total


def stage_3_mid_tier(limit: int, dry_run: bool, entity_type: str | None) -> int:
    """Stage 3: Web research for mid-tier entities (have some data, need gaps filled)."""
    logger.info("── STAGE 3: Web research (mid tier) ──")

    from scrapers.deep_research import run as research_run

    total = 0
    types = [entity_type] if entity_type else ["firm", "person"]

    for etype in types:
        count = research_run(
            entity_type=etype,
            limit=limit,
            dry_run=dry_run,
            tier="mid",
            min_confidence=0.25,
        )
        total += count

    return total


def stage_4_long_tail(limit: int, dry_run: bool, entity_type: str | None) -> int:
    """Stage 4: LLM-only bios for long-tail entities.

    These entities have minimal web presence, so we use the LLM's
    training knowledge to generate basic descriptions.
    """
    logger.info("── STAGE 4: LLM bios (long tail) ──")

    db = get_client()

    # Find published entities missing bios that aren't in the enrichment queue
    types = [entity_type] if entity_type else ["firm", "person"]
    queued = 0

    for etype in types:
        table = "firms" if etype == "firm" else "people"
        desc_field = "short_description" if etype == "firm" else "bio"

        # Get entities missing descriptions, ordered by lowest quality score
        query = (
            db.table(table)
            .select("id")
            .eq("publish_status", "published")
            .is_(desc_field, "null")
            .order("quality_score", desc=False)
            .limit(limit)
        )
        if etype == "firm":
            query = query.is_("merged_into", "null")

        result = query.execute()

        for entity in result.data or []:
            if dry_run:
                logger.info("  DRY RUN: Would queue %s %s for LLM enrichment",
                            etype, entity["id"][:8])
                queued += 1
            else:
                from scrapers.shared.db import add_to_enrichment_queue
                add_to_enrichment_queue(entity["id"], etype)
                queued += 1

    logger.info("  Queued %d entities for LLM enrichment", queued)

    # Now drain the queue with enrich.py
    if queued > 0 and not dry_run:
        from scrapers.enrich import run as enrich_run
        enrich_run(limit=queued, entity_type=entity_type, dry_run=dry_run)

    return queued


def run_fleet(
    stages: list[int] | None = None,
    limit: int = 50,
    dry_run: bool = False,
    entity_type: str | None = None,
):
    """Run the enrichment fleet."""
    db = get_client()
    start = time.monotonic()

    # Check API key for LLM stages
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Print current gaps
    gaps = count_gaps(db)
    print_gaps(gaps)

    all_stages = stages or [1, 2, 3, 4]
    results = {}

    for stage in all_stages:
        stage_start = time.monotonic()

        if stage == 1:
            if not has_api_key:
                logger.warning("Skipping Stage 1 (LLM): ANTHROPIC_API_KEY not set")
                continue
            if gaps["queue_pending"] == 0:
                logger.info("Skipping Stage 1: no pending queue items")
                continue
            stage_1_drain_queue(
                limit=min(limit, gaps["queue_pending"]),
                dry_run=dry_run,
                entity_type=entity_type,
            )
        elif stage == 2:
            results[2] = stage_2_deep_research(limit, dry_run, entity_type)
        elif stage == 3:
            results[3] = stage_3_mid_tier(limit, dry_run, entity_type)
        elif stage == 4:
            if not has_api_key:
                logger.warning("Skipping Stage 4 (LLM): ANTHROPIC_API_KEY not set")
                continue
            results[4] = stage_4_long_tail(limit, dry_run, entity_type)

        elapsed = time.monotonic() - stage_start
        logger.info("  Stage %d completed in %.1fs", stage, elapsed)

    # Print updated gaps
    gaps_after = count_gaps(db)
    total_elapsed = time.monotonic() - start

    logger.info("")
    logger.info("=" * 60)
    logger.info("FLEET RUN COMPLETE (%.1fs)", total_elapsed)
    logger.info("=" * 60)
    if not dry_run:
        logger.info("Firms:  desc %d→%d, website %d→%d, image %d→%d",
                    gaps["firms_no_desc"], gaps_after["firms_no_desc"],
                    gaps["firms_no_website"], gaps_after["firms_no_website"],
                    gaps["firms_no_image"], gaps_after["firms_no_image"])
        logger.info("People: bio %d→%d, image %d→%d",
                    gaps["people_no_bio"], gaps_after["people_no_bio"],
                    gaps["people_no_image"], gaps_after["people_no_image"])


def main():
    parser = argparse.ArgumentParser(
        description="Tiered enrichment fleet — multi-stage entity enrichment"
    )
    parser.add_argument(
        "--stage", type=int, action="append", dest="stages",
        help="Run specific stage(s). Can be repeated. Default: all stages.",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Max entities per stage per type (default: 50)",
    )
    parser.add_argument(
        "--type", choices=["firm", "person"], default=None,
        help="Process only firms or people (default: both)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate without writing to database",
    )
    args = parser.parse_args()
    run_fleet(
        stages=args.stages,
        limit=args.limit,
        dry_run=args.dry_run,
        entity_type=args.type,
    )


if __name__ == "__main__":
    main()
