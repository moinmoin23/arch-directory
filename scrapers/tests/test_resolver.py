"""Tests for scrapers.shared.resolver — uses mocked Supabase client."""

from unittest.mock import MagicMock, patch
import pytest
from scrapers.shared.resolver import resolve_entity, ResolveResult


def _mock_client():
    """Build a mock Supabase client with chainable query builder."""
    client = MagicMock()

    def make_query(data):
        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.is_.return_value = q
        q.limit.return_value = q
        q.execute.return_value = MagicMock(data=data)
        return q

    client._make_query = make_query
    return client


@patch("scrapers.shared.resolver.get_client")
class TestResolveExactMatch:
    def test_exact_match_returns_entity(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client

        # Step 1: exact match on canonical_name
        exact_query = client._make_query([{"id": "abc-123", "canonical_name": "foster and partners"}])
        client.table.return_value = exact_query

        result = resolve_entity("Foster + Partners", "firm")

        assert result.entity_id == "abc-123"
        assert result.confidence == 1.0
        assert result.match_type == "exact"


@patch("scrapers.shared.resolver.get_client")
class TestResolveAliasMatch:
    def test_alias_match_returns_entity(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client

        # Step 1: no exact match
        no_match = client._make_query([])
        # Step 2: alias match
        alias_match = client._make_query([{"entity_id": "def-456"}])

        call_count = [0]
        def table_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return no_match  # firms table
            return alias_match  # entity_aliases table

        client.table.side_effect = table_side_effect

        result = resolve_entity("BIG", "firm")

        assert result.entity_id == "def-456"
        assert result.confidence == 1.0
        assert result.match_type == "alias"


@patch("scrapers.shared.resolver.add_to_review_queue")
@patch("scrapers.shared.resolver.get_client")
class TestResolveTrigram:
    def test_high_similarity_auto_matches(self, mock_get_client, mock_review):
        client = _mock_client()
        mock_get_client.return_value = client

        # Steps 1 & 2: no match
        no_match = client._make_query([])
        client.table.return_value = no_match

        # Step 3: trigram match with high similarity
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data=[{"id": "ghi-789", "similarity": 0.92, "canonical_name": "test"}]
        )
        client.rpc.return_value = rpc_mock

        result = resolve_entity("Test Firm", "firm")

        assert result.entity_id == "ghi-789"
        assert result.confidence == 0.92
        assert result.match_type == "trigram"
        mock_review.assert_not_called()

    def test_ambiguous_similarity_goes_to_review(self, mock_get_client, mock_review):
        client = _mock_client()
        mock_get_client.return_value = client

        no_match = client._make_query([])
        client.table.return_value = no_match

        # Trigram with ambiguous similarity (0.6-0.85)
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data=[{"id": "jkl-012", "similarity": 0.72, "canonical_name": "test"}]
        )
        client.rpc.return_value = rpc_mock

        result = resolve_entity("Test Studio", "firm")

        assert result.entity_id is None
        assert result.match_type == "review"
        mock_review.assert_called_once()


@patch("scrapers.shared.resolver.get_client")
class TestResolveNewEntity:
    def test_no_match_creates_new(self, mock_get_client):
        client = _mock_client()
        mock_get_client.return_value = client

        no_match = client._make_query([])
        client.table.return_value = no_match

        # No trigram matches either
        rpc_trigram = MagicMock()
        rpc_trigram.execute.return_value = MagicMock(data=[])

        # RPC creates entity
        rpc_create = MagicMock()
        rpc_create.execute.return_value = MagicMock(data={"id": "new-001"})

        def rpc_side_effect(name, params=None):
            if name == "match_entity_trigram":
                return rpc_trigram
            return rpc_create

        client.rpc.side_effect = rpc_side_effect

        result = resolve_entity("Brand New Firm", "firm")

        assert result.entity_id == "new-001"
        assert result.match_type == "new"
        assert result.confidence == 0.0


class TestResolveResult:
    def test_dataclass_fields(self):
        r = ResolveResult(entity_id="abc", confidence=0.95, match_type="exact")
        assert r.entity_id == "abc"
        assert r.confidence == 0.95
        assert r.match_type == "exact"
