"""
Utility functions for the Property Owner Extraction & Deduplication Pipeline.

This module provides logging setup, helper functions, and common utilities
used throughout the application.
"""

import logging
import logging.config
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

from config.settings import LOGGING_CONFIG, CHECKPOINT_DIR


# =======================
# Logging Setup
# =======================

def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        log_level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Apply logging configuration
    logging.config.dictConfig(LOGGING_CONFIG)

    # Get root logger
    logger = logging.getLogger()

    # Override log level if specified
    if log_level:
        logger.setLevel(getattr(logging, log_level.upper()))

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# =======================
# Checkpoint Management
# =======================

def save_checkpoint(data: Any, checkpoint_name: str) -> Path:
    """
    Save pipeline checkpoint to disk.

    Args:
        data: Data to save (must be JSON-serializable)
        checkpoint_name: Name of the checkpoint file

    Returns:
        Path to saved checkpoint file
    """
    logger = get_logger(__name__)

    # Create checkpoint filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_file = CHECKPOINT_DIR / f"{checkpoint_name}_{timestamp}.json"

    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Checkpoint saved: {checkpoint_file}")
        return checkpoint_file

    except Exception as e:
        logger.error(f"Failed to save checkpoint {checkpoint_name}: {e}")
        raise


def load_checkpoint(checkpoint_name: str, latest: bool = True) -> Optional[Any]:
    """
    Load pipeline checkpoint from disk.

    Args:
        checkpoint_name: Name prefix of the checkpoint file
        latest: If True, load the most recent checkpoint

    Returns:
        Loaded checkpoint data or None if not found
    """
    logger = get_logger(__name__)

    # Find matching checkpoint files
    checkpoint_files = list(CHECKPOINT_DIR.glob(f"{checkpoint_name}_*.json"))

    if not checkpoint_files:
        logger.warning(f"No checkpoint found for: {checkpoint_name}")
        return None

    # Sort by modification time and get latest
    if latest:
        checkpoint_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
    else:
        checkpoint_file = checkpoint_files[0]

    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Checkpoint loaded: {checkpoint_file}")
        return data

    except Exception as e:
        logger.error(f"Failed to load checkpoint {checkpoint_file}: {e}")
        return None


def clear_checkpoints(checkpoint_name: Optional[str] = None) -> int:
    """
    Clear checkpoint files.

    Args:
        checkpoint_name: Specific checkpoint name to clear, or None for all

    Returns:
        Number of files deleted
    """
    logger = get_logger(__name__)

    # Determine pattern
    pattern = f"{checkpoint_name}_*.json" if checkpoint_name else "*.json"

    # Find and delete files
    checkpoint_files = list(CHECKPOINT_DIR.glob(pattern))
    count = 0

    for file_path in checkpoint_files:
        try:
            file_path.unlink()
            count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {file_path}: {e}")

    logger.info(f"Cleared {count} checkpoint file(s)")
    return count


# =======================
# Data Utilities
# =======================

def generate_record_hash(record: Dict[str, Any], fields: List[str]) -> str:
    """
    Generate a unique hash for a record based on specific fields.

    Args:
        record: Property record dictionary
        fields: List of field names to include in hash

    Returns:
        MD5 hash string
    """
    # Extract values for specified fields
    values = []
    for field in fields:
        value = record.get(field, "")
        # Normalize to string and lowercase
        value_str = str(value).strip().lower() if value else ""
        values.append(value_str)

    # Create concatenated string
    combined = "|".join(values)

    # Generate MD5 hash
    hash_obj = hashlib.md5(combined.encode('utf-8'))
    return hash_obj.hexdigest()


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get a value from a dictionary with optional default.

    Args:
        data: Dictionary to query
        key: Key to retrieve
        default: Default value if key not found or value is None/empty

    Returns:
        Value from dictionary or default
    """
    value = data.get(key, default)

    # Return default if value is None or empty string
    if value is None or (isinstance(value, str) and not value.strip()):
        return default

    return value


def parse_currency(value: str) -> Optional[float]:
    """
    Parse currency string to float.

    Args:
        value: Currency string (e.g., "$1,234.56", "1234.56")

    Returns:
        Float value or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None

    try:
        # Remove currency symbols and commas
        cleaned = value.strip().replace("$", "").replace(",", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def parse_date(date_str: str, formats: Optional[List[str]] = None) -> Optional[str]:
    """
    Parse date string to ISO format (YYYY-MM-DD).

    Args:
        date_str: Date string to parse
        formats: List of datetime formats to try (default common formats)

    Returns:
        ISO formatted date string or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    # Default formats to try
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to append if truncated

    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def validate_dict_structure(data: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    Validate that a dictionary contains all required keys.

    Args:
        data: Dictionary to validate
        required_keys: List of required key names

    Returns:
        True if all required keys present, False otherwise
    """
    return all(key in data for key in required_keys)


# =======================
# Progress Tracking
# =======================

def print_progress(current: int, total: int, prefix: str = "", bar_length: int = 50):
    """
    Print a progress bar to console.

    Args:
        current: Current progress count
        total: Total count
        prefix: Prefix string to display
        bar_length: Length of the progress bar in characters
    """
    if total == 0:
        percent = 100.0
    else:
        percent = min(100.0 * current / total, 100.0)

    filled_length = int(bar_length * current // total) if total > 0 else bar_length
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write(f'\r{prefix} |{bar}| {percent:.1f}% ({current}/{total})')
    sys.stdout.flush()

    if current >= total:
        print()  # New line when complete


# =======================
# File Utilities
# =======================

def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to directory

    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: Path) -> str:
    """
    Get human-readable file size.

    Args:
        file_path: Path to file

    Returns:
        File size string (e.g., "1.23 MB")
    """
    if not file_path.exists():
        return "0 B"

    size_bytes = file_path.stat().st_size

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.2f} PB"


# =======================
# Timing Utilities
# =======================

class Timer:
    """Context manager for timing code execution."""

    def __init__(self, name: str = "Operation", logger: Optional[logging.Logger] = None):
        """
        Initialize timer.

        Args:
            name: Name of the operation being timed
            logger: Logger instance to use for output
        """
        self.name = name
        self.logger = logger or get_logger(__name__)
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start the timer."""
        self.start_time = datetime.now()
        self.logger.info(f"{self.name} started...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and log duration."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.info(f"{self.name} completed in {duration:.2f} seconds")

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
