"""Read and update ingest_cursors for resumable pipeline runs."""

import logging
from datetime import datetime, timezone

from .db import get_client

logger = logging.getLogger(__name__)


def get_cursor(source_name: str) -> str | None:
    """Return the last_cursor value for a source, or None if no prior run."""
    result = (
        get_client()
        .table("ingest_cursors")
        .select("last_cursor")
        .eq("source_name", source_name)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["last_cursor"]
    return None


def update_cursor(
    source_name: str,
    cursor: str,
    count: int,
    status: str = "ok",
    errors: list | None = None,
) -> None:
    """Create or update the cursor for a source after a run."""
    get_client().table("ingest_cursors").upsert(
        {
            "source_name": source_name,
            "last_cursor": cursor,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "entity_count": count,
            "status": status,
            "errors": errors,
        },
        on_conflict="source_name",
    ).execute()
    logger.info(
        "Cursor updated: source=%s cursor=%s count=%d status=%s",
        source_name,
        cursor,
        count,
        status,
    )
