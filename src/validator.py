"""
Data validation module for property records.

This module validates property records against required fields,
data types, and patterns as defined in the requirements.
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from config.settings import (
    REQUIRED_FIELDS,
    FIELD_TYPES,
    VALIDATION_PATTERNS,
)
from src.utils import get_logger


class PropertyValidator:
    """Validator for property records."""

    def __init__(self):
        """Initialize the validator."""
        self.logger = get_logger(__name__)
        self.required_fields = REQUIRED_FIELDS
        self.field_types = FIELD_TYPES
        self.patterns = VALIDATION_PATTERNS

        # Compiled regex patterns for efficiency
        self.compiled_patterns = {
            field: re.compile(pattern)
            for field, pattern in self.patterns.items()
        }

    def validate_record(
        self,
        record: Dict[str, Any],
        strict: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Validate a single property record.

        Args:
            record: Property record to validate
            strict: If True, fail on any validation error. If False, only fail on missing required fields.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate required fields
        required_errors = self._validate_required_fields(record)
        errors.extend(required_errors)

        # If strict mode or required fields missing, stop here
        if strict or required_errors:
            if required_errors:
                return False, errors

        # Validate field types
        type_errors = self._validate_field_types(record)
        errors.extend(type_errors)

        # Validate field patterns
        pattern_errors = self._validate_patterns(record)
        errors.extend(pattern_errors)

        # Determine validity
        is_valid = len(errors) == 0 if strict else len(required_errors) == 0

        return is_valid, errors

    def _validate_required_fields(self, record: Dict[str, Any]) -> List[str]:
        """
        Validate that all required fields are present and non-empty.

        Args:
            record: Property record

        Returns:
            List of error messages
        """
        errors = []

        for field in self.required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")
            elif record[field] is None or (isinstance(record[field], str) and not record[field].strip()):
                errors.append(f"Required field is empty: {field}")

        return errors

    def _validate_field_types(self, record: Dict[str, Any]) -> List[str]:
        """
        Validate field data types.

        Args:
            record: Property record

        Returns:
            List of error messages
        """
        errors = []

        for field, expected_type in self.field_types.items():
            if field not in record:
                continue  # Skip missing fields (handled by required fields check)

            value = record[field]

            # Skip None values (optional fields)
            if value is None:
                continue

            # Check if value matches expected type(s)
            if isinstance(expected_type, tuple):
                # Multiple allowed types
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' has invalid type: expected {expected_type}, got {type(value)}"
                    )
            else:
                # Single expected type
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' has invalid type: expected {expected_type}, got {type(value)}"
                    )

        return errors

    def _validate_patterns(self, record: Dict[str, Any]) -> List[str]:
        """
        Validate field patterns using regex.

        Args:
            record: Property record

        Returns:
            List of error messages
        """
        errors = []

        for field, pattern in self.compiled_patterns.items():
            if field not in record:
                continue  # Skip missing fields

            value = record[field]

            # Skip None or empty values
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            # Convert to string if needed
            value_str = str(value).strip()

            # Validate against pattern
            if not pattern.match(value_str):
                errors.append(
                    f"Field '{field}' does not match required pattern: {value_str}"
                )

        return errors

    def validate_batch(
        self,
        records: List[Dict[str, Any]],
        strict: bool = False,
        stop_on_error: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, Dict[str, Any], List[str]]]]:
        """
        Validate a batch of property records.

        Args:
            records: List of property records
            strict: If True, use strict validation
            stop_on_error: If True, stop validation on first error

        Returns:
            Tuple of (valid_records, invalid_records_with_errors)
            where invalid_records_with_errors is a list of (index, record, errors)
        """
        valid_records = []
        invalid_records = []

        for idx, record in enumerate(records):
            is_valid, errors = self.validate_record(record, strict=strict)

            if is_valid:
                valid_records.append(record)
            else:
                invalid_records.append((idx, record, errors))

                if stop_on_error:
                    self.logger.warning(f"Stopping validation at record {idx} due to errors")
                    break

        self.logger.info(
            f"Validated {len(records)} records: {len(valid_records)} valid, {len(invalid_records)} invalid"
        )

        return valid_records, invalid_records

    def get_validation_summary(
        self,
        invalid_records: List[Tuple[int, Dict[str, Any], List[str]]]
    ) -> Dict[str, Any]:
        """
        Generate a summary of validation errors.

        Args:
            invalid_records: List of invalid records with errors

        Returns:
            Dictionary with validation summary statistics
        """
        if not invalid_records:
            return {
                "total_invalid": 0,
                "error_counts": {},
                "most_common_errors": [],
            }

        # Count error types
        error_counts = {}
        for _, _, errors in invalid_records:
            for error in errors:
                # Extract error type (first part before ':')
                error_type = error.split(":")[0].strip()
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Sort errors by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_invalid": len(invalid_records),
            "error_counts": error_counts,
            "most_common_errors": sorted_errors[:5],  # Top 5 errors
        }

    def filter_valid_records(
        self,
        records: List[Dict[str, Any]],
        strict: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Filter and return only valid records.

        Args:
            records: List of property records
            strict: If True, use strict validation

        Returns:
            List of valid records
        """
        valid_records, invalid_records = self.validate_batch(records, strict=strict)

        if invalid_records:
            self.logger.warning(f"Filtered out {len(invalid_records)} invalid records")

            # Log first few errors for debugging
            for idx, record, errors in invalid_records[:3]:
                self.logger.debug(f"Record {idx} errors: {errors}")

        return valid_records

    def validate_field(
        self,
        field_name: str,
        value: Any,
        check_type: bool = True,
        check_pattern: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate a single field value.

        Args:
            field_name: Name of the field
            value: Field value
            check_type: Whether to check type validation
            check_pattern: Whether to check pattern validation

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check type
        if check_type and field_name in self.field_types:
            expected_type = self.field_types[field_name]

            if value is not None:
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Invalid type: expected {expected_type}, got {type(value)}"
                        )
                else:
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Invalid type: expected {expected_type}, got {type(value)}"
                        )

        # Check pattern
        if check_pattern and field_name in self.compiled_patterns:
            if value is not None and str(value).strip():
                pattern = self.compiled_patterns[field_name]
                value_str = str(value).strip()

                if not pattern.match(value_str):
                    errors.append(f"Does not match required pattern: {value_str}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def is_required_field(self, field_name: str) -> bool:
        """
        Check if a field is required.

        Args:
            field_name: Name of the field

        Returns:
            True if field is required, False otherwise
        """
        return field_name in self.required_fields

    def get_field_type(self, field_name: str) -> Optional[Any]:
        """
        Get expected type for a field.

        Args:
            field_name: Name of the field

        Returns:
            Expected type or None if not defined
        """
        return self.field_types.get(field_name)

    def get_field_pattern(self, field_name: str) -> Optional[str]:
        """
        Get validation pattern for a field.

        Args:
            field_name: Name of the field

        Returns:
            Regex pattern string or None if not defined
        """
        return self.patterns.get(field_name)
