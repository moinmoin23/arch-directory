"""FabLabs.io ingestion — global fab lab directory.

Ingests from the public FabLabs.io API (v0). Each lab becomes a firm
with sector='technology', and capabilities/links are preserved.

Only active labs are ingested. Labs without a name or country are skipped.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/fablabs_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/fablabs_ingest.py --include-inactive
"""

import argparse
import logging
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.cursors import update_cursor
from scrapers.shared.db import (
    add_to_enrichment_queue,
    get_client,
    upsert_alias,
    upsert_firm,
)
from scrapers.shared.normalize import generate_aliases, generate_slug, normalize_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

API_URL = "https://api.fablabs.io/0/labs.json"

# Capability codes → human-readable labels
CAPABILITY_LABELS = {
    "three_d_printing": "3D Printing",
    "cnc_milling": "CNC Milling",
    "circuit_production": "Circuit Production",
    "laser": "Laser Cutting",
    "precision_milling": "Precision Milling",
    "vinyl_cutting": "Vinyl Cutting",
}


def _extract_website(links: list[dict]) -> str | None:
    """Pick the first non-social-media link as the website."""
    social_patterns = (
        "instagram.com", "twitter.com", "x.com",
        "facebook.com", "youtube.com", "linkedin.com",
        "tiktok.com",
    )
    for link in links:
        url = link.get("url", "")
        if url and not any(p in url.lower() for p in social_patterns):
            return url
    return None


def _build_description(lab: dict) -> str:
    """Build a short description from blurb, capabilities, and kind."""
    parts = []

    kind = lab.get("kind_name", "fab_lab").replace("_", " ").title()
    parts.append(kind)

    blurb = (lab.get("blurb") or "").strip()
    if blurb:
        # Truncate long blurbs to ~300 chars
        if len(blurb) > 300:
            blurb = blurb[:297] + "..."
        parts.append(blurb)

    caps = lab.get("capabilities", [])
    if caps:
        labels = [CAPABILITY_LABELS.get(c, c.replace("_", " ").title()) for c in caps]
        parts.append("Capabilities: " + ", ".join(labels))

    return ". ".join(parts) if parts else None


def _process_lab(lab: dict, db_client) -> bool:
    """Process a single lab record. Returns True if upserted."""
    name = (lab.get("name") or "").strip()
    country = (lab.get("country_code") or "").strip().upper()
    if not name or not country:
        return False

    normalized = normalize_name(name)
    slug = generate_slug(name)

    # Check for existing firm by canonical_name to avoid duplicating
    existing = db_client.table("firms").select("id").eq(
        "canonical_name", normalized
    ).is_("merged_into", "null").limit(1).execute()

    if existing.data:
        # Already exists — skip (don't overwrite manually curated data)
        return False

    # Also check aliases
    alias_match = db_client.table("entity_aliases").select("entity_id").eq(
        "entity_type", "firm"
    ).eq("alias_normalized", normalized).limit(1).execute()

    if alias_match.data:
        return False

    city = (lab.get("city") or lab.get("county") or "").strip()
    website = _extract_website(lab.get("links", []))
    description = _build_description(lab)

    row = upsert_firm({
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": "technology",
        "country": country,
        "city": city or None,
        "website": website,
        "short_description": description,
    })

    if not row:
        return False

    firm_id = row["id"]

    # Generate aliases
    for alias in generate_aliases(name):
        upsert_alias(firm_id, "firm", alias, normalize_name(alias))

    # Add to enrichment queue
    add_to_enrichment_queue(firm_id, "firm")

    return True


def run(include_inactive: bool = False) -> int:
    """Run FabLabs.io ingestion. Returns count of new firms created."""
    db_client = get_client()

    logger.info("Fetching FabLabs.io directory...")
    try:
        resp = httpx.get(API_URL, timeout=60.0)
        resp.raise_for_status()
        labs = resp.json()
    except httpx.HTTPError:
        logger.exception("Failed to fetch FabLabs.io API")
        update_cursor("fablabs", "", 0, "error")
        return 0

    logger.info("Fetched %d labs from FabLabs.io", len(labs))

    if not include_inactive:
        labs = [l for l in labs if l.get("activity_status") == "active"]
        logger.info("Filtered to %d active labs", len(labs))

    created = 0
    skipped = 0
    errors = 0

    for i, lab in enumerate(labs):
        try:
            if _process_lab(lab, db_client):
                created += 1
            else:
                skipped += 1
        except Exception:
            logger.exception("Error processing lab: %s", lab.get("name", "?"))
            errors += 1

        if (i + 1) % 200 == 0:
            logger.info("Progress: %d/%d processed (%d created, %d skipped)",
                        i + 1, len(labs), created, skipped)

    status = "ok" if errors == 0 else "partial"
    update_cursor("fablabs", str(len(labs)), created, status)

    logger.info(
        "FabLabs.io ingestion complete: %d created, %d skipped, %d errors (of %d total)",
        created, skipped, errors, len(labs),
    )
    return created


def main():
    parser = argparse.ArgumentParser(description="FabLabs.io ingestion")
    parser.add_argument("--include-inactive", action="store_true",
                        help="Include inactive/closed/planned labs")
    args = parser.parse_args()
    run(include_inactive=args.include_inactive)


if __name__ == "__main__":
    main()
