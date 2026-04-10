"""Firm image enrichment — extracts hero images from firm websites.

Strategy:
  1. Fetch firm homepage
  2. Extract og:image, twitter:image, and hero <img> tags
  3. Try to bump CDN resolution parameters (?width=800 → ?width=1600)
  4. Validate image: fetch HEAD, check content-type and size
  5. Save with photo credit if extractable

Resolution target: min 1200px wide, aim for 1600-2000px for sharp screen display.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/firm_images.py --dry-run --limit 5
    PYTHONPATH=. scrapers/.venv/bin/python scrapers/firm_images.py --limit 50
"""

import argparse
import logging
import re
import sys
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

import httpx

sys.path.insert(0, ".")

from scrapers.shared.db import get_client
from scrapers.shared.rate_limit import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FETCH_LIMITER = RateLimiter(min_delay=1.0)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MIN_WIDTH = 800  # minimum acceptable image width (for sharp cards at 1x-2x)
TARGET_WIDTH = 1600  # preferred width when bumping CDN params
MIN_BYTES = 40_000  # minimum file size (filters out thumbnails and tiny placeholders)
MAX_BYTES = 8_000_000  # maximum file size (8MB cap)


def bump_cdn_width(url: str, target: int = TARGET_WIDTH) -> str:
    """Bump width/w/size parameters in CDN URLs for higher resolution.

    Handles common patterns: ?width=800, ?w=1200, ?size=medium, etc.
    """
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        changed = False

        # Common width parameters
        for key in ("width", "w", "size"):
            if key in qs:
                try:
                    current = int(qs[key][0])
                    if current < target:
                        qs[key] = [str(target)]
                        changed = True
                except (ValueError, IndexError):
                    pass

        # Bump height proportionally if both present
        if "height" in qs and "width" in qs and changed:
            try:
                h = int(qs["height"][0])
                w = int(qs["width"][0])
                new_h = int(h * target / w) if w > 0 else h
                qs["height"] = [str(new_h)]
            except (ValueError, IndexError):
                pass

        # Remove quality caps that hurt sharpness
        if "quality" in qs:
            try:
                q = int(qs["quality"][0])
                if q < 85:
                    qs["quality"] = ["90"]
                    changed = True
            except (ValueError, IndexError):
                pass

        if not changed:
            return url

        new_query = urlencode(qs, doseq=True)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment,
        ))
    except Exception:
        return url


def validate_image(url: str) -> tuple[bool, int, str]:
    """Check an image URL is valid and of good quality.

    Returns (ok, size_bytes, reason).
    """
    # Skip obvious bad patterns
    lower_url = url.lower()
    # Get the filename part for pattern checks
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    filename = path.split("/")[-1]
    if any(filename.startswith(bad) for bad in ("logo.", "logo_", "logo-", "favicon", "placeholder")):
        return False, 0, "filename looks like logo/placeholder"
    if any(bad in filename for bad in ("sprite.", "icon-", "-icon.", "placeholder")):
        return False, 0, "filename looks like icon/placeholder"
    # Drupal-style thumbnail paths and WP thumbs directories
    if "/styles/" in path or "/thumbs/" in path or "_thumb" in filename or "-thumb." in filename:
        return False, 0, "thumbnail path"
    # Google Sites / other generic favicon patterns
    if "sitesv" in path or "/favicon" in path:
        return False, 0, "generic site favicon"
    # Small size hints in filename (e.g. -540x, -300x, _150)
    m = re.search(r"[-_](\d{2,3})x(\d{2,3})", filename)
    if m:
        w = int(m.group(1))
        if w < MIN_WIDTH:
            return False, 0, f"filename size {m.group(0)} too small"

    for verify in (True, False):  # retry with SSL verification disabled
        try:
            # HEAD first to get content-type and size cheaply
            resp = httpx.head(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
                follow_redirects=True,
                verify=verify,
            )
            if resp.status_code == 405 or resp.status_code == 403:
                # Some servers don't support HEAD — try GET with range
                resp = httpx.get(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Range": "bytes=0-1024",
                    },
                    timeout=10,
                    follow_redirects=True,
                    verify=verify,
                )

            if resp.status_code >= 400:
                if verify:
                    continue
                return False, 0, f"HTTP {resp.status_code}"

            content_type = resp.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ("image/jpeg", "image/png", "image/webp", "image/jpg", "image/avif")):
                return False, 0, f"not an image: {content_type}"

            # Content-length may be missing on HEAD
            size = int(resp.headers.get("content-length", 0))
            if size and size < MIN_BYTES:
                return False, size, f"too small ({size} bytes)"
            if size and size > MAX_BYTES:
                return False, size, f"too large ({size} bytes)"

            return True, size, "ok"
        except httpx.ConnectError as e:
            if verify:
                continue
            return False, 0, f"connect error: {str(e)[:80]}"
        except Exception as e:
            return False, 0, f"error: {str(e)[:80]}"

    return False, 0, "exhausted retries"


def extract_image_candidates(url: str) -> tuple[list[tuple[str, str]], str | None]:
    """Fetch a URL and extract image candidates with metadata.

    Returns ([(kind, url, credit)], credit_text).
    """
    FETCH_LIMITER.wait()

    html = None
    for verify in (True, False):
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
                verify=verify,
            )
            resp.raise_for_status()
            html = resp.text
            break
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if verify:
                continue
            return [], f"connect error: {str(e)[:100]}"
        except httpx.HTTPStatusError as e:
            return [], f"HTTP {e.response.status_code}"
        except Exception as e:
            return [], f"fetch error: {str(e)[:100]}"

    if html is None:
        return [], "no content"

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return [], "parse error"

    # Collect candidates with priority (lower number = higher priority)
    ranked: list[tuple[int, str, str]] = []

    def add(priority: int, kind: str, img_url: str):
        ranked.append((priority, kind, img_url))

    # Strategy 1 (priority 1): Images from srcset with explicit large size
    for img in soup.find_all("img")[:30]:
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            parts = srcset.split(",")
            max_w = 0
            max_url = None
            for p in parts:
                m = re.match(r"\s*(\S+)\s+(\d+)w", p.strip())
                if m:
                    w = int(m.group(2))
                    if w > max_w:
                        max_w = w
                        max_url = m.group(1)
            if max_url and max_w >= MIN_WIDTH:
                add(1, f"srcset {max_w}w", urljoin(url, max_url))

    # Strategy 2 (priority 2): Hero/banner <img> tags (by class)
    for img in soup.find_all("img")[:30]:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src or src.startswith("data:"):
            continue
        parent = img.parent
        parent_class = " ".join(parent.get("class", [])) if parent else ""
        img_class = " ".join(img.get("class", []))
        combined = (parent_class + " " + img_class).lower()
        if any(kw in combined for kw in ["hero", "banner", "cover", "splash", "featured"]):
            add(2, "hero img", bump_cdn_width(urljoin(url, src)))

    # Strategy 3 (priority 3): Images with explicit size hints in filename (≥ MIN_WIDTH)
    size_pattern = re.compile(r"[-_](\d{3,4})x(\d{3,4})")
    for img in soup.find_all("img")[:15]:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src or src.startswith("data:"):
            continue
        if any(bad in src.lower() for bad in ["logo", "favicon", "sprite", "social"]):
            continue
        m = size_pattern.search(src)
        if m:
            w = int(m.group(1))
            h = int(m.group(2))
            if w >= MIN_WIDTH and h >= 400:
                add(3, f"large img ({w}x{h})", urljoin(url, src))

    # Strategy 4 (priority 4): og:image (bumped) — reliable but typically share-optimized
    for prop in ("og:image:secure_url", "og:image", "og:image:url"):
        meta = soup.find("meta", property=prop)
        if meta and meta.get("content"):
            img_url = meta["content"]
            if img_url.startswith("http"):
                bumped = bump_cdn_width(img_url)
                if bumped != img_url:
                    add(4, "og:image bumped", bumped)
                add(5, "og:image", img_url)

    # Strategy 5 (priority 6): twitter:image
    for name in ("twitter:image", "twitter:image:src"):
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            img_url = meta["content"]
            if img_url.startswith("http"):
                add(6, "twitter:image", img_url)

    # Sort by priority, preserving order within
    ranked.sort(key=lambda x: x[0])
    candidates = [(kind, u) for _, kind, u in ranked]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kind, u in candidates:
        if u not in seen:
            seen.add(u)
            unique.append((kind, u))

    return unique, None


def extract_credit(url: str) -> str | None:
    """Try to extract photo credit from a page."""
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
    except Exception:
        return None

    # Meta tags
    for name in ("author", "photographer", "article:author"):
        meta = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if meta and meta.get("content"):
            val = meta["content"].strip()
            if val and 2 <= len(val) <= 150:
                return val

    # Look for figcaption or credit classes near hero
    for fig in soup.find_all("figcaption")[:5]:
        text = fig.get_text(strip=True)
        if text and any(kw in text.lower() for kw in ["photo", "credit", "courtesy", "©"]):
            return text[:150]

    return None


def pick_best_image(candidates: list[tuple[str, str]]) -> tuple[str, str] | None:
    """Validate candidates in order and return the first good one."""
    for kind, url in candidates:
        ok, size, reason = validate_image(url)
        if ok:
            logger.info("    ✓ %s: %s (%d bytes)", kind, url[:100], size)
            return kind, url
        else:
            logger.debug("    ✗ %s: %s (%s)", kind, url[:100], reason)
    return None


def process_firm(db, firm: dict, dry_run: bool) -> bool:
    """Extract and save a hero image for a firm."""
    name = firm["display_name"]
    website = firm.get("website")

    if not website:
        return False

    # Fix missing protocol
    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    logger.info("%s — %s", name, website)

    candidates, err = extract_image_candidates(website)
    if err:
        logger.info("  fetch failed: %s", err)
        return False

    if not candidates:
        logger.info("  no image candidates found")
        return False

    best = pick_best_image(candidates)
    if not best:
        logger.info("  no valid image passed checks")
        return False

    kind, image_url = best
    credit = extract_credit(website)

    if dry_run:
        logger.info("  DRY RUN would save: %s (credit=%s)", image_url[:100], credit)
        return True

    update = {"image_url": image_url}
    if credit:
        update["image_credit"] = credit

    db.table("firms").update(update).eq("id", firm["id"]).execute()
    logger.info("  SAVED: %s %s", kind, "(+ credit)" if credit else "")
    return True


def run(limit: int, dry_run: bool, offset: int = 0, sector: str | None = None):
    db = get_client()

    # Firms with website but no image, ordered by quality score
    query = (
        db.table("firms")
        .select("id, display_name, website, image_url, quality_score, sector")
        .eq("publish_status", "published")
        .is_("merged_into", "null")
        .is_("image_url", "null")
        .not_.is_("website", "null")
    )
    if sector:
        query = query.eq("sector", sector)
    firms = query.order("quality_score", desc=True).range(offset, offset + limit - 1).execute()

    targets = firms.data or []
    logger.info("Processing %d firms (dry_run=%s)", len(targets), dry_run)

    success = 0
    for firm in targets:
        try:
            if process_firm(db, firm, dry_run):
                success += 1
        except Exception:
            logger.exception("Failed on %s", firm["display_name"])

    logger.info("\nDone: %d / %d firms got images", success, len(targets))
    return success


def main():
    parser = argparse.ArgumentParser(description="Firm image enrichment from websites")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--sector", choices=["architecture", "design", "technology", "multidisciplinary"], default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.limit, args.dry_run, args.offset, args.sector)


if __name__ == "__main__":
    main()
