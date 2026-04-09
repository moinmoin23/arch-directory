"""OpenStreetMap enrichment — architect offices and geocoding.

Mode 'discover': Query Overpass API for office=architect nodes/ways globally.
Mode 'geocode': Geocode existing firms with city+country but no lat/lng.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/osm_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/osm_ingest.py --mode geocode --limit 200
"""

import argparse
import logging
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.db import get_client
from scrapers.shared.rate_limit import RateLimiter
from scrapers.shared.resolver import resolve_entity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TektonGraph/1.0 (https://tektongraph.com; data enrichment bot)"

# Overpass is slow — single request, no rate limit needed
# Nominatim: strict 1 req/sec
NOMINATIM_LIMITER = RateLimiter(min_delay=1.0)


# ── Country code mapping (OSM uses full names in addr:country) ─────

COUNTRY_TO_CODE: dict[str, str] = {
    "DE": "DE", "FR": "FR", "GB": "GB", "US": "US", "NL": "NL", "IT": "IT",
    "ES": "ES", "CH": "CH", "AT": "AT", "BE": "BE", "SE": "SE", "NO": "NO",
    "DK": "DK", "FI": "FI", "PT": "PT", "IE": "IE", "PL": "PL", "CZ": "CZ",
    "AU": "AU", "CA": "CA", "JP": "JP", "KR": "KR", "BR": "BR", "MX": "MX",
    "IN": "IN", "CN": "CN", "SG": "SG", "HK": "HK", "NZ": "NZ", "ZA": "ZA",
}


# ── Overpass discovery ─────────────────────────────────────────────


def discover_architect_offices(db) -> int:
    """Query Overpass for office=architect by region and reconcile/create firms."""
    # Split into regional bounding boxes to avoid timeouts
    REGIONS = [
        ("Europe", "35,-25,72,45"),
        ("North America", "15,-170,72,-50"),
        ("Asia", "-10,60,55,150"),
        ("Oceania", "-50,110,0,180"),
        ("South America", "-60,-90,15,-30"),
        ("Africa & Middle East", "-40,-20,40,60"),
    ]

    all_elements = []
    for name, bbox in REGIONS:
        query = f"""
        [out:json][timeout:90][bbox:{bbox}];
        (
          node["office"="architect"]["name"];
          way["office"="architect"]["name"];
        );
        out body center;
        """
        logger.info("Querying Overpass for %s...", name)
        try:
            resp = httpx.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])
            logger.info("  %s: %d elements", name, len(elements))
            all_elements.extend(elements)
            time.sleep(5)  # be polite to Overpass
        except Exception:
            logger.exception("Overpass query failed for %s", name)

    elements = all_elements
    logger.info("Overpass total: %d elements", len(elements))

    created = 0
    enriched = 0

    for elem in elements:
        tags = elem.get("tags", {})
        name = tags.get("name")
        if not name or len(name) < 3:
            continue

        # Extract location
        lat = elem.get("lat") or (elem.get("center", {}).get("lat"))
        lon = elem.get("lon") or (elem.get("center", {}).get("lon"))
        city = tags.get("addr:city")
        country = tags.get("addr:country", "")
        website = tags.get("website") or tags.get("contact:website")

        # Normalize country code
        country_code = country.upper() if len(country) == 2 else COUNTRY_TO_CODE.get(country.upper())

        hints: dict = {}
        if country_code:
            hints["country"] = country_code
        if city:
            hints["city"] = city
        if website:
            hints["website"] = website

        result = resolve_entity(
            name,
            "firm",
            sector="architecture",
            hints=hints or None,
        )

        if not result.entity_id:
            continue

        # Enrich with geo data
        update: dict = {}
        if lat is not None and lon is not None:
            update["latitude"] = lat
            update["longitude"] = lon
        if city:
            update["city"] = city
        if country_code:
            update["country"] = country_code
            update["country_code"] = country_code
        if website:
            update["website"] = website

        if update:
            # Only fill missing fields
            existing = db.table("firms").select(
                "latitude, longitude, city, country, website"
            ).eq("id", result.entity_id).limit(1).execute()

            if existing.data:
                row = existing.data[0]
                fill: dict = {}
                if lat is not None and row.get("latitude") is None:
                    fill["latitude"] = lat
                    fill["longitude"] = lon
                if city and not row.get("city"):
                    fill["city"] = city
                if country_code and not row.get("country"):
                    fill["country"] = country_code
                    fill["country_code"] = country_code
                if website and not row.get("website"):
                    fill["website"] = website

                if fill:
                    db.table("firms").update(fill).eq("id", result.entity_id).execute()
                    enriched += 1

        if result.match_type == "new":
            created += 1

    logger.info("OSM discover: %d new firms, %d enriched with geo/contact data", created, enriched)
    return created + enriched


# ── Nominatim geocoding ────────────────────────────────────────────


def geocode_existing_firms(db, limit: int = 200) -> int:
    """Geocode firms that have city+country but no coordinates."""
    firms = (
        db.table("firms")
        .select("id, display_name, city, country")
        .eq("publish_status", "published")
        .is_("latitude", "null")
        .not_.is_("city", "null")
        .not_.is_("country", "null")
        .limit(limit)
        .execute()
    )

    if not firms.data:
        logger.info("No firms to geocode")
        return 0

    logger.info("Geocoding %d firms...", len(firms.data))
    geocoded = 0

    for firm in firms.data:
        NOMINATIM_LIMITER.wait()

        query = f"{firm['city']}, {firm['country']}"
        try:
            resp = httpx.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()

            if results:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                db.table("firms").update({
                    "latitude": lat,
                    "longitude": lon,
                }).eq("id", firm["id"]).execute()
                geocoded += 1
                logger.debug("Geocoded: %s → (%.4f, %.4f)", firm["display_name"], lat, lon)
        except Exception:
            logger.debug("Geocoding failed for: %s", firm["display_name"])

    logger.info("Geocoded %d/%d firms", geocoded, len(firms.data))
    return geocoded


# ── Main ───────────────────────────────────────────────────────────


def run(mode: str = "all", limit: int = 200) -> int:
    db = get_client()
    total = 0

    if mode in ("all", "discover"):
        total += discover_architect_offices(db)

    if mode in ("all", "geocode"):
        total += geocode_existing_firms(db, limit=limit)

    return total


def main():
    parser = argparse.ArgumentParser(description="OSM architect office discovery + geocoding")
    parser.add_argument(
        "--mode",
        choices=["all", "discover", "geocode"],
        default="all",
        help="Run mode",
    )
    parser.add_argument("--limit", type=int, default=200, help="Max firms to geocode")
    args = parser.parse_args()
    count = run(args.mode, args.limit)
    print(f"\nOSM ingestion: {count} entities processed")


if __name__ == "__main__":
    main()
