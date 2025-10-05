"""
Unit tests for the PropertyDeduplicator module.

Tests exact and fuzzy matching deduplication according to FR-4.
"""

import pytest
from src.deduplicator import PropertyDeduplicator


@pytest.fixture
def deduplicator():
    """Create a PropertyDeduplicator instance for testing."""
    return PropertyDeduplicator()


class TestExactDuplication:
    """Test exact duplicate detection."""

    def test_exact_duplicates_by_parcel_id(self, deduplicator):
        """Test exact duplicates detected by parcel_id."""
        records = [
            {
                "owner_name": "John Smith",
                "parcel_id": "ABC123",
                "property_address": "123 Main St",
            },
            {
                "owner_name": "John Smith",
                "parcel_id": "ABC123",
                "property_address": "123 Main St",
            },
        ]

        unique, groups = deduplicator.find_duplicates(records, use_exact=True, use_fuzzy=False)

        assert len(groups) == 1
        assert len(groups[0]) == 2
        assert len(unique) == 0

    def test_no_exact_duplicates(self, deduplicator):
        """Test no duplicates when parcel_ids differ."""
        records = [
            {"owner_name": "John Smith", "parcel_id": "ABC123"},
            {"owner_name": "John Smith", "parcel_id": "DEF456"},
        ]

        unique, groups = deduplicator.find_duplicates(records, use_exact=True, use_fuzzy=False)

        assert len(groups) == 0
        assert len(unique) == 2


class TestFuzzyDuplication:
    """Test fuzzy duplicate detection (FR-4.2)."""

    def test_fuzzy_match_high_similarity(self, deduplicator):
        """Test fuzzy match with high name and address similarity."""
        rec1 = {
            "owner_name": "John Smith",
            "property_address": "123 Main Street",
        }
        rec2 = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
        }

        is_dup = deduplicator._is_fuzzy_duplicate(rec1, rec2)
        assert is_dup is True

    def test_fuzzy_match_name_only(self, deduplicator):
        """Test fuzzy match when only names are similar."""
        rec1 = {
            "owner_name": "John Michael Smith",
            "property_address": "",
        }
        rec2 = {
            "owner_name": "John M Smith",
            "property_address": "",
        }

        is_dup = deduplicator._is_fuzzy_duplicate(rec1, rec2)
        # Should match on name alone when address is missing
        assert is_dup is True

    def test_fuzzy_no_match_different_names(self, deduplicator):
        """Test no fuzzy match when names are different."""
        rec1 = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
        }
        rec2 = {
            "owner_name": "Jane Doe",
            "property_address": "123 Main St",
        }

        is_dup = deduplicator._is_fuzzy_duplicate(rec1, rec2)
        assert is_dup is False

    def test_fuzzy_no_match_different_addresses(self, deduplicator):
        """Test no fuzzy match when addresses are too different."""
        rec1 = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
        }
        rec2 = {
            "owner_name": "John Smith",
            "property_address": "456 Oak Ave",
        }

        is_dup = deduplicator._is_fuzzy_duplicate(rec1, rec2)
        # Addresses too different (< 95% threshold)
        assert is_dup is False

    def test_similarity_scores(self, deduplicator):
        """Test similarity score calculation."""
        rec1 = {
            "owner_name": "John Smith",
            "property_address": "123 Main Street",
            "parcel_id": "ABC123",
        }
        rec2 = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
            "parcel_id": "ABC123",
        }

        scores = deduplicator.get_similarity_score(rec1, rec2)

        assert "owner_name" in scores
        assert "property_address" in scores
        assert "parcel_id" in scores

        assert scores["owner_name"] == 100.0  # Exact match
        assert scores["property_address"] > 90.0  # High similarity
        assert scores["parcel_id"] == 100.0  # Exact match


class TestDuplicateDetection:
    """Test full duplicate detection."""

    def test_find_duplicates_mixed(self, deduplicator):
        """Test finding both exact and fuzzy duplicates."""
        records = [
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "Jane Doe", "parcel_id": "DEF456", "property_address": "456 Oak Ave"},
            {"owner_name": "Jane Doe", "parcel_id": "", "property_address": "456 Oak Avenue"},
        ]

        unique, groups = deduplicator.find_duplicates(records)

        # Should find at least one duplicate group (exact match by parcel_id)
        assert len(groups) >= 1
        # Some records should be unique
        assert len(unique) >= 1

    def test_no_duplicates(self, deduplicator):
        """Test when no duplicates exist."""
        records = [
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "Jane Doe", "parcel_id": "DEF456", "property_address": "456 Oak Ave"},
            {"owner_name": "Bob Johnson", "parcel_id": "GHI789", "property_address": "789 Elm St"},
        ]

        unique, groups = deduplicator.find_duplicates(records)

        assert len(groups) == 0
        assert len(unique) == 3


class TestMergeDuplicates:
    """Test duplicate merging strategies."""

    def test_merge_most_complete(self, deduplicator):
        """Test merging duplicates with 'most_complete' strategy."""
        duplicates = [
            {"owner_name": "John Smith", "property_address": "123 Main St", "city": ""},
            {"owner_name": "John Smith", "property_address": "", "city": "Raleigh"},
        ]

        merged = deduplicator.merge_duplicate_group(duplicates, strategy="most_complete")

        assert merged["owner_name"] == "John Smith"
        assert merged["property_address"] == "123 Main St"
        assert merged["city"] == "Raleigh"
        assert merged["is_merged"] is True
        assert merged["duplicate_count"] == 2

    def test_merge_first_strategy(self, deduplicator):
        """Test merging duplicates with 'first' strategy."""
        duplicates = [
            {"owner_name": "John Smith", "city": "Raleigh"},
            {"owner_name": "John M Smith", "city": "Durham"},
        ]

        merged = deduplicator.merge_duplicate_group(duplicates, strategy="first")

        assert merged["owner_name"] == "John Smith"
        assert merged["city"] == "Raleigh"

    def test_merge_last_strategy(self, deduplicator):
        """Test merging duplicates with 'last' strategy."""
        duplicates = [
            {"owner_name": "John Smith", "city": "Raleigh"},
            {"owner_name": "John M Smith", "city": "Durham"},
        ]

        merged = deduplicator.merge_duplicate_group(duplicates, strategy="last")

        assert merged["owner_name"] == "John M Smith"
        assert merged["city"] == "Durham"


class TestDeduplicateAndMerge:
    """Test combined deduplication and merging."""

    def test_deduplicate_and_merge(self, deduplicator):
        """Test full deduplication with merging."""
        records = [
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main Street"},
            {"owner_name": "Jane Doe", "parcel_id": "DEF456", "property_address": "456 Oak Ave"},
        ]

        deduplicated, duplicates = deduplicator.deduplicate_and_merge(records)

        # Should have 2 unique records (John and Jane)
        assert len(deduplicated) == 2
        # Should have identified duplicates
        assert len(duplicates) >= 2

    def test_duplicate_statistics(self, deduplicator):
        """Test duplicate statistics calculation."""
        records = [
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "John Smith", "parcel_id": "ABC123", "property_address": "123 Main St"},
            {"owner_name": "Jane Doe", "parcel_id": "DEF456", "property_address": "456 Oak Ave"},
        ]

        unique, groups = deduplicator.find_duplicates(records, use_exact=True, use_fuzzy=False)
        stats = deduplicator.get_duplicate_statistics(groups)

        assert stats["total_groups"] >= 0
        assert "total_duplicates" in stats
        assert "avg_group_size" in stats
