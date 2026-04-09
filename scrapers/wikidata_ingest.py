"""Wikidata enrichment — reconciles existing entities and discovers new ones.

Uses SPARQL queries against https://query.wikidata.org/ to fetch structured
data about architects, architecture firms, awards, education, and projects.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/wikidata_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/wikidata_ingest.py --mode reconcile
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/wikidata_ingest.py --mode discover --limit 500
"""

import argparse
import logging
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.db import (
    get_client,
    upsert_education,
    upsert_project,
    link_project_entity,
    upsert_entity_relationship,
)
from scrapers.shared.normalize import generate_slug, normalize_name
from scrapers.shared.rate_limit import RateLimiter
from scrapers.shared.resolver import resolve_entity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "TektonGraph/1.0 (https://tektongraph.com; data enrichment bot)"
RATE_LIMITER = RateLimiter(min_delay=2.0)

# ── SPARQL helpers ─────────────────────────────────────────────────


def sparql_query(query: str) -> list[dict]:
    """Execute a SPARQL query and return results as list of dicts."""
    RATE_LIMITER.wait()
    try:
        resp = httpx.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except Exception:
        logger.exception("SPARQL query failed")
        return []


def val(binding: dict, key: str) -> str | None:
    """Extract a value from a SPARQL binding."""
    if key in binding:
        return binding[key].get("value")
    return None


def qid(binding: dict, key: str) -> str | None:
    """Extract a Wikidata QID from a URI binding."""
    uri = val(binding, key)
    if uri and "/entity/" in uri:
        return uri.split("/entity/")[-1]
    return None


def year_from_date(binding: dict, key: str) -> int | None:
    """Extract year from an xsd:dateTime binding."""
    v = val(binding, key)
    if v:
        try:
            return int(v[:4])
        except (ValueError, IndexError):
            pass
    return None


# ── Reconciliation: enrich existing entities ───────────────────────


def reconcile_firms(db):
    """Match existing published firms to Wikidata and enrich them."""
    firms = (
        db.table("firms")
        .select("id, display_name, country, wikidata_id")
        .eq("publish_status", "published")
        .is_("merged_into", "null")
        .is_("wikidata_id", "null")
        .limit(1000)
        .execute()
    )

    if not firms.data:
        logger.info("No firms to reconcile")
        return 0

    logger.info("Reconciling %d firms against Wikidata...", len(firms.data))
    matched = 0

    for firm in firms.data:
        name = firm["display_name"]
        country = firm.get("country") or ""

        # Search for architecture firms matching this name
        query = f"""
        SELECT ?item ?itemLabel ?country ?countryLabel ?inception ?website ?coord WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q4830453 .
          ?item rdfs:label "{name.replace('"', '\\"')}"@en .
          OPTIONAL {{ ?item wdt:P17 ?country . }}
          OPTIONAL {{ ?item wdt:P571 ?inception . }}
          OPTIONAL {{ ?item wdt:P856 ?website . }}
          OPTIONAL {{ ?item wdt:P625 ?coord . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }} LIMIT 5
        """

        results = sparql_query(query)
        if not results:
            continue

        best = results[0]
        wid = qid(best, "item")
        if not wid:
            continue

        # Update firm with Wikidata data
        update: dict = {"wikidata_id": wid}
        inception = year_from_date(best, "inception")
        if inception and not firm.get("founded_year"):
            update["founded_year"] = inception
        website = val(best, "website")
        if website and not firm.get("website"):
            update["website"] = website
        coord = val(best, "coord")
        if coord and coord.startswith("Point("):
            try:
                parts = coord.replace("Point(", "").replace(")", "").split()
                update["longitude"] = float(parts[0])
                update["latitude"] = float(parts[1])
            except (ValueError, IndexError):
                pass

        db.table("firms").update(update).eq("id", firm["id"]).execute()
        matched += 1
        logger.info("Matched firm: '%s' → %s", name, wid)

    logger.info("Reconciled %d/%d firms", matched, len(firms.data))
    return matched


def reconcile_people(db):
    """Match existing published people to Wikidata and enrich them."""
    people = (
        db.table("people")
        .select("id, display_name, nationality, wikidata_id")
        .eq("publish_status", "published")
        .is_("wikidata_id", "null")
        .limit(1000)
        .execute()
    )

    if not people.data:
        logger.info("No people to reconcile")
        return 0

    logger.info("Reconciling %d people against Wikidata...", len(people.data))
    matched = 0

    for person in people.data:
        name = person["display_name"]

        query = f"""
        SELECT ?item ?itemLabel ?birthYear ?deathYear ?nationality ?nationalityLabel WHERE {{
          ?item wdt:P106 wd:Q42973 .
          ?item rdfs:label "{name.replace('"', '\\"')}"@en .
          OPTIONAL {{ ?item wdt:P569 ?birthDate . BIND(YEAR(?birthDate) AS ?birthYear) }}
          OPTIONAL {{ ?item wdt:P570 ?deathDate . BIND(YEAR(?deathDate) AS ?deathYear) }}
          OPTIONAL {{ ?item wdt:P27 ?nationality . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }} LIMIT 5
        """

        results = sparql_query(query)
        if not results:
            continue

        best = results[0]
        wid = qid(best, "item")
        if not wid:
            continue

        update: dict = {"wikidata_id": wid}
        birth = val(best, "birthYear")
        if birth:
            try:
                update["birth_year"] = int(float(birth))
            except ValueError:
                pass
        death = val(best, "deathYear")
        if death:
            try:
                update["death_year"] = int(float(death))
            except ValueError:
                pass
        nationality_label = val(best, "nationalityLabel")
        if nationality_label and not person.get("nationality"):
            update["nationality"] = nationality_label

        db.table("people").update(update).eq("id", person["id"]).execute()
        matched += 1

        # Fetch and store education, awards, employer for this person
        _enrich_person_details(db, person["id"], wid)

        logger.info("Matched person: '%s' → %s", name, wid)

    logger.info("Reconciled %d/%d people", matched, len(people.data))
    return matched


def _enrich_person_details(db, person_id: str, wikidata_id: str):
    """Fetch education, awards, and employer data for a matched person."""

    # Education (P69)
    edu_query = f"""
    SELECT ?inst ?instLabel ?degree ?degreeLabel ?field ?fieldLabel ?startYear ?endYear WHERE {{
      wd:{wikidata_id} wdt:P69 ?inst .
      OPTIONAL {{ wd:{wikidata_id} p:P69 ?stmt . ?stmt ps:P69 ?inst .
                  OPTIONAL {{ ?stmt pq:P512 ?degree . }}
                  OPTIONAL {{ ?stmt pq:P812 ?field . }}
                  OPTIONAL {{ ?stmt pq:P580 ?start . BIND(YEAR(?start) AS ?startYear) }}
                  OPTIONAL {{ ?stmt pq:P582 ?end . BIND(YEAR(?end) AS ?endYear) }}
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }} LIMIT 10
    """
    for row in sparql_query(edu_query):
        inst_label = val(row, "instLabel")
        if not inst_label:
            continue
        degree_label = val(row, "degreeLabel")
        field_label = val(row, "fieldLabel")
        start = val(row, "startYear")
        end = val(row, "endYear")

        upsert_education(
            person_id=person_id,
            institution_name=inst_label,
            degree=degree_label,
            field=field_label,
            start_year=int(float(start)) if start else None,
            end_year=int(float(end)) if end else None,
            source="wikidata",
        )

    # Awards (P166)
    award_query = f"""
    SELECT ?award ?awardLabel ?year WHERE {{
      wd:{wikidata_id} wdt:P166 ?award .
      OPTIONAL {{ wd:{wikidata_id} p:P166 ?stmt . ?stmt ps:P166 ?award .
                  OPTIONAL {{ ?stmt pq:P585 ?date . BIND(YEAR(?date) AS ?year) }}
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }} LIMIT 20
    """
    for row in sparql_query(award_query):
        award_label = val(row, "awardLabel")
        if not award_label:
            continue
        award_qid = qid(row, "award")
        year = val(row, "year")
        year_int = int(float(year)) if year else None

        # Create or find award
        slug = generate_slug(f"{award_label}-{year_int}" if year_int else award_label)
        try:
            result = db.table("awards").upsert(
                {
                    "slug": slug,
                    "award_name": award_label,
                    "year": year_int,
                    "prestige": "2",
                },
                on_conflict="slug",
            ).execute()
            if result.data:
                award_id = result.data[0]["id"]
                # Link person to award
                db.table("award_recipients").upsert(
                    {
                        "award_id": award_id,
                        "person_id": person_id,
                        "year": year_int,
                    },
                    on_conflict="award_id,firm_id,person_id,year",
                ).execute()
        except Exception:
            logger.debug("Failed to upsert award: %s", award_label)


# ── Discovery: find new architects not in DB ───────────────────────


def discover_architects(db, limit: int = 2000):
    """Discover notable architects from Wikidata not yet in the DB."""
    offset = 0
    page_size = 500
    total_created = 0

    while offset < limit:
        query = f"""
        SELECT ?item ?itemLabel ?birthYear ?deathYear ?nationalityLabel ?genderLabel WHERE {{
          ?item wdt:P106 wd:Q42973 .
          ?item wikibase:sitelinks ?sitelinks .
          FILTER(?sitelinks >= 5)
          OPTIONAL {{ ?item wdt:P569 ?birthDate . BIND(YEAR(?birthDate) AS ?birthYear) }}
          OPTIONAL {{ ?item wdt:P570 ?deathDate . BIND(YEAR(?deathDate) AS ?deathYear) }}
          OPTIONAL {{ ?item wdt:P27 ?nationality . }}
          OPTIONAL {{ ?item wdt:P21 ?gender . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        ORDER BY DESC(?sitelinks)
        LIMIT {page_size}
        OFFSET {offset}
        """

        results = sparql_query(query)
        if not results:
            break

        for row in results:
            wid = qid(row, "item")
            name = val(row, "itemLabel")
            if not wid or not name or name.startswith("Q"):
                continue

            # Skip if already in DB
            existing = (
                db.table("people")
                .select("id")
                .eq("wikidata_id", wid)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            nationality = val(row, "nationalityLabel")
            birth = val(row, "birthYear")
            death = val(row, "deathYear")

            result = resolve_entity(
                name,
                "person",
                sector="architecture",
                wikidata_id=wid,
                hints={"country": nationality} if nationality else None,
            )

            if result.entity_id and result.match_type == "new":
                # Fill additional fields
                update: dict = {}
                if birth:
                    try:
                        update["birth_year"] = int(float(birth))
                    except ValueError:
                        pass
                if death:
                    try:
                        update["death_year"] = int(float(death))
                    except ValueError:
                        pass
                if nationality:
                    update["nationality"] = nationality
                update["role"] = "Architect"

                if update:
                    db.table("people").update(update).eq("id", result.entity_id).execute()

                total_created += 1

            elif result.entity_id and result.match_type in ("exact", "alias", "trigram", "wikidata"):
                # Existing entity — just set wikidata_id if missing
                db.table("people").update(
                    {"wikidata_id": wid}
                ).eq("id", result.entity_id).is_("wikidata_id", "null").execute()

        logger.info("Discovered page offset=%d, created=%d so far", offset, total_created)
        offset += page_size

    logger.info("Discovery complete: %d new architects created", total_created)
    return total_created


def discover_firms(db, limit: int = 1000):
    """Discover notable architecture firms from Wikidata."""
    offset = 0
    page_size = 500
    total_created = 0

    while offset < limit:
        query = f"""
        SELECT ?item ?itemLabel ?countryLabel ?inception ?website ?coord WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q4830453 .
          ?item wikibase:sitelinks ?sitelinks .
          FILTER(?sitelinks >= 3)
          OPTIONAL {{ ?item wdt:P17 ?country . }}
          OPTIONAL {{ ?item wdt:P571 ?inception . }}
          OPTIONAL {{ ?item wdt:P856 ?website . }}
          OPTIONAL {{ ?item wdt:P625 ?coord . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        ORDER BY DESC(?sitelinks)
        LIMIT {page_size}
        OFFSET {offset}
        """

        results = sparql_query(query)
        if not results:
            break

        for row in results:
            wid = qid(row, "item")
            name = val(row, "itemLabel")
            if not wid or not name or name.startswith("Q"):
                continue

            existing = (
                db.table("firms")
                .select("id")
                .eq("wikidata_id", wid)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            country = val(row, "countryLabel")
            website = val(row, "website")
            inception = year_from_date(row, "inception")

            hints: dict = {}
            if country:
                hints["country"] = country
            if website:
                hints["website"] = website

            result = resolve_entity(
                name,
                "firm",
                sector="architecture",
                wikidata_id=wid,
                hints=hints or None,
            )

            if result.entity_id and result.match_type == "new":
                update: dict = {}
                if inception:
                    update["founded_year"] = inception
                coord = val(row, "coord")
                if coord and coord.startswith("Point("):
                    try:
                        parts = coord.replace("Point(", "").replace(")", "").split()
                        update["longitude"] = float(parts[0])
                        update["latitude"] = float(parts[1])
                    except (ValueError, IndexError):
                        pass
                if update:
                    db.table("firms").update(update).eq("id", result.entity_id).execute()
                total_created += 1

            elif result.entity_id and result.match_type in ("exact", "alias", "trigram", "wikidata"):
                db.table("firms").update(
                    {"wikidata_id": wid}
                ).eq("id", result.entity_id).is_("wikidata_id", "null").execute()

        logger.info("Discovered firms page offset=%d, created=%d so far", offset, total_created)
        offset += page_size

    logger.info("Firm discovery complete: %d new firms created", total_created)
    return total_created


# ── Main ───────────────────────────────────────────────────────────


def run(mode: str = "all", limit: int = 2000) -> int:
    """Run Wikidata ingestion. Returns total entities processed."""
    db = get_client()
    total = 0

    if mode in ("all", "reconcile"):
        total += reconcile_firms(db)
        total += reconcile_people(db)

    if mode in ("all", "discover"):
        total += discover_architects(db, limit=limit)
        total += discover_firms(db, limit=min(limit, 1000))

    return total


def main():
    parser = argparse.ArgumentParser(description="Wikidata enrichment")
    parser.add_argument(
        "--mode",
        choices=["all", "reconcile", "discover"],
        default="all",
        help="Run mode: reconcile existing, discover new, or both",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Max new entities to discover",
    )
    args = parser.parse_args()
    count = run(args.mode, args.limit)
    print(f"\nWikidata ingestion complete: {count} entities processed")


if __name__ == "__main__":
    main()
