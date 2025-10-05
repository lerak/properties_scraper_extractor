#!/usr/bin/env python3
"""
Property Owner Extraction & Deduplication Pipeline - CLI Entry Point

This is the main command-line interface for running the property data
extraction pipeline.
"""

import click
import sys
from pathlib import Path

from src.pipeline import PropertyPipeline
from src.utils import setup_logging, get_logger


@click.command()
@click.option(
    "--api-limit",
    type=int,
    default=None,
    help="Maximum number of records to fetch from Wake County API (default: 1000)"
)
@click.option(
    "--scraper-limit",
    type=int,
    default=None,
    help="Maximum number of records to scrape from Orange County (default: 300)"
)
@click.option(
    "--no-api",
    is_flag=True,
    default=False,
    help="Disable Wake County API fetching"
)
@click.option(
    "--no-scraping",
    is_flag=True,
    default=False,
    help="Disable Orange County scraping"
)
@click.option(
    "--output-format",
    type=click.Choice(["excel", "csv", "json"], case_sensitive=False),
    default="excel",
    help="Output file format (default: excel)"
)
@click.option(
    "--no-checkpoints",
    is_flag=True,
    default=False,
    help="Disable checkpoint saving"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Logging level (default: INFO)"
)
@click.option(
    "--version",
    is_flag=True,
    help="Show version and exit"
)
def main(
    api_limit,
    scraper_limit,
    no_api,
    no_scraping,
    output_format,
    no_checkpoints,
    log_level,
    version
):
    """
    Property Owner Extraction & Deduplication Pipeline

    Extracts property owner data from Wake County API and Orange County
    Tax Assessor website, then validates, cleans, deduplicates, merges,
    and exports to formatted Excel/CSV/JSON.

    \b
    Examples:
      # Run full pipeline with defaults
      python main.py

      # API only, limit to 100 records
      python main.py --no-scraping --api-limit 100

      # Scraping only, output to CSV
      python main.py --no-api --output-format csv

      # Debug mode with verbose logging
      python main.py --log-level DEBUG
    """
    # Show version
    if version:
        click.echo("Property Owner Extraction Pipeline v1.0.0")
        return

    # Setup logging
    setup_logging(log_level)
    logger = get_logger(__name__)

    # Display banner
    click.echo("=" * 70)
    click.echo("  Property Owner Extraction & Deduplication Pipeline")
    click.echo("=" * 70)
    click.echo()

    # Validate options
    if no_api and no_scraping:
        logger.error("Cannot disable both API and scraping")
        click.echo("Error: Cannot disable both --no-api and --no-scraping", err=True)
        sys.exit(1)

    # Display configuration
    click.echo("Configuration:")
    api_status = "Disabled" if no_api else f"Enabled (limit: {api_limit or 'default'})"
    click.echo(f"  Wake County API: {api_status}")
    scraper_status = "Disabled" if no_scraping else f"Enabled (limit: {scraper_limit or 'default'})"
    click.echo(f"  Orange County Scraping: {scraper_status}")
    click.echo(f"  Output Format: {output_format.upper()}")
    click.echo(f"  Checkpoints: {'Disabled' if no_checkpoints else 'Enabled'}")
    click.echo(f"  Log Level: {log_level}")
    click.echo()

    try:
        # Initialize pipeline
        logger.info("Initializing pipeline...")
        pipeline = PropertyPipeline(
            enable_api=not no_api,
            enable_scraping=not no_scraping,
            enable_checkpoints=not no_checkpoints
        )

        # Run pipeline
        click.echo("Starting pipeline execution...")
        click.echo()

        result = pipeline.run(
            api_limit=api_limit,
            scraper_limit=scraper_limit,
            output_format=output_format.lower()
        )

        # Display results
        click.echo()
        click.echo("=" * 70)

        if result["success"]:
            click.echo("  ✓ Pipeline Completed Successfully!")
            click.echo("=" * 70)
            click.echo()

            # Summary
            click.echo("Summary:")
            click.echo(f"  Total Records: {result['total_records']}")
            click.echo(f"  Output File: {result['output_path']}")
            click.echo(f"  Duration: {result['statistics']['duration_seconds']} seconds")
            click.echo()

            # Detailed statistics
            if log_level == "DEBUG":
                click.echo("Detailed Statistics:")
                _print_statistics(result["statistics"])

            sys.exit(0)
        else:
            click.echo("  ✗ Pipeline Failed")
            click.echo("=" * 70)
            click.echo()
            click.echo(f"Error: {result['error']}", err=True)

            sys.exit(1)

    except KeyboardInterrupt:
        click.echo()
        logger.warning("Pipeline interrupted by user")
        click.echo("Pipeline interrupted by user", err=True)
        sys.exit(130)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo()
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def _print_statistics(stats: dict, indent: int = 2):
    """
    Print statistics in a formatted way.

    Args:
        stats: Statistics dictionary
        indent: Indentation level
    """
    prefix = " " * indent

    for key, value in stats.items():
        if isinstance(value, dict):
            click.echo(f"{prefix}{key}:")
            _print_statistics(value, indent + 2)
        else:
            click.echo(f"{prefix}{key}: {value}")


@click.group()
def cli():
    """Property Owner Extraction Pipeline - Additional Commands"""
    pass


@cli.command()
@click.option(
    "--checkpoint-name",
    type=str,
    default=None,
    help="Specific checkpoint to clear (default: all)"
)
def clear_checkpoints(checkpoint_name):
    """Clear saved pipeline checkpoints."""
    from src.utils import clear_checkpoints as clear_cp

    count = clear_cp(checkpoint_name)
    click.echo(f"Cleared {count} checkpoint file(s)")


@cli.command()
def list_outputs():
    """List all output files."""
    from config.settings import OUTPUT_DIR

    files = list(OUTPUT_DIR.glob("*"))

    if not files:
        click.echo("No output files found")
        return

    click.echo(f"Output files in {OUTPUT_DIR}:")
    for file_path in sorted(files):
        size = file_path.stat().st_size
        click.echo(f"  {file_path.name} ({size:,} bytes)")


@cli.command()
@click.argument("module", type=click.Choice(["validator", "cleaner", "deduplicator"]))
def test_module(module):
    """Run basic tests for a specific module."""
    click.echo(f"Testing {module} module...")

    if module == "validator":
        from src.validator import PropertyValidator
        validator = PropertyValidator()

        test_record = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
            "source": "Test",
            "extracted_at": "2025-01-01"
        }

        is_valid, errors = validator.validate_record(test_record)
        click.echo(f"  Valid: {is_valid}")
        if errors:
            click.echo(f"  Errors: {errors}")

    elif module == "cleaner":
        from src.cleaner import PropertyCleaner
        cleaner = PropertyCleaner()

        test_name = "SMITH, JOHN"
        cleaned = cleaner.normalize_owner_name(test_name)
        click.echo(f"  '{test_name}' → '{cleaned}'")

        test_addr = "123 Main Street"
        cleaned_addr = cleaner.normalize_address(test_addr)
        click.echo(f"  '{test_addr}' → '{cleaned_addr}'")

    elif module == "deduplicator":
        from src.deduplicator import PropertyDeduplicator
        dedup = PropertyDeduplicator()

        rec1 = {"owner_name": "John Smith", "property_address": "123 Main St"}
        rec2 = {"owner_name": "John Smith", "property_address": "123 Main Street"}

        is_dup = dedup._is_fuzzy_duplicate(rec1, rec2)
        scores = dedup.get_similarity_score(rec1, rec2)

        click.echo(f"  Is duplicate: {is_dup}")
        click.echo(f"  Similarity scores: {scores}")

    click.echo("✓ Module test complete")


if __name__ == "__main__":
    # Use main() for direct execution, cli() for grouped commands
    main()
