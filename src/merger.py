"""
Data merging module for combining property records from multiple sources.

This module merges records from Wake County API and Orange County scraper
based on parcel_id matching as specified in FR-5.
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from src.utils import get_logger


class PropertyMerger:
    """Merger for combining property records from multiple sources."""

    def __init__(self):
        """Initialize the merger."""
        self.logger = get_logger(__name__)

    def merge_sources(
        self,
        wake_records: List[Dict[str, Any]],
        orange_records: List[Dict[str, Any]],
        merge_key: str = "parcel_id"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Merge records from Wake County and Orange County sources.

        Args:
            wake_records: Records from Wake County API
            orange_records: Records from Orange County scraper
            merge_key: Field to use for merging (default: parcel_id)

        Returns:
            Tuple of (merged_records, statistics)
        """
        self.logger.info(
            f"Merging {len(wake_records)} Wake County + {len(orange_records)} Orange County records"
        )

        # Group records by merge key
        wake_by_key = self._group_by_key(wake_records, merge_key)
        orange_by_key = self._group_by_key(orange_records, merge_key)

        merged_records = []
        stats = {
            "wake_only": 0,
            "orange_only": 0,
            "merged": 0,
            "total": 0,
        }

        # Get all unique keys
        all_keys = set(wake_by_key.keys()) | set(orange_by_key.keys())

        for key in all_keys:
            wake_group = wake_by_key.get(key, [])
            orange_group = orange_by_key.get(key, [])

            if wake_group and orange_group:
                # Records exist in both sources - merge them
                for wake_rec in wake_group:
                    for orange_rec in orange_group:
                        merged = self.merge_record_pair(wake_rec, orange_rec)
                        merged_records.append(merged)
                        stats["merged"] += 1

            elif wake_group:
                # Only Wake County records
                merged_records.extend(wake_group)
                stats["wake_only"] += len(wake_group)

            elif orange_group:
                # Only Orange County records
                merged_records.extend(orange_group)
                stats["orange_only"] += len(orange_group)

        stats["total"] = len(merged_records)

        self.logger.info(
            f"Merge complete: {stats['total']} total records "
            f"({stats['wake_only']} Wake only, {stats['orange_only']} Orange only, "
            f"{stats['merged']} merged)"
        )

        return merged_records, stats

    def _group_by_key(
        self,
        records: List[Dict[str, Any]],
        key: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group records by a specific key field.

        Args:
            records: List of property records
            key: Field name to group by

        Returns:
            Dictionary mapping key values to lists of records
        """
        grouped = defaultdict(list)

        for record in records:
            key_value = record.get(key)

            if key_value:
                # Normalize key value
                key_normalized = str(key_value).strip().upper()
                grouped[key_normalized].append(record)

        return grouped

    def merge_record_pair(
        self,
        record1: Dict[str, Any],
        record2: Dict[str, Any],
        prefer_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge two property records into one.

        Strategy:
        - Prefer non-empty values
        - If both have values, prefer record from preferred source
        - Combine source information

        Args:
            record1: First property record
            record2: Second property record
            prefer_source: Source to prefer when both have values (e.g., "Wake County API")

        Returns:
            Merged property record
        """
        merged = {}

        # Get all unique fields
        all_fields = set(record1.keys()) | set(record2.keys())

        for field in all_fields:
            value1 = record1.get(field)
            value2 = record2.get(field)

            # Handle special fields
            if field == "source":
                # Combine sources
                sources = []
                if value1:
                    sources.append(value1)
                if value2:
                    sources.append(value2)
                merged[field] = " + ".join(sources) if sources else ""
                continue

            elif field == "source_url":
                # Combine URLs
                urls = []
                if value1:
                    urls.append(value1)
                if value2:
                    urls.append(value2)
                merged[field] = " | ".join(urls) if urls else ""
                continue

            elif field == "extracted_at":
                # Use most recent extraction time
                if value1 and value2:
                    merged[field] = max(value1, value2)
                else:
                    merged[field] = value1 or value2 or ""
                continue

            # For regular fields, merge values
            merged[field] = self._merge_field_values(
                value1, value2, prefer_source, record1.get("source"), record2.get("source")
            )

        # Add merge metadata
        merged["is_cross_source_merged"] = True

        return merged

    def _merge_field_values(
        self,
        value1: Any,
        value2: Any,
        prefer_source: Optional[str],
        source1: Optional[str],
        source2: Optional[str]
    ) -> Any:
        """
        Merge two field values using merge strategy.

        Args:
            value1: Value from first record
            value2: Value from second record
            prefer_source: Source to prefer
            source1: Source of first record
            source2: Source of second record

        Returns:
            Merged value
        """
        # If one is None or empty, use the other
        is_empty1 = value1 is None or (isinstance(value1, str) and not value1.strip())
        is_empty2 = value2 is None or (isinstance(value2, str) and not value2.strip())

        if is_empty1 and not is_empty2:
            return value2
        elif is_empty2 and not is_empty1:
            return value1
        elif is_empty1 and is_empty2:
            return ""

        # Both have values - apply preference
        if prefer_source:
            if source1 == prefer_source:
                return value1
            elif source2 == prefer_source:
                return value2

        # No preference or preference not matched - use longest/most complete
        if isinstance(value1, str) and isinstance(value2, str):
            return value1 if len(value1) >= len(value2) else value2
        else:
            # For non-strings, prefer first value
            return value1

    def combine_all_records(
        self,
        *record_lists: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine multiple lists of records into one.

        Args:
            *record_lists: Variable number of record lists

        Returns:
            Combined list of all records
        """
        combined = []

        for record_list in record_lists:
            if record_list:
                combined.extend(record_list)

        self.logger.info(f"Combined {len(record_lists)} lists into {len(combined)} total records")

        return combined

    def separate_by_source(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Separate records by their source.

        Args:
            records: List of property records

        Returns:
            Dictionary mapping source names to lists of records
        """
        by_source = defaultdict(list)

        for record in records:
            source = record.get("source", "Unknown")
            by_source[source].append(record)

        return dict(by_source)

    def get_cross_source_records(
        self,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get records that were merged from multiple sources.

        Args:
            records: List of property records

        Returns:
            List of cross-source merged records
        """
        cross_source = [
            rec for rec in records
            if rec.get("is_cross_source_merged", False)
        ]

        self.logger.info(f"Found {len(cross_source)} cross-source merged records")

        return cross_source

    def get_merge_statistics(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate statistics about merged records.

        Args:
            records: List of property records

        Returns:
            Dictionary with merge statistics
        """
        total = len(records)

        # Count by source
        by_source = self.separate_by_source(records)
        source_counts = {source: len(recs) for source, recs in by_source.items()}

        # Count cross-source merges
        cross_source = self.get_cross_source_records(records)
        cross_source_count = len(cross_source)

        # Count single-source records
        single_source_count = total - cross_source_count

        return {
            "total_records": total,
            "single_source": single_source_count,
            "cross_source_merged": cross_source_count,
            "by_source": source_counts,
        }
