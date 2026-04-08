"""GitHub computational design ingestion.

Discovers people and firms from GitHub repos tagged with relevant topics
(computational-design, parametric-design, digital-fabrication, etc.)
and from contributor graphs of key architecture/design tool repos.

Uses the GitHub REST API via httpx (with token from GH_TOKEN env var or
the gh CLI's stored token).

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/github_ingest.py
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/github_ingest.py --limit 50
"""

import argparse
import logging
import os
import subprocess
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

API_BASE = "https://api.github.com"
PER_PAGE = 30  # GitHub default/max for search is 30/100
RATE_LIMIT_S = 2.0  # be polite — search API has 30 req/min limit

# Topics to search for repos
TOPICS = [
    "computational-design",
    "parametric-design",
    "digital-fabrication",
    "grasshopper3d",
    "rhino3d",
    "generative-design",
]

# Key repos to scrape top contributors from
KEY_REPOS = [
    "compas-dev/compas",
    "ladybug-tools/ladybug",
    "ladybug-tools/honeybee",
    "BHoM/BHoM",
    "mcneel/rhino-developer-samples",
    "CadQuery/cadquery",
    "topoptpy/topopt",
]


def _get_token() -> str | None:
    """Get GitHub API token from env or gh CLI."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _make_client() -> httpx.Client:
    """Create an authenticated httpx client."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        logger.info("Using authenticated GitHub API access")
    else:
        logger.warning("No GitHub token found — rate limits will be very low")
    return httpx.Client(base_url=API_BASE, headers=headers, timeout=30.0)


def _resolve_or_create_person(name: str, github_url: str, bio: str | None,
                              location: str | None) -> str | None:
    """Find or create a person from GitHub profile data."""
    if not name or len(name.strip()) < 3:
        return None

    normalized = normalize_name(name)
    client = get_client()

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
        "sector": "technology",
        "role": "Computational Designer",
        "bio": bio[:500] if bio else None,
    })
    if not row:
        return None

    pid = row["id"]
    for a in generate_aliases(name):
        upsert_alias(pid, "person", a, normalize_name(a))
    add_to_enrichment_queue(pid, "person")
    return pid


def _process_user(http: httpx.Client, username: str, stats: dict) -> str | None:
    """Fetch a GitHub user profile and create/resolve a person."""
    try:
        resp = http.get(f"/users/{username}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        user = resp.json()
    except httpx.HTTPError:
        logger.warning("Failed to fetch user %s", username)
        stats["errors"] += 1
        return None

    # Skip bots and orgs
    if user.get("type") != "User":
        return None

    name = user.get("name") or username
    bio = user.get("bio")
    location = user.get("location")
    github_url = user.get("html_url", f"https://github.com/{username}")

    pid = _resolve_or_create_person(name, github_url, bio, location)
    if pid:
        stats["people"] += 1
    return pid


def _process_org(http: httpx.Client, org_login: str, stats: dict) -> str | None:
    """Fetch a GitHub org and resolve/create as a firm."""
    try:
        resp = http.get(f"/orgs/{org_login}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        org = resp.json()
    except httpx.HTTPError:
        return None

    name = org.get("name") or org_login
    description = org.get("description")
    blog = org.get("blog")
    location = org.get("location")

    result = resolve_entity(
        name, "firm",
        sector="technology",
        hints={
            "website": blog or f"https://github.com/{org_login}",
            "city": location,
        },
    )
    if result.entity_id and result.match_type == "new":
        stats["firms"] += 1
    return result.entity_id


def _ingest_topic_repos(http: httpx.Client, topic: str, max_pages: int,
                        seen_users: set, stats: dict) -> None:
    """Search repos by topic and process their owners."""
    cursor_key = f"github_topic_{topic}"
    page = 1

    # Resume from last page if we have a cursor
    last = get_cursor(cursor_key)
    if last and last.isdigit():
        page = int(last) + 1

    pages_fetched = 0

    while pages_fetched < max_pages:
        try:
            resp = http.get("/search/repositories", params={
                "q": f"topic:{topic} stars:>5",
                "sort": "stars",
                "order": "desc",
                "per_page": PER_PAGE,
                "page": page,
            })
            if resp.status_code == 403:
                logger.warning("Rate limited on topic %s page %d — stopping", topic, page)
                break
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            logger.exception("API error for topic %s", topic)
            stats["errors"] += 1
            break

        items = data.get("items", [])
        if not items:
            break

        for repo in items:
            owner = repo.get("owner", {})
            login = owner.get("login", "")
            owner_type = owner.get("type", "")

            if login in seen_users:
                continue
            seen_users.add(login)

            time.sleep(0.5)  # sub-request rate limit

            entity_id = None
            entity_etype = None
            if owner_type == "User":
                entity_id = _process_user(http, login, stats)
                entity_etype = "person"
            elif owner_type == "Organization":
                entity_id = _process_org(http, login, stats)
                entity_etype = "firm"

            # Store the repo as a source
            source_row = upsert_source({
                "title": repo.get("full_name", ""),
                "source_name": "GitHub",
                "url": repo.get("html_url", ""),
                "author": login,
                "source_type": "repository",
                "sector": "technology",
            })
            stats["sources"] += 1

            if entity_id and source_row and entity_etype:
                link_entity_source(entity_id, entity_etype, source_row["id"], "repository_owner")

        pages_fetched += 1
        page += 1
        update_cursor(cursor_key, str(page - 1), stats["sources"], "ok")
        time.sleep(RATE_LIMIT_S)

    logger.info("Topic '%s': processed %d pages", topic, pages_fetched)


def _ingest_repo_contributors(http: httpx.Client, repo: str,
                              seen_users: set, stats: dict) -> None:
    """Fetch top contributors for a key repo."""
    try:
        resp = http.get(f"/repos/{repo}/contributors", params={"per_page": 30})
        if resp.status_code != 200:
            logger.warning("Could not fetch contributors for %s: %d", repo, resp.status_code)
            return
        contributors = resp.json()
    except httpx.HTTPError:
        logger.warning("Failed to fetch contributors for %s", repo)
        return

    for contrib in contributors:
        login = contrib.get("login", "")
        if login in seen_users or contrib.get("type") != "User":
            continue
        seen_users.add(login)
        time.sleep(0.5)
        _process_user(http, login, stats)

    logger.info("Repo '%s': processed %d contributors", repo, len(contributors))


def run(limit: int = 3) -> int:
    """Run GitHub ingestion. limit = max pages per topic search."""
    stats = {"people": 0, "firms": 0, "sources": 0, "errors": 0}
    seen_users: set[str] = set()

    logger.info("Starting GitHub ingestion (topics: %d, key repos: %d, max_pages: %d)",
                len(TOPICS), len(KEY_REPOS), limit)

    http = _make_client()

    try:
        # Phase 1: Topic-based repo discovery
        for topic in TOPICS:
            logger.info("Searching topic: %s", topic)
            _ingest_topic_repos(http, topic, limit, seen_users, stats)

        # Phase 2: Key repo contributor graphs
        for repo in KEY_REPOS:
            logger.info("Fetching contributors: %s", repo)
            _ingest_repo_contributors(http, repo, seen_users, stats)
            time.sleep(RATE_LIMIT_S)

    finally:
        http.close()

    status = "ok" if stats["errors"] == 0 else "partial"
    total = stats["people"] + stats["firms"]
    update_cursor("github", str(total), total, status)

    logger.info(
        "GitHub ingestion complete: %d people, %d firms, %d sources, %d errors",
        stats["people"], stats["firms"], stats["sources"], stats["errors"],
    )
    return total


def main():
    parser = argparse.ArgumentParser(description="GitHub computational design ingestion")
    parser.add_argument("--limit", type=int, default=3,
                        help="Max pages per topic search (30 repos/page)")
    args = parser.parse_args()
    run(args.limit)


if __name__ == "__main__":
    main()
