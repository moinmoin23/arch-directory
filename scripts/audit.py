"""Data quality audit — samples entities and surfaces problems.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/audit.py
"""

import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

# Bootstrap env before any shared imports
sys.path.insert(0, ".")

from scrapers.shared.db import get_client
from scrapers.shared.normalize import normalize_name

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Helpers ──────────────────────────────────────────────────────────


@dataclass
class Issue:
    severity: str  # critical, high, medium, low
    category: str
    entity_type: str
    entity_id: str
    name: str
    detail: str


@dataclass
class AuditReport:
    firms_sampled: int = 0
    people_sampled: int = 0
    total_firms: int = 0
    total_people: int = 0
    total_sources: int = 0
    total_aliases: int = 0
    total_enrichment_queue: int = 0
    total_review_queue: int = 0
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity, category, entity_type, entity_id, name, detail):
        self.issues.append(Issue(severity, category, entity_type, entity_id, name, detail))


# ── Junk detection patterns ─────────────────────────────────────────

_JUNK_NAME_PATTERNS = [
    re.compile(r"^\d+$"),  # purely numeric
    re.compile(r"^[a-z]$", re.I),  # single character
    re.compile(r"^\W+$"),  # only punctuation
]

_IRRELEVANT_FIRM_KEYWORDS = [
    "hospital", "clinic", "medical", "pharma", "health",
    "neurology", "cardiology", "oncology", "surgery", "dentist",
    "veterinary", "nursing", "midwi", "pathology", "radiology",
    "ministry", "department of", "army", "navy", "air force",
    "police", "prison", "correctional",
]

_SLUG_BAD_PATTERNS = [
    re.compile(r"--+"),  # double hyphens
    re.compile(r"[^a-z0-9-]"),  # non-slug chars
    re.compile(r"^-|-$"),  # leading/trailing hyphens
]


def _is_junk_name(name: str) -> bool:
    return any(p.search(name) for p in _JUNK_NAME_PATTERNS) or len(name) < 2


def _is_irrelevant_firm(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in _IRRELEVANT_FIRM_KEYWORDS)


def _has_bad_slug(slug: str) -> bool:
    return any(p.search(slug) for p in _SLUG_BAD_PATTERNS)


def _is_thin_firm(row: dict) -> bool:
    """A firm with fewer than 3 meaningful fields filled."""
    fields = ["country", "city", "website", "founded_year", "short_description", "size_range"]
    filled = sum(1 for f in fields if row.get(f))
    return filled < 2


def _is_thin_person(row: dict) -> bool:
    fields = ["role", "title", "nationality", "bio", "current_firm_id"]
    filled = sum(1 for f in fields if row.get(f))
    return filled < 2


# ── Audit checks ────────────────────────────────────────────────────


def audit_firms(client, report: AuditReport, limit: int = 200):
    """Audit a sample of firms."""
    # Get total count
    total = client.table("firms").select("id", count="exact").execute()
    report.total_firms = total.count

    # Random sample (order by id as proxy for random)
    firms = (
        client.table("firms")
        .select("id, slug, display_name, canonical_name, sector, country, city, website, founded_year, short_description, size_range, merged_into")
        .is_("merged_into", "null")
        .limit(limit)
        .execute()
    )
    report.firms_sampled = len(firms.data)

    for f in firms.data:
        fid = f["id"]
        name = f["display_name"]

        # Junk name
        if _is_junk_name(name):
            report.add("critical", "junk_name", "firm", fid, name, f"Name too short or garbage: '{name}'")

        # Irrelevant entity (medical, military, etc.)
        if _is_irrelevant_firm(name):
            report.add("high", "irrelevant_entity", "firm", fid, name, f"Likely irrelevant: '{name}'")

        # Bad slug
        if _has_bad_slug(f["slug"]):
            report.add("medium", "bad_slug", "firm", fid, name, f"Bad slug: '{f['slug']}'")

        # Thin record
        if _is_thin_firm(f):
            report.add("low", "thin_record", "firm", fid, name, "Fewer than 2 metadata fields filled")

        # Missing required fields
        if not f.get("sector"):
            report.add("high", "missing_field", "firm", fid, name, "Missing sector")

        # Canonical name mismatch
        expected_canonical = normalize_name(name)
        if f["canonical_name"] != expected_canonical:
            report.add("medium", "canonical_mismatch", "firm", fid, name,
                        f"canonical='{f['canonical_name']}' vs expected='{expected_canonical}'")


def audit_people(client, report: AuditReport, limit: int = 200):
    """Audit a sample of people."""
    total = client.table("people").select("id", count="exact").execute()
    report.total_people = total.count

    people = (
        client.table("people")
        .select("id, slug, display_name, canonical_name, sector, role, title, nationality, bio, current_firm_id")
        .limit(limit)
        .execute()
    )
    report.people_sampled = len(people.data)

    for p in people.data:
        pid = p["id"]
        name = p["display_name"]

        # Junk name
        if _is_junk_name(name):
            report.add("critical", "junk_name", "person", pid, name, f"Name too short or garbage: '{name}'")

        # Bad slug
        if _has_bad_slug(p["slug"]):
            report.add("medium", "bad_slug", "person", pid, name, f"Bad slug: '{p['slug']}'")

        # Thin record
        if _is_thin_person(p):
            report.add("low", "thin_record", "person", pid, name, "Fewer than 2 metadata fields filled")

        # Single-word name (likely incomplete)
        if " " not in name.strip():
            report.add("medium", "suspicious_name", "person", pid, name, "Single-word name — may be incomplete")

        # Canonical mismatch
        expected_canonical = normalize_name(name)
        if p["canonical_name"] != expected_canonical:
            report.add("medium", "canonical_mismatch", "person", pid, name,
                        f"canonical='{p['canonical_name']}' vs expected='{expected_canonical}'")


def audit_aliases(client, report: AuditReport):
    """Check for junk aliases."""
    report.total_aliases = client.table("entity_aliases").select("id", count="exact").execute().count

    # Sample aliases
    aliases = (
        client.table("entity_aliases")
        .select("id, entity_id, entity_type, alias, alias_normalized")
        .limit(500)
        .execute()
    )

    for a in aliases.data:
        # Very short alias (likely noise)
        if len(a["alias_normalized"]) < 2:
            report.add("medium", "junk_alias", a["entity_type"], a["entity_id"],
                        a["alias"], f"Alias too short: '{a['alias_normalized']}'")

        # Single character acronym
        if len(a["alias_normalized"]) == 1:
            report.add("high", "junk_alias", a["entity_type"], a["entity_id"],
                        a["alias"], f"Single-char alias: '{a['alias_normalized']}'")


def audit_duplicates(client, report: AuditReport):
    """Use trigram similarity to find likely duplicates among firms."""
    # Self-join via RPC is expensive, so do a simpler check:
    # group by canonical_name and flag duplicates
    firms = (
        client.table("firms")
        .select("id, canonical_name, display_name")
        .is_("merged_into", "null")
        .order("canonical_name")
        .execute()
    )

    name_groups: dict[str, list] = {}
    for f in firms.data:
        cn = f["canonical_name"]
        name_groups.setdefault(cn, []).append(f)

    for cn, group in name_groups.items():
        if len(group) > 1:
            names = [g["display_name"] for g in group]
            report.add("critical", "exact_duplicate", "firm", group[0]["id"],
                        cn, f"Exact canonical_name duplicate: {names}")


def audit_queues(client, report: AuditReport):
    """Report on enrichment and review queue health."""
    eq = client.table("enrichment_queue").select("status", count="exact").execute()
    report.total_enrichment_queue = eq.count

    # Enrichment queue by status
    for status in ["pending", "processing", "done", "failed"]:
        count = client.table("enrichment_queue").select("id", count="exact").eq("status", status).execute()
        if count.count > 0 and status in ("failed", "processing"):
            report.add("medium", "enrichment_stuck", "system", "", "",
                        f"Enrichment queue: {count.count} items in '{status}' state")

    rq = client.table("review_queue").select("id", count="exact").execute()
    report.total_review_queue = rq.count

    pending = client.table("review_queue").select("id", count="exact").eq("status", "pending").execute()
    if pending.count > 100:
        report.add("high", "review_backlog", "system", "", "",
                    f"Review queue: {pending.count} pending items need operator attention")


def audit_sources(client, report: AuditReport):
    """Check source health."""
    total = client.table("sources").select("id", count="exact").execute()
    report.total_sources = total.count

    # Check for sources without URLs
    no_url = client.table("sources").select("id", count="exact").is_("url", "null").execute()
    if no_url.count > 0:
        report.add("medium", "missing_field", "source", "", "",
                    f"{no_url.count} sources without URLs")

    # Cursor health
    cursors = client.table("ingest_cursors").select("source_name, status, errors").execute()
    for c in cursors.data:
        if c["status"] == "error":
            report.add("medium", "broken_feed", "source", "", c["source_name"],
                        f"Feed '{c['source_name']}' in error state")


# ── Report output ───────────────────────────────────────────────────


def print_report(report: AuditReport):
    print("\n" + "=" * 70)
    print("  DATA QUALITY AUDIT REPORT")
    print("=" * 70)

    print(f"\n  Dataset Overview:")
    print(f"    Firms:             {report.total_firms:>8,}")
    print(f"    People:            {report.total_people:>8,}")
    print(f"    Sources:           {report.total_sources:>8,}")
    print(f"    Aliases:           {report.total_aliases:>8,}")
    print(f"    Enrichment queue:  {report.total_enrichment_queue:>8,}")
    print(f"    Review queue:      {report.total_review_queue:>8,}")
    print(f"\n  Sampled: {report.firms_sampled} firms, {report.people_sampled} people")

    # Group by severity
    by_severity = Counter(i.severity for i in report.issues)
    print(f"\n  Issues by severity:")
    for sev in ["critical", "high", "medium", "low"]:
        count = by_severity.get(sev, 0)
        print(f"    {sev:10s}  {count:>5}")

    # Group by category
    by_category = Counter(i.category for i in report.issues)
    print(f"\n  Issues by category:")
    for cat, count in by_category.most_common():
        print(f"    {cat:25s}  {count:>5}")

    # Show top examples per severity
    for sev in ["critical", "high", "medium"]:
        items = [i for i in report.issues if i.severity == sev]
        if items:
            print(f"\n  {'─' * 60}")
            print(f"  {sev.upper()} issues (showing up to 10):")
            for item in items[:10]:
                print(f"    [{item.category}] {item.entity_type}: {item.name}")
                print(f"      → {item.detail}")

    # Thin record stats (full count, not just sample)
    thin_firms = len([i for i in report.issues if i.category == "thin_record" and i.entity_type == "firm"])
    thin_people = len([i for i in report.issues if i.category == "thin_record" and i.entity_type == "person"])
    print(f"\n  {'─' * 60}")
    print(f"  Thin records in sample:")
    print(f"    Firms:  {thin_firms}/{report.firms_sampled} sampled ({thin_firms/max(report.firms_sampled,1)*100:.0f}%)")
    print(f"    People: {thin_people}/{report.people_sampled} sampled ({thin_people/max(report.people_sampled,1)*100:.0f}%)")

    # Extrapolated
    if report.firms_sampled > 0:
        est_thin_firms = int(thin_firms / report.firms_sampled * report.total_firms)
        est_thin_people = int(thin_people / report.people_sampled * report.total_people)
        print(f"\n  Estimated thin records (extrapolated to full dataset):")
        print(f"    Firms:  ~{est_thin_firms:,}")
        print(f"    People: ~{est_thin_people:,}")

    print("\n" + "=" * 70)

    # Return summary dict for programmatic use
    return {
        "total_issues": len(report.issues),
        "by_severity": dict(by_severity),
        "by_category": dict(by_category),
    }


def main():
    client = get_client()
    report = AuditReport()

    print("Running data quality audit...")
    audit_firms(client, report, limit=200)
    audit_people(client, report, limit=200)
    audit_aliases(client, report)
    audit_duplicates(client, report)
    audit_queues(client, report)
    audit_sources(client, report)

    summary = print_report(report)

    # Write machine-readable report
    issues_json = [
        {
            "severity": i.severity,
            "category": i.category,
            "entity_type": i.entity_type,
            "entity_id": i.entity_id,
            "name": i.name,
            "detail": i.detail,
        }
        for i in report.issues
    ]
    with open("scripts/audit-report.json", "w") as f:
        json.dump({"summary": summary, "issues": issues_json}, f, indent=2)
    print(f"\n  Full report written to scripts/audit-report.json")


if __name__ == "__main__":
    main()
