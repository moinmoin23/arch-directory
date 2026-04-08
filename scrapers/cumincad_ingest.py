"""CumInCAD-equivalent ingestion via OpenAlex venue-filtered queries.

Instead of scraping CumInCAD directly (behind verification wall), we query
OpenAlex for papers published in computational architecture venues:
eCAADe, ACADIA, CAADRIA, etc. This gives us the same researchers with
full metadata (authors, institutions, topics) via a public API.

Only creates people who have institutional affiliations matching our
relevance filter — no noise.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/cumincad_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/cumincad_ingest.py --limit 100
"""

import argparse
import logging
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.cursors import get_cursor, update_cursor
from scrapers.shared.db import (
    add_to_enrichment_queue,
    get_client,
    link_entity_source,
    upsert_alias,
    upsert_person,
    upsert_source,
)
from scrapers.shared.normalize import generate_aliases, generate_slug, normalize_name
from scrapers.shared.resolver import resolve_entity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

API_BASE = "https://api.openalex.org"
MAILTO = "directory@example.com"
PER_PAGE = 50
RATE_LIMIT_S = 1.0

# OpenAlex source IDs for computational architecture conference venues.
# These are the conferences indexed in CumInCAD.
VENUES = {
    "eCAADe": "S4393919075",       # ~4,090 works total
    "ACADIA": "S4393916958",       # ~2,101 works total
}

# Additional keyword searches scoped to architecture venues
# (catches papers from CAADRIA, SIGraDi, Fabricate, Rob|Arch
# which may not have dedicated source IDs in OpenAlex)
KEYWORD_SEARCHES = [
    "robotic fabrication architecture",
    "digital fabrication architecture conference",
    "computational design architecture CAADRIA",
    "biomaterial architecture design",
    "parametric architecture fabrication",
]


def _resolve_or_create_person(client, name: str, sector: str = "technology") -> str | None:
    """Find or create a person. Returns entity ID."""
    normalized = normalize_name(name)

    # Exact match
    existing = client.table("people").select("id").eq(
        "canonical_name", normalized
    ).limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]

    # Alias match
    alias = client.table("entity_aliases").select("entity_id").eq(
        "entity_type", "person"
    ).eq("alias_normalized", normalized).limit(1).execute()
    if alias.data:
        return alias.data[0]["entity_id"]

    # Create new
    slug = generate_slug(name)
    row = upsert_person({
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": sector,
        "role": "Researcher",
    })
    if not row:
        return None

    pid = row["id"]
    for a in generate_aliases(name):
        upsert_alias(pid, "person", a, normalize_name(a))
    add_to_enrichment_queue(pid, "person")
    return pid


def _resolve_institution(name: str, country: str | None, sector: str) -> str | None:
    """Resolve an institution via the shared resolver."""
    result = resolve_entity(
        name, "firm", sector=sector,
        hints={"country": country} if country else None,
    )
    return result.entity_id


def _link_person_firm(client, person_id: str, firm_id: str):
    """Create firm_people link and set current_firm_id."""
    existing = client.table("firm_people").select("id").eq(
        "firm_id", firm_id
    ).eq("person_id", person_id).limit(1).execute()
    if not existing.data:
        client.table("firm_people").upsert({
            "firm_id": firm_id,
            "person_id": person_id,
            "role": "Researcher",
            "is_current": True,
        }, on_conflict="firm_id,person_id").execute()
    client.table("people").update({
        "current_firm_id": firm_id,
    }).eq("id", person_id).is_("current_firm_id", "null").execute()


# Institution relevance filter (same as openalex_ingest.py)
_RELEVANT_INST_KEYWORDS = [
    "architect", "design", " art", "arts", "engineer", "technology",
    "polytech", "fabricat", "comput", "urban", "built environment",
    "construction", "material", "sustainability", "media lab",
    "creative", "planning", "landscape", "robot", "smart", "digital",
    "technical university", "institute of technology",
    "technische", "técnic", "politecnic", "politécnic",
]


def _is_relevant_institution(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in _RELEVANT_INST_KEYWORDS)


def _process_work(work: dict, db_client) -> dict:
    """Process a single OpenAlex work. Returns stats."""
    stats = {"source": 0, "people": 0, "firm_links": 0}

    title = work.get("title", "").strip()
    if not title:
        return stats

    doi = work.get("doi") or ""
    openalex_id = work.get("id", "")
    url = doi if doi else openalex_id
    if not url:
        return stats

    year = work.get("publication_year")

    # Upsert source
    source_row = upsert_source({
        "title": title[:500],
        "source_name": "CumInCAD/OpenAlex",
        "url": url,
        "published_at": f"{year}-01-01T00:00:00Z" if year else None,
        "author": _first_author(work),
        "source_type": "api",
        "sector": "technology",
    })
    source_id = source_row["id"] if source_row else None
    stats["source"] = 1

    # Process authors with relevant institutional affiliations
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        author_name = author.get("display_name", "").strip()
        if not author_name or len(author_name) < 4:
            continue

        institutions = authorship.get("institutions", [])
        relevant_inst = None
        for inst in institutions:
            inst_name = inst.get("display_name", "")
            if _is_relevant_institution(inst_name):
                relevant_inst = inst
                break

        # For CumInCAD venue papers, create the person even without a relevant
        # institution — they're publishing in a computational architecture
        # conference, so they're relevant by definition.
        pid = _resolve_or_create_person(db_client, author_name)
        if not pid:
            continue
        stats["people"] += 1

        if source_id:
            link_entity_source(pid, "person", source_id, "author")

        # Link to institution if relevant
        if relevant_inst:
            country = relevant_inst.get("country_code", "")
            firm_id = _resolve_institution(
                relevant_inst["display_name"], country, "technology"
            )
            if firm_id:
                _link_person_firm(db_client, pid, firm_id)
                stats["firm_links"] += 1
                if source_id:
                    link_entity_source(firm_id, "firm", source_id, "author_affiliation")

    return stats


def _first_author(work: dict) -> str | None:
    authorships = work.get("authorships", [])
    if authorships:
        return authorships[0].get("author", {}).get("display_name")
    return None


def _ingest_venue(venue_name: str, source_id: str, http_client: httpx.Client,
                  db_client, max_pages: int) -> dict:
    """Ingest papers from a specific OpenAlex venue."""
    cursor_key = f"cumincad_{venue_name.lower()}"
    last_cursor = get_cursor(cursor_key)

    stats = {"sources": 0, "people": 0, "firm_links": 0, "errors": 0}
    cursor = last_cursor or "*"
    pages = 0

    while pages < max_pages:
        params = {
            "filter": f"primary_location.source.id:https://openalex.org/{source_id},"
                      f"from_publication_date:2010-01-01",
            "per_page": PER_PAGE,
            "cursor": cursor,
            "sort": "cited_by_count:desc",
            "mailto": MAILTO,
        }

        try:
            resp = http_client.get(f"{API_BASE}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            logger.exception("API error for venue %s page %d", venue_name, pages)
            stats["errors"] += 1
            break

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            try:
                ws = _process_work(work, db_client)
                stats["sources"] += ws["source"]
                stats["people"] += ws["people"]
                stats["firm_links"] += ws["firm_links"]
            except Exception:
                logger.exception("Failed work: %s", work.get("id", "?"))
                stats["errors"] += 1

        pages += 1
        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(RATE_LIMIT_S)

    status = "ok" if stats["errors"] == 0 else "partial"
    update_cursor(cursor_key, cursor, stats["sources"], status)
    return stats


def _ingest_keywords(search: str, http_client: httpx.Client,
                     db_client, max_pages: int) -> dict:
    """Ingest papers from keyword search with architecture focus."""
    cursor_key = f"cumincad_kw_{search.replace(' ', '_')[:30]}"
    last_cursor = get_cursor(cursor_key)

    stats = {"sources": 0, "people": 0, "firm_links": 0, "errors": 0}
    cursor = last_cursor or "*"
    pages = 0

    while pages < max_pages:
        params = {
            "search": search,
            "filter": "cited_by_count:>3,from_publication_date:2015-01-01",
            "per_page": PER_PAGE,
            "cursor": cursor,
            "sort": "cited_by_count:desc",
            "mailto": MAILTO,
        }

        try:
            resp = http_client.get(f"{API_BASE}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            logger.exception("API error for search '%s'", search)
            stats["errors"] += 1
            break

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            try:
                ws = _process_work(work, db_client)
                stats["sources"] += ws["source"]
                stats["people"] += ws["people"]
                stats["firm_links"] += ws["firm_links"]
            except Exception:
                stats["errors"] += 1

        pages += 1
        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(RATE_LIMIT_S)

    status = "ok" if stats["errors"] == 0 else "partial"
    update_cursor(cursor_key, cursor, stats["sources"], status)
    return stats


def run(limit: int = 5) -> int:
    """Run CumInCAD ingestion. limit = max pages per venue/search."""
    db_client = get_client()
    total = 0

    logger.info("Starting CumInCAD ingestion (venues: %d, keywords: %d, max_pages: %d)",
                len(VENUES), len(KEYWORD_SEARCHES), limit)

    with httpx.Client(timeout=30.0) as http_client:
        # Phase 1: Venue-filtered queries (highest signal)
        for name, source_id in VENUES.items():
            logger.info("Ingesting venue: %s", name)
            stats = _ingest_venue(name, source_id, http_client, db_client, max_pages=limit)
            logger.info("  %s: %d sources, %d people, %d firm links, %d errors",
                        name, stats["sources"], stats["people"], stats["firm_links"], stats["errors"])
            total += stats["people"]

        # Phase 2: Keyword searches (broader but noisier)
        for search in KEYWORD_SEARCHES:
            logger.info("Ingesting keyword: %s", search[:40])
            stats = _ingest_keywords(search, http_client, db_client, max_pages=min(limit, 3))
            logger.info("  '%s': %d sources, %d people, %d firm links",
                        search[:30], stats["sources"], stats["people"], stats["firm_links"])
            total += stats["people"]

    logger.info("CumInCAD ingestion complete: %d total people processed", total)
    return total


def main():
    parser = argparse.ArgumentParser(description="CumInCAD ingestion via OpenAlex")
    parser.add_argument("--limit", type=int, default=5, help="Max pages per venue (50 works/page)")
    args = parser.parse_args()
    run(args.limit)


if __name__ == "__main__":
    main()
