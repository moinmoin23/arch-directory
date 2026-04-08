"""Compute quality scores and publish_status for all entities.

Scoring rules for firms (0-100):
  +20  has country
  +15  has city
  +15  has short_description
  +10  has website
  +10  has founded_year
  +10  has size_range
  +10  has at least 1 alias
  +10  has at least 1 associated person

Scoring rules for people (0-100):
  +25  has current_firm_id
  +20  has role or title
  +15  has bio
  +15  has nationality
  +15  has at least 1 alias
  +10  has sector != default

Publish rules:
  quality >= 30  AND  not irrelevant  →  'published'
  quality < 30                        →  'draft'
  irrelevant keyword match            →  'hidden'

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/quality.py
    PYTHONPATH=. scrapers/.venv/bin/python scripts/quality.py --dry-run
"""

import argparse
import logging
import sys

sys.path.insert(0, ".")

from scrapers.shared.db import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_IRRELEVANT_KEYWORDS = [
    "hospital", "clinic", "medical", "pharma", "health",
    "neurology", "cardiology", "oncology", "surgery", "dentist",
    "veterinary", "nursing", "pathology", "radiology",
    "ministry of", "department of defense", "army", "navy",
    "air force", "police", "prison", "correctional",
]

# Supabase client returns max 1000 rows per request.
PAGE_SIZE = 1000


def _is_irrelevant(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in _IRRELEVANT_KEYWORDS)


def _score_firm(f: dict, alias_count: int, people_count: int) -> int:
    score = 0
    if f.get("country"):
        score += 20
    if f.get("city"):
        score += 15
    if f.get("short_description"):
        score += 15
    if f.get("website"):
        score += 10
    if f.get("founded_year"):
        score += 10
    if f.get("size_range"):
        score += 10
    if alias_count > 0:
        score += 10
    if people_count > 0:
        score += 10
    return score


def _score_person(p: dict, alias_count: int) -> int:
    score = 0
    if p.get("current_firm_id"):
        score += 25
    if p.get("role") or p.get("title"):
        score += 20
    if p.get("bio"):
        score += 15
    if p.get("nationality"):
        score += 15
    if alias_count > 0:
        score += 15
    if p.get("sector") and p["sector"] != "architecture":
        score += 10
    return score


def _fetch_all(client, table, select, **filters):
    """Fetch all rows from a table, paginating through 1000-row pages."""
    rows = []
    offset = 0
    while True:
        q = client.table(table).select(select)
        for k, v in filters.items():
            q = q.eq(k, v)
        result = q.range(offset, offset + PAGE_SIZE - 1).execute()
        rows.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def compute_firms(client, dry_run: bool):
    logger.info("Computing firm quality scores...")

    # Load alias counts per entity
    aliases = _fetch_all(client, "entity_aliases", "entity_id", entity_type="firm")
    alias_counts: dict[str, int] = {}
    for a in aliases:
        alias_counts[a["entity_id"]] = alias_counts.get(a["entity_id"], 0) + 1

    # Load people counts per firm
    firm_people = _fetch_all(client, "firm_people", "firm_id")
    people_counts: dict[str, int] = {}
    for fp in firm_people:
        people_counts[fp["firm_id"]] = people_counts.get(fp["firm_id"], 0) + 1

    # Process firms in pages
    offset = 0
    stats = {"published": 0, "draft": 0, "hidden": 0}
    while True:
        firms = (
            client.table("firms")
            .select("id, display_name, country, city, website, founded_year, size_range, short_description")
            .is_("merged_into", "null")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        if not firms.data:
            break

        for f in firms.data:
            fid = f["id"]
            ac = alias_counts.get(fid, 0)
            pc = people_counts.get(fid, 0)
            score = _score_firm(f, ac, pc)

            if _is_irrelevant(f["display_name"]):
                status = "hidden"
            elif score >= 30:
                status = "published"
            else:
                status = "draft"

            stats[status] += 1

            if not dry_run:
                client.table("firms").update({
                    "quality_score": score,
                    "publish_status": status,
                }).eq("id", fid).execute()

        offset += PAGE_SIZE
        if len(firms.data) < PAGE_SIZE:
            break

    logger.info("Firms: published=%d, draft=%d, hidden=%d",
                stats["published"], stats["draft"], stats["hidden"])
    return stats


def compute_people(client, dry_run: bool):
    logger.info("Computing people quality scores...")

    aliases = _fetch_all(client, "entity_aliases", "entity_id", entity_type="person")
    alias_counts: dict[str, int] = {}
    for a in aliases:
        alias_counts[a["entity_id"]] = alias_counts.get(a["entity_id"], 0) + 1

    offset = 0
    stats = {"published": 0, "draft": 0, "hidden": 0}
    while True:
        people = (
            client.table("people")
            .select("id, display_name, role, title, sector, nationality, bio, current_firm_id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        if not people.data:
            break

        for p in people.data:
            pid = p["id"]
            ac = alias_counts.get(pid, 0)
            score = _score_person(p, ac)

            if score >= 30:
                status = "published"
            else:
                status = "draft"

            stats[status] += 1

            if not dry_run:
                client.table("people").update({
                    "quality_score": score,
                    "publish_status": status,
                }).eq("id", pid).execute()

        offset += PAGE_SIZE
        if len(people.data) < PAGE_SIZE:
            break

    logger.info("People: published=%d, draft=%d, hidden=%d",
                stats["published"], stats["draft"], stats["hidden"])
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Compute but don't write")
    args = parser.parse_args()

    client = get_client()
    firm_stats = compute_firms(client, args.dry_run)
    people_stats = compute_people(client, args.dry_run)

    mode = "DRY RUN" if args.dry_run else "APPLIED"
    print(f"\n  Quality scores computed ({mode}):")
    print(f"    Firms:  {firm_stats}")
    print(f"    People: {people_stats}")


if __name__ == "__main__":
    main()
