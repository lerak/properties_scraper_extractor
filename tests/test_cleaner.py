"""
Unit tests for the PropertyCleaner module.

Tests name and address normalization according to FR-3.
"""

import pytest
from src.cleaner import PropertyCleaner


@pytest.fixture
def cleaner():
    """Create a PropertyCleaner instance for testing."""
    return PropertyCleaner()


class TestOwnerNameNormalization:
    """Test owner name normalization (FR-3.1)."""

    def test_last_first_conversion(self, cleaner):
        """Test 'LAST, FIRST' to 'FIRST LAST' conversion."""
        assert cleaner.normalize_owner_name("SMITH, JOHN") == "John Smith"
        assert cleaner.normalize_owner_name("SMITH, JOHN MICHAEL") == "John Michael Smith"

    def test_entity_suffixes(self, cleaner):
        """Test entity suffix normalization."""
        assert cleaner.normalize_owner_name("ABC Properties L.L.C.") == "ABC Properties LLC"
        assert cleaner.normalize_owner_name("XYZ Corporation Inc.") == "Xyz Corporation INC"
        assert cleaner.normalize_owner_name("Smith Family Trust") == "Smith Family TRUST"

    def test_extra_spaces(self, cleaner):
        """Test extra space removal."""
        assert cleaner.normalize_owner_name("  Extra   Spaces  ") == "Extra Spaces"
        assert cleaner.normalize_owner_name("John    Smith") == "John Smith"

    def test_empty_string(self, cleaner):
        """Test empty string handling."""
        assert cleaner.normalize_owner_name("") == ""
        assert cleaner.normalize_owner_name("   ") == ""

    def test_none_handling(self, cleaner):
        """Test None handling."""
        assert cleaner.normalize_owner_name(None) == ""

    def test_special_characters(self, cleaner):
        """Test special character handling."""
        result = cleaner.normalize_owner_name("O'BRIEN & SONS")
        assert "O'Brien" in result or "Obrien" in result
        assert "Sons" in result

    def test_mixed_case(self, cleaner):
        """Test mixed case conversion."""
        assert cleaner.normalize_owner_name("jOhN sMiTh") == "John Smith"

    def test_title_case_preservation(self, cleaner):
        """Test that title case is applied correctly."""
        result = cleaner.normalize_owner_name("JOHN SMITH")
        assert result == "John Smith"


class TestAddressNormalization:
    """Test address normalization (FR-3.2)."""

    def test_street_abbreviations(self, cleaner):
        """Test street type abbreviations."""
        assert cleaner.normalize_address("123 Main Street") == "123 MAIN ST"
        assert cleaner.normalize_address("456 Oak Avenue") == "456 OAK AVE"
        assert cleaner.normalize_address("789 North Elm Road") == "789 N ELM RD"

    def test_multiple_abbreviations(self, cleaner):
        """Test multiple abbreviations in one address."""
        result = cleaner.normalize_address("100 South East Park Drive")
        assert "S" in result
        assert "E" in result
        assert "DR" in result

    def test_extra_spaces(self, cleaner):
        """Test extra space removal."""
        assert cleaner.normalize_address("123  Main   Street") == "123 MAIN ST"

    def test_empty_string(self, cleaner):
        """Test empty string handling."""
        assert cleaner.normalize_address("") == ""
        assert cleaner.normalize_address("   ") == ""

    def test_uppercase_conversion(self, cleaner):
        """Test uppercase conversion."""
        result = cleaner.normalize_address("123 main street")
        assert result.isupper()

    def test_complex_address(self, cleaner):
        """Test complex address with multiple components."""
        result = cleaner.normalize_address("456 North Oak Avenue Apartment 2")
        assert "N" in result
        assert "AVE" in result


class TestCityNormalization:
    """Test city name normalization."""

    def test_title_case(self, cleaner):
        """Test city name title casing."""
        assert cleaner.normalize_city("chapel hill") == "Chapel Hill"
        assert cleaner.normalize_city("RALEIGH") == "Raleigh"

    def test_extra_spaces(self, cleaner):
        """Test extra space removal."""
        assert cleaner.normalize_city("  Chapel   Hill  ") == "Chapel Hill"

    def test_empty_string(self, cleaner):
        """Test empty string handling."""
        assert cleaner.normalize_city("") == ""


class TestStateNormalization:
    """Test state code normalization."""

    def test_uppercase_conversion(self, cleaner):
        """Test state code uppercase."""
        assert cleaner.normalize_state("nc") == "NC"
        assert cleaner.normalize_state("Nc") == "NC"

    def test_full_name_conversion(self, cleaner):
        """Test full state name to abbreviation."""
        assert cleaner.normalize_state("North Carolina") == "NC"
        assert cleaner.normalize_state("NORTH CAROLINA") == "NC"

    def test_truncation(self, cleaner):
        """Test truncation to 2 characters."""
        assert cleaner.normalize_state("NCA") == "NC"

    def test_empty_string(self, cleaner):
        """Test empty string handling."""
        assert cleaner.normalize_state("") == ""


class TestZipCodeNormalization:
    """Test ZIP code normalization."""

    def test_5_digit_zip(self, cleaner):
        """Test 5-digit ZIP code."""
        assert cleaner.normalize_zip_code("12345") == "12345"
        assert cleaner.normalize_zip_code("123") == "00123"

    def test_9_digit_zip_with_hyphen(self, cleaner):
        """Test 9-digit ZIP code with hyphen."""
        assert cleaner.normalize_zip_code("12345-6789") == "12345-6789"

    def test_9_digit_zip_without_hyphen(self, cleaner):
        """Test 9-digit ZIP code without hyphen."""
        assert cleaner.normalize_zip_code("123456789") == "12345-6789"

    def test_zip_with_spaces(self, cleaner):
        """Test ZIP code with spaces."""
        result = cleaner.normalize_zip_code("12345 6789")
        assert "-" in result or len(result) == 5

    def test_empty_string(self, cleaner):
        """Test empty string handling."""
        assert cleaner.normalize_zip_code("") == ""


class TestRecordCleaning:
    """Test full record cleaning."""

    def test_clean_record(self, cleaner):
        """Test cleaning a complete record."""
        record = {
            "owner_name": "SMITH, JOHN",
            "property_address": "123 Main Street",
            "mailing_address": "456 Oak Avenue",
            "city": "chapel hill",
            "state": "nc",
            "zip_code": "12345",
        }

        cleaned = cleaner.clean_record(record)

        assert cleaned["owner_name"] == "John Smith"
        assert "MAIN ST" in cleaned["property_address"]
        assert "OAK AVE" in cleaned["mailing_address"]
        assert cleaned["city"] == "Chapel Hill"
        assert cleaned["state"] == "NC"
        assert cleaned["zip_code"] == "12345"

    def test_clean_batch(self, cleaner):
        """Test batch cleaning."""
        records = [
            {"owner_name": "SMITH, JOHN", "property_address": "123 Main Street"},
            {"owner_name": "DOE, JANE", "property_address": "456 Oak Avenue"},
        ]

        cleaned = cleaner.clean_batch(records)

        assert len(cleaned) == 2
        assert cleaned[0]["owner_name"] == "John Smith"
        assert cleaned[1]["owner_name"] == "Jane Doe"
