"""
Wake County API fetcher for property data.

This module handles fetching property records from the Wake County Open Data API
with rate limiting, retries, and error handling.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import (
    WAKE_COUNTY_API,
    RATE_LIMITS,
    COMPLIANCE_CONFIG,
    RAW_DATA_DIR,
)
from src.utils import get_logger, save_checkpoint, Timer


class WakeCountyAPIFetcher:
    """Fetcher for Wake County Open Data API."""

    def __init__(self):
        """Initialize the API fetcher."""
        self.logger = get_logger(__name__)
        self.config = WAKE_COUNTY_API
        self.base_url = WAKE_COUNTY_API["base_url"]
        self.endpoint = WAKE_COUNTY_API["endpoint"]
        self.max_records = WAKE_COUNTY_API["max_records"]
        self.timeout = WAKE_COUNTY_API["timeout"]
        self.retry_attempts = WAKE_COUNTY_API["retry_attempts"]
        self.retry_delay = WAKE_COUNTY_API["retry_delay"]

        # Rate limiting
        self.delay = RATE_LIMITS["api_delay"]

        # Compliance
        self.user_agent = COMPLIANCE_CONFIG["user_agent"]

        # Session for connection pooling
        self.session = self._create_session()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_records": 0,
        }

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with configured headers.

        Returns:
            Configured requests session
        """
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        })
        return session

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        attempt: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request with retry logic.

        Args:
            url: URL to request
            params: Query parameters
            attempt: Current attempt number

        Returns:
            JSON response or None if failed
        """
        self.stats["total_requests"] += 1

        try:
            self.logger.debug(f"Making request to {url} (attempt {attempt}/{self.retry_attempts})")

            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )

            response.raise_for_status()

            self.stats["successful_requests"] += 1
            return response.json()

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")

            # Don't retry on 4xx errors (client errors)
            if 400 <= response.status_code < 500:
                self.stats["failed_requests"] += 1
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"Request timeout (attempt {attempt}/{self.retry_attempts})")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")

        # Retry logic
        if attempt < self.retry_attempts:
            wait_time = self.retry_delay * attempt  # Exponential backoff
            self.logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return self._make_request(url, params, attempt + 1)

        self.stats["failed_requests"] += 1
        return None

    def fetch_properties(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch property records from Wake County ArcGIS API.

        Args:
            limit: Maximum number of records to fetch (default: max_records from config)
            offset: Number of records to skip
            filters: Optional filters to apply (e.g., {"CITY": "RALEIGH"})

        Returns:
            List of property records
        """
        with Timer("Wake County API fetch", self.logger):
            # Use configured max if no limit specified
            if limit is None:
                limit = self.max_records

            # Build request URL
            url = f"{self.base_url}/{self.endpoint}"

            # Build query parameters for ArcGIS
            params = self.config.get("query_params", {}).copy()

            # Set result count and offset
            params["resultRecordCount"] = min(limit, 2000)  # ArcGIS max is 2000
            params["resultOffset"] = offset

            # Add filters if provided
            if filters:
                # Build WHERE clause for ArcGIS
                where_clauses = [params.get("where", "1=1")]
                for key, value in filters.items():
                    where_clauses.append(f"{key}='{value}'")
                params["where"] = " AND ".join(where_clauses)

            self.logger.info(f"Fetching up to {limit} records from Wake County ArcGIS API...")

            # Make request
            data = self._make_request(url, params)

            if not data:
                self.logger.error("Failed to fetch data from API")
                return []

            # Extract records (ArcGIS format)
            records = self._extract_records(data)

            # Apply rate limiting
            if self.delay > 0:
                self.logger.debug(f"Rate limiting: waiting {self.delay} seconds")
                time.sleep(self.delay)

            self.stats["total_records"] += len(records)
            self.logger.info(f"Successfully fetched {len(records)} records")

            return records

    def _extract_records(self, data: Any) -> List[Dict[str, Any]]:
        """
        Extract property records from ArcGIS API response.

        Args:
            data: API response data

        Returns:
            List of property records
        """
        # ArcGIS returns: {"features": [{"attributes": {...}}, ...]}
        if isinstance(data, dict):
            features = data.get("features", [])
            # Extract attributes from each feature
            records = [feature.get("attributes", {}) for feature in features if "attributes" in feature]
            return records
        elif isinstance(data, list):
            # Fallback for list format
            return data
        else:
            self.logger.warning(f"Unexpected response format: {type(data)}")
            return []

    def fetch_and_normalize(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch property records and normalize to standard schema.

        Args:
            limit: Maximum number of records to fetch
            offset: Number of records to skip
            filters: Optional filters to apply

        Returns:
            List of normalized property records
        """
        # Fetch raw records
        raw_records = self.fetch_properties(limit, offset, filters)

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
        Normalize a single API record to standard schema.

        Args:
            record: Raw API record

        Returns:
            Normalized record or None if invalid
        """
        try:
            # Map ArcGIS fields to standard schema
            # Based on Wake County ArcGIS FeatureServer fields
            normalized = {
                "owner_name": record.get("OWNER", ""),
                "parcel_id": record.get("PIN_NUM", record.get("REID", "")),
                "property_address": record.get("SITE_ADDRESS", ""),
                "mailing_address": "",  # Not available in this dataset
                "city": record.get("CITY", ""),
                "state": "NC",
                "zip_code": str(record.get("ZIPNUM", "")) if record.get("ZIPNUM") else "",
                "county": "Wake",
                "assessed_value": record.get("TOTAL_VALUE_ASSD", None),
                "sale_date": record.get("SALE_DATE", ""),
                "sale_price": record.get("TOTSALPRICE", None),
                "source": "Wake County API",
                "source_url": f"{self.base_url}/{self.endpoint}",
                "extracted_at": datetime.now().isoformat(),
            }

            return normalized

        except Exception as e:
            self.logger.error(f"Failed to normalize record: {e}")
            return None

    def save_raw_data(self, records: List[Dict[str, Any]], filename: str = "wake_county_raw.json"):
        """
        Save raw API records to file.

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

    def get_statistics(self) -> Dict[str, int]:
        """
        Get fetcher statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics counters."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_records": 0,
        }

    def close(self):
        """Close the requests session."""
        if self.session:
            self.session.close()
            self.logger.debug("API session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
