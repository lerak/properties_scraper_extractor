"""
Main pipeline orchestration module.

This module coordinates all stages of the property data extraction pipeline:
1. Data Fetching (API + Scraping)
2. Validation
3. Cleaning/Normalization
4. Deduplication
5. Merging
6. Enrichment
7. Export
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from config.settings import PIPELINE_CONFIG, ENV_CONFIG
from src.fetchers.api_fetcher import WakeCountyAPIFetcher
from src.fetchers.orange_scraper import OrangeCountyScraper
from src.validator import PropertyValidator
from src.cleaner import PropertyCleaner
from src.deduplicator import PropertyDeduplicator
from src.merger import PropertyMerger
from src.enricher import PropertyEnricher
from src.exporter import PropertyExporter
from src.utils import get_logger, setup_logging, Timer, save_checkpoint


class PropertyPipeline:
    """Main orchestration pipeline for property data extraction."""

    def __init__(
        self,
        enable_api: bool = True,
        enable_scraping: bool = True,
        enable_checkpoints: bool = True
    ):
        """
        Initialize the pipeline.

        Args:
            enable_api: Whether to fetch from Wake County API
            enable_scraping: Whether to scrape Orange County data
            enable_checkpoints: Whether to save checkpoints
        """
        # Setup logging
        setup_logging()
        self.logger = get_logger(__name__)

        # Configuration
        self.enable_api = enable_api
        self.enable_scraping = enable_scraping and ENV_CONFIG.get("ENABLE_SCRAPING", True)
        self.enable_checkpoints = enable_checkpoints and PIPELINE_CONFIG["enable_checkpoints"]

        # Initialize components
        self.validator = PropertyValidator()
        self.cleaner = PropertyCleaner()
        self.deduplicator = PropertyDeduplicator()
        self.merger = PropertyMerger()
        self.enricher = PropertyEnricher()
        self.exporter = PropertyExporter()

        # Pipeline state
        self.statistics = {
            "pipeline_started": None,
            "pipeline_completed": None,
            "duration_seconds": 0,
            "stages": {},
        }

        self.logger.info("Pipeline initialized")

    def run(
        self,
        api_limit: Optional[int] = None,
        scraper_limit: Optional[int] = None,
        output_format: str = "excel"
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline.

        Args:
            api_limit: Maximum records to fetch from API
            scraper_limit: Maximum records to scrape
            output_format: Output format (excel, csv, json)

        Returns:
            Dictionary with pipeline results and statistics
        """
        with Timer("Complete pipeline", self.logger):
            self.statistics["pipeline_started"] = datetime.now().isoformat()

            try:
                # Stage 1: Data Fetching
                wake_records, orange_records = self._stage_fetch_data(api_limit, scraper_limit)

                # Stage 2: Validation
                wake_records, orange_records = self._stage_validate(wake_records, orange_records)

                # Stage 3: Cleaning
                wake_records, orange_records = self._stage_clean(wake_records, orange_records)

                # Stage 4: Merging
                all_records, merge_stats = self._stage_merge(wake_records, orange_records)

                # Stage 5: Deduplication
                deduplicated_records, duplicates = self._stage_deduplicate(all_records)

                # Stage 6: Enrichment
                enriched_records = self._stage_enrich(deduplicated_records)

                # Stage 7: Export
                output_path = self._stage_export(
                    enriched_records,
                    wake_records,
                    orange_records,
                    duplicates,
                    output_format
                )

                # Finalize statistics
                self.statistics["pipeline_completed"] = datetime.now().isoformat()
                self._calculate_final_stats(enriched_records, duplicates)

                self.logger.info("Pipeline completed successfully!")

                return {
                    "success": True,
                    "output_path": str(output_path),
                    "total_records": len(enriched_records),
                    "statistics": self.statistics,
                }

            except Exception as e:
                self.logger.error(f"Pipeline failed: {e}", exc_info=True)
                self.statistics["pipeline_completed"] = datetime.now().isoformat()
                self.statistics["error"] = str(e)

                return {
                    "success": False,
                    "error": str(e),
                    "statistics": self.statistics,
                }

    def _stage_fetch_data(
        self,
        api_limit: Optional[int],
        scraper_limit: Optional[int]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Stage 1: Fetch data from API and scraper.

        Args:
            api_limit: API record limit
            scraper_limit: Scraper record limit

        Returns:
            Tuple of (wake_records, orange_records)
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 1: Data Fetching")
        self.logger.info("=" * 60)

        wake_records = []
        orange_records = []

        # Fetch from Wake County API
        if self.enable_api:
            try:
                with WakeCountyAPIFetcher() as api_fetcher:
                    wake_records = api_fetcher.fetch_and_normalize(limit=api_limit)
                    api_fetcher.save_raw_data(wake_records)

                    self.statistics["stages"]["fetch_api"] = {
                        "records_fetched": len(wake_records),
                        "statistics": api_fetcher.get_statistics(),
                    }

            except Exception as e:
                self.logger.error(f"API fetching failed: {e}")
                self.statistics["stages"]["fetch_api"] = {"error": str(e)}

        # Scrape from Orange County
        if self.enable_scraping:
            try:
                with OrangeCountyScraper() as scraper:
                    scraper.start()
                    orange_records = scraper.scrape_and_normalize(max_records=scraper_limit)
                    scraper.save_raw_data(orange_records)

                    self.statistics["stages"]["fetch_scraper"] = {
                        "records_scraped": len(orange_records),
                        "statistics": scraper.get_statistics(),
                    }

            except Exception as e:
                self.logger.error(f"Scraping failed: {e}")
                self.statistics["stages"]["fetch_scraper"] = {"error": str(e)}

        # Checkpoint
        if self.enable_checkpoints:
            save_checkpoint(
                {"wake_records": wake_records, "orange_records": orange_records},
                "01_fetched_data"
            )

        self.logger.info(f"Fetch complete: {len(wake_records)} Wake + {len(orange_records)} Orange")

        return wake_records, orange_records

    def _stage_validate(
        self,
        wake_records: List[Dict[str, Any]],
        orange_records: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Stage 2: Validate records.

        Args:
            wake_records: Wake County records
            orange_records: Orange County records

        Returns:
            Tuple of (validated_wake_records, validated_orange_records)
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 2: Validation")
        self.logger.info("=" * 60)

        # Validate Wake County records
        wake_valid = self.validator.filter_valid_records(wake_records, strict=False)

        # Validate Orange County records
        orange_valid = self.validator.filter_valid_records(orange_records, strict=False)

        self.statistics["stages"]["validation"] = {
            "wake_valid": len(wake_valid),
            "wake_invalid": len(wake_records) - len(wake_valid),
            "orange_valid": len(orange_valid),
            "orange_invalid": len(orange_records) - len(orange_valid),
        }

        self.logger.info(
            f"Validation complete: {len(wake_valid)} Wake + {len(orange_valid)} Orange valid"
        )

        return wake_valid, orange_valid

    def _stage_clean(
        self,
        wake_records: List[Dict[str, Any]],
        orange_records: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Stage 3: Clean and normalize records.

        Args:
            wake_records: Wake County records
            orange_records: Orange County records

        Returns:
            Tuple of (cleaned_wake_records, cleaned_orange_records)
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 3: Cleaning & Normalization")
        self.logger.info("=" * 60)

        # Clean Wake County records
        wake_cleaned = self.cleaner.clean_batch(wake_records)

        # Clean Orange County records
        orange_cleaned = self.cleaner.clean_batch(orange_records)

        self.statistics["stages"]["cleaning"] = {
            "wake_cleaned": len(wake_cleaned),
            "orange_cleaned": len(orange_cleaned),
        }

        # Checkpoint
        if self.enable_checkpoints:
            save_checkpoint(
                {"wake_records": wake_cleaned, "orange_records": orange_cleaned},
                "02_cleaned_data"
            )

        self.logger.info(
            f"Cleaning complete: {len(wake_cleaned)} Wake + {len(orange_cleaned)} Orange"
        )

        return wake_cleaned, orange_cleaned

    def _stage_merge(
        self,
        wake_records: List[Dict[str, Any]],
        orange_records: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Stage 4: Merge records from different sources.

        Args:
            wake_records: Wake County records
            orange_records: Orange County records

        Returns:
            Tuple of (merged_records, merge_statistics)
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 4: Merging")
        self.logger.info("=" * 60)

        # Merge records
        merged_records, merge_stats = self.merger.merge_sources(wake_records, orange_records)

        self.statistics["stages"]["merging"] = merge_stats

        self.logger.info(f"Merging complete: {merge_stats['total']} total records")

        return merged_records, merge_stats

    def _stage_deduplicate(
        self,
        records: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Stage 5: Deduplicate records.

        Args:
            records: All records

        Returns:
            Tuple of (deduplicated_records, duplicate_records)
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 5: Deduplication")
        self.logger.info("=" * 60)

        # Deduplicate
        deduplicated, duplicates = self.deduplicator.deduplicate_and_merge(
            records,
            merge_strategy="most_complete"
        )

        # Get duplicate statistics
        unique_records, duplicate_groups = self.deduplicator.find_duplicates(records)
        dedup_stats = self.deduplicator.get_duplicate_statistics(duplicate_groups)

        self.statistics["stages"]["deduplication"] = {
            "input_records": len(records),
            "unique_records": len(deduplicated),
            "duplicates_removed": len(duplicates),
            "duplicate_groups": dedup_stats.get("total_groups", 0),
        }

        # Checkpoint
        if self.enable_checkpoints:
            save_checkpoint(
                {"deduplicated": deduplicated, "duplicates": duplicates},
                "03_deduplicated_data"
            )

        self.logger.info(
            f"Deduplication complete: {len(deduplicated)} unique, {len(duplicates)} duplicates"
        )

        return deduplicated, duplicates

    def _stage_enrich(
        self,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 6: Enrich records with quality scores.

        Args:
            records: Deduplicated records

        Returns:
            Enriched records
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 6: Enrichment")
        self.logger.info("=" * 60)

        # Enrich records
        enriched = self.enricher.enrich_batch(records)

        # Get quality distribution
        quality_dist = self.enricher.get_quality_distribution(enriched)

        self.statistics["stages"]["enrichment"] = {
            "records_enriched": len(enriched),
            "quality_distribution": quality_dist,
        }

        # Checkpoint
        if self.enable_checkpoints:
            save_checkpoint(enriched, "04_enriched_data")

        self.logger.info(f"Enrichment complete: {len(enriched)} records enriched")

        return enriched

    def _stage_export(
        self,
        all_records: List[Dict[str, Any]],
        wake_records: List[Dict[str, Any]],
        orange_records: List[Dict[str, Any]],
        duplicates: List[Dict[str, Any]],
        output_format: str
    ) -> Path:
        """
        Stage 7: Export records to file.

        Args:
            all_records: All enriched records
            wake_records: Wake County records
            orange_records: Orange County records
            duplicates: Duplicate records
            output_format: Output format (excel, csv, json)

        Returns:
            Path to output file
        """
        self.logger.info("=" * 60)
        self.logger.info("STAGE 7: Export")
        self.logger.info("=" * 60)

        # Export based on format
        if output_format == "excel":
            output_path = self.exporter.export_to_excel(
                all_records,
                wake_records,
                orange_records,
                duplicates,
                self.statistics
            )
        elif output_format == "csv":
            output_path = self.exporter.export_to_csv(all_records)
        elif output_format == "json":
            output_path = self.exporter.export_to_json(all_records)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        self.statistics["stages"]["export"] = {
            "output_format": output_format,
            "output_path": str(output_path),
        }

        self.logger.info(f"Export complete: {output_path}")

        return output_path

    def _calculate_final_stats(
        self,
        final_records: List[Dict[str, Any]],
        duplicates: List[Dict[str, Any]]
    ):
        """
        Calculate final pipeline statistics.

        Args:
            final_records: Final enriched records
            duplicates: Duplicate records
        """
        # Calculate duration
        start_time = datetime.fromisoformat(self.statistics["pipeline_started"])
        end_time = datetime.fromisoformat(self.statistics["pipeline_completed"])
        duration = (end_time - start_time).total_seconds()

        self.statistics["duration_seconds"] = round(duration, 2)
        self.statistics["total_output_records"] = len(final_records)
        self.statistics["total_duplicates"] = len(duplicates)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Dictionary with pipeline statistics
        """
        return self.statistics.copy()
