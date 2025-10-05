"""
Unit tests for the PropertyValidator module.

Tests data validation according to FR-2.
"""

import pytest
from src.validator import PropertyValidator


@pytest.fixture
def validator():
    """Create a PropertyValidator instance for testing."""
    return PropertyValidator()


class TestRequiredFields:
    """Test required field validation (FR-2.1)."""

    def test_all_required_fields_present(self, validator):
        """Test validation passes when all required fields present."""
        record = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
            "source": "Test",
            "extracted_at": "2025-01-01",
        }

        is_valid, errors = validator.validate_record(record)

        assert is_valid is True
        assert len(errors) == 0

    def test_missing_required_field(self, validator):
        """Test validation fails when required field missing."""
        record = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
            # Missing 'source' and 'extracted_at'
        }

        is_valid, errors = validator.validate_record(record)

        assert is_valid is False
        assert any("source" in error.lower() for error in errors)
        assert any("extracted_at" in error.lower() for error in errors)

    def test_empty_required_field(self, validator):
        """Test validation fails when required field is empty."""
        record = {
            "owner_name": "",
            "property_address": "123 Main St",
            "source": "Test",
            "extracted_at": "2025-01-01",
        }

        is_valid, errors = validator.validate_record(record)

        assert is_valid is False
        assert any("owner_name" in error.lower() for error in errors)


class TestFieldTypes:
    """Test field type validation (FR-2.2)."""

    def test_correct_field_types(self, validator):
        """Test validation passes with correct types."""
        record = {
            "owner_name": "John Smith",
            "parcel_id": "ABC123",
            "property_address": "123 Main St",
            "assessed_value": 250000.00,
            "sale_price": 300000,
            "source": "Test",
            "extracted_at": "2025-01-01",
        }

        is_valid, errors = validator.validate_record(record, strict=False)

        # Type errors should not exist
        type_errors = [e for e in errors if "type" in e.lower()]
        assert len(type_errors) == 0

    def test_incorrect_field_type(self, validator):
        """Test validation detects incorrect types."""
        record = {
            "owner_name": 12345,  # Should be string
            "property_address": "123 Main St",
            "source": "Test",
            "extracted_at": "2025-01-01",
        }

        is_valid, errors = validator.validate_record(record, strict=True)

        assert any("owner_name" in error and "type" in error.lower() for error in errors)

    def test_optional_numeric_fields(self, validator):
        """Test that numeric fields can be None."""
        record = {
            "owner_name": "John Smith",
            "property_address": "123 Main St",
            "assessed_value": None,  # Optional
            "sale_price": None,  # Optional
            "source": "Test",
            "extracted_at": "2025-01-01",
        }

        is_valid, errors = validator.validate_record(record, strict=False)

        # Should be valid (these fields are optional)
        assert is_valid is True


class TestPatternValidation:
    """Test pattern matching validation (FR-2.3)."""

    def test_valid_zip_code_5_digit(self, validator):
        """Test 5-digit ZIP code pattern."""
        is_valid, errors = validator.validate_field("zip_code", "12345", check_pattern=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_valid_zip_code_9_digit(self, validator):
        """Test 9-digit ZIP code pattern."""
        is_valid, errors = validator.validate_field("zip_code", "12345-6789", check_pattern=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_zip_code(self, validator):
        """Test invalid ZIP code pattern."""
        is_valid, errors = validator.validate_field("zip_code", "ABCDE", check_pattern=True)

        assert is_valid is False
        assert len(errors) > 0

    def test_valid_state_code(self, validator):
        """Test valid state code pattern."""
        is_valid, errors = validator.validate_field("state", "NC", check_pattern=True)

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_state_code(self, validator):
        """Test invalid state code pattern."""
        is_valid, errors = validator.validate_field("state", "N", check_pattern=True)

        assert is_valid is False
        assert len(errors) > 0

    def test_valid_parcel_id(self, validator):
        """Test valid parcel ID pattern."""
        is_valid, errors = validator.validate_field("parcel_id", "ABC-123", check_pattern=True)

        assert is_valid is True

    def test_invalid_parcel_id(self, validator):
        """Test invalid parcel ID pattern."""
        is_valid, errors = validator.validate_field("parcel_id", "abc@123", check_pattern=True)

        assert is_valid is False


class TestBatchValidation:
    """Test batch validation."""

    def test_validate_batch_all_valid(self, validator):
        """Test batch validation with all valid records."""
        records = [
            {"owner_name": "John Smith", "property_address": "123 Main St", "source": "Test", "extracted_at": "2025-01-01"},
            {"owner_name": "Jane Doe", "property_address": "456 Oak Ave", "source": "Test", "extracted_at": "2025-01-01"},
        ]

        valid, invalid = validator.validate_batch(records)

        assert len(valid) == 2
        assert len(invalid) == 0

    def test_validate_batch_mixed(self, validator):
        """Test batch validation with mix of valid and invalid."""
        records = [
            {"owner_name": "John Smith", "property_address": "123 Main St", "source": "Test", "extracted_at": "2025-01-01"},
            {"owner_name": "", "property_address": "456 Oak Ave", "source": "Test", "extracted_at": "2025-01-01"},  # Invalid
            {"owner_name": "Bob Johnson", "property_address": "789 Elm St", "source": "Test", "extracted_at": "2025-01-01"},
        ]

        valid, invalid = validator.validate_batch(records)

        assert len(valid) == 2
        assert len(invalid) == 1
        assert invalid[0][0] == 1  # Index of invalid record

    def test_filter_valid_records(self, validator):
        """Test filtering to keep only valid records."""
        records = [
            {"owner_name": "John Smith", "property_address": "123 Main St", "source": "Test", "extracted_at": "2025-01-01"},
            {"owner_name": "", "property_address": "456 Oak Ave"},  # Invalid
        ]

        valid = validator.filter_valid_records(records)

        assert len(valid) == 1
        assert valid[0]["owner_name"] == "John Smith"


class TestValidationSummary:
    """Test validation summary statistics."""

    def test_validation_summary(self, validator):
        """Test validation summary generation."""
        invalid = [
            (0, {}, ["Missing required field: owner_name", "Missing required field: source"]),
            (1, {}, ["Missing required field: property_address"]),
            (2, {}, ["Missing required field: owner_name"]),
        ]

        summary = validator.get_validation_summary(invalid)

        assert summary["total_invalid"] == 3
        assert "error_counts" in summary
        assert "most_common_errors" in summary
        assert len(summary["most_common_errors"]) > 0

    def test_validation_summary_empty(self, validator):
        """Test validation summary with no errors."""
        summary = validator.get_validation_summary([])

        assert summary["total_invalid"] == 0
        assert summary["error_counts"] == {}


class TestHelperMethods:
    """Test helper methods."""

    def test_is_required_field(self, validator):
        """Test required field check."""
        assert validator.is_required_field("owner_name") is True
        assert validator.is_required_field("assessed_value") is False

    def test_get_field_type(self, validator):
        """Test field type retrieval."""
        field_type = validator.get_field_type("owner_name")
        assert field_type is str

        field_type = validator.get_field_type("assessed_value")
        assert field_type is not None

    def test_get_field_pattern(self, validator):
        """Test field pattern retrieval."""
        pattern = validator.get_field_pattern("zip_code")
        assert pattern is not None

        pattern = validator.get_field_pattern("owner_name")
        assert pattern is None  # No pattern for owner_name
