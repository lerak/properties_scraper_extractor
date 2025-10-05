"""
Configuration settings for the Property Owner Extraction & Deduplication Pipeline.

This module contains all configuration parameters including data sources,
rate limits, thresholds, file paths, and processing parameters.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base Directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
SRC_DIR = BASE_DIR / "src"
TESTS_DIR = BASE_DIR / "tests"
LOGS_DIR = BASE_DIR / "logs"
NOTEBOOKS_DIR = BASE_DIR / "notebooks"

# Data Subdirectories
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"

# Ensure directories exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, CHECKPOINT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# =======================
# Data Source Configuration
# =======================

# Wake County API Configuration
# ArcGIS FeatureServer REST API for property parcels
WAKE_COUNTY_API = {
    "base_url": "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/FeatureServer/0",
    "endpoint": "query",
    "max_records": 1000,
    "timeout": 30,  # seconds
    "retry_attempts": 3,
    "retry_delay": 5,  # seconds
    "query_params": {
        "where": "1=1",  # Query all records
        "outFields": "*",  # All fields
        "f": "json",  # JSON format
        "returnGeometry": "false",  # No geometry needed
    }
}

# Orange County Web Scraping Configuration
ORANGE_COUNTY_SCRAPER = {
    "base_url": "https://orange.propertytaxpayments.net/search",
    "max_records": 300,
    "timeout": 30,  # seconds
    "headless": True,
    "browser": "chromium",  # chromium, firefox, or webkit
    "search_type": "owner_name",  # Default search type
}

# =======================
# Rate Limiting Configuration
# =======================

RATE_LIMITS = {
    "api_delay": 0.5,  # seconds between API requests
    "scraper_delay": 2.5,  # seconds between page requests (2-3 seconds as per requirements)
    "max_concurrent_requests": 1,  # sequential processing for politeness
}

# =======================
# Processing Thresholds
# =======================

# Deduplication Thresholds (FR-4.2)
DEDUP_THRESHOLDS = {
    "exact_match_fields": ["parcel_id"],  # Fields for exact matching
    "fuzzy_name_threshold": 90,  # Minimum similarity % for owner names
    "fuzzy_address_threshold": 95,  # Minimum similarity % for addresses
    "fuzzy_algorithm": "token_sort_ratio",  # fuzzywuzzy algorithm
}

# Quality Score Weights (FR-6.2)
QUALITY_SCORE_WEIGHTS = {
    "owner_name": 20,
    "parcel_id": 15,
    "property_address": 15,
    "mailing_address": 10,
    "city": 5,
    "state": 5,
    "zip_code": 5,
    "county": 5,
    "assessed_value": 10,
    "sale_date": 5,
    "sale_price": 5,
}

# Quality Score Thresholds
QUALITY_THRESHOLDS = {
    "high_quality": 80,  # >= 80 = High Quality
    "medium_quality": 50,  # 50-79 = Medium Quality
    # < 50 = Low Quality
}

# =======================
# Data Validation Rules
# =======================

# Required Fields (FR-2)
REQUIRED_FIELDS = [
    "owner_name",
    "property_address",
    "source",
    "extracted_at",
]

# Field Type Validation
FIELD_TYPES = {
    "owner_name": str,
    "parcel_id": str,
    "property_address": str,
    "mailing_address": str,
    "city": str,
    "state": str,
    "zip_code": str,
    "county": str,
    "assessed_value": (int, float, type(None)),
    "sale_date": str,
    "sale_price": (int, float, type(None)),
    "source": str,
    "source_url": str,
    "extracted_at": str,
}

# Pattern Validation (FR-2.3)
VALIDATION_PATTERNS = {
    "zip_code": r"^\d{5}(-\d{4})?$",  # 12345 or 12345-6789
    "parcel_id": r"^[A-Z0-9\-]+$",  # Alphanumeric with hyphens
    "state": r"^[A-Z]{2}$",  # Two-letter state code
}

# =======================
# Normalization Rules (FR-3)
# =======================

# Owner Name Normalization
NAME_NORMALIZATION = {
    "convert_last_first": True,  # "SMITH, JOHN" -> "JOHN SMITH"
    "entity_suffixes": ["LLC", "CORP", "INC", "TRUST", "LP", "LLP", "CO"],
    "title_case": True,  # Convert to title case
    "remove_extra_spaces": True,
}

# Address Normalization
ADDRESS_NORMALIZATION = {
    "street_abbreviations": {
        "STREET": "ST",
        "AVENUE": "AVE",
        "BOULEVARD": "BLVD",
        "DRIVE": "DR",
        "ROAD": "RD",
        "LANE": "LN",
        "COURT": "CT",
        "CIRCLE": "CIR",
        "PLACE": "PL",
        "NORTH": "N",
        "SOUTH": "S",
        "EAST": "E",
        "WEST": "W",
    },
    "uppercase": True,
    "remove_extra_spaces": True,
}

# =======================
# Excel Export Configuration (FR-7)
# =======================

EXCEL_CONFIG = {
    "file_prefix": "property_owners",
    "sheets": {
        "All_Properties": {
            "name": "All Properties",
            "description": "Complete dataset with all properties",
        },
        "Wake_County": {
            "name": "Wake County",
            "description": "Properties from Wake County API",
        },
        "Orange_County": {
            "name": "Orange County",
            "description": "Properties from Orange County scraper",
        },
        "Duplicates": {
            "name": "Duplicates",
            "description": "Identified duplicate records",
        },
        "Statistics": {
            "name": "Statistics",
            "description": "Pipeline statistics and metadata",
        },
    },
    "formatting": {
        "freeze_panes": "A2",  # Freeze header row
        "auto_filter": True,
        "column_width": 20,
        "header_bold": True,
        "header_background": "D3D3D3",  # Light gray
    },
    "conditional_formatting": {
        "quality_score": {
            "high": {"min": 80, "color": "90EE90"},  # Light green
            "medium": {"min": 50, "max": 79, "color": "FFFFE0"},  # Light yellow
            "low": {"max": 49, "color": "FFB6C6"},  # Light red
        },
    },
}

# =======================
# Logging Configuration
# =======================

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "%(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "pipeline.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console", "file"],
    },
}

# =======================
# Pipeline Configuration
# =======================

PIPELINE_CONFIG = {
    "enable_checkpoints": True,
    "checkpoint_frequency": 100,  # Save checkpoint every N records
    "enable_progress_bar": True,
    "parallel_processing": False,  # Sequential for politeness
    "max_workers": 1,
}

# =======================
# Legal & Compliance
# =======================

COMPLIANCE_CONFIG = {
    "respect_robots_txt": True,
    "user_agent": "PropertyDataExtractor/1.0 (Educational/Portfolio Project)",
    "max_retries": 3,
    "backoff_factor": 2,
    "request_timeout": 30,
}

# =======================
# Environment Variables
# =======================

def get_env_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Dict containing environment-specific configuration
    """
    return {
        "DEBUG": os.getenv("DEBUG", "False").lower() == "true",
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "OUTPUT_FORMAT": os.getenv("OUTPUT_FORMAT", "excel"),
        "ENABLE_SCRAPING": os.getenv("ENABLE_SCRAPING", "True").lower() == "true",
    }

# Load environment configuration
ENV_CONFIG = get_env_config()
