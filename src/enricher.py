"""
Data enrichment module for property records.

This module adds quality scores and metadata to property records
as specified in FR-6.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import QUALITY_SCORE_WEIGHTS, QUALITY_THRESHOLDS
from src.utils import get_logger


class PropertyEnricher:
    """Enricher for adding quality scores and metadata to property records."""

    def __init__(self):
        """Initialize the enricher."""
        self.logger = get_logger(__name__)
        self.score_weights = QUALITY_SCORE_WEIGHTS
        self.thresholds = QUALITY_THRESHOLDS

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single property record with quality score and metadata.

        Args:
            record: Property record to enrich

        Returns:
            Enriched record with quality_score, quality_level, and completeness fields
        """
        enriched = record.copy()

        # Calculate quality score
        quality_score = self.calculate_quality_score(record)
        enriched["quality_score"] = quality_score

        # Determine quality level
        quality_level = self.get_quality_level(quality_score)
        enriched["quality_level"] = quality_level

        # Calculate field completeness
        completeness = self.calculate_completeness(record)
        enriched["completeness_percent"] = completeness

        # Add enrichment timestamp
        enriched["enriched_at"] = datetime.now().isoformat()

        return enriched

    def calculate_quality_score(self, record: Dict[str, Any]) -> float:
        """
        Calculate quality score for a record based on field completeness.

        According to FR-6.2, the score is calculated using weighted points
        for each field that is present and non-empty.

        Args:
            record: Property record

        Returns:
            Quality score (0-100)
        """
        total_score = 0.0

        for field, weight in self.score_weights.items():
            # Check if field exists and has a non-empty value
            if self._has_value(record, field):
                total_score += weight

        # Ensure score is in 0-100 range
        total_score = max(0.0, min(100.0, total_score))

        return round(total_score, 2)

    def _has_value(self, record: Dict[str, Any], field: str) -> bool:
        """
        Check if a field has a meaningful value.

        Args:
            record: Property record
            field: Field name to check

        Returns:
            True if field has a non-empty value, False otherwise
        """
        if field not in record:
            return False

        value = record[field]

        # Check for None
        if value is None:
            return False

        # Check for empty strings
        if isinstance(value, str) and not value.strip():
            return False

        # Check for zero values in numeric fields (may be valid or invalid depending on context)
        # For assessed_value and sale_price, 0 is considered invalid
        if field in ["assessed_value", "sale_price"]:
            if isinstance(value, (int, float)) and value == 0:
                return False

        return True

    def get_quality_level(self, quality_score: float) -> str:
        """
        Determine quality level based on score.

        Thresholds:
        - >= 80: High Quality
        - 50-79: Medium Quality
        - < 50: Low Quality

        Args:
            quality_score: Quality score (0-100)

        Returns:
            Quality level string
        """
        if quality_score >= self.thresholds["high_quality"]:
            return "High"
        elif quality_score >= self.thresholds["medium_quality"]:
            return "Medium"
        else:
            return "Low"

    def calculate_completeness(self, record: Dict[str, Any]) -> float:
        """
        Calculate overall field completeness percentage.

        Args:
            record: Property record

        Returns:
            Completeness percentage (0-100)
        """
        # Get all weighted fields
        total_fields = len(self.score_weights)

        if total_fields == 0:
            return 0.0

        # Count non-empty fields
        filled_fields = sum(
            1 for field in self.score_weights.keys()
            if self._has_value(record, field)
        )

        # Calculate percentage
        completeness = (filled_fields / total_fields) * 100

        return round(completeness, 2)

    def enrich_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich a batch of property records.

        Args:
            records: List of property records

        Returns:
            List of enriched records
        """
        enriched_records = []

        for record in records:
            try:
                enriched = self.enrich_record(record)
                enriched_records.append(enriched)
            except Exception as e:
                self.logger.error(f"Failed to enrich record: {e}")
                # Keep original record if enrichment fails
                enriched_records.append(record)

        self.logger.info(f"Enriched {len(enriched_records)} records")

        return enriched_records

    def get_field_coverage(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate field coverage statistics across all records.

        Args:
            records: List of property records

        Returns:
            Dictionary with coverage statistics for each field
        """
        if not records:
            return {}

        total_records = len(records)
        coverage = {}

        for field in self.score_weights.keys():
            filled_count = sum(
                1 for record in records
                if self._has_value(record, field)
            )

            coverage[field] = {
                "filled_count": filled_count,
                "missing_count": total_records - filled_count,
                "coverage_percent": round((filled_count / total_records) * 100, 2),
                "weight": self.score_weights[field],
            }

        return coverage

    def get_quality_distribution(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate quality score distribution across records.

        Args:
            records: List of enriched property records

        Returns:
            Dictionary with quality distribution statistics
        """
        if not records:
            return {
                "total_records": 0,
                "high_quality": 0,
                "medium_quality": 0,
                "low_quality": 0,
                "avg_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
            }

        # Count by quality level
        high_count = sum(
            1 for rec in records
            if rec.get("quality_level") == "High"
        )
        medium_count = sum(
            1 for rec in records
            if rec.get("quality_level") == "Medium"
        )
        low_count = sum(
            1 for rec in records
            if rec.get("quality_level") == "Low"
        )

        # Get scores
        scores = [
            rec.get("quality_score", 0)
            for rec in records
            if "quality_score" in rec
        ]

        if not scores:
            scores = [0]

        return {
            "total_records": len(records),
            "high_quality": high_count,
            "medium_quality": medium_count,
            "low_quality": low_count,
            "high_quality_percent": round((high_count / len(records)) * 100, 2),
            "medium_quality_percent": round((medium_count / len(records)) * 100, 2),
            "low_quality_percent": round((low_count / len(records)) * 100, 2),
            "avg_score": round(sum(scores) / len(scores), 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
        }

    def filter_by_quality(
        self,
        records: List[Dict[str, Any]],
        min_quality_level: str = "Low",
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter records by quality criteria.

        Args:
            records: List of enriched property records
            min_quality_level: Minimum quality level (Low, Medium, High)
            min_score: Minimum quality score (0-100)

        Returns:
            Filtered list of records
        """
        quality_order = {"Low": 0, "Medium": 1, "High": 2}
        min_level_value = quality_order.get(min_quality_level, 0)

        filtered = []

        for record in records:
            # Check quality level
            record_level = record.get("quality_level", "Low")
            record_level_value = quality_order.get(record_level, 0)

            if record_level_value < min_level_value:
                continue

            # Check quality score
            if min_score is not None:
                record_score = record.get("quality_score", 0)
                if record_score < min_score:
                    continue

            filtered.append(record)

        self.logger.info(
            f"Filtered {len(records)} records to {len(filtered)} "
            f"(min level: {min_quality_level}, min score: {min_score})"
        )

        return filtered

    def sort_by_quality(
        self,
        records: List[Dict[str, Any]],
        descending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sort records by quality score.

        Args:
            records: List of enriched property records
            descending: Sort in descending order (highest quality first)

        Returns:
            Sorted list of records
        """
        return sorted(
            records,
            key=lambda r: r.get("quality_score", 0),
            reverse=descending
        )

    def get_top_quality_records(
        self,
        records: List[Dict[str, Any]],
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top N records by quality score.

        Args:
            records: List of enriched property records
            n: Number of top records to return

        Returns:
            List of top N records
        """
        sorted_records = self.sort_by_quality(records, descending=True)
        return sorted_records[:n]

    def add_rank(
        self,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Add quality rank to each record.

        Args:
            records: List of enriched property records

        Returns:
            List of records with quality_rank field added
        """
        # Sort by quality score
        sorted_records = self.sort_by_quality(records, descending=True)

        # Add rank
        for rank, record in enumerate(sorted_records, start=1):
            record["quality_rank"] = rank

        return sorted_records
