"""Scrape award lists from Wikipedia via MediaWiki API.

Self-contained — no pre-generated JSON files needed. Covers award programs
not already in the existing awards_ingest.py (Pritzker/RIBA Gold/AIA Gold).

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/wikipedia_awards_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/wikipedia_awards_ingest.py --dry-run
"""

import argparse
import logging
import re
import sys
import time

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, ".")

from scrapers.shared.db import get_client
from scrapers.shared.normalize import generate_slug
from scrapers.shared.rate_limit import RateLimiter
from scrapers.shared.resolver import resolve_entity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RATE_LIMITER = RateLimiter(min_delay=1.0)

# ── Award program definitions ─────────────────────────────────────

AWARD_PROGRAMS = [
    {
        "name": "RIBA Stirling Prize",
        "organization": "Royal Institute of British Architects",
        "prestige": "1",
        "wikipedia_page": "Stirling_Prize",
        "sector": "architecture",
    },
    {
        "name": "Aga Khan Award for Architecture",
        "organization": "Aga Khan Development Network",
        "prestige": "1",
        "wikipedia_page": "Aga_Khan_Award_for_Architecture",
        "sector": "architecture",
    },
    {
        "name": "European Union Prize for Contemporary Architecture",
        "organization": "European Commission / Mies van der Rohe Foundation",
        "prestige": "1",
        "wikipedia_page": "European_Union_Prize_for_Contemporary_Architecture",
        "sector": "architecture",
    },
    {
        "name": "Driehaus Architecture Prize",
        "organization": "University of Notre Dame",
        "prestige": "1",
        "wikipedia_page": "Driehaus_Architecture_Prize",
        "sector": "architecture",
    },
    {
        "name": "Praemium Imperiale",
        "organization": "Japan Art Association",
        "prestige": "1",
        "wikipedia_page": "Praemium_Imperiale",
        "sector": "architecture",
    },
    {
        "name": "Wolf Prize in Arts",
        "organization": "Wolf Foundation",
        "prestige": "1",
        "wikipedia_page": "Wolf_Prize_in_Arts",
        "sector": "architecture",
    },
]


# ── Wikipedia fetching ─────────────────────────────────────────────


def fetch_wikipedia_html(page_title: str) -> str | None:
    """Fetch the rendered HTML of a Wikipedia page via the MediaWiki API."""
    RATE_LIMITER.wait()
    try:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "parse",
                "page": page_title,
                "prop": "text",
                "format": "json",
                "formatversion": "2",
            },
            headers={"User-Agent": "TektonGraph/1.0 (https://tektongraph.com; directory@tektongraph.com) python-httpx"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("parse", {}).get("text", "")
    except Exception:
        logger.exception("Failed to fetch Wikipedia page: %s", page_title)
        return None


def extract_table_rows(html: str) -> list[list[str]]:
    """Extract all table rows from HTML, returning cell text per row."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table in soup.find_all("table", class_="wikitable"):
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
    return rows


def extract_year(text: str) -> int | None:
    """Extract a 4-digit year from text."""
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if match:
        return int(match.group(1))
    return None


def clean_name(text: str) -> str:
    """Clean a name extracted from Wikipedia — remove refs, brackets, etc."""
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = text.strip(" ,;")
    return text


# ── Award processing ──────────────────────────────────────────────


def process_award_program(db, program: dict, dry_run: bool) -> int:
    """Process a single award program from Wikipedia."""
    html = fetch_wikipedia_html(program["wikipedia_page"])
    if not html:
        return 0

    rows = extract_table_rows(html)
    if not rows:
        logger.warning("No table rows found for %s", program["name"])
        return 0

    logger.info("Found %d table rows for %s", len(rows), program["name"])
    count = 0

    for row in rows:
        if len(row) < 2:
            continue

        # Try to extract year and recipient from the row
        year = None
        recipient_name = None

        for cell in row:
            if not year:
                year = extract_year(cell)
            if not recipient_name and len(cell) > 2 and not cell.isdigit():
                # Skip cells that are just years or short labels
                cleaned = clean_name(cell)
                if cleaned and len(cleaned) > 2 and not cleaned.isdigit():
                    recipient_name = cleaned

        if not recipient_name or not year:
            continue

        # Skip header-like rows
        lower = recipient_name.lower()
        if any(kw in lower for kw in ["year", "winner", "architect", "laureate", "recipient", "name"]):
            continue

        if dry_run:
            logger.info("DRY RUN: %s %d — %s", program["name"], year, recipient_name)
            count += 1
            continue

        # Determine if this is a firm or person (heuristic: firms have certain keywords)
        is_firm = any(kw in recipient_name.lower() for kw in [
            "architects", "studio", "associates", "partners", "group",
            "office", "practice", "atelier", "workshop",
        ])

        entity_type = "firm" if is_firm else "person"
        result = resolve_entity(
            recipient_name,
            entity_type,
            sector=program["sector"],
        )

        if not result.entity_id:
            continue

        # Create/upsert award
        award_slug = generate_slug(f"{program['name']}-{year}")
        try:
            award_result = db.table("awards").upsert(
                {
                    "slug": award_slug,
                    "award_name": program["name"],
                    "organization": program["organization"],
                    "year": year,
                    "prestige": program["prestige"],
                },
                on_conflict="slug",
            ).execute()

            if award_result.data:
                award_id = award_result.data[0]["id"]
                recipient_data: dict = {
                    "award_id": award_id,
                    "year": year,
                }
                if entity_type == "firm":
                    recipient_data["firm_id"] = result.entity_id
                else:
                    recipient_data["person_id"] = result.entity_id

                db.table("award_recipients").upsert(
                    recipient_data,
                    on_conflict="award_id,firm_id,person_id,year",
                ).execute()
                count += 1
                logger.info("Award: %s %d → %s (%s)", program["name"], year, recipient_name, entity_type)
        except Exception:
            logger.debug("Failed to upsert award for %s %d", program["name"], year)

    return count


# ── Main ──────────────────────────────────────────────────────────


def run(dry_run: bool = False) -> int:
    db = get_client()
    total = 0

    for program in AWARD_PROGRAMS:
        logger.info("Processing: %s", program["name"])
        count = process_award_program(db, program, dry_run)
        total += count
        logger.info("%s: %d award records", program["name"], count)

    return total


def main():
    parser = argparse.ArgumentParser(description="Wikipedia awards scraper")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    count = run(args.dry_run)
    print(f"\nWikipedia awards: {count} records processed")


if __name__ == "__main__":
    main()
