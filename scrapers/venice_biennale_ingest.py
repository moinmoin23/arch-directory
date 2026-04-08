"""Venice Biennale Architecture ingestion — creates relationships from structured data.

Ingests directors, Golden Lion winners, and pavilion architects.
Creates/resolves people, firms, awards, and links them together.
Focuses on strengthening existing records (nationality, firm links).

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/venice_biennale_ingest.py
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

COUNTRY_CODES = {
    "united states": "US", "united kingdom": "UK", "japan": "JP",
    "france": "FR", "germany": "DE", "italy": "IT", "spain": "ES",
    "brazil": "BR", "china": "CN", "india": "IN", "mexico": "MX",
    "australia": "AU", "canada": "CA", "switzerland": "CH",
    "netherlands": "NL", "denmark": "DK", "norway": "NO",
    "sweden": "SE", "finland": "FI", "portugal": "PT",
    "ireland": "IE", "chile": "CL", "colombia": "CO",
    "ghana": "GH", "lebanon": "LB", "bahrain": "BH",
    "south africa": "ZA", "nigeria": "NG", "scotland": "UK",
    "korea": "KR", "south korea": "KR", "taiwan": "TW",
    "croatia": "HR", "slovenia": "SI", "austria": "AT",
    "belgium": "BE", "poland": "PL", "czech republic": "CZ",
    "greece": "GR", "turkey": "TR", "argentina": "AR",
    "peru": "PE", "venezuela": "VE", "uruguay": "UY",
    "israel": "IL", "new zealand": "NZ", "singapore": "SG",
    "malaysia": "MY", "indonesia": "ID", "philippines": "PH",
    "thailand": "TH", "vietnam": "VN", "egypt": "EG",
    "morocco": "MA", "kenya": "KE", "tanzania": "TZ",
    "united arab emirates": "AE", "saudi arabia": "SA",
    "qatar": "QA", "kuwait": "KW", "iraq": "IQ",
    "burkina faso": "BF", "senegal": "SN", "ethiopia": "ET",
}

DATA_FILE = "/tmp/venice_biennale.json"


def _get_country_code(nationality: str) -> str | None:
    if not nationality:
        return None
    lower = nationality.lower().strip()
    if "/" in lower:
        lower = lower.split("/")[0].strip()
    return COUNTRY_CODES.get(lower)


def _resolve_person(client, name: str, nationality: str | None = None,
                    firm_name: str | None = None, role: str | None = None) -> dict:
    """Resolve or create a person. Returns stats dict."""
    stats = {"created": False, "nationality_filled": False, "firm_linked": False}
    normalized = normalize_name(name)
    slug = generate_slug(name)
    country = _get_country_code(nationality) if nationality else None

    # Try exact match
    existing = client.table("people").select(
        "id, nationality, current_firm_id, role"
    ).eq("canonical_name", normalized).limit(1).execute()

    if not existing.data:
        # Try alias
        alias = client.table("entity_aliases").select("entity_id").eq(
            "entity_type", "person"
        ).eq("alias_normalized", normalized).limit(1).execute()
        if alias.data:
            existing = client.table("people").select(
                "id, nationality, current_firm_id, role"
            ).eq("id", alias.data[0]["entity_id"]).limit(1).execute()

    if existing.data:
        pid = existing.data[0]["id"]
        updates = {}
        # Fill nationality if missing
        if country and not existing.data[0].get("nationality"):
            updates["nationality"] = country
            stats["nationality_filled"] = True
        # Fill role if missing
        if role and not existing.data[0].get("role"):
            updates["role"] = role
        if updates:
            client.table("people").update(updates).eq("id", pid).execute()
    else:
        # Create new
        row = upsert_person({
            "slug": slug,
            "display_name": name,
            "canonical_name": normalized,
            "sector": "architecture",
            "nationality": country,
            "role": role or "Architect",
        })
        if not row:
            return {"person_id": None, **stats}
        pid = row["id"]
        stats["created"] = True
        for alias in generate_aliases(name):
            upsert_alias(pid, "person", alias, normalize_name(alias))

    # Link to firm if provided
    if firm_name:
        firm_id = _resolve_firm(client, firm_name)
        if firm_id:
            _link_person_firm(client, pid, firm_id, role or "Principal")
            stats["firm_linked"] = True

    stats["person_id"] = pid
    return stats


def _resolve_firm(client, name: str) -> str | None:
    normalized = normalize_name(name)
    slug = generate_slug(name)

    existing = client.table("firms").select("id").eq(
        "canonical_name", normalized
    ).is_("merged_into", "null").limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]

    alias = client.table("entity_aliases").select("entity_id").eq(
        "entity_type", "firm"
    ).eq("alias_normalized", normalized).limit(1).execute()
    if alias.data:
        return alias.data[0]["entity_id"]

    row = upsert_firm({
        "slug": slug,
        "display_name": name,
        "canonical_name": normalized,
        "sector": "architecture",
    })
    if row:
        fid = row["id"]
        for alias_text in generate_aliases(name):
            upsert_alias(fid, "firm", alias_text, normalize_name(alias_text))
        return fid
    return None


def _link_person_firm(client, person_id: str, firm_id: str, role: str):
    existing = client.table("firm_people").select("id").eq(
        "firm_id", firm_id
    ).eq("person_id", person_id).limit(1).execute()
    if not existing.data:
        client.table("firm_people").upsert({
            "firm_id": firm_id,
            "person_id": person_id,
            "role": role,
            "is_current": True,
        }, on_conflict="firm_id,person_id").execute()
    # Set current_firm_id if not set
    client.table("people").update({
        "current_firm_id": firm_id,
    }).eq("id", person_id).is_("current_firm_id", "null").execute()


def _ensure_award(client, award_name: str, year: int) -> str | None:
    slug = generate_slug(f"{award_name} {year}")
    existing = client.table("awards").select("id").eq("slug", slug).limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]
    result = client.table("awards").upsert({
        "slug": slug,
        "award_name": award_name,
        "organization": "Venice Biennale",
        "year": year,
        "prestige": "1",
    }, on_conflict="slug").execute()
    return result.data[0]["id"] if result.data else None


def _link_recipient(client, award_id: str, person_id: str,
                    firm_id: str | None, year: int):
    client.table("award_recipients").upsert({
        "award_id": award_id,
        "person_id": person_id,
        "firm_id": firm_id,
        "year": year,
    }, on_conflict="award_id,firm_id,person_id,year").execute()


def run() -> int:
    client = get_client()
    data = json.load(open(DATA_FILE))
    editions = data.get("editions", data) if isinstance(data, dict) else data

    totals = {
        "people_created": 0, "people_updated": 0,
        "nationality_filled": 0, "firm_linked": 0,
        "awards_created": 0, "recipients_linked": 0,
    }

    for ed in editions:
        year = ed["year"]
        logger.info("Processing edition %d: %s", year, ed.get("title", ""))

        # Process director(s)
        directors = ed.get("director", [])
        if isinstance(directors, dict):
            directors = [directors]
        for d in directors:
            if not d.get("name"):
                continue
            stats = _resolve_person(
                client, d["name"], d.get("nationality"),
                d.get("firm"), "Curator/Director"
            )
            if stats.get("person_id"):
                award_id = _ensure_award(client, "Venice Biennale Director", year)
                if award_id:
                    _link_recipient(client, award_id, stats["person_id"], None, year)
                    totals["recipients_linked"] += 1
                    totals["awards_created"] += 1
            if stats.get("created"):
                totals["people_created"] += 1
            else:
                totals["people_updated"] += 1
            if stats.get("nationality_filled"):
                totals["nationality_filled"] += 1
            if stats.get("firm_linked"):
                totals["firm_linked"] += 1

        # Process Golden Lion Lifetime Achievement
        for p in ed.get("golden_lion_lifetime", []):
            if not p.get("name"):
                continue
            stats = _resolve_person(
                client, p["name"], p.get("nationality"),
                p.get("firm"), "Architect"
            )
            if stats.get("person_id"):
                award_id = _ensure_award(
                    client, "Golden Lion Lifetime Achievement", year
                )
                if award_id:
                    _link_recipient(client, award_id, stats["person_id"], None, year)
                    totals["recipients_linked"] += 1
                    totals["awards_created"] += 1
            if stats.get("created"):
                totals["people_created"] += 1
            else:
                totals["people_updated"] += 1
            if stats.get("nationality_filled"):
                totals["nationality_filled"] += 1
            if stats.get("firm_linked"):
                totals["firm_linked"] += 1

        # Process Golden Lion Best Participant
        for p in ed.get("golden_lion_best_participant", []):
            if not p.get("name"):
                continue
            stats = _resolve_person(
                client, p["name"], p.get("nationality"),
                p.get("firm"), "Architect"
            )
            if stats.get("person_id"):
                award_id = _ensure_award(
                    client, "Golden Lion Best Participant", year
                )
                if award_id:
                    _link_recipient(client, award_id, stats["person_id"], None, year)
                    totals["recipients_linked"] += 1
                    totals["awards_created"] += 1
            if stats.get("created"):
                totals["people_created"] += 1
            else:
                totals["people_updated"] += 1
            if stats.get("nationality_filled"):
                totals["nationality_filled"] += 1
            if stats.get("firm_linked"):
                totals["firm_linked"] += 1

        # Process Best National Pavilion
        bp = ed.get("golden_lion_best_pavilion", {})
        if isinstance(bp, dict) and bp.get("architect"):
            stats = _resolve_person(
                client, bp["architect"], bp.get("nationality"),
                bp.get("firm"), "Architect"
            )
            if stats.get("person_id"):
                award_id = _ensure_award(
                    client, "Golden Lion Best National Pavilion", year
                )
                if award_id:
                    _link_recipient(client, award_id, stats["person_id"], None, year)
                    totals["recipients_linked"] += 1
                    totals["awards_created"] += 1
            if stats.get("created"):
                totals["people_created"] += 1
            else:
                totals["people_updated"] += 1
            if stats.get("nationality_filled"):
                totals["nationality_filled"] += 1
            if stats.get("firm_linked"):
                totals["firm_linked"] += 1

        # Process notable participants
        for p in ed.get("notable_participants", []):
            if not p.get("name"):
                continue
            stats = _resolve_person(
                client, p["name"], p.get("nationality"),
                p.get("firm"), p.get("role", "Participant")
            )
            if stats.get("created"):
                totals["people_created"] += 1
            else:
                totals["people_updated"] += 1
            if stats.get("nationality_filled"):
                totals["nationality_filled"] += 1
            if stats.get("firm_linked"):
                totals["firm_linked"] += 1

    logger.info("Venice Biennale ingestion complete:")
    logger.info("  People created: %d", totals["people_created"])
    logger.info("  People updated: %d", totals["people_updated"])
    logger.info("  Nationality gaps filled: %d", totals["nationality_filled"])
    logger.info("  Firm links created: %d", totals["firm_linked"])
    logger.info("  Awards created: %d", totals["awards_created"])
    logger.info("  Recipients linked: %d", totals["recipients_linked"])
    return totals["people_created"] + totals["people_updated"]


if __name__ == "__main__":
    run()
