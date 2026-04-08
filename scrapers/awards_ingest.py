"""Awards ingestion — loads structured award data and creates relationships.

Ingests Pritzker Prize, RIBA Royal Gold Medal, and AIA Gold Medal data.
Creates/resolves people, firms, awards, and links them together.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/awards_ingest.py
"""

import json
import logging
import sys

sys.path.insert(0, ".")

from scrapers.shared.db import get_client, upsert_firm, upsert_person, upsert_alias
from scrapers.shared.normalize import normalize_name, generate_slug, generate_aliases

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Award definitions
AWARDS = {
    "pritzker": {
        "file": "/tmp/pritzker_laureates.json",
        "award_name": "Pritzker Architecture Prize",
        "organization": "The Hyatt Foundation",
        "prestige": "1",
    },
    "riba": {
        "file": "/tmp/riba_gold_medal.json",
        "award_name": "RIBA Royal Gold Medal",
        "organization": "Royal Institute of British Architects",
        "prestige": "1",
    },
    "aia": {
        "file": "/tmp/aia_gold_medal.json",
        "award_name": "AIA Gold Medal",
        "organization": "American Institute of Architects",
        "prestige": "1",
    },
}

# Country code mapping for common nationalities
COUNTRY_CODES = {
    "united states": "US", "united kingdom": "UK", "japan": "JP",
    "france": "FR", "germany": "DE", "italy": "IT", "spain": "ES",
    "brazil": "BR", "china": "CN", "india": "IN", "mexico": "MX",
    "australia": "AU", "canada": "CA", "switzerland": "CH",
    "netherlands": "NL", "denmark": "DK", "norway": "NO",
    "sweden": "SE", "finland": "FI", "portugal": "PT",
    "ireland": "IE", "chile": "CL", "colombia": "CO",
    "iraq": "IQ", "egypt": "EG", "bangladesh": "BD",
    "burkina faso": "BF", "ghana": "GH", "morocco": "MA",
    "south africa": "ZA", "tanzania": "TZ", "lebanon": "LB",
}


def _get_country_code(nationality: str) -> str | None:
    """Convert nationality text to 2-letter country code."""
    if not nationality:
        return None
    lower = nationality.lower().strip()
    # Handle dual nationalities — use the first one
    if "/" in lower:
        lower = lower.split("/")[0].strip()
    return COUNTRY_CODES.get(lower, nationality[:2].upper() if len(nationality) >= 2 else None)


def _resolve_or_create_person(client, name: str, nationality: str) -> str | None:
    """Find or create a person. Returns entity ID."""
    normalized = normalize_name(name)
    slug = generate_slug(name)
    country = _get_country_code(nationality)

    # Try exact match first
    existing = (
        client.table("people")
        .select("id")
        .eq("canonical_name", normalized)
        .limit(1)
        .execute()
    )
    if existing.data:
        # Update nationality if missing
        if country:
            client.table("people").update({"nationality": country}).eq("id", existing.data[0]["id"]).is_("nationality", "null").execute()
        return existing.data[0]["id"]

    # Try alias match
    alias_match = (
        client.table("entity_aliases")
        .select("entity_id")
        .eq("entity_type", "person")
        .eq("alias_normalized", normalized)
        .limit(1)
        .execute()
    )
    if alias_match.data:
        return alias_match.data[0]["entity_id"]

    # Create new person
    row = upsert_person({
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": "architecture",
        "nationality": country,
        "role": "Architect",
    })
    if row:
        pid = row["id"]
        for alias in generate_aliases(name):
            upsert_alias(pid, "person", alias, normalize_name(alias))
        return pid
    return None


def _resolve_or_create_firm(client, name: str) -> str | None:
    """Find or create a firm. Returns entity ID."""
    normalized = normalize_name(name)
    slug = generate_slug(name)

    # Try exact match
    existing = (
        client.table("firms")
        .select("id")
        .eq("canonical_name", normalized)
        .is_("merged_into", "null")
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    # Try alias match
    alias_match = (
        client.table("entity_aliases")
        .select("entity_id")
        .eq("entity_type", "firm")
        .eq("alias_normalized", normalized)
        .limit(1)
        .execute()
    )
    if alias_match.data:
        return alias_match.data[0]["entity_id"]

    # Create new firm
    row = upsert_firm({
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": "architecture",
    })
    if row:
        fid = row["id"]
        for alias in generate_aliases(name):
            upsert_alias(fid, "firm", alias, normalize_name(alias))
        return fid
    return None


def _ensure_award(client, award_name: str, organization: str, year: int,
                  prestige: str) -> str | None:
    """Find or create an award record. Returns award ID."""
    slug = generate_slug(f"{award_name} {year}")

    existing = (
        client.table("awards")
        .select("id")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    result = client.table("awards").upsert({
        "slug": slug,
        "award_name": award_name,
        "organization": organization,
        "year": year,
        "prestige": prestige,
    }, on_conflict="slug").execute()

    return result.data[0]["id"] if result.data else None


def _link_award_recipient(client, award_id: str, person_id: str,
                          firm_id: str | None, year: int) -> None:
    """Create award_recipient link (idempotent)."""
    client.table("award_recipients").upsert({
        "award_id": award_id,
        "person_id": person_id,
        "firm_id": firm_id,
        "year": year,
    }, on_conflict="award_id,firm_id,person_id,year").execute()


def _link_person_firm(client, person_id: str, firm_id: str, role: str) -> None:
    """Create firm_people link and set current_firm_id (idempotent)."""
    # Check if link exists
    existing = (
        client.table("firm_people")
        .select("id")
        .eq("firm_id", firm_id)
        .eq("person_id", person_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        client.table("firm_people").upsert({
            "firm_id": firm_id,
            "person_id": person_id,
            "role": role,
            "is_current": True,
        }, on_conflict="firm_id,person_id").execute()

    # Set current_firm_id on the person
    client.table("people").update({
        "current_firm_id": firm_id,
    }).eq("id", person_id).is_("current_firm_id", "null").execute()


def ingest_award_source(client, award_key: str, config: dict) -> dict:
    """Ingest one award source. Returns stats."""
    stats = {"people_created": 0, "people_linked": 0, "firms_created": 0,
             "awards_created": 0, "recipients_linked": 0, "skipped": 0}

    try:
        data = json.load(open(config["file"]))
    except FileNotFoundError:
        logger.error("File not found: %s", config["file"])
        return stats

    logger.info("Ingesting %s (%d entries)", config["award_name"], len(data))

    for entry in data:
        year = entry["year"]
        person_name = entry["person_name"]
        firm_name = entry.get("firm_name")
        nationality = entry.get("nationality", "")

        # Skip entries that are clearly not a person (e.g., "City of Barcelona")
        if not person_name or person_name.startswith("City of"):
            stats["skipped"] += 1
            continue

        # Resolve/create person
        person_id = _resolve_or_create_person(client, person_name, nationality)
        if not person_id:
            logger.warning("Failed to resolve person: %s", person_name)
            stats["skipped"] += 1
            continue

        # Resolve/create firm if provided
        firm_id = None
        if firm_name:
            firm_id = _resolve_or_create_firm(client, firm_name)
            if firm_id:
                _link_person_firm(client, person_id, firm_id, "Principal")
                stats["people_linked"] += 1

        # Ensure award record exists
        award_id = _ensure_award(
            client, config["award_name"], config["organization"],
            year, config["prestige"],
        )
        if not award_id:
            logger.warning("Failed to create award for year %d", year)
            continue

        stats["awards_created"] += 1

        # Link recipient
        _link_award_recipient(client, award_id, person_id, firm_id, year)
        stats["recipients_linked"] += 1

    return stats


def run() -> int:
    client = get_client()
    total_recipients = 0

    for key, config in AWARDS.items():
        stats = ingest_award_source(client, key, config)
        logger.info(
            "%s: %d recipients linked, %d people→firm links, %d skipped",
            config["award_name"],
            stats["recipients_linked"],
            stats["people_linked"],
            stats["skipped"],
        )
        total_recipients += stats["recipients_linked"]

    logger.info("Awards ingestion complete: %d total recipients", total_recipients)
    return total_recipients


if __name__ == "__main__":
    run()
