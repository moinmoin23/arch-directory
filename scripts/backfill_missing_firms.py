"""Backfill missing data for OMA, Herzog & de Meuron, and og:image for 3 other entities.

One-time script. Safe to re-run — uses upserts and update-by-id.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/backfill_missing_firms.py
    PYTHONPATH=. scrapers/.venv/bin/python scripts/backfill_missing_firms.py --dry-run
"""

import argparse
import logging
import sys

sys.path.insert(0, ".")

from scrapers.shared.db import get_client, upsert_tag, link_entity_tag
from scrapers.shared.normalize import normalize_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Firm updates ─────────────────────────────────────────────────

FIRM_UPDATES = [
    {
        "id": "b58cdc9b-efaa-4b70-bd2e-0689f9ef8947",
        "fields": {
            "website": "https://www.oma.com",
            "short_description": (
                "OMA (Office for Metropolitan Architecture) is an international architecture, "
                "urbanism, and cultural analysis firm founded by Rem Koolhaas, known for "
                "projects like the CCTV Headquarters in Beijing, Seattle Central Library, "
                "and Casa da Musica in Porto."
            ),
            "founded_year": 1975,
            "country": "Netherlands",
            "city": "Rotterdam",
            "logo_url": "https://img.logo.dev/oma.com?token=pk_anonymous&size=128",
            # OMA website og:image is empty; use a known public image
            "image_url": None,
        },
        "tags": [
            ("Urbanism", "urbanism", "discipline"),
            ("Deconstructivism", "deconstructivism", "style"),
            ("Cultural Buildings", "cultural-buildings", "typology"),
            ("Pritzker Prize", "pritzker-prize", "award"),
            ("Research-Driven", "research-driven", "approach"),
        ],
    },
    {
        "id": "3927b6c7-5eab-4af1-ba11-206fedb0ef5c",
        "fields": {
            "website": "https://www.herzogdemeuron.com",
            "short_description": (
                "Herzog & de Meuron is a Swiss architecture firm founded by Jacques Herzog "
                "and Pierre de Meuron, renowned for the Tate Modern in London, Beijing "
                "National Stadium (Bird's Nest), and the Elbphilharmonie in Hamburg."
            ),
            "founded_year": 1978,
            "country": "Switzerland",
            "city": "Basel",
            "logo_url": "https://img.logo.dev/herzogdemeuron.com?token=pk_anonymous&size=128",
            # herzogdemeuron.com is JS-rendered; no og:image extractable via curl
            "image_url": None,
        },
        "tags": [
            ("Minimalism", "minimalism", "style"),
            ("Museum Design", "museum-design", "typology"),
            ("Pritzker Prize", "pritzker-prize", "award"),
            ("Facade Innovation", "facade-innovation", "approach"),
            ("Adaptive Reuse", "adaptive-reuse", "approach"),
        ],
    },
]

# ── og:image-only updates ────────────────────────────────────────

IMAGE_UPDATES = [
    {
        "id": "a0000000-0000-0000-0000-000000000007",
        "image_url": "https://dam-prod.media.mit.edu/thumb/2025/11/26/LiebermanNewYorker-ezgif.com-optimize.gif.1400x1400.gif",
    },
    # dfab.ch — JS-rendered, no og:image extractable via curl
    # thelivingnewyork.com — appears to be down / 404
]


def main(dry_run: bool = False) -> None:
    db = get_client()

    # ── Full firm updates ────────────────────────────────────────
    for item in FIRM_UPDATES:
        firm_id = item["id"]
        fields = {k: v for k, v in item["fields"].items() if v is not None}
        logger.info("Updating firm %s: %s", firm_id, list(fields.keys()))

        if not dry_run:
            db.table("firms").update(fields).eq("id", firm_id).execute()

        # Tags
        for tag_name, tag_slug, tag_category in item["tags"]:
            logger.info("  Tag: %s (%s)", tag_name, tag_slug)
            if not dry_run:
                tag_row = upsert_tag(tag_name, tag_slug, tag_category)
                if tag_row:
                    link_entity_tag(firm_id, "firm", tag_row["id"], source="manual")

    # ── Image-only updates ───────────────────────────────────────
    for item in IMAGE_UPDATES:
        entity_id = item["id"]
        image_url = item["image_url"]
        logger.info("Setting image_url for %s", entity_id)
        if not dry_run:
            db.table("firms").update({"image_url": image_url}).eq(
                "id", entity_id
            ).execute()

    logger.info("Done.%s", " (dry run — no changes written)" if dry_run else "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
