"""Filter researchers by relevancy to architecture, design, and technology for the built environment.

Checks each published researcher's linked source titles against relevancy
keywords. Researchers whose sources only match irrelevant domains (medical,
pure physics, etc.) get flagged for unpublishing.

This is conservative: entities are only flagged if they match irrelevant
keywords AND do NOT match any relevant keyword. Borderline cases are kept.

Usage:
    # Dry run — show what would be flagged
    PYTHONPATH=. scrapers/.venv/bin/python scripts/filter_researchers.py

    # Apply — set flagged researchers to draft
    PYTHONPATH=. scrapers/.venv/bin/python scripts/filter_researchers.py --apply

    # Write full report to file
    PYTHONPATH=. scrapers/.venv/bin/python scripts/filter_researchers.py --report
"""

import argparse
import csv
import logging
import os
import sys

sys.path.insert(0, ".")
from scrapers.shared.db import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Keywords for the built environment and adjacent fields ──────────

RELEVANT_KEYWORDS = [
    # Architecture & building
    "architect", "building", "construction", "facade", "structural",
    "concrete", "timber", "brick", "masonry", "mortar", "cement",
    "aggregate", "rebar", "reinforce", "steel struct", "cladding",
    "insulation", "waterproof", "roofing", "flooring", "wall ",
    # Digital fabrication & manufacturing
    "fabricat", "robot", "cnc", "additive manufactur", "3d print",
    "laser cut", "milling", "print", "extru", "cast", "mold", "mould",
    "assembl", "prefab", "modular",
    # Urban & spatial
    "urban", "city", "cities", "housing", "spatial", "land use",
    "public space", "neighborhood", "neighbourhood", "district",
    "zoning", "densit", "sprawl", "walkab", "transit",
    # Design & computation
    "design", "bim", "cad", "parametric", "generative",
    "topology optim", "computation", "algorithm", "form finding",
    "form-finding", "tessellat", "pattern", "origami", "fold",
    "mesh", "voxel", "slicing", "geometry", "morpholog",
    # Sustainability & environment
    "sustain", "energy efficien", "thermal", "acousti",
    "climate", "carbon", "emission", "renewable", "passive",
    "net zero", "circular", "recycl", "reuse", "waste",
    "dayligh", "ventilat", "hvac", "lighting", "indoor",
    "occupan", "comfort", "ergonomic", "bioclimat",
    # Materials for construction
    "material", "wood", "glass", "ceramic", "composite",
    "foam", "textile", "membrane", "cable", "tension",
    "fiber", "fibre reinforc", "laminate", "plywood", "bamboo",
    "earth", "rammed", "adobe", "biobased", "mycelium",
    "self-heal", "shape memory", "responsive material",
    # Structural & civil engineering
    "seismic", "earthquake", "wind load", "fire resist", "safety",
    "geotechnical", "soil", "foundation", "bridge", "tunnel",
    "infrastructure", "dam", "retaining",
    "finite element", "cfd", "simulat", "load",
    # Surveying & sensing
    "gis", "lidar", "point cloud", "photogramm", "scan",
    "sensor", "iot", "smart build", "digital twin",
    "augmented reality", "virtual reality", "mixed reality",
    "monitor", "structur health",
    # Heritage & preservation
    "heritage", "preserv", "renovation", "retrofit", "restor",
    "conservat", "archaeolog", "histor",
    # Landscape
    "landscape", "garden", "vegetation", "green roof",
    "stormwater", "flood", "erosion",
    # Robotics for construction
    "autonomous", "drone", "uav", "swarm", "multi-agent",
    "path planning", "mobile robot", "manipulat",
    "cooperative", "human-robot",
    # Art & installation (adjacent)
    "pavilion", "install", "exhibit", "gallery", "museum",
    "sculpture", "public art",
    # Pedagogy in design
    "studio", "pedagog", "curricul", "teach", "education",
    "workshop",
]

IRRELEVANT_KEYWORDS = [
    # Medical & biomedical
    "cancer", "tumor", "tumour", "oncolog", "chemotherap", "radiotherap",
    "drug delivery", "biomedical", "biomedicin", "patholog",
    "virus", "vaccine", "protein fold", "gene express", "gene edit",
    "dna sequenc", "rna", "genomic", "transcriptom", "proteom",
    "pharmaceutical", "pharmacolog", "dosage", "toxicolog",
    "medical imag", "clinical trial", "patient", "disease", "therap",
    "diagnos", "symptom", "surgery", "implant",
    "schizophreni", "alzheimer", "diabetes", "cardiac", "cardiovascul",
    "blood", "brain barrier", "neural pathway", "synapt",
    "immunolog", "antibod", "antigen", "inflammat",
    # Pure physics
    "quantum comput", "quantum bit", "qubit", "boson sampl",
    "superconductor", "superconducti", "magnetoresist",
    "astrophys", "cosmolog", "particle physics", "dark matter",
    "black hole", "neutron star", "gravitational wave",
    "string theory", "higgs",
    # Electronics (non-building)
    "transistor", "diode", "semiconductor", "integrated circuit",
    "organic electronics", "organic field-effect",
    "memristor", "spintronic",
    "optical fiber", "fibre optic", "data transmission",
    "telecommunicat", "5g", "6g", "wireless network",
    # Electrochemistry / batteries (non-building)
    "battery", "lithium", "sodium-ion", "fuel cell",
    "catalys", "electrolyte", "electrochemis", "electrolys",
    "hydrogen storage", "supercapacitor",
    # Pure AI/ML (not applied to design)
    "language model", "transformer model", "large language",
    "image classif", "object detect", "speech recogn",
    "natural language process", "sentiment analy",
    # Food & agriculture
    "food", "crop", "agricultur", "irrigation", "fertili",
    # Astronomy
    "telescope", "exoplanet", "galaxy", "stellar",
]


def classify_researcher(db, person_id: str) -> tuple[str, str]:
    """Classify a researcher as 'relevant', 'irrelevant', or 'borderline'.

    Returns (classification, reason).
    """
    sources = (
        db.table("entity_sources")
        .select("sources(title, source_name)")
        .eq("entity_id", person_id)
        .eq("entity_type", "person")
        .limit(10)
        .execute()
    )

    titles = []
    source_names = set()
    for s in sources.data or []:
        if s.get("sources"):
            if s["sources"].get("title"):
                titles.append(s["sources"]["title"])
            if s["sources"].get("source_name"):
                source_names.add(s["sources"]["source_name"])

    if not titles:
        return "borderline", "no source titles linked"

    combined = " ".join(titles).lower()

    # Check relevancy
    relevant_matches = [kw for kw in RELEVANT_KEYWORDS if kw in combined]
    irrelevant_matches = [kw for kw in IRRELEVANT_KEYWORDS if kw in combined]

    # Architecture-specific sources are always relevant
    arch_sources = {"ArchDaily", "Dezeen", "Designboom", "CumInCAD/OpenAlex"}
    if source_names & arch_sources:
        return "relevant", f"from {source_names & arch_sources}"

    if irrelevant_matches and not relevant_matches:
        reason = f"irrelevant: {', '.join(irrelevant_matches[:3])}"
        return "irrelevant", reason

    if relevant_matches:
        return "relevant", f"matched: {', '.join(relevant_matches[:3])}"

    return "borderline", "no keyword matches"


def run(apply: bool = False, report: bool = False):
    db = get_client()

    # Get all published researchers in batches
    all_researchers = []
    offset = 0
    while True:
        batch = (
            db.table("people")
            .select("id, slug, display_name, quality_score")
            .eq("role", "Researcher")
            .eq("publish_status", "published")
            .order("display_name")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        all_researchers.extend(batch.data)
        offset += 1000

    logger.info("Checking %d published researchers for relevancy...", len(all_researchers))

    results = {"relevant": [], "irrelevant": [], "borderline": []}

    for i, person in enumerate(all_researchers):
        classification, reason = classify_researcher(db, person["id"])
        results[classification].append({
            "id": person["id"],
            "slug": person["slug"],
            "name": person["display_name"],
            "score": person.get("quality_score", 0),
            "reason": reason,
        })

        if (i + 1) % 500 == 0:
            logger.info("  ...checked %d / %d", i + 1, len(all_researchers))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("RELEVANCY FILTER RESULTS")
    logger.info("=" * 60)
    logger.info("Relevant:    %d (keep published)", len(results["relevant"]))
    logger.info("Irrelevant:  %d (flag as draft)", len(results["irrelevant"]))
    logger.info("Borderline:  %d (keep published — manual review later)", len(results["borderline"]))
    logger.info("=" * 60)

    # Show samples
    logger.info("")
    logger.info("Sample IRRELEVANT (will be set to draft):")
    for p in results["irrelevant"][:10]:
        logger.info("  - %s — %s", p["name"], p["reason"])

    logger.info("")
    logger.info("Sample BORDERLINE (kept published):")
    for p in results["borderline"][:10]:
        logger.info("  - %s — %s", p["name"], p["reason"])

    # Write report CSV
    if report:
        report_path = os.path.join(os.path.dirname(__file__), "researcher_filter_report.csv")
        with open(report_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["classification", "name", "slug", "score", "reason"])
            writer.writeheader()
            for classification in ["irrelevant", "borderline", "relevant"]:
                for p in results[classification]:
                    writer.writerow({
                        "classification": classification,
                        "name": p["name"],
                        "slug": p["slug"],
                        "score": p["score"],
                        "reason": p["reason"],
                    })
        logger.info("\nReport written to %s", report_path)

    # Apply
    if apply:
        flagged = results["irrelevant"]
        logger.info("\nSetting %d irrelevant researchers to draft...", len(flagged))

        for i, p in enumerate(flagged):
            db.table("people").update({
                "publish_status": "draft",
            }).eq("id", p["id"]).execute()

            if (i + 1) % 100 == 0:
                logger.info("  ...updated %d / %d", i + 1, len(flagged))

        logger.info("Done. %d researchers set to draft.", len(flagged))
        logger.info("To reverse: UPDATE people SET publish_status = 'published' WHERE role = 'Researcher' AND publish_status = 'draft';")
    else:
        logger.info("\nDRY RUN — no changes made. Run with --apply to set irrelevant researchers to draft.")


def main():
    parser = argparse.ArgumentParser(description="Filter researchers by relevancy")
    parser.add_argument("--apply", action="store_true", help="Actually set irrelevant researchers to draft")
    parser.add_argument("--report", action="store_true", help="Write detailed CSV report")
    args = parser.parse_args()
    run(apply=args.apply, report=args.report)


if __name__ == "__main__":
    main()
