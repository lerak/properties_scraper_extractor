"""
Data deduplication module for property records.

This module identifies duplicate records using exact matching and
fuzzy matching algorithms as specified in FR-4.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

from config.settings import DEDUP_THRESHOLDS
from src.utils import get_logger, generate_record_hash


class PropertyDeduplicator:
    """Deduplicator for identifying duplicate property records."""

    def __init__(self):
        """Initialize the deduplicator."""
        if not FUZZYWUZZY_AVAILABLE:
            raise ImportError(
                "fuzzywuzzy is not installed. Install with: pip install fuzzywuzzy python-Levenshtein"
            )

        self.logger = get_logger(__name__)
        self.exact_match_fields = DEDUP_THRESHOLDS["exact_match_fields"]
        self.fuzzy_name_threshold = DEDUP_THRESHOLDS["fuzzy_name_threshold"]
        self.fuzzy_address_threshold = DEDUP_THRESHOLDS["fuzzy_address_threshold"]
        self.fuzzy_algorithm = DEDUP_THRESHOLDS["fuzzy_algorithm"]

        # Get fuzzy matching function
        self.fuzzy_matcher = getattr(fuzz, self.fuzzy_algorithm, fuzz.token_sort_ratio)

    def find_duplicates(
        self,
        records: List[Dict[str, Any]],
        use_exact: bool = True,
        use_fuzzy: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Find duplicate records in a list.

        Args:
            records: List of property records
            use_exact: Whether to use exact matching
            use_fuzzy: Whether to use fuzzy matching

        Returns:
            Tuple of (unique_records, duplicate_groups)
            where duplicate_groups is a list of lists, each containing duplicate records
        """
        self.logger.info(f"Finding duplicates in {len(records)} records...")

        duplicate_groups = []
        seen_indices = set()

        # Step 1: Exact matching by parcel_id
        if use_exact:
            exact_groups, exact_seen = self._find_exact_duplicates(records)
            duplicate_groups.extend(exact_groups)
            seen_indices.update(exact_seen)

            self.logger.info(f"Found {len(exact_groups)} exact duplicate groups")

        # Step 2: Fuzzy matching on remaining records
        if use_fuzzy:
            remaining_records = [
                (idx, rec) for idx, rec in enumerate(records)
                if idx not in seen_indices
            ]

            fuzzy_groups, fuzzy_seen = self._find_fuzzy_duplicates(remaining_records)
            duplicate_groups.extend(fuzzy_groups)
            seen_indices.update(fuzzy_seen)

            self.logger.info(f"Found {len(fuzzy_groups)} fuzzy duplicate groups")

        # Collect unique records
        unique_records = [
            rec for idx, rec in enumerate(records)
            if idx not in seen_indices
        ]

        self.logger.info(
            f"Deduplication complete: {len(unique_records)} unique, "
            f"{len(duplicate_groups)} duplicate groups"
        )

        return unique_records, duplicate_groups

    def _find_exact_duplicates(
        self,
        records: List[Dict[str, Any]]
    ) -> Tuple[List[List[Dict[str, Any]]], Set[int]]:
        """
        Find exact duplicates by matching on exact_match_fields.

        Args:
            records: List of property records

        Returns:
            Tuple of (duplicate_groups, seen_indices)
        """
        # Group records by exact match fields
        groups = defaultdict(list)

        for idx, record in enumerate(records):
            # Generate hash from exact match fields
            key = self._get_exact_match_key(record)

            if key:
                groups[key].append((idx, record))

        # Find groups with duplicates
        duplicate_groups = []
        seen_indices = set()

        for key, group in groups.items():
            if len(group) > 1:
                # Multiple records with same key = duplicates
                duplicate_records = [rec for idx, rec in group]
                duplicate_groups.append(duplicate_records)

                # Mark all indices as seen
                for idx, rec in group:
                    seen_indices.add(idx)

        return duplicate_groups, seen_indices

    def _get_exact_match_key(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Generate exact match key from record.

        Args:
            record: Property record

        Returns:
            Match key or None if fields missing
        """
        # Get values for exact match fields
        values = []
        for field in self.exact_match_fields:
            value = record.get(field)
            if not value:
                return None  # Missing required field

            # Normalize value
            value_str = str(value).strip().upper()
            values.append(value_str)

        return "|".join(values)

    def _find_fuzzy_duplicates(
        self,
        records: List[Tuple[int, Dict[str, Any]]]
    ) -> Tuple[List[List[Dict[str, Any]]], Set[int]]:
        """
        Find fuzzy duplicates using similarity matching.

        Args:
            records: List of (index, record) tuples

        Returns:
            Tuple of (duplicate_groups, seen_indices)
        """
        duplicate_groups = []
        seen_indices = set()

        # Compare each pair of records
        for i in range(len(records)):
            if records[i][0] in seen_indices:
                continue

            idx_i, rec_i = records[i]
            current_group = [rec_i]
            group_indices = {idx_i}

            # Compare with remaining records
            for j in range(i + 1, len(records)):
                if records[j][0] in seen_indices:
                    continue

                idx_j, rec_j = records[j]

                # Check if records are fuzzy duplicates
                if self._is_fuzzy_duplicate(rec_i, rec_j):
                    current_group.append(rec_j)
                    group_indices.add(idx_j)

            # If we found duplicates, add the group
            if len(current_group) > 1:
                duplicate_groups.append(current_group)
                seen_indices.update(group_indices)

        return duplicate_groups, seen_indices

    def _is_fuzzy_duplicate(
        self,
        record1: Dict[str, Any],
        record2: Dict[str, Any]
    ) -> bool:
        """
        Check if two records are fuzzy duplicates.

        According to FR-4.2:
        - Owner name similarity >= 90%
        - Property address similarity >= 95%

        Args:
            record1: First property record
            record2: Second property record

        Returns:
            True if records are fuzzy duplicates, False otherwise
        """
        # Get owner names
        name1 = str(record1.get("owner_name", "")).strip().upper()
        name2 = str(record2.get("owner_name", "")).strip().upper()

        # Get property addresses
        addr1 = str(record1.get("property_address", "")).strip().upper()
        addr2 = str(record2.get("property_address", "")).strip().upper()

        # Skip if essential fields are missing
        if not name1 or not name2:
            return False

        # Calculate name similarity
        name_similarity = self.fuzzy_matcher(name1, name2)

        # Calculate address similarity (if both present)
        address_similarity = 0
        if addr1 and addr2:
            address_similarity = self.fuzzy_matcher(addr1, addr2)

        # Check thresholds
        name_match = name_similarity >= self.fuzzy_name_threshold

        # Address match required if both addresses present
        if addr1 and addr2:
            address_match = address_similarity >= self.fuzzy_address_threshold
            return name_match and address_match
        else:
            # If address missing, rely on name match only
            return name_match

    def get_similarity_score(
        self,
        record1: Dict[str, Any],
        record2: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate similarity scores between two records.

        Args:
            record1: First property record
            record2: Second property record

        Returns:
            Dictionary with similarity scores for each field
        """
        scores = {}

        # Name similarity
        name1 = str(record1.get("owner_name", "")).strip().upper()
        name2 = str(record2.get("owner_name", "")).strip().upper()
        if name1 and name2:
            scores["owner_name"] = self.fuzzy_matcher(name1, name2)

        # Address similarity
        addr1 = str(record1.get("property_address", "")).strip().upper()
        addr2 = str(record2.get("property_address", "")).strip().upper()
        if addr1 and addr2:
            scores["property_address"] = self.fuzzy_matcher(addr1, addr2)

        # Parcel ID (exact match)
        parcel1 = str(record1.get("parcel_id", "")).strip().upper()
        parcel2 = str(record2.get("parcel_id", "")).strip().upper()
        if parcel1 and parcel2:
            scores["parcel_id"] = 100.0 if parcel1 == parcel2 else 0.0

        return scores

    def merge_duplicate_group(
        self,
        duplicate_group: List[Dict[str, Any]],
        strategy: str = "most_complete"
    ) -> Dict[str, Any]:
        """
        Merge a group of duplicate records into one.

        Args:
            duplicate_group: List of duplicate records
            strategy: Merge strategy ("most_complete", "first", "last")

        Returns:
            Merged record
        """
        if not duplicate_group:
            return {}

        if len(duplicate_group) == 1:
            return duplicate_group[0]

        if strategy == "first":
            return duplicate_group[0]

        elif strategy == "last":
            return duplicate_group[-1]

        elif strategy == "most_complete":
            return self._merge_most_complete(duplicate_group)

        else:
            self.logger.warning(f"Unknown merge strategy: {strategy}, using 'most_complete'")
            return self._merge_most_complete(duplicate_group)

    def _merge_most_complete(
        self,
        duplicate_group: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge duplicates by selecting most complete values.

        Args:
            duplicate_group: List of duplicate records

        Returns:
            Merged record with most complete data
        """
        merged = {}

        # Get all unique fields
        all_fields = set()
        for record in duplicate_group:
            all_fields.update(record.keys())

        # For each field, select the most complete value
        for field in all_fields:
            values = []
            for record in duplicate_group:
                value = record.get(field)
                if value is not None and value != "":
                    values.append(value)

            if values:
                # Prefer longest string (most complete)
                if isinstance(values[0], str):
                    merged[field] = max(values, key=len)
                else:
                    # For non-strings, use first non-null value
                    merged[field] = values[0]
            else:
                merged[field] = ""

        # Add metadata about merge
        merged["is_merged"] = True
        merged["duplicate_count"] = len(duplicate_group)

        return merged

    def deduplicate_and_merge(
        self,
        records: List[Dict[str, Any]],
        merge_strategy: str = "most_complete",
        use_exact: bool = True,
        use_fuzzy: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Find duplicates and merge them.

        Args:
            records: List of property records
            merge_strategy: Strategy for merging duplicates
            use_exact: Whether to use exact matching
            use_fuzzy: Whether to use fuzzy matching

        Returns:
            Tuple of (deduplicated_records, original_duplicates)
            where original_duplicates contains all records from duplicate groups
        """
        # Find duplicates
        unique_records, duplicate_groups = self.find_duplicates(
            records,
            use_exact=use_exact,
            use_fuzzy=use_fuzzy
        )

        # Merge each duplicate group
        merged_records = []
        all_duplicates = []

        for group in duplicate_groups:
            merged = self.merge_duplicate_group(group, strategy=merge_strategy)
            merged_records.append(merged)
            all_duplicates.extend(group)

        # Combine unique and merged records
        deduplicated_records = unique_records + merged_records

        self.logger.info(
            f"Deduplication complete: {len(deduplicated_records)} total records "
            f"({len(unique_records)} unique + {len(merged_records)} merged)"
        )

        return deduplicated_records, all_duplicates

    def get_duplicate_statistics(
        self,
        duplicate_groups: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate statistics about duplicates.

        Args:
            duplicate_groups: List of duplicate groups

        Returns:
            Dictionary with duplicate statistics
        """
        if not duplicate_groups:
            return {
                "total_groups": 0,
                "total_duplicates": 0,
                "avg_group_size": 0,
                "max_group_size": 0,
            }

        group_sizes = [len(group) for group in duplicate_groups]

        return {
            "total_groups": len(duplicate_groups),
            "total_duplicates": sum(group_sizes),
            "avg_group_size": sum(group_sizes) / len(group_sizes),
            "max_group_size": max(group_sizes),
            "min_group_size": min(group_sizes),
        }
