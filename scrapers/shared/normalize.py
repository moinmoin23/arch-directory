"""Name normalization, slug generation, and alias extraction."""

import re

from unidecode import unidecode

# Legal suffixes to strip (order matters — longer first to avoid partial matches)
_LEGAL_SUFFIXES = [
    "pty ltd", "pvt ltd",
    "gmbh", "sarl", "corp", "llc", "llp",
    "inc", "ltd", "ag", "kg", "sa", "bv", "nv", "lp",
    "co", "company",
]

# Words to strip when generating short aliases
_COMMON_WORDS = {
    "architects", "architecture", "studio", "studios",
    "design", "designs", "lab", "labs", "laboratory",
    "group", "associates", "partners", "office",
    "atelier", "workshop", "collective", "practice",
    "research", "institute", "center", "centre",
}

# Compiled pattern for legal suffixes (word-boundary match at end of string)
_SUFFIX_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _LEGAL_SUFFIXES) + r")\s*$"
)


def normalize_name(name: str) -> str:
    """Normalize an entity name for matching.

    Steps: strip → lowercase → remove legal suffixes → & → and →
    strip punctuation (keep hyphens/spaces) → transliterate → collapse spaces.
    """
    s = name.strip().lower()

    # Normalize symbols early
    s = s.replace("&", " and ").replace("+", " and ")

    # Strip punctuation except hyphens and spaces (before suffix removal
    # so "Ltd." becomes "ltd" and matches the suffix pattern)
    s = re.sub(r"[^\w\s-]", "", s)

    # Remove legal suffixes (may need multiple passes for "Inc Ltd" etc.)
    for _ in range(3):
        s_new = _SUFFIX_PATTERN.sub("", s).strip()
        if s_new == s:
            break
        s = s_new

    # Transliterate non-ASCII to ASCII
    s = unidecode(s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    normalized = normalize_name(name)
    slug = re.sub(r"\s+", "-", normalized)
    slug = re.sub(r"-{2,}", "-", slug)  # collapse multiple hyphens
    return slug.strip("-")


def generate_aliases(name: str) -> list[str]:
    """Generate common name variants for entity resolution.

    Returns a list of unique aliases (all normalized):
    1. The full normalized name
    2. Acronym (first letters of multi-word names, if 2+ words)
    3. Name with common words stripped (if different from full)
    """
    full = normalize_name(name)
    aliases = [full]

    words = full.split()

    # Acronym for multi-word names (e.g., "big" from "bjarke ingels group")
    if len(words) >= 2:
        acronym = "".join(w[0] for w in words if w)
        if len(acronym) >= 2 and acronym != full:
            aliases.append(acronym)

    # Strip common words
    stripped_words = [w for w in words if w not in _COMMON_WORDS]
    if stripped_words and stripped_words != words:
        short = " ".join(stripped_words)
        if short and short != full:
            aliases.append(short)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for a in aliases:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique
