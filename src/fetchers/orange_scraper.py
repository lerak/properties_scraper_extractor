"""
Orange County property scraper using Playwright.

This module implements scraping for the Orange County Tax Assessor website,
extending the base web scraper class.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import ORANGE_COUNTY_SCRAPER, RAW_DATA_DIR
from config.selectors import ORANGE_COUNTY_SELECTORS, get_selector
from src.fetchers.web_scraper import WebScraperBase
from src.utils import get_logger, Timer


class OrangeCountyScraper(WebScraperBase):
    """Scraper for Orange County Tax Assessor website."""

    def __init__(self):
        """Initialize Orange County scraper."""
        super().__init__(
            headless=ORANGE_COUNTY_SCRAPER["headless"],
            browser_type=ORANGE_COUNTY_SCRAPER["browser"],
            timeout=ORANGE_COUNTY_SCRAPER["timeout"] * 1000,  # Convert to ms
        )

        self.base_url = ORANGE_COUNTY_SCRAPER["base_url"]
        self.max_records = ORANGE_COUNTY_SCRAPER["max_records"]

        self.logger = get_logger(__name__)

    def scrape_properties(
        self,
        max_records: Optional[int] = None,
        search_params: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape property records from Orange County website.

        Args:
            max_records: Maximum number of records to scrape
            search_params: Optional search parameters (e.g., {"city": "Chapel Hill"})

        Returns:
            List of scraped property records
        """
        with Timer("Orange County scraping", self.logger):
            # Use configured max if not specified
            if max_records is None:
                max_records = self.max_records

            self.logger.info(f"Starting Orange County scrape (max {max_records} records)")

            # Navigate to base URL
            if not self.navigate(self.base_url):
                self.logger.error("Failed to navigate to Orange County website")
                return []

            # Perform search if parameters provided
            if search_params:
                if not self._perform_search(search_params):
                    self.logger.error("Search failed")
                    return []

            # Extract property records
            records = self._extract_property_records(max_records)

            self.logger.info(f"Successfully scraped {len(records)} records")
            return records

    def _perform_search(self, search_params: Dict[str, str]) -> bool:
        """
        Perform a property search.

        Args:
            search_params: Search parameters

        Returns:
            True if search successful, False otherwise
        """
        try:
            self.logger.debug(f"Performing search with params: {search_params}")

            selectors = ORANGE_COUNTY_SELECTORS["search_form"]

            # Fill search form
            for field, value in search_params.items():
                field_selector = selectors.get(f"{field}_input")
                if field_selector:
                    self.fill_input(field_selector, value)

            # Submit search
            submit_selector = selectors.get("search_button") or selectors.get("submit_button")
            if submit_selector:
                self.click(submit_selector)
            else:
                self.logger.warning("No submit button selector found")
                return False

            # Wait for results
            time.sleep(2)  # Allow page to load
            return True

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return False

    def _extract_property_records(self, max_records: int) -> List[Dict[str, Any]]:
        """
        Extract property records from search results or listings.

        Args:
            max_records: Maximum number of records to extract

        Returns:
            List of property records
        """
        records = []
        property_links = self._get_property_links(max_records)

        if not property_links:
            self.logger.warning("No property links found, attempting direct extraction")
            # Try extracting from current page
            record = self._extract_single_property()
            if record:
                records.append(record)
            return records

        self.logger.info(f"Found {len(property_links)} property links")

        # Visit each property page
        for idx, link in enumerate(property_links, 1):
            try:
                self.logger.debug(f"Processing property {idx}/{len(property_links)}: {link}")

                # Navigate to property detail page
                if not self.navigate(link):
                    self.logger.warning(f"Failed to navigate to {link}")
                    self.stats["failed_extractions"] += 1
                    continue

                # Extract property data
                record = self._extract_single_property()

                if record:
                    records.append(record)
                    self.stats["successful_extractions"] += 1
                    self.stats["total_records"] += 1
                else:
                    self.stats["failed_extractions"] += 1

                # Check if we've reached max records
                if len(records) >= max_records:
                    self.logger.info(f"Reached maximum records limit: {max_records}")
                    break

            except Exception as e:
                self.logger.error(f"Failed to process property {link}: {e}")
                self.stats["failed_extractions"] += 1
                continue

        return records

    def _get_property_links(self, max_links: int) -> List[str]:
        """
        Extract links to property detail pages.

        Args:
            max_links: Maximum number of links to extract

        Returns:
            List of property detail URLs
        """
        links = []

        try:
            # Check if results table exists
            table_selectors = ORANGE_COUNTY_SELECTORS["results_table"]

            # Try to find results table
            for selector_name in ["table", "table_alt"]:
                selector = table_selectors.get(selector_name)
                if selector and self.check_element_exists(selector):
                    # Extract links from table rows
                    row_selector = table_selectors.get("rows") or table_selectors.get("rows_alt")
                    if row_selector:
                        # Get all row elements
                        rows = self.page.query_selector_all(row_selector)

                        for row in rows[:max_links]:
                            # Try to find link in row
                            link_element = row.query_selector("a[href]")
                            if link_element:
                                href = link_element.get_attribute("href")
                                if href:
                                    # Make absolute URL if relative
                                    if href.startswith("http"):
                                        full_url = href
                                    else:
                                        base = self.base_url.rsplit("/", 1)[0]
                                        full_url = f"{base}/{href.lstrip('/')}"

                                    links.append(full_url)

                        if links:
                            break

        except Exception as e:
            self.logger.error(f"Failed to extract property links: {e}")

        return links

    def _extract_single_property(self) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single property detail page.

        Returns:
            Property record dictionary or None if extraction fails
        """
        try:
            # Get selectors for property details
            detail_selectors = ORANGE_COUNTY_SELECTORS["property_details"]

            # Extract all fields
            record = {
                "owner_name": self.extract_text(detail_selectors["owner_name"]),
                "parcel_id": self.extract_text(detail_selectors["parcel_id"]),
                "property_address": self.extract_text(detail_selectors["property_address"]),
                "mailing_address": self.extract_text(detail_selectors["mailing_address"]),
                "city": self.extract_text(detail_selectors["city"]),
                "state": self.extract_text(detail_selectors["state"]),
                "zip_code": self.extract_text(detail_selectors["zip_code"]),
                "county": "Orange",
                "assessed_value": self.extract_text(detail_selectors["assessed_value"]),
                "sale_date": self.extract_text(detail_selectors["sale_date"]),
                "sale_price": self.extract_text(detail_selectors["sale_price"]),
                "source": "Orange County Scraper",
                "source_url": self.page.url,
                "extracted_at": datetime.now().isoformat(),
            }

            # Check if we got meaningful data
            if not record["owner_name"] and not record["parcel_id"]:
                self.logger.warning("No owner name or parcel ID found")
                return None

            return record

        except Exception as e:
            self.logger.error(f"Failed to extract property data: {e}")
            return None

    def scrape_and_normalize(
        self,
        max_records: Optional[int] = None,
        search_params: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape property records and normalize data.

        Args:
            max_records: Maximum number of records to scrape
            search_params: Optional search parameters

        Returns:
            List of normalized property records
        """
        # Scrape raw records
        raw_records = self.scrape_properties(max_records, search_params)

        if not raw_records:
            return []

        # Normalize records
        normalized_records = []
        for record in raw_records:
            normalized = self._normalize_record(record)
            if normalized:
                normalized_records.append(normalized)

        self.logger.info(f"Normalized {len(normalized_records)} records")
        return normalized_records

    def _normalize_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize a scraped record.

        Args:
            record: Raw scraped record

        Returns:
            Normalized record or None if invalid
        """
        try:
            # Record is already in standard schema format
            # Just clean up any empty strings to None for consistency
            normalized = {}

            for key, value in record.items():
                if isinstance(value, str):
                    # Clean whitespace
                    value = value.strip()
                    # Convert empty strings to empty (not None, to preserve schema)
                    normalized[key] = value if value else ""
                else:
                    normalized[key] = value

            return normalized

        except Exception as e:
            self.logger.error(f"Failed to normalize record: {e}")
            return None

    def save_raw_data(
        self,
        records: List[Dict[str, Any]],
        filename: str = "orange_county_raw.json"
    ):
        """
        Save raw scraped records to file.

        Args:
            records: List of records to save
            filename: Output filename
        """
        filepath = RAW_DATA_DIR / filename

        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, default=str)

            self.logger.info(f"Saved {len(records)} raw records to {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to save raw data: {e}")
