"""Deep web research agent for entity enrichment.

Searches the web for each entity, extracts structured data, and writes
back to the database with confidence gating. Supports firms and people.

Features:
  - Photography credit extraction from image sources
  - Education extraction for people (institution, degree, field)
  - Confidence scoring: only writes data above threshold
  - Cross-reference against existing DB data

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --type firm --limit 20
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --type person --limit 20
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --dry-run --limit 5
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/deep_research.py --tier top --limit 50
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time

import httpx

sys.path.insert(0, ".")

from scrapers.shared.db import (
    get_client,
    upsert_tag,
    link_entity_tag,
    upsert_education,
)
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
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for result_div in soup.select(".result"):
            title_el = result_div.select_one(".result__title a, .result__a")
            snippet_el = result_div.select_one(".result__snippet")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
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

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception:
        return ""


# ── Image extraction with photography credits ────────────────────

def extract_image_with_credit(url: str) -> tuple[str | None, str | None]:
    """Extract image URL and photography credit from a page.

    Returns (image_url, credit_text). Checks og:image, twitter:image,
    then looks for photographer/credit info in nearby elements and meta tags.
    """
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

        img_url = None
        credit = None

        # Try og:image first (most reliable)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            candidate = og_image["content"]
            if candidate.startswith("http"):
                img_url = candidate

        # Try twitter:image
        if not img_url:
            tw_image = soup.find("meta", attrs={"name": "twitter:image"})
            if tw_image and tw_image.get("content"):
                candidate = tw_image["content"]
                if candidate.startswith("http"):
                    img_url = candidate

        if not img_url:
            return None, None

        # ── Extract photography credit ──

        # 1. Check meta tags for credit info
        for meta_name in [
            "author", "photographer", "dc.creator",
            "twitter:creator", "article:author",
        ]:
            meta = soup.find("meta", attrs={"name": meta_name}) or soup.find(
                "meta", attrs={"property": meta_name}
            )
            if meta and meta.get("content"):
                credit = meta["content"].strip()
                break

        # 2. Check for <figcaption> elements near images
        if not credit:
            for fig in soup.find_all("figcaption"):
                text = fig.get_text(strip=True)
                if _looks_like_credit(text):
                    credit = _clean_credit(text)
                    break

        # 3. Check for elements with credit-related classes/IDs
        if not credit:
            for selector in [
                "[class*='credit']", "[class*='photo-credit']",
                "[class*='photographer']", "[class*='caption']",
                "[class*='byline']", "[id*='credit']",
            ]:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(strip=True)
                    if _looks_like_credit(text) and len(text) < 200:
                        credit = _clean_credit(text)
                        break

        # 4. Look for copyright/photo patterns in page text
        if not credit:
            page_text = soup.get_text(separator=" ", strip=True)
            credit = _extract_credit_from_text(page_text)

        return img_url, credit
    except Exception:
        return None, None


def _looks_like_credit(text: str) -> bool:
    """Check if text looks like a photography credit."""
    if not text or len(text) > 200:
        return False
    lower = text.lower()
    credit_signals = [
        "photo", "photograph", "image", "credit", "courtesy",
        "\u00a9",  # ©
        "(c)", "copyright", "by ", "shot by", "captured by",
    ]
    return any(s in lower for s in credit_signals)


def _clean_credit(text: str) -> str:
    """Clean up a credit string."""
    # Remove common prefixes
    text = re.sub(
        r"^(photo|photograph|image|credit|courtesy)[:\s]*(of|by)?[:\s]*",
        "", text, flags=re.IGNORECASE,
    ).strip()
    # Remove HTML artifacts
    text = re.sub(r"\s+", " ", text).strip()
    # Cap length
    return text[:150] if text else ""


def _extract_credit_from_text(text: str) -> str | None:
    """Try to extract a photographer credit from page text."""
    patterns = [
        r"(?:[Pp]hoto(?:graph)?(?:y|s)?|[Ii]mage)\s*(?:by|:|\u00a9)\s*([A-Z][a-zA-Z\s\-\.&+]{2,50})",
        r"\u00a9\s*(?:\d{4}\s+)?([A-Z][a-zA-Z\s\-\.&+]{2,50}?)(?:\.|,|\n|All|$)",
        r"(?:courtesy\s+(?:of\s+)?|credit:\s*)([A-Z][a-zA-Z\s\-\.&+]{2,50}?)(?:\.|,|\n|$)",
        r"(?:shot\s+by|captured\s+by)\s+([A-Z][a-zA-Z\s\-\.&+]{2,50}?)(?:\.|,|\n|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            credit = m.group(1).strip()
            # Clean trailing punctuation/whitespace
            credit = re.sub(r"[\s.]+$", "", credit)
            if len(credit) >= 3:
                return credit[:150]
    return None


# ── Wikimedia Commons image lookup ─────────────────────────────────

def get_wikimedia_image(wikidata_id: str) -> tuple[str | None, str | None]:
    """Get the main image and its credit for a Wikidata entity.

    Returns (image_url, credit_text).
    """
    if not wikidata_id:
        return None, None
    try:
        resp = httpx.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetclaims",
                "entity": wikidata_id,
                "property": "P18",
                "format": "json",
            },
            headers={"User-Agent": "TektonGraph/1.0 (directory enrichment)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        claims = data.get("claims", {}).get("P18", [])
        if not claims:
            return None, None

        filename = claims[0]["mainsnak"]["datavalue"]["value"]
        filename_encoded = filename.replace(" ", "_")
        md5 = hashlib.md5(filename_encoded.encode()).hexdigest()
        img_url = f"https://upload.wikimedia.org/wikipedia/commons/{md5[0]}/{md5[0:2]}/{filename_encoded}"

        # Fetch credit from Wikimedia Commons API
        credit = _get_commons_credit(filename_encoded)
        return img_url, credit
    except Exception:
        pass
    return None, None


def _get_commons_credit(filename: str) -> str | None:
    """Fetch photographer/author credit from Wikimedia Commons."""
    try:
        resp = httpx.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "format": "json",
            },
            headers={"User-Agent": "TektonGraph/1.0 (directory enrichment)"},
            timeout=10,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            ii = page.get("imageinfo", [{}])
            if not ii:
                continue
            meta = ii[0].get("extmetadata", {})

            # Try Artist first, then Credit
            artist = meta.get("Artist", {}).get("value", "")
            credit = meta.get("Credit", {}).get("value", "")

            # Clean HTML from the value
            from bs4 import BeautifulSoup
            if artist:
                artist = BeautifulSoup(artist, "html.parser").get_text(strip=True)
                if artist and len(artist) < 150:
                    return artist
            if credit:
                credit = BeautifulSoup(credit, "html.parser").get_text(strip=True)
                if credit and len(credit) < 150:
                    return credit
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


# ── Education extraction ──────────────────────────────────────────

# Common architecture/design schools for validation
_KNOWN_SCHOOLS = [
    "AA", "Architectural Association", "MIT", "Harvard GSD", "Harvard",
    "Columbia GSAPP", "Columbia", "Yale", "Princeton", "Cornell", "UCLA",
    "SCI-Arc", "ETH Zurich", "ETH", "Bartlett", "UCL", "TU Delft",
    "Politecnico di Milano", "Cooper Union", "Pratt", "RISD",
    "RCA", "Royal College of Art", "Cranbrook", "IIT", "Illinois Institute",
    "University of Tokyo", "Tongji", "Tsinghua", "CEPT", "NUS",
    "University of Cambridge", "Oxford", "Stanford", "Berkeley",
    "University of Stuttgart", "University of Pennsylvania", "University of Michigan",
    "University of Virginia", "University of Oregon", "University of Minnesota",
    "University of Texas", "University of Southern California", "USC",
    "Georgia Tech", "Carnegie Mellon", "Parsons", "Rhode Island",
    "Glasgow School of Art", "Royal Danish Academy", "KTH",
    "Hochschule", "Bauhaus", "Technische Universit", "Polytechnic",
    "School of Architecture", "School of Design", "University of",
]

_DEGREE_PATTERNS = [
    r"\b(Ph\.?D|PhD|Doctor(?:ate)?)\b",
    r"\b(M\.?Arch|Master of Architecture)\b",
    r"\b(M\.?A\.?|Master of Arts)\b",
    r"\b(M\.?S\.?|Master of Science)\b",
    r"\b(M\.?Des\.?|Master of Design)\b",
    r"\b(MFA|Master of Fine Arts)\b",
    r"\b(MBA)\b",
    r"\b(B\.?Arch|Bachelor of Architecture)\b",
    r"\b(B\.?A\.?|Bachelor of Arts)\b",
    r"\b(B\.?S\.?|Bachelor of Science)\b",
    r"\b(B\.?Des\.?|Bachelor of Design)\b",
    r"\b(BFA|Bachelor of Fine Arts)\b",
    r"\b(Diploma|Dipl\.?Arch)\b",
]

_FIELD_KEYWORDS = [
    "architecture", "urban design", "urban planning", "landscape architecture",
    "interior design", "industrial design", "graphic design", "computational design",
    "structural engineering", "civil engineering", "art history",
    "fine arts", "digital media", "computer science", "mechanical engineering",
]


def extract_education(text: str, person_name: str) -> list[dict]:
    """Extract education records from web page text.

    Returns list of {institution_name, degree, field, year} dicts.
    Education extraction is inherently fuzzy — only return high-confidence matches.
    """
    education = []
    text_lower = text.lower()

    # Look for sentences mentioning education
    sentences = re.split(r"[.!?\n]", text)
    edu_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        if any(kw in sent_lower for kw in [
            "studied", "graduated", "degree", "educated",
            "bachelor", "master", "ph.d", "phd", "diploma",
            "university", "college", "school of", "institute",
            "alma mater",
        ]):
            edu_sentences.append(sent.strip())

    for sent in edu_sentences:
        # Find institution
        institution = None
        for school in _KNOWN_SCHOOLS:
            if school.lower() in sent.lower():
                # Try to get the full institution name from context
                # Look for "University of X" or "X University" patterns
                for pattern in [
                    rf"({re.escape(school)}[\w\s]*(?:University|Institute|School|College|Academy)[\w\s]*)",
                    rf"((?:University|Institute|School|College|Academy)[\w\s]*{re.escape(school)}[\w\s]*)",
                    rf"({re.escape(school)})",
                ]:
                    m = re.search(pattern, sent, re.IGNORECASE)
                    if m:
                        institution = m.group(1).strip()
                        # Clean up trailing words
                        institution = re.sub(r"\s+(in|at|from|where|and|he|she|they)\b.*$", "", institution, flags=re.IGNORECASE)
                        break
                if institution:
                    break

        if not institution:
            continue

        # Find degree
        degree = None
        for pattern in _DEGREE_PATTERNS:
            m = re.search(pattern, sent)
            if m:
                degree = m.group(1)
                break

        # Find field
        field = None
        for fw in _FIELD_KEYWORDS:
            if fw in sent.lower():
                field = fw.title()
                break

        # Find year (graduation year or period)
        year = None
        year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", sent)
        if year_match:
            year = int(year_match.group(1))

        # Only add if we haven't seen this institution
        if not any(e["institution_name"] == institution for e in education):
            education.append({
                "institution_name": institution,
                "degree": degree,
                "field": field,
                "end_year": year,
            })

    return education[:5]  # Max 5 education records


# ── Confidence scoring ────────────────────────────────────────────

def score_confidence(
    entity: dict,
    description: str | None,
    website: str | None,
    image_url: str | None,
    tags: list[str],
    entity_type: str,
) -> float:
    """Score overall confidence of extracted data (0.0 to 1.0).

    Higher = more confident the data is correct and useful.
    """
    score = 0.0
    max_score = 0.0

    name = entity.get("display_name", "")

    # Description quality
    max_score += 30
    if description:
        if len(description) >= 50:
            score += 20
        elif len(description) >= 30:
            score += 10
        # Bonus if description mentions the entity name
        if name.lower() in description.lower():
            score += 10

    # Website quality
    max_score += 20
    if website:
        score += 15
        # Bonus if domain relates to entity name
        name_slug = normalize_name(name).replace(" ", "")
        if name_slug in website.lower().replace("-", "").replace(".", ""):
            score += 5

    # Image quality
    max_score += 15
    if image_url:
        score += 10
        # Wikimedia images are more reliable
        if "wikimedia" in image_url or "wikipedia" in image_url:
            score += 5

    # Tags
    max_score += 15
    if tags:
        score += min(len(tags) * 3, 15)

    # Entity already has some data (cross-reference bonus)
    max_score += 20
    if entity.get("country"):
        score += 5
    if entity.get("sector"):
        score += 5
    if entity_type == "firm":
        if entity.get("founded_year"):
            score += 5
        if entity.get("city"):
            score += 5
    else:
        if entity.get("role"):
            score += 5
        if entity.get("nationality"):
            score += 5

    return score / max_score if max_score > 0 else 0.0


# ── Research logic ─────────────────────────────────────────────────


def research_firm(db, firm: dict, dry_run: bool, min_confidence: float = 0.3) -> bool:
    """Deep research a single firm. Returns True if enriched."""
    name = firm["display_name"]
    country = firm.get("country") or ""
    city = firm.get("city") or ""
    sector = firm.get("sector") or "architecture"

    logger.info("Researching firm: %s (%s)", name, country)

    # Build search queries based on sector
    sector_terms = {
        "architecture": "architecture firm",
        "design": "design studio",
        "technology": "technology lab",
        "multidisciplinary": "design practice",
    }
    term = sector_terms.get(sector, "architecture firm")

    queries = [
        f'"{name}" {term}',
        f'"{name}" {city} {country} architects',
    ]

    all_snippets = []
    found_website = None
    found_image = None
    image_credit = None

    for query in queries:
        results = web_search(query)
        for r in results:
            all_snippets.append(r["snippet"])

            # Try to find official website
            if not found_website and not firm.get("website"):
                url = r["url"]
                if name.lower().replace(" ", "") in url.lower().replace(" ", ""):
                    found_website = url

            # Try to extract image with credit from top result
            if not found_image and r["url"]:
                found_image, image_credit = extract_image_with_credit(r["url"])

        if results:
            break  # First successful query is enough

    if not all_snippets:
        logger.info("  No search results for %s", name)
        return False

    # Synthesize description from snippets
    combined = " ".join(all_snippets)
    description = _synthesize_description(name, combined, "firm")

    # Get logo from website domain
    logo_url = get_logo_url(firm.get("website") or found_website)

    # Try Wikimedia image if we have wikidata_id
    if not found_image and firm.get("wikidata_id"):
        found_image, image_credit = get_wikimedia_image(firm["wikidata_id"])

    # Extract tags from snippets
    tags = _extract_tags(combined, "firm")

    # Confidence gate
    confidence = score_confidence(
        firm, description, found_website, found_image, tags, "firm"
    )

    if confidence < min_confidence:
        logger.info("  Low confidence %.2f for %s, skipping", confidence, name)
        return False

    if dry_run:
        logger.info("  DRY RUN [conf=%.2f]: %s", confidence, (description or "")[:100])
        logger.info("  Website: %s, Logo: %s, Image: %s, Credit: %s, Tags: %s",
                     found_website, bool(logo_url), bool(found_image),
                     image_credit, tags)
        return True

    # Write to DB (additive only — never overwrite existing data)
    update: dict = {}
    if not firm.get("short_description") and description and len(description) >= 20:
        update["short_description"] = description
    if not firm.get("website") and found_website:
        update["website"] = found_website
    if not firm.get("logo_url") and logo_url:
        update["logo_url"] = logo_url
    if not firm.get("image_url") and found_image:
        update["image_url"] = found_image
    if not firm.get("image_credit") and image_credit:
        update["image_credit"] = image_credit

    if update:
        db.table("firms").update(update).eq("id", firm["id"]).execute()

    # Add tags
    for tag_name in tags:
        slug = normalize_name(tag_name)
        if len(slug) >= 2:
            tag_row = upsert_tag(tag_name, slug)
            if tag_row:
                link_entity_tag(firm["id"], "firm", tag_row["id"], source="web_research")

    logger.info("  Enriched [conf=%.2f]: desc=%d chars, web=%s, logo=%s, img=%s, credit=%s, tags=%d",
                confidence, len(description or ""), bool(found_website),
                bool(logo_url), bool(found_image), bool(image_credit), len(tags))
    return True


def research_person(db, person: dict, dry_run: bool, min_confidence: float = 0.3) -> bool:
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

    # Find image with credit
    found_image = None
    image_credit = None

    # Try Wikimedia first (reliable source with good credits)
    if person.get("wikidata_id"):
        found_image, image_credit = get_wikimedia_image(person["wikidata_id"])

    # Try og:image from search results
    if not found_image:
        for r in results[:2]:
            found_image, image_credit = extract_image_with_credit(r["url"])
            if found_image:
                break

    # Extract tags
    tags = _extract_tags(combined, "person")

    # Extract education from search result pages
    education_records = []
    for r in results[:2]:
        page_text = fetch_page_text(r["url"])
        if page_text:
            edu = extract_education(page_text, name)
            education_records.extend(edu)
    # Deduplicate by institution name
    seen_institutions = set()
    unique_education = []
    for edu in education_records:
        inst = edu["institution_name"].lower()
        if inst not in seen_institutions:
            seen_institutions.add(inst)
            unique_education.append(edu)

    # Confidence gate
    confidence = score_confidence(
        person, bio, None, found_image, tags, "person"
    )
    # Boost confidence if we found education
    if unique_education:
        confidence = min(confidence + 0.1, 1.0)

    if confidence < min_confidence:
        logger.info("  Low confidence %.2f for %s, skipping", confidence, name)
        return False

    if dry_run:
        logger.info("  DRY RUN [conf=%.2f] bio: %s", confidence, (bio or "")[:100])
        logger.info("  Image: %s, Credit: %s, Tags: %s, Education: %d records",
                     bool(found_image), image_credit, tags, len(unique_education))
        for edu in unique_education:
            logger.info("    %s — %s %s",
                         edu["institution_name"], edu.get("degree", ""), edu.get("field", ""))
        return True

    update: dict = {}
    if not person.get("bio") and bio and len(bio) >= 20:
        update["bio"] = bio
    if not person.get("image_url") and found_image:
        update["image_url"] = found_image
    if not person.get("image_credit") and image_credit:
        update["image_credit"] = image_credit

    if update:
        db.table("people").update(update).eq("id", person["id"]).execute()

    for tag_name in tags:
        slug = normalize_name(tag_name)
        if len(slug) >= 2:
            tag_row = upsert_tag(tag_name, slug)
            if tag_row:
                link_entity_tag(person["id"], "person", tag_row["id"], source="web_research")

    # Write education records
    for edu in unique_education:
        upsert_education(
            person_id=person["id"],
            institution_name=edu["institution_name"],
            degree=edu.get("degree"),
            field=edu.get("field"),
            end_year=edu.get("end_year"),
            source="web_research",
        )

    logger.info("  Enriched [conf=%.2f]: bio=%d chars, img=%s, credit=%s, tags=%d, edu=%d",
                confidence, len(bio or ""), bool(found_image),
                bool(image_credit), len(tags), len(unique_education))
    return True


# ── Text synthesis helpers ─────────────────────────────────────────

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
    return list(found)[:5]


def _synthesize_description(name: str, snippets_text: str, entity_type: str) -> str | None:
    """Create a clean description from search snippets."""
    sentences = re.split(r"[.!?]+", snippets_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

    name_lower = name.lower()
    name_parts = name_lower.split()

    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = 0

        if name_lower in sent_lower:
            score += 10
        elif any(part in sent_lower for part in name_parts if len(part) > 3):
            score += 5

        if entity_type == "firm":
            for kw in ["founded", "established", "architecture", "design", "studio",
                        "practice", "firm", "office", "based in"]:
                if kw in sent_lower:
                    score += 2
        else:
            for kw in ["architect", "designer", "known for", "born", "graduated",
                        "studied", "founded", "professor", "award", "prize"]:
                if kw in sent_lower:
                    score += 2

        if any(kw in sent_lower for kw in ["cookie", "privacy", "subscribe",
                                             "sign up", "click", "menu", "log in"]):
            score -= 20

        if len(sent) > 300:
            score -= 3

        if score > 0:
            scored.append((score, sent))

    if not scored:
        return None

    scored.sort(key=lambda x: -x[0])

    best = scored[0][1].strip()
    if not best.endswith("."):
        best += "."

    best = re.sub(r"\s+", " ", best)
    best = re.sub(r"^[^A-Z]*", "", best)

    if len(best) < 30:
        return None

    return best[:300]


# ── Entity selection by tier ──────────────────────────────────────

def select_entities(db, entity_type: str, tier: str, limit: int) -> list[dict]:
    """Select entities for enrichment based on tier.

    Tiers:
      top    — top entities by source count (deep research)
      mid    — entities with some data but gaps
      tail   — entities with minimal data
      all    — any entity missing key data
    """
    table = "firms" if entity_type == "firm" else "people"
    cols = (
        "id, display_name, sector, country, city, website, short_description, "
        "logo_url, image_url, image_credit, wikidata_id, quality_score"
        if entity_type == "firm"
        else "id, display_name, sector, role, nationality, bio, image_url, "
             "image_credit, wikidata_id, quality_score"
    )

    query = (
        db.table(table)
        .select(cols)
        .eq("publish_status", "published")
    )

    if entity_type == "firm":
        query = query.is_("merged_into", "null")

    if tier == "top":
        # Top entities: highest quality score, most likely to have web presence
        query = query.order("quality_score", desc=True).limit(limit * 2)
    elif tier == "mid":
        # Mid tier: have some data but missing key fields
        query = query.order("quality_score", desc=True).limit(limit * 3)
    elif tier == "tail":
        # Tail: minimal data, lower quality
        query = query.order("quality_score", desc=False).limit(limit * 2)
    else:  # "all"
        query = query.order("quality_score", desc=True).limit(limit * 2)

    result = query.execute()
    entities = result.data or []

    # Filter to entities that actually need enrichment
    if entity_type == "firm":
        targets = [
            e for e in entities
            if not e.get("short_description") or not e.get("website")
            or not e.get("image_url")
        ]
    else:
        targets = [
            e for e in entities
            if not e.get("bio") or not e.get("image_url")
        ]

    return targets[:limit]


# ── Main ───────────────────────────────────────────────────────────

def run(
    entity_type: str = "firm",
    limit: int = 20,
    dry_run: bool = False,
    tier: str = "all",
    min_confidence: float = 0.3,
) -> int:
    db = get_client()
    total = 0

    targets = select_entities(db, entity_type, tier, limit)
    logger.info(
        "Researching %d %ss (tier=%s, dry_run=%s, min_conf=%.2f)",
        len(targets), entity_type, tier, dry_run, min_confidence,
    )

    if entity_type == "firm":
        for entity in targets:
            if research_firm(db, entity, dry_run, min_confidence):
                total += 1
    else:
        for entity in targets:
            if research_person(db, entity, dry_run, min_confidence):
                total += 1

    logger.info("Research complete: %d/%d entities enriched", total, len(targets))
    return total


def main():
    parser = argparse.ArgumentParser(description="Deep web research enrichment")
    parser.add_argument("--type", choices=["firm", "person"], default="firm")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--tier", choices=["top", "mid", "tail", "all"], default="all",
        help="Entity tier: top (deep), mid (gaps), tail (minimal), all",
    )
    parser.add_argument(
        "--min-confidence", type=float, default=0.3,
        help="Minimum confidence threshold (0.0-1.0)",
    )
    args = parser.parse_args()
    count = run(args.type, args.limit, args.dry_run, args.tier, args.min_confidence)
    print(f"\nDeep research: {count} entities enriched")


if __name__ == "__main__":
    main()
