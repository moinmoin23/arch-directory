"""Pipeline orchestrator — runs scrapers in sequence.

Usage:
    python scrapers/pipeline.py                  # run all registered scrapers
    python scrapers/pipeline.py --sources rss    # run specific scrapers
    python scrapers/pipeline.py --sources rss,openalex
"""

import argparse
import importlib
import logging
import sys
import time
from dataclasses import dataclass, field

# Configure logging before any imports that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


@dataclass
class SourceResult:
    name: str
    entity_count: int = 0
    duration_s: float = 0.0
    error: str | None = None


# Registry: source_name → module path (relative to scrapers/)
# Each module must expose a `run() -> int` function that returns entity count.
SOURCES: dict[str, str] = {
    "rss": "scrapers.rss_ingest",
    "openalex": "scrapers.openalex_ingest",
    "awards": "scrapers.awards_ingest",
    "venice": "scrapers.venice_biennale_ingest",
    "cumincad": "scrapers.cumincad_ingest",
}


def run_source(name: str, module_path: str) -> SourceResult:
    """Import and run a single scraper module."""
    t0 = time.time()
    try:
        mod = importlib.import_module(module_path)
        count = mod.run()
        return SourceResult(
            name=name,
            entity_count=count,
            duration_s=time.time() - t0,
        )
    except Exception as exc:
        logger.exception("Source '%s' failed", name)
        return SourceResult(
            name=name,
            duration_s=time.time() - t0,
            error=str(exc),
        )


def print_summary(results: list[SourceResult]) -> None:
    """Print a human-readable summary table."""
    print("\n" + "=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  {'Source':<20} {'Entities':>10} {'Time':>10} {'Status':>10}")
    print("-" * 60)

    total_entities = 0
    total_time = 0.0
    failures = 0

    for r in results:
        status = "OK" if r.error is None else "FAILED"
        if r.error:
            failures += 1
        total_entities += r.entity_count
        total_time += r.duration_s
        print(
            f"  {r.name:<20} {r.entity_count:>10} {r.duration_s:>9.1f}s {status:>10}"
        )

    print("-" * 60)
    print(
        f"  {'TOTAL':<20} {total_entities:>10} {total_time:>9.1f}s"
        f"   {failures} failed"
    )
    print("=" * 60 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ingestion pipeline")
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help="Comma-separated source names to run (default: all)",
    )
    args = parser.parse_args()

    if args.sources:
        selected = [s.strip() for s in args.sources.split(",")]
        unknown = [s for s in selected if s not in SOURCES]
        if unknown:
            logger.error(
                "Unknown sources: %s. Available: %s",
                ", ".join(unknown),
                ", ".join(SOURCES.keys()),
            )
            return 1
    else:
        selected = list(SOURCES.keys())

    if not selected:
        logger.warning("No sources registered yet. Add scrapers to SOURCES dict.")
        print("\nNo sources registered. Register scrapers in pipeline.py SOURCES dict.")
        return 0

    logger.info("Running %d source(s): %s", len(selected), ", ".join(selected))

    results = []
    for name in selected:
        logger.info("--- Starting: %s ---", name)
        result = run_source(name, SOURCES[name])
        results.append(result)
        if result.error:
            logger.error("Source '%s' failed: %s", name, result.error)
        else:
            logger.info(
                "Source '%s' done: %d entities in %.1fs",
                name,
                result.entity_count,
                result.duration_s,
            )

    print_summary(results)
    return 1 if any(r.error for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
