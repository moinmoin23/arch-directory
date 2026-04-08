"""Operator dashboard — shows system health at a glance.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/dashboard.py
"""

import sys

sys.path.insert(0, ".")

from scrapers.shared.db import get_client


def _count(client, table, **filters):
    q = client.table(table).select("id", count="exact")
    for k, v in filters.items():
        if v is None:
            q = q.is_(k, "null")
        else:
            q = q.eq(k, v)
    return q.execute().count


def main():
    client = get_client()

    # ── Entity counts ────────────────────────────────────────────
    total_firms = _count(client, "firms")
    active_firms = client.table("firms").select("id", count="exact").is_("merged_into", "null").execute().count
    total_people = _count(client, "people")
    total_sources = _count(client, "sources")
    total_aliases = _count(client, "entity_aliases")

    print("\n" + "=" * 65)
    print("  OPERATOR DASHBOARD")
    print("=" * 65)

    print(f"\n  ── Entity Counts ──")
    print(f"    Firms (active):    {active_firms:>8,}")
    print(f"    Firms (merged):    {total_firms - active_firms:>8,}")
    print(f"    People:            {total_people:>8,}")
    print(f"    Sources:           {total_sources:>8,}")
    print(f"    Aliases:           {total_aliases:>8,}")

    # ── Publish status ───────────────────────────────────────────
    print(f"\n  ── Publish Status ──")
    for table, label in [("firms", "Firms"), ("people", "People")]:
        for status in ["published", "draft", "hidden"]:
            count = _count(client, table, publish_status=status)
            print(f"    {label:8s} {status:12s} {count:>8,}")

    # ── Quality score distribution ───────────────────────────────
    print(f"\n  ── Quality Scores (firms) ──")
    firms = client.table("firms").select("quality_score").is_("merged_into", "null").limit(2000).execute()
    if firms.data:
        scores = [f["quality_score"] for f in firms.data]
        buckets = {"0-19": 0, "20-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
        for s in scores:
            if s < 20:
                buckets["0-19"] += 1
            elif s < 40:
                buckets["20-39"] += 1
            elif s < 60:
                buckets["40-59"] += 1
            elif s < 80:
                buckets["60-79"] += 1
            else:
                buckets["80-100"] += 1
        for bucket, count in buckets.items():
            bar = "█" * (count // 20)
            print(f"    {bucket:8s}  {count:>6,}  {bar}")

    # ── Enrichment queue ─────────────────────────────────────────
    print(f"\n  ── Enrichment Queue ──")
    for status in ["pending", "processing", "done", "failed"]:
        count = _count(client, "enrichment_queue", status=status)
        flag = " ⚠" if status in ("failed", "processing") and count > 0 else ""
        print(f"    {status:12s}  {count:>8,}{flag}")

    # ── Review queue ─────────────────────────────────────────────
    print(f"\n  ── Review Queue ──")
    for status in ["pending", "accepted", "rejected", "skipped"]:
        count = _count(client, "review_queue", status=status)
        print(f"    {status:12s}  {count:>8,}")

    # ── Source health ────────────────────────────────────────────
    print(f"\n  ── Source Health ──")
    cursors = client.table("ingest_cursors").select("source_name, entity_count, status, last_run_at").order("source_name").execute()
    for c in cursors.data:
        flag = " ⚠" if c["status"] == "error" else ""
        last_run = c.get("last_run_at", "")[:10] if c.get("last_run_at") else "never"
        print(f"    {c['source_name']:40s}  {c['entity_count']:>5}  {c['status']:>8}{flag}  {last_run}")

    # ── Top duplicate candidates ─────────────────────────────────
    print(f"\n  ── Top Duplicate Candidates (review queue, highest confidence) ──")
    top_dupes = (
        client.table("review_queue")
        .select("candidate_name, confidence, suggested_entity_id")
        .eq("status", "pending")
        .order("confidence", desc=True)
        .limit(10)
        .execute()
    )
    for d in top_dupes.data:
        print(f"    {d['confidence']:.2f}  {d['candidate_name'][:50]}")

    print("\n" + "=" * 65 + "\n")


if __name__ == "__main__":
    main()
