"""RSS feed ingestion — polls curated feeds across architecture, design, and technology.

Extracts articles as sources. Tries to match firm/lab names mentioned in titles
against existing entities in the database.

Usage:
    python scrapers/rss_ingest.py          # standalone
    python scrapers/pipeline.py --sources rss  # via pipeline
"""

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from scrapers.shared.cursors import get_cursor, update_cursor
from scrapers.shared.db import add_to_enrichment_queue, get_client, upsert_source

logger = logging.getLogger(__name__)

# ── Feed registry ───────────────────────────────────────────────────
# Each feed: (url, source_name, sector)
FEEDS: list[tuple[str, str, str]] = [
    # Architecture
    (
        "https://feeds.feedburner.com/Archdaily",
        "ArchDaily",
        "architecture",
    ),
    (
        "https://www.dezeen.com/feed/",
        "Dezeen",
        "architecture",
    ),
    # Design
    (
        "https://www.designboom.com/feed/",
        "Designboom",
        "design",
    ),
    (
        "https://www.itsnicethat.com/rss",
        "Its Nice That",
        "design",
    ),
    # Technology
    (
        "https://www.technologyreview.com/feed/",
        "MIT Technology Review",
        "technology",
    ),
    (
        "https://www.wired.com/feed/category/design/latest/rss",
        "Wired Design",
        "technology",
    ),
]


def _parse_published(entry: dict) -> str | None:
    """Extract ISO timestamp from a feed entry, or None."""
    sp = entry.get("published_parsed") or entry.get("updated_parsed")
    if sp:
        try:
            return datetime.fromtimestamp(mktime(sp), tz=timezone.utc).isoformat()
        except (OverflowError, ValueError, OSError):
            pass
    return None


def _load_known_entities() -> dict[str, str]:
    """Load all firm canonical_names from DB for title matching.

    Returns {normalized_name: entity_id}.
    """
    client = get_client()
    firms = client.table("firms").select("id, canonical_name").is_(
        "merged_into", "null"
    ).execute()
    lookup: dict[str, str] = {}
    for f in firms.data:
        lookup[f["canonical_name"]] = f["id"]
    return lookup


def _match_firm_in_title(title: str, known: dict[str, str]) -> str | None:
    """Check if any known firm name appears in the title (simple substring).

    Returns entity_id if found, else None.
    """
    title_lower = title.lower()
    for canonical, entity_id in known.items():
        # Only match multi-word names (avoid false positives on short names)
        if len(canonical) >= 5 and canonical in title_lower:
            return entity_id
    return None


def _ingest_feed(
    url: str,
    source_name: str,
    sector: str,
    known_entities: dict[str, str],
) -> int:
    """Ingest a single RSS feed. Returns count of new/updated sources."""
    cursor_key = f"rss_{source_name.lower().replace(' ', '_')}"
    last_cursor = get_cursor(cursor_key)

    logger.info("Fetching feed: %s", source_name)
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        logger.warning(
            "Feed error for %s: %s", source_name, feed.bozo_exception
        )
        update_cursor(cursor_key, last_cursor or "", 0, "error",
                       [str(feed.bozo_exception)])
        return 0

    count = 0
    newest_id: str | None = None
    errors: list[str] = []

    for entry in feed.entries:
        entry_id = entry.get("id") or entry.get("link", "")

        # Skip entries we've already processed (cursor-based)
        if last_cursor and entry_id <= last_cursor:
            continue

        link = entry.get("link")
        if not link:
            continue

        title = entry.get("title", "").strip()
        if not title:
            continue

        # Track newest entry for cursor
        if newest_id is None:
            newest_id = entry_id

        published = _parse_published(entry)
        author = entry.get("author", "").strip() or None

        # Upsert the source article
        source_data = {
            "title": title[:500],
            "source_name": source_name,
            "url": link,
            "published_at": published,
            "author": author,
            "source_type": "rss",
            "sector": sector,
        }
        result = upsert_source(source_data)
        if result:
            count += 1
        else:
            errors.append(f"Failed to upsert: {link}")
            continue

        # Try to match a known firm in the title — if found, ensure
        # it's in the enrichment queue (strong signal = name in headline)
        matched_id = _match_firm_in_title(title, known_entities)
        if matched_id:
            logger.debug("Title match: '%s' → %s", title[:60], matched_id)
            add_to_enrichment_queue(matched_id, "firm")

    # Update cursor to newest entry
    final_cursor = newest_id or last_cursor or ""
    status = "ok" if not errors else "partial"
    update_cursor(cursor_key, final_cursor, count, status,
                   errors[:10] if errors else None)

    logger.info(
        "Feed %s: %d new sources (%d errors)", source_name, count, len(errors)
    )
    return count


def run() -> int:
    """Run RSS ingestion across all feeds. Returns total source count."""
    logger.info("Starting RSS ingestion (%d feeds)", len(FEEDS))

    known = _load_known_entities()
    logger.info("Loaded %d known entities for title matching", len(known))

    total = 0
    for url, source_name, sector in FEEDS:
        try:
            count = _ingest_feed(url, source_name, sector, known)
            total += count
        except Exception:
            logger.exception("Feed failed: %s", source_name)

    logger.info("RSS ingestion complete: %d total sources", total)
    return total


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    run()
