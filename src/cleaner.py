"""
Data cleaning module for property records.

This module normalizes owner names and addresses according to
the requirements (FR-3).
"""

import re
from typing import Dict, List, Optional, Any

from config.settings import NAME_NORMALIZATION, ADDRESS_NORMALIZATION
from src.utils import get_logger


class PropertyCleaner:
    """Cleaner for normalizing property record data."""

    def __init__(self):
        """Initialize the cleaner."""
        self.logger = get_logger(__name__)
        self.name_config = NAME_NORMALIZATION
        self.address_config = ADDRESS_NORMALIZATION

    def clean_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize a property record.

        Args:
            record: Property record to clean

        Returns:
            Cleaned record
        """
        cleaned = record.copy()

        # Clean owner name
        if "owner_name" in cleaned:
            cleaned["owner_name"] = self.normalize_owner_name(cleaned["owner_name"])

        # Clean addresses
        for address_field in ["property_address", "mailing_address"]:
            if address_field in cleaned:
                cleaned[address_field] = self.normalize_address(cleaned[address_field])

        # Clean city
        if "city" in cleaned:
            cleaned["city"] = self.normalize_city(cleaned["city"])

        # Clean state
        if "state" in cleaned:
            cleaned["state"] = self.normalize_state(cleaned["state"])

        # Clean zip code
        if "zip_code" in cleaned:
            cleaned["zip_code"] = self.normalize_zip_code(cleaned["zip_code"])

        return cleaned

    def normalize_owner_name(self, name: str) -> str:
        """
        Normalize owner name according to FR-3.1.

        Transformations:
        - Convert "LAST, FIRST" to "FIRST LAST"
        - Handle entity suffixes (LLC, CORP, etc.)
        - Convert to title case
        - Remove extra spaces

        Args:
            name: Raw owner name

        Returns:
            Normalized owner name
        """
        if not name or not isinstance(name, str):
            return ""

        # Remove extra spaces
        if self.name_config["remove_extra_spaces"]:
            name = " ".join(name.split())

        # Convert "LAST, FIRST" to "FIRST LAST"
        if self.name_config["convert_last_first"]:
            name = self._convert_last_first_format(name)

        # Handle entity suffixes
        if self.name_config["entity_suffixes"]:
            name = self._normalize_entity_suffix(name)

        # Convert to title case
        if self.name_config["title_case"]:
            name = self._to_title_case(name)

        # Final cleanup: remove extra spaces again
        name = " ".join(name.split())

        return name.strip()

    def _convert_last_first_format(self, name: str) -> str:
        """
        Convert "LAST, FIRST" format to "FIRST LAST".

        Args:
            name: Name in "LAST, FIRST" format

        Returns:
            Name in "FIRST LAST" format
        """
        # Check if name contains comma (indicating "LAST, FIRST" format)
        if "," in name:
            parts = name.split(",", 1)
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()

                # Check if this looks like a person's name (not a company)
                # Companies usually don't have commas in this format
                if not any(suffix in name.upper() for suffix in ["LLC", "CORP", "INC", "TRUST", "LP", "LLP"]):
                    return f"{first_name} {last_name}"

        return name

    def _normalize_entity_suffix(self, name: str) -> str:
        """
        Normalize entity suffixes (LLC, CORP, INC, etc.).

        Args:
            name: Entity name

        Returns:
            Name with normalized suffix
        """
        name_upper = name.upper()

        for suffix in self.name_config["entity_suffixes"]:
            # Check for various formats: "LLC", "L.L.C.", "L L C", etc.
            patterns = [
                rf'\b{suffix}\b',  # Standard: "LLC"
                rf'\b{re.escape("".join(c + "." for c in suffix))}\b',  # Dotted: "L.L.C."
                rf'\b{" ".join(suffix)}\b',  # Spaced: "L L C"
            ]

            for pattern in patterns:
                if re.search(pattern, name_upper):
                    # Replace with standard format
                    name = re.sub(pattern, suffix, name_upper, flags=re.IGNORECASE)
                    break

        return name

    def _to_title_case(self, name: str) -> str:
        """
        Convert name to title case while preserving acronyms.

        Args:
            name: Name to convert

        Returns:
            Title-cased name
        """
        # List of words that should stay uppercase
        uppercase_words = self.name_config["entity_suffixes"] + ["LLC", "LP", "LLP"]

        words = name.split()
        result = []

        for word in words:
            # Keep entity suffixes uppercase
            if word.upper() in uppercase_words:
                result.append(word.upper())
            # Keep already uppercase acronyms (2-3 letters)
            elif len(word) <= 3 and word.isupper():
                result.append(word)
            # Title case for regular words
            else:
                result.append(word.title())

        return " ".join(result)

    def normalize_address(self, address: str) -> str:
        """
        Normalize street address according to FR-3.2.

        Transformations:
        - Standardize street abbreviations (STREET → ST)
        - Convert to uppercase
        - Remove extra spaces

        Args:
            address: Raw address

        Returns:
            Normalized address
        """
        if not address or not isinstance(address, str):
            return ""

        # Remove extra spaces
        if self.address_config["remove_extra_spaces"]:
            address = " ".join(address.split())

        # Convert to uppercase
        if self.address_config["uppercase"]:
            address = address.upper()

        # Standardize street abbreviations
        address = self._standardize_street_abbreviations(address)

        # Final cleanup
        address = " ".join(address.split())

        return address.strip()

    def _standardize_street_abbreviations(self, address: str) -> str:
        """
        Standardize street type abbreviations.

        Args:
            address: Address string

        Returns:
            Address with standardized abbreviations
        """
        abbreviations = self.address_config["street_abbreviations"]

        for full_word, abbrev in abbreviations.items():
            # Match whole words only (with word boundaries)
            pattern = rf'\b{re.escape(full_word)}\b'
            address = re.sub(pattern, abbrev, address, flags=re.IGNORECASE)

        return address

    def normalize_city(self, city: str) -> str:
        """
        Normalize city name.

        Args:
            city: Raw city name

        Returns:
            Normalized city name
        """
        if not city or not isinstance(city, str):
            return ""

        # Remove extra spaces and convert to title case
        city = " ".join(city.split())
        city = city.title()

        return city.strip()

    def normalize_state(self, state: str) -> str:
        """
        Normalize state code.

        Args:
            state: Raw state code

        Returns:
            Normalized state code (uppercase, 2 letters)
        """
        if not state or not isinstance(state, str):
            return ""

        # Convert to uppercase and trim
        state = state.strip().upper()

        # If state name is full (e.g., "North Carolina"), convert to abbreviation
        state_abbrev_map = {
            "NORTH CAROLINA": "NC",
            "SOUTH CAROLINA": "SC",
            "VIRGINIA": "VA",
            "GEORGIA": "GA",
            "TENNESSEE": "TN",
        }

        if state in state_abbrev_map:
            state = state_abbrev_map[state]

        # Ensure it's 2 characters
        if len(state) > 2:
            state = state[:2]

        return state

    def normalize_zip_code(self, zip_code: str) -> str:
        """
        Normalize ZIP code.

        Args:
            zip_code: Raw ZIP code

        Returns:
            Normalized ZIP code (5 or 9 digit format)
        """
        if not zip_code or not isinstance(zip_code, str):
            return ""

        # Remove all non-digit characters except hyphen
        zip_code = re.sub(r'[^\d-]', '', zip_code)

        # Remove leading/trailing hyphens
        zip_code = zip_code.strip('-')

        # Handle 9-digit ZIP (12345-6789)
        if '-' in zip_code:
            parts = zip_code.split('-')
            if len(parts) == 2:
                main = parts[0].zfill(5)  # Pad main part to 5 digits
                ext = parts[1][:4].ljust(4, '0')  # Extension is 4 digits
                return f"{main}-{ext}"

        # Handle continuous 9-digit ZIP (123456789)
        elif len(zip_code) == 9:
            return f"{zip_code[:5]}-{zip_code[5:]}"

        # Handle 5-digit ZIP
        elif len(zip_code) <= 5:
            return zip_code.zfill(5)  # Pad to 5 digits

        # Invalid format - return first 5 digits
        else:
            return zip_code[:5]

    def clean_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean a batch of property records.

        Args:
            records: List of property records

        Returns:
            List of cleaned records
        """
        cleaned_records = []

        for record in records:
            try:
                cleaned = self.clean_record(record)
                cleaned_records.append(cleaned)
            except Exception as e:
                self.logger.error(f"Failed to clean record: {e}")
                # Keep original record if cleaning fails
                cleaned_records.append(record)

        self.logger.info(f"Cleaned {len(cleaned_records)} records")
        return cleaned_records
