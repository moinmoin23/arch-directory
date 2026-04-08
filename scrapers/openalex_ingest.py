"""OpenAlex ingestion — academic works across architecture, design & technology.

Queries OpenAlex for recent, well-cited works. Upserts institutions as firms,
authors as people, and publications as sources.

Usage:
    python scrapers/openalex_ingest.py                      # standalone
    python scrapers/pipeline.py --sources openalex           # via pipeline
"""

import logging
import time

import httpx

from scrapers.shared.cursors import get_cursor, update_cursor
from scrapers.shared.db import upsert_source
from scrapers.shared.resolver import resolve_entity

logger = logging.getLogger(__name__)

API_BASE = "https://api.openalex.org"
MAILTO = "directory@example.com"  # polite pool access
PER_PAGE = 50
MAX_PAGES = 3  # modest first run: ~150 works per topic
RATE_LIMIT_S = 1.0

# OpenAlex concept IDs / search terms for relevant topics
TOPIC_QUERIES = [
    "computational design",
    "digital fabrication",
    "sustainable architecture",
    "parametric design",
    "smart buildings",
    "biophilic design",
    "material science architecture",
    "urban design technology",
    "interaction design",
]

# Map OpenAlex concepts to our sectors
SECTOR_KEYWORDS = {
    "architecture": [
        "architecture", "building", "urban", "construction",
        "housing", "landscape",
    ],
    "design": [
        "design", "interaction", "graphic", "product", "material",
    ],
    "technology": [
        "computation", "digital", "fabrication", "smart", "robot",
        "algorithm", "machine learning", "artificial intelligence",
    ],
}

# Only ingest institutions whose name signals relevance to our directory.
# This prevents generic universities and medical centers from flooding the DB.
# Keywords in institution name that signal relevance.
# Substring match, case-insensitive.
_RELEVANT_INST_KEYWORDS = [
    "architect", "design", " art", "arts", "engineer", "technology",
    "polytech", "fabricat", "comput", "urban", "built environment",
    "construction", "material", "sustainability", "media lab",
    "creative", "planning", "landscape", "robot", "smart", "digital",
    "technical university", "institute of technology",
    "technische", "técnic", "politecnic", "politécnic",
]



def _is_relevant_institution(name: str) -> bool:
    """Cheap pre-filter: does the institution name suggest relevance?

    This is intentionally broad — it's a noise reducer, not a classifier.
    Phase 9 (LLM enrichment) handles proper relevance classification.
    """
    name_lower = name.lower()
    return any(kw in name_lower for kw in _RELEVANT_INST_KEYWORDS)


def _classify_sector(topics: list[str]) -> str:
    """Classify a work into a sector based on its topic keywords."""
    topic_text = " ".join(topics).lower()
    scores = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        scores[sector] = sum(1 for kw in keywords if kw in topic_text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "technology"


def _extract_topics(work: dict) -> list[str]:
    """Extract topic display names from an OpenAlex work."""
    topics = []
    for topic in work.get("topics", []):
        name = topic.get("display_name", "")
        if name:
            topics.append(name)
    # Fallback to concepts if no topics
    if not topics:
        for concept in work.get("concepts", []):
            if concept.get("level", 99) <= 2:
                name = concept.get("display_name", "")
                if name:
                    topics.append(name)
    return topics


def _ingest_topic(query: str, client: httpx.Client) -> int:
    """Query OpenAlex for a single topic. Returns entity count."""
    cursor_key = f"openalex_{query.replace(' ', '_')}"
    last_cursor = get_cursor(cursor_key)

    entity_count = 0
    errors: list[str] = []
    cursor = last_cursor or "*"
    pages_fetched = 0

    while pages_fetched < MAX_PAGES:
        params = {
            "search": query,
            "filter": "cited_by_count:>5,from_publication_date:2020-01-01",
            "per_page": PER_PAGE,
            "cursor": cursor,
            "sort": "cited_by_count:desc",
            "mailto": MAILTO,
        }

        try:
            resp = client.get(f"{API_BASE}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            logger.exception("OpenAlex API error for query '%s'", query)
            errors.append(f"HTTP error on page {pages_fetched}")
            break

        results = data.get("results", [])
        if not results:
            break

        next_cursor = data.get("meta", {}).get("next_cursor")

        for work in results:
            try:
                _process_work(work)
                entity_count += 1
            except Exception:
                logger.exception(
                    "Failed to process work: %s", work.get("id", "?")
                )
                errors.append(f"process error: {work.get('id', '?')}")

        pages_fetched += 1
        cursor = next_cursor

        if not next_cursor:
            break

        time.sleep(RATE_LIMIT_S)

    # Update cursor
    status = "ok" if not errors else "partial"
    update_cursor(cursor_key, cursor or "*", entity_count, status,
                   errors[:10] if errors else None)

    logger.info(
        "Topic '%s': %d entities, %d pages, %d errors",
        query, entity_count, pages_fetched, len(errors),
    )
    return entity_count


def _process_work(work: dict) -> None:
    """Process a single OpenAlex work: upsert source, institutions, authors."""
    title = work.get("title", "").strip()
    if not title:
        return

    # Determine the best URL for this work
    doi = work.get("doi") or ""
    openalex_id = work.get("id", "")
    url = doi if doi else openalex_id
    if not url:
        return

    year = work.get("publication_year")
    topics = _extract_topics(work)
    sector = _classify_sector(topics)

    # Upsert the publication as a source
    upsert_source({
        "title": title[:500],
        "source_name": "OpenAlex",
        "url": url,
        "published_at": f"{year}-01-01T00:00:00Z" if year else None,
        "author": _first_author_name(work),
        "source_type": "api",
        "sector": sector,
    })

    # Process institutions (upsert as firms)
    seen_institutions: set[str] = set()
    for authorship in work.get("authorships", []):
        for inst in authorship.get("institutions", []):
            inst_name = inst.get("display_name", "").strip()
            if not inst_name or inst_name in seen_institutions:
                continue
            seen_institutions.add(inst_name)

            country = inst.get("country_code", "")

            # Only ingest institutions relevant to architecture/design/tech
            if not _is_relevant_institution(inst_name):
                continue

            resolve_entity(
                inst_name,
                "firm",
                sector=sector,
                hints={"country": country} if country else None,
            )

    # Process authors — only those affiliated with a relevant institution
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        author_name = author.get("display_name", "").strip()
        if not author_name:
            continue

        # Only ingest authors who have at least one relevant institution
        institutions = authorship.get("institutions", [])
        has_relevant = any(
            _is_relevant_institution(i.get("display_name", ""))
            for i in institutions
        )
        if not has_relevant:
            continue

        resolve_entity(
            author_name,
            "person",
            sector=sector,
        )


def _first_author_name(work: dict) -> str | None:
    """Extract the first author's display name."""
    authorships = work.get("authorships", [])
    if authorships:
        author = authorships[0].get("author", {})
        return author.get("display_name")
    return None


def run() -> int:
    """Run OpenAlex ingestion across all topics. Returns total entity count."""
    logger.info(
        "Starting OpenAlex ingestion (%d topics, max %d pages each)",
        len(TOPIC_QUERIES), MAX_PAGES,
    )

    total = 0
    with httpx.Client(timeout=30.0) as client:
        for query in TOPIC_QUERIES:
            try:
                count = _ingest_topic(query, client)
                total += count
            except Exception:
                logger.exception("Topic failed: %s", query)

    logger.info("OpenAlex ingestion complete: %d total entities", total)
    return total


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    run()
