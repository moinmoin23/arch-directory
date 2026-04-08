"""Operator review workflow for the review queue.

Presents review_queue items one at a time with context.
Operator can: accept match, reject match, skip, or quit.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/review.py
    PYTHONPATH=. scrapers/.venv/bin/python scripts/review.py --limit 50
    PYTHONPATH=. scrapers/.venv/bin/python scripts/review.py --min-confidence 0.7
    PYTHONPATH=. scrapers/.venv/bin/python scripts/review.py --summary
"""

import argparse
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from scrapers.shared.db import get_client


def show_summary(client):
    """Print review queue stats."""
    pending = client.table("review_queue").select("id", count="exact").eq("status", "pending").execute()
    accepted = client.table("review_queue").select("id", count="exact").eq("status", "accepted").execute()
    rejected = client.table("review_queue").select("id", count="exact").eq("status", "rejected").execute()
    skipped = client.table("review_queue").select("id", count="exact").eq("status", "skipped").execute()

    print(f"\n  Review Queue Summary:")
    print(f"    Pending:   {pending.count:>6,}")
    print(f"    Accepted:  {accepted.count:>6,}")
    print(f"    Rejected:  {rejected.count:>6,}")
    print(f"    Skipped:   {skipped.count:>6,}")
    print(f"    Total:     {pending.count + accepted.count + rejected.count + skipped.count:>6,}")

    # Confidence distribution of pending
    items = (
        client.table("review_queue")
        .select("confidence")
        .eq("status", "pending")
        .order("confidence", desc=True)
        .limit(1000)
        .execute()
    )
    if items.data:
        confs = [r["confidence"] for r in items.data if r["confidence"]]
        buckets = {"0.8+": 0, "0.7-0.8": 0, "0.6-0.7": 0, "<0.6": 0}
        for c in confs:
            if c >= 0.8:
                buckets["0.8+"] += 1
            elif c >= 0.7:
                buckets["0.7-0.8"] += 1
            elif c >= 0.6:
                buckets["0.6-0.7"] += 1
            else:
                buckets["<0.6"] += 1
        print(f"\n  Pending confidence distribution:")
        for bucket, count in buckets.items():
            print(f"    {bucket:10s}  {count:>5}")
    print()


def review_items(client, limit: int, min_confidence: float):
    """Interactive review loop."""
    items = (
        client.table("review_queue")
        .select("id, candidate_name, entity_type, suggested_entity_id, confidence, match_type")
        .eq("status", "pending")
        .gte("confidence", min_confidence)
        .order("confidence", desc=True)
        .limit(limit)
        .execute()
    )

    if not items.data:
        print("  No pending items matching criteria.")
        return

    print(f"\n  {len(items.data)} items to review (highest confidence first)")
    print(f"  Commands: [a]ccept  [r]eject  [s]kip  [q]uit\n")

    reviewed = 0
    for i, item in enumerate(items.data):
        # Fetch the suggested entity for context
        entity_context = ""
        if item["suggested_entity_id"]:
            table = "firms" if item["entity_type"] == "firm" else "people"
            entity = (
                client.table(table)
                .select("display_name, canonical_name, country, city")
                .eq("id", item["suggested_entity_id"])
                .limit(1)
                .execute()
            )
            if entity.data:
                e = entity.data[0]
                location = ", ".join(filter(None, [e.get("city"), e.get("country")]))
                entity_context = f"{e['display_name']} ({location or 'no location'})"

        print(f"  ── [{i+1}/{len(items.data)}] ──────────────────────────────────")
        print(f"  Candidate:   {item['candidate_name']}")
        print(f"  Type:        {item['entity_type']}")
        print(f"  Confidence:  {item['confidence']:.2f}  ({item['match_type']})")
        print(f"  Suggested:   {entity_context or 'none'}")

        while True:
            choice = input("  > ").strip().lower()
            if choice in ("a", "accept"):
                client.table("review_queue").update({
                    "status": "accepted",
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", item["id"]).execute()
                print("    ✓ Accepted")
                reviewed += 1
                break
            elif choice in ("r", "reject"):
                client.table("review_queue").update({
                    "status": "rejected",
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", item["id"]).execute()
                print("    ✗ Rejected")
                reviewed += 1
                break
            elif choice in ("s", "skip"):
                client.table("review_queue").update({
                    "status": "skipped",
                }).eq("id", item["id"]).execute()
                print("    ○ Skipped")
                break
            elif choice in ("q", "quit"):
                print(f"\n  Reviewed {reviewed} items. Exiting.")
                return
            else:
                print("    [a]ccept  [r]eject  [s]kip  [q]uit")

    print(f"\n  Done. Reviewed {reviewed} items.")


def main():
    parser = argparse.ArgumentParser(description="Review queue operator workflow")
    parser.add_argument("--limit", type=int, default=50, help="Max items to show")
    parser.add_argument("--min-confidence", type=float, default=0.6, help="Min confidence to show")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    args = parser.parse_args()

    client = get_client()

    show_summary(client)

    if not args.summary:
        review_items(client, args.limit, args.min_confidence)


if __name__ == "__main__":
    main()
