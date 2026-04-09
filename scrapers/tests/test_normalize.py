"""Tests for scrapers.shared.normalize — pure functions, no DB needed."""

import pytest
from scrapers.shared.normalize import normalize_name, generate_slug, generate_aliases


class TestNormalizeName:
    def test_basic_lowering(self):
        assert normalize_name("Foster + Partners") == "foster and partners"

    def test_strips_legal_suffixes(self):
        assert normalize_name("Acme Corp") == "acme"
        assert normalize_name("Example Ltd.") == "example"
        assert normalize_name("Test GmbH") == "test"

    def test_strips_multiple_suffixes(self):
        assert normalize_name("Foo Inc Ltd") == "foo"

    def test_ampersand_replacement(self):
        assert normalize_name("Herzog & de Meuron") == "herzog and de meuron"

    def test_plus_replacement(self):
        assert normalize_name("BIG + Heatherwick") == "big and heatherwick"

    def test_unicode_transliteration(self):
        assert normalize_name("Büro Ole Scheeren") == "buro ole scheeren"
        assert normalize_name("São Paulo") == "sao paulo"

    def test_collapses_whitespace(self):
        assert normalize_name("  Zaha   Hadid   ") == "zaha hadid"

    def test_strips_punctuation(self):
        assert normalize_name("O'Brien & Associates") == "obrien and associates"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_preserves_hyphens(self):
        assert normalize_name("Jean-Paul") == "jean-paul"


class TestGenerateSlug:
    def test_basic_slug(self):
        assert generate_slug("Foster + Partners") == "foster-and-partners"

    def test_slug_no_trailing_hyphens(self):
        slug = generate_slug("Acme Corp")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_slug_unicode(self):
        assert generate_slug("Büro Happold") == "buro-happold"

    def test_slug_no_double_hyphens(self):
        slug = generate_slug("Test -- Firm")
        assert "--" not in slug


class TestGenerateAliases:
    def test_includes_full_name(self):
        aliases = generate_aliases("Bjarke Ingels Group")
        assert "bjarke ingels" in aliases  # "group" is a common word, stripped

    def test_includes_acronym(self):
        aliases = generate_aliases("Bjarke Ingels Group")
        assert "big" in aliases

    def test_no_acronym_for_single_word(self):
        aliases = generate_aliases("MVRDV")
        assert len(aliases) == 1
        assert aliases[0] == "mvrdv"

    def test_strips_common_words(self):
        aliases = generate_aliases("SOM Design Studio")
        full = normalize_name("SOM Design Studio")
        stripped = [a for a in aliases if a != full and len(a.split()) <= 2]
        # "som" should be one of the aliases after stripping "design" and "studio"
        assert "som" in aliases

    def test_no_duplicates(self):
        aliases = generate_aliases("Zaha Hadid Architects")
        assert len(aliases) == len(set(aliases))

    def test_returns_at_least_one(self):
        aliases = generate_aliases("X")
        assert len(aliases) >= 1
