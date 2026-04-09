"""Deep web research agent for entity enrichment.

Searches the web for each entity, extracts structured data, and writes
back to the database with confidence gating. Supports firms and people.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --type firm --limit 20
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --type person --limit 20
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --dry-run --limit 5
"""

import argparse
import json
import logging
import os
import re
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.db import get_client, upsert_tag, link_entity_tag
from scrapers.shared.normalize import normalize_name
from scrapers.shared.rate_limit import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEARCH_LIMITER = RateLimiter(min_delay=2.0)

# ── Web search via DuckDuckGo HTML ────────────────────────────────

DDG_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return results as [{title, url, snippet}]."""
    SEARCH_LIMITER.wait()
    try:
        resp = httpx.post(
            DDG_URL,
            data={"q": query, "b": ""},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text

        results = []
        # Parse DuckDuckGo HTML results
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for result_div in soup.select(".result"):
            title_el = result_div.select_one(".result__title a, .result__a")
            snippet_el = result_div.select_one(".result__snippet")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            # DuckDuckGo wraps URLs in redirects
            if "uddg=" in href:
                from urllib.parse import unquote, parse_qs, urlparse
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                href = unquote(params.get("uddg", [href])[0])

            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            results.append({
                "title": title,
                "url": href,
                "snippet": snippet,
            })

            if len(results) >= max_results:
                break

        return results
    except Exception:
        logger.exception("Web search failed for: %s", query)
        return []


def fetch_page_text(url: str, max_chars: int = 5000) -> str:
    """Fetch a web page and extract main text content."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception:
        return ""


def extract_image_from_page(url: str) -> str | None:
    """Try to extract a relevant image (logo/photo) from a page."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try og:image first (most reliable)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            img_url = og_image["content"]
            if img_url.startswith("http"):
                return img_url

        # Try twitter:image
        tw_image = soup.find("meta", attrs={"name": "twitter:image"})
        if tw_image and tw_image.get("content"):
            img_url = tw_image["content"]
            if img_url.startswith("http"):
                return img_url

        return None
    except Exception:
        return None


# ── Wikimedia Commons image lookup ─────────────────────────────────

def get_wikimedia_image(wikidata_id: str) -> str | None:
    """Get the main image for a Wikidata entity via Wikimedia Commons."""
    if not wikidata_id:
        return None
    try:
        resp = httpx.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetclaims",
                "entity": wikidata_id,
                "property": "P18",  # image property
                "format": "json",
            },
            headers={"User-Agent": "TektonGraph/1.0 (directory enrichment)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        claims = data.get("claims", {}).get("P18", [])
        if claims:
            filename = claims[0]["mainsnak"]["datavalue"]["value"]
            # Convert filename to Wikimedia Commons URL
            filename = filename.replace(" ", "_")
            import hashlib
            md5 = hashlib.md5(filename.encode()).hexdigest()
            return f"https://upload.wikimedia.org/wikipedia/commons/{md5[0]}/{md5[0:2]}/{filename}"
    except Exception:
        pass
    return None


# ── Logo.dev for firm logos ────────────────────────────────────────

def get_logo_url(website: str) -> str | None:
    """Get a firm logo URL from Logo.dev based on domain."""
    if not website:
        return None
    try:
        from urllib.parse import urlparse
        domain = urlparse(website).netloc or website
        domain = domain.replace("www.", "")
        if domain:
            return f"https://img.logo.dev/{domain}?token=pk_anonymous&size=128"
    except Exception:
        pass
    return None


# ── Research logic ─────────────────────────────────────────────────


def research_firm(db, firm: dict, dry_run: bool) -> bool:
    """Deep research a single firm. Returns True if enriched."""
    name = firm["display_name"]
    country = firm.get("country") or ""
    city = firm.get("city") or ""

    logger.info("Researching firm: %s (%s)", name, country)

    # Search queries
    queries = [
        f'"{name}" architecture firm',
        f'"{name}" {city} {country} architects',
    ]

    all_snippets = []
    found_website = None
    found_image = None

    for query in queries:
        results = web_search(query)
        for r in results:
            all_snippets.append(r["snippet"])

            # Try to find official website
            if not found_website and not firm.get("website"):
                url = r["url"]
                if name.lower().replace(" ", "") in url.lower().replace(" ", ""):
                    found_website = url

            # Try to extract image from top result
            if not found_image and r["url"]:
                found_image = extract_image_from_page(r["url"])

        if results:
            break  # First successful query is enough

    if not all_snippets:
        logger.info("  No search results for %s", name)
        return False

    # Synthesize description from snippets
    combined = " ".join(all_snippets)
    description = _synthesize_description(name, combined, "firm")

    if not description or len(description) < 20:
        logger.info("  Could not synthesize description for %s", name)
        return False

    # Get logo from website domain
    logo_url = get_logo_url(firm.get("website") or found_website)

    # Try Wikimedia image if we have wikidata_id
    if not found_image and firm.get("wikidata_id"):
        found_image = get_wikimedia_image(firm["wikidata_id"])

    # Extract tags from snippets
    tags = _extract_tags(combined, "firm")

    if dry_run:
        logger.info("  DRY RUN: %s", description[:100])
        logger.info("  Website: %s, Logo: %s, Image: %s, Tags: %s",
                     found_website, bool(logo_url), bool(found_image), tags)
        return True

    # Write to DB (additive only)
    update: dict = {}
    if not firm.get("short_description") and description:
        update["short_description"] = description
    if not firm.get("website") and found_website:
        update["website"] = found_website
    if not firm.get("logo_url") and logo_url:
        update["logo_url"] = logo_url
    if not firm.get("image_url") and found_image:
        update["image_url"] = found_image

    if update:
        db.table("firms").update(update).eq("id", firm["id"]).execute()

    # Add tags
    for tag_name in tags:
        slug = normalize_name(tag_name)
        if len(slug) >= 2:
            tag_row = upsert_tag(tag_name, slug)
            if tag_row:
                link_entity_tag(firm["id"], "firm", tag_row["id"], source="web_research")

    logger.info("  Enriched: desc=%d chars, web=%s, logo=%s, img=%s, tags=%d",
                len(description), bool(found_website), bool(logo_url), bool(found_image), len(tags))
    return True


def research_person(db, person: dict, dry_run: bool) -> bool:
    """Deep research a single person. Returns True if enriched."""
    name = person["display_name"]
    nationality = person.get("nationality") or ""
    role = person.get("role") or "architect"

    logger.info("Researching person: %s (%s)", name, nationality)

    results = web_search(f'"{name}" {role} {nationality}')

    if not results:
        logger.info("  No search results for %s", name)
        return False

    all_snippets = [r["snippet"] for r in results]
    combined = " ".join(all_snippets)

    # Synthesize bio
    bio = _synthesize_description(name, combined, "person")

    # Find image
    found_image = None
    # Try Wikimedia first
    if person.get("wikidata_id"):
        found_image = get_wikimedia_image(person["wikidata_id"])

    # Try og:image from search results
    if not found_image:
        for r in results[:2]:
            found_image = extract_image_from_page(r["url"])
            if found_image:
                break

    # Extract tags
    tags = _extract_tags(combined, "person")

    if dry_run:
        logger.info("  DRY RUN bio: %s", (bio or "")[:100])
        logger.info("  Image: %s, Tags: %s", bool(found_image), tags)
        return True

    update: dict = {}
    if not person.get("bio") and bio and len(bio) >= 20:
        update["bio"] = bio
    if not person.get("image_url") and found_image:
        update["image_url"] = found_image

    if update:
        db.table("people").update(update).eq("id", person["id"]).execute()

    for tag_name in tags:
        slug = normalize_name(tag_name)
        if len(slug) >= 2:
            tag_row = upsert_tag(tag_name, slug)
            if tag_row:
                link_entity_tag(person["id"], "person", tag_row["id"], source="web_research")

    logger.info("  Enriched: bio=%d chars, img=%s, tags=%d",
                len(bio or ""), bool(found_image), len(tags))
    return True


# ── Text synthesis helpers ─────────────────────────────────────────

# Architecture/design keywords for tag extraction
_TAG_KEYWORDS = {
    "sustainable": "sustainable architecture",
    "parametric": "parametric design",
    "computational": "computational design",
    "digital fabrication": "digital fabrication",
    "robotic": "robotic fabrication",
    "residential": "residential architecture",
    "commercial": "commercial architecture",
    "museum": "museum design",
    "cultural": "cultural architecture",
    "urban design": "urban design",
    "landscape": "landscape architecture",
    "interior": "interior design",
    "high-rise": "high-rise",
    "skyscraper": "high-rise",
    "hospital": "healthcare architecture",
    "healthcare": "healthcare architecture",
    "education": "educational architecture",
    "university": "educational architecture",
    "housing": "housing",
    "social housing": "social housing",
    "adaptive reuse": "adaptive reuse",
    "renovation": "renovation",
    "restoration": "restoration",
    "heritage": "heritage architecture",
    "brutali": "brutalism",
    "minimali": "minimalism",
    "modernist": "modernism",
    "postmodern": "postmodernism",
    "deconstructiv": "deconstructivism",
    "timber": "timber construction",
    "concrete": "concrete architecture",
    "glass": "glass architecture",
    "steel": "steel construction",
    "3d print": "3D printing",
    "biophilic": "biophilic design",
    "net zero": "net zero",
    "carbon": "low carbon",
    "passive": "passive design",
    "mixed-use": "mixed-use",
    "master plan": "master planning",
    "civic": "civic architecture",
    "religious": "religious architecture",
    "church": "religious architecture",
    "mosque": "religious architecture",
    "sport": "sports architecture",
    "stadium": "sports architecture",
    "transport": "transportation design",
    "airport": "transportation design",
    "bridge": "bridge design",
    "pavilion": "pavilion design",
    "installation": "installation art",
    "workplace": "workplace design",
    "retail": "retail architecture",
    "hospitality": "hospitality design",
    "hotel": "hospitality design",
}


def _extract_tags(text: str, entity_type: str) -> list[str]:
    """Extract relevant tags from text based on keyword matching."""
    text_lower = text.lower()
    found = set()
    for keyword, tag in _TAG_KEYWORDS.items():
        if keyword in text_lower:
            found.add(tag)
    return list(found)[:5]  # Max 5 tags


def _synthesize_description(name: str, snippets_text: str, entity_type: str) -> str | None:
    """Create a clean description from search snippets.

    This is a simple extraction — takes the most informative sentence
    about the entity from the combined snippets.
    """
    # Split into sentences
    sentences = re.split(r"[.!?]+", snippets_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

    # Score sentences by relevance
    name_lower = name.lower()
    name_parts = name_lower.split()

    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = 0

        # Contains entity name
        if name_lower in sent_lower:
            score += 10
        elif any(part in sent_lower for part in name_parts if len(part) > 3):
            score += 5

        # Contains useful keywords
        if entity_type == "firm":
            for kw in ["founded", "established", "architecture", "design", "studio", "practice", "firm", "office", "based in"]:
                if kw in sent_lower:
                    score += 2
        else:
            for kw in ["architect", "designer", "known for", "born", "graduated", "studied", "founded", "professor", "award", "prize"]:
                if kw in sent_lower:
                    score += 2

        # Penalize sentences that look like navigation/UI text
        if any(kw in sent_lower for kw in ["cookie", "privacy", "subscribe", "sign up", "click", "menu", "log in"]):
            score -= 20

        # Penalize very long sentences
        if len(sent) > 300:
            score -= 3

        if score > 0:
            scored.append((score, sent))

    if not scored:
        return None

    scored.sort(key=lambda x: -x[0])

    # Take top 1-2 sentences
    best = scored[0][1].strip()
    if not best.endswith("."):
        best += "."

    # Clean up
    best = re.sub(r"\s+", " ", best)
    # Remove leading "..." or fragments
    best = re.sub(r"^[^A-Z]*", "", best)

    if len(best) < 30:
        return None

    return best[:300]  # Cap at 300 chars


# ── Main ───────────────────────────────────────────────────────────


def run(entity_type: str = "firm", limit: int = 20, dry_run: bool = False) -> int:
    db = get_client()
    total = 0

    if entity_type == "firm":
        # Get published firms missing descriptions, ordered by quality score
        firms = (
            db.table("firms")
            .select("id, display_name, sector, country, city, website, short_description, logo_url, image_url, wikidata_id, quality_score")
            .eq("publish_status", "published")
            .is_("merged_into", "null")
            .order("quality_score", desc=True)
            .limit(limit * 2)  # Over-fetch to filter
            .execute()
        )

        # Prioritize firms missing any key data
        targets = [
            f for f in firms.data
            if not f.get("short_description") or not f.get("website")
            or not f.get("logo_url") or not f.get("image_url")
        ]
        targets = targets[:limit]

        logger.info("Researching %d firms (dry_run=%s)", len(targets), dry_run)
        for firm in targets:
            if research_firm(db, firm, dry_run):
                total += 1

    elif entity_type == "person":
        # Get published people missing bios
        people = (
            db.table("people")
            .select("id, display_name, sector, role, nationality, bio, image_url, wikidata_id, quality_score")
            .eq("publish_status", "published")
            .is_("bio", "null")
            .order("quality_score", desc=True)
            .limit(limit)
            .execute()
        )

        logger.info("Researching %d people (dry_run=%s)", len(people.data), dry_run)
        for person in people.data:
            if research_person(db, person, dry_run):
                total += 1

    logger.info("Research complete: %d entities enriched", total)
    return total


def main():
    parser = argparse.ArgumentParser(description="Deep web research enrichment")
    parser.add_argument("--type", choices=["firm", "person"], default="firm")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    count = run(args.type, args.limit, args.dry_run)
    print(f"\nDeep research: {count} entities enriched")


if __name__ == "__main__":
    main()
