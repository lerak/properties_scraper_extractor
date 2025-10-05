# REQUIREMENTS.MD - Technical Specifications

## Python Dependencies (requirements.txt)

```txt
# Core Data Processing
pandas>=1.5.0,<2.0.0
numpy>=1.24.0,<2.0.0

# Excel Generation
openpyxl>=3.1.0,<4.0.0

# Web Scraping
playwright>=1.40.0,<2.0.0
beautifulsoup4>=4.12.0,<5.0.0
lxml>=4.9.0,<5.0.0

# HTTP Requests
requests>=2.31.0,<3.0.0

# String Matching (Deduplication)
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0,<1.0.0

# Configuration & Environment
python-dotenv>=1.0.0,<2.0.0

# Progress Bars & CLI
tqdm>=4.66.0,<5.0.0
click>=8.1.0,<9.0.0

# Date/Time Handling
python-dateutil>=2.8.0,<3.0.0

# Development Dependencies (requirements-dev.txt)
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.12.0,<4.0.0
black>=23.0.0,<24.0.0
flake8>=6.0.0,<7.0.0
mypy>=1.7.0,<2.0.0
```

---

## System Requirements

### Minimum Specifications
- **CPU:** Dual-core processor (2.0 GHz or higher)
- **RAM:** 2 GB minimum, 4 GB recommended
- **Storage:** 
  - 500 MB for Python dependencies
  - 300 MB for Playwright browser binaries
  - 500 MB for data files and logs
  - **Total:** 1.5 GB free space minimum
- **Operating System:**
  - Windows 10 or higher
  - macOS 10.14 (Mojave) or higher
  - Linux (Ubuntu 20.04+, Debian 10+, Fedora 33+)
- **Python:** Version 3.8, 3.9, 3.10, or 3.11 (3.12 not tested)
- **Internet:** Stable broadband connection (required for API and scraping)

### Recommended Specifications (For 1000+ Records)
- **RAM:** 8 GB or more
- **Storage:** SSD for faster file I/O
- **Internet:** 10 Mbps or faster

---

## Functional Requirements

### FR-1: Data Acquisition

**FR-1.1: API Data Fetching**
- MUST fetch minimum 100 records from Wake County API
- MUST support pagination (configurable limit/offset)
- MUST handle rate limiting (max 1 request/second)
- MUST retry failed requests 3 times with exponential backoff
- MUST log all API requests with timestamp and response code
- MUST save raw JSON responses for debugging

**FR-1.2: Web Scraping**
- MUST scrape minimum 20 records from Orange County site
- MUST respect 2-second minimum delay between requests
- MUST use Playwright for JavaScript-heavy sites
- MUST save raw HTML for each scraped page
- MUST continue pipeline if individual scrapes fail
- MUST NOT exceed 500 requests per session

**FR-1.3: Checkpoint System**
- MUST save progress after every 10 records
- MUST allow resuming from last checkpoint
- MUST store checkpoints in data/checkpoints/

### FR-2: Data Validation

**FR-2.1: Required Field Validation**
- MUST validate presence of: owner_name, property_address, parcel_id
- MUST flag records with missing required fields as CRITICAL
- MUST flag empty strings or "N/A" as invalid

**FR-2.2: Data Type Validation**
- MUST verify string fields contain strings
- MUST verify numeric fields contain valid numbers
- MUST verify date fields match YYYY-MM-DD format

**FR-2.3: Pattern Validation**
- MUST flag PO Box addresses as WARNING
- MUST flag parcel IDs not matching expected format
- MUST detect suspicious patterns (all caps, all numbers in name)

**FR-2.4: Validation Reporting**
- MUST generate validation report with:
  - Count of invalid records
  - Breakdown by issue type (missing, invalid, suspicious)
  - Sample records for each issue type

### FR-3: Data Cleaning & Normalization

**FR-3.1: Owner Name Normalization**
- MUST convert all names to uppercase
- MUST handle "LAST, FIRST" format → "FIRST LAST"
- MUST standardize entity suffixes:
  - LLC, L.L.C., L L C, L. L. C. → LLC
  - CORP, CORPORATION, INC, INCORPORATED → CORP
  - TRUST, FAMILY TRUST, LIVING TRUST → TRUST
- MUST remove extra whitespace (multiple spaces → single)
- MUST preserve & and - characters
- MUST remove other special characters (!@#$%^*()+={}[]|\\:;"'<>?,./`)

**FR-3.2: Address Normalization**
- MUST convert all addresses to uppercase
- MUST extract unit numbers to separate field:
  - APT, APARTMENT, UNIT, STE, SUITE, #
- MUST standardize street suffixes:
  - STREET, STR, ST. → ST
  - AVENUE, AVE. → AVE
  - ROAD, RD. → RD
  - DRIVE, DR. → DR
  - BOULEVARD, BLVD. → BLVD
  - LANE, LN. → LN
  - COURT, CT. → CT
  - CIRCLE, CIR. → CIR
- MUST standardize directionals:
  - NORTH, N. → N
  - SOUTH, S. → S
  - EAST, E. → E
  - WEST, W. → W
  - NORTHEAST, NE., N.E. → NE
  - (etc. for all combinations)
- MUST remove extra whitespace

**FR-3.3: Parcel ID Normalization**
- MUST remove dashes and spaces
- MUST zero-pad to standard length if applicable
- MUST convert to uppercase

**FR-3.4: Preservation**
- MUST keep original values in separate fields
- MUST add normalized values as new fields
- MUST NOT overwrite original data

### FR-4: Deduplication

**FR-4.1: Exact Duplicate Detection**
- MUST group records by normalized_address
- MUST identify records with identical normalized_address as potential duplicates
- MUST compare city and ZIP to confirm (same city/ZIP = duplicate)

**FR-4.2: Fuzzy Duplicate Detection**
- MUST use Levenshtein distance for string similarity
- MUST flag as duplicate if:
  - Owner name similarity >= 90% AND
  - Address similarity >= 95%
- MUST be configurable (thresholds in settings)

**FR-4.3: Cross-Source Matching**
- MUST match records across sources using parcel_id as primary key
- MUST NOT treat cross-source matches as duplicates (these are merges)

**FR-4.4: Duplicate Resolution**
- MUST keep "best" record when duplicates found
- "Best" defined as:
  - Most complete (fewest NULL fields)
  - Most recent (if timestamp available)
  - From merged source (if one is merged, one is not)
- MUST mark non-kept records with:
  - is_duplicate = True
  - duplicate_of = [parcel_id of kept record]
  - dedup_reason = "exact_address_match" or "fuzzy_match"

**FR-4.5: Deduplication Reporting**
- MUST log count of duplicates removed
- MUST log reasons for duplicate flagging
- MUST include dedup stats in summary sheet

### FR-5: Data Merging

**FR-5.1: Cross-Source Matching**
- MUST match API records with scraped records by parcel_id
- MUST handle cases where:
  - Record exists in both sources (merge)
  - Record exists in API only (keep as-is)
  - Record exists in scraped only (keep as-is)

**FR-5.2: Field Merging Strategy**
- MUST use API as base record
- MUST add scraped fields as enhancements
- MUST NOT overwrite API core fields (owner, address) with scraped data
- MUST prefer scraped data for detail fields:
  - square_footage, year_built, bedrooms, bathrooms
  - sale_price, sale_date
  - deed_book, deed_page

**FR-5.3: Conflict Detection**
- MUST detect when owner_name differs by >10% between sources
- MUST detect when property_address differs between sources
- MUST flag all conflicts in notes field
- MUST log all conflicts to quality report

**FR-5.4: Source Tracking**
- MUST tag each record with data_source:
  - "api_only" - only from API
  - "scraped_only" - only from scraping
  - "merged" - combined from both
- MUST track which specific fields came from which source

**FR-5.5: Merge Statistics**
- MUST calculate enrichment rate: (merged_records / total_records) * 100
- MUST calculate fields added by scraping
- MUST include in summary sheet

### FR-6: Enrichment

**FR-6.1: Source URL Generation**
- MUST generate clickable URL to original county record
- URL format for Wake County: `https://data.wake.gov/property/{parcel_id}`
- URL format for Orange County: [actual URL pattern from research]
- MUST test generated URLs work (at least for sample)

**FR-6.2: Quality Score Calculation**
- MUST calculate 0-100 score using formula:
  ```
  Base = 0
  IF owner_name present: +15
  IF property_address present: +15
  IF parcel_id present: +10
  IF city present: +5
  IF state present: +2
  IF zip present: +3
  IF assessed_value present: +8
  IF sale_price present: +7
  IF sale_date present: +5
  IF square_footage present: +6
  IF year_built present: +6
  IF bedrooms present: +4
  IF bathrooms present: +4
  IF deed_book present: +3
  IF deed_page present: +2
  IF data_source = "merged": +10 bonus
  IF all_validated_clean: +5 bonus
  TOTAL capped at 100
  ```

**FR-6.3: Owner Type Classification**
- MUST classify as "individual" or "entity"
- Entity indicators: LLC, CORP, INC, TRUST, LP, LLP, PARTNERSHIP
- Default to "individual" if no indicators

**FR-6.4: Enrichment Level**
- MUST classify each record:
  - "basic" - only required fields present
  - "enhanced" - some optional fields present
  - "complete" - most/all optional fields present
- Thresholds:
  - basic: quality_score < 70
  - enhanced: quality_score 70-89
  - complete: quality_score >= 90

**FR-6.5: Notes Generation**
- MUST add notes for:
  - "Enriched with scraped data" (if merged)
  - "Missing sale data" (if no sale_price/date)
  - "Possible duplicate - manually review" (if fuzzy match close)
  - "Conflict detected: owner names differ" (if conflict)
  - "Low quality score - missing fields" (if score < 60)

**FR-6.6: Timestamp**
- MUST add fetch_timestamp to each record
- Format: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)

### FR-7: Excel Export

**FR-7.1: Multi-Sheet Workbook**
- MUST create 5 sheets:
  1. Combined Data
  2. API Data Only
  3. Scraped Enhancements
  4. Summary Statistics
  5. Data Quality Report

**FR-7.2: Sheet 1 - Combined Data Formatting**
- MUST include columns (in order):
  1. Owner Name (width: 30 chars)
  2. Property Address (width: 40 chars)
  3. City (width: 20 chars)
  4. State (width: 5 chars)
  5. ZIP (width: 10 chars)
  6. Parcel ID (width: 20 chars)
  7. Assessed Value (width: 15 chars, currency format)
  8. Sale Price (width: 15 chars, currency format)
  9. Sale Date (width: 12 chars, date format MM/DD/YYYY)
  10. Square Footage (width: 12 chars, number format with commas)
  11. Year Built (width: 10 chars)
  12. Bedrooms (width: 10 chars)
  13. Bathrooms (width: 10 chars)
  14. Owner Type (width: 15 chars)
  15. Quality Score (width: 12 chars)
  16. Source (width: 15 chars)
  17. Source URL (width: 15 chars, hyperlink display "View")
  18. Notes (width: 40 chars, text wrap enabled)

- MUST apply formatting:
  - Header row: Bold, background color (light blue), frozen pane
  - Auto-filter enabled on all columns
  - Alternate row colors (white, light gray)
  - Borders on all cells
  - Text alignment: Left for text, Right for numbers
  - Hyperlink source URLs using HYPERLINK() formula

- MUST apply conditional formatting:
  - Quality Score column:
    - Green background if >= 80
    - Yellow background if 60-79
    - Red background if < 60
  - Row color coding by Source:
    - Light blue if "api_only"
    - Light green if "scraped_only"
    - Light yellow if "merged"

**FR-7.3: Sheet 2 - API Data Only**
- MUST include all raw API records before enrichment
- MUST show baseline data quality
- MUST use same column structure as Sheet 1
- MUST NOT include scraped-only fields (leave blank)

**FR-7.4: Sheet 3 - Scraped Enhancements**
- MUST include only records that were scraped
- MUST highlight additional fields obtained through scraping
- MUST show enrichment value added

**FR-7.5: Sheet 4 - Summary Statistics**
- MUST include key metrics in two-column format (Metric | Value):
  - Total API Records Fetched
  - Total Scraped Records
  - Records After Validation
  - Duplicates Removed
  - Final Unique Records
  - Enrichment Rate (%)
  - Average Quality Score (Overall)
  - Average Quality Score (API Only)
  - Average Quality Score (Scraped Only)
  - Average Quality Score (Merged)
  - Field Completeness %: owner_name, property_address, parcel_id, assessed_value, sale_price, sale_date, square_footage, year_built, bedrooms, bathrooms
  - Data Collection Start Time
  - Data Collection End Time
  - Total Processing Time
  - Data Source: Wake County + Orange County

**FR-7.6: Sheet 5 - Data Quality Report**
- MUST include columns:
  - Parcel ID
  - Issue Type (CRITICAL | WARNING)
  - Issue Description
  - Quality Score
  - Link to Record (hyperlink to row in Sheet 1)
- MUST list all records with:
  - Missing required fields
  - Quality score < 60
  - Data conflicts between sources
  - Scraping failures
- MUST sort by severity (CRITICAL first, then WARNING)
- MUST sort by quality score (lowest first within severity)

**FR-7.7: File Naming**
- MUST use format: `property_owners_YYYYMMDD_HHMMSS_[source].xlsx`
- Example: `property_owners_20250115_143022_wake_county.xlsx`

**FR-7.8: File Size Management**
- IF record count > 10,000: MUST split into multiple files
- Each file max 10,000 records
- File naming: append `_part1`, `_part2`, etc.

### FR-8: Logging & Error Handling

**FR-8.1: Logging Requirements**
- MUST log to both console (stdout) and file
- Log file location: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- MUST use log levels appropriately:
  - DEBUG: Detailed diagnostic info (e.g., "Processing record 123")
  - INFO: Confirmation of expected behavior (e.g., "Fetched 100 records")
  - WARNING: Something unexpected but recoverable (e.g., "Missing field: sale_date")
  - ERROR: Serious problem, operation failed (e.g., "API request failed after 3 retries")
  - CRITICAL: Program may crash (e.g., "Cannot write to output file")

**FR-8.2: Log Content Requirements**
- MUST log with timestamp (ISO 8601 format)
- MUST log module/function name
- MUST log for:
  - Pipeline start/end
  - Each stage start/end
  - API requests (URL, params, response code, time taken)
  - Scraping operations (URL, success/failure, time taken)
  - Validation failures (record ID, reason)
  - Deduplication decisions (records merged, reason)
  - Data conflicts (fields, values, sources)
  - Errors with full stack trace

**FR-8.3: Error Handling Strategy**
- MUST catch and handle specific exceptions:
  - NetworkError → retry with backoff
  - TimeoutError → retry with longer timeout
  - ValidationError → log and skip record
  - FileNotFoundError → create directory/file
  - PermissionError → notify user, suggest fix
- MUST NOT crash pipeline on single record failure
- MUST continue processing remaining records
- MUST summarize all errors at end

**FR-8.4: Checkpoint System**
- MUST save checkpoint after:
  - API fetch complete
  - Scraping batch complete (every 10 records)
  - Cleaning complete
  - Deduplication complete
- Checkpoint format: JSON file with:
  - Stage completed
  - Records processed so far
  - Timestamp
  - Configuration used
- MUST support --resume flag to continue from last checkpoint

### FR-9: Command-Line Interface

**FR-9.1: Required Arguments**
- None (all optional with defaults)

**FR-9.2: Optional Arguments**
- `--limit INTEGER` (default: 100)
  - Number of records to fetch from API
  - Range: 1-10000
  
- `--scrape-limit INTEGER` (default: 20)
  - Number of records to scrape
  - Range: 0-500
  - If 0, skip scraping entirely
  
- `--source STRING` (default: "wake_county")
  - Data source identifier
  - Choices: wake_county, cook_county, travis_county
  
- `--output PATH` (default: "./data/output/owners.xlsx")
  - Output Excel file path
  - Must end in .xlsx
  
- `--skip-scraping` (flag)
  - Skip web scraping, use API only
  
- `--resume` (flag)
  - Resume from last checkpoint
  
- `--log-level STRING` (default: "INFO")
  - Logging verbosity
  - Choices: DEBUG, INFO, WARNING, ERROR, CRITICAL
  
- `--headless BOOL` (default: True)
  - Run browser in headless mode
  - Set to False for debugging scraper

**FR-9.3: Exit Codes**
- 0: Success
- 1: General error
- 2: Configuration error (invalid parameters)
- 3: Data source error (API/scraping failed)
- 4: Data quality error (too many validation failures)

**FR-9.4: Help Text**
- MUST provide --help flag
- MUST show all options with descriptions
- MUST show examples

### FR-10: Configuration Management

**FR-10.1: Settings File (config/settings.py)**
- MUST externalize all configurable values:
  - API URLs and endpoints
  - Rate limiting delays
  - Deduplication thresholds
  - Quality score weights
  - Output format preferences
  - Field mappings (API → common schema)

**FR-10.2: Environment Variables**
- MUST support .env file for sensitive values
- MUST use environment variables for:
  - API keys (if any added in future)
  - Output directory paths
  - Log levels

**FR-10.3: Validation**
- MUST validate configuration on startup
- MUST check required fields present
- MUST check data types correct
- MUST check value ranges valid
- MUST provide clear error messages for invalid config

---

## Non-Functional Requirements

### NFR-1: Performance

**NFR-1.1: API Fetching**
- MUST fetch 1,000 records in under 2 minutes
- Target: ~100 records per request, ~10 requests total
- Rate limit: 1 second between requests = ~20 seconds max

**NFR-1.2: Web Scraping**
- Rate limit: 2-3 seconds per request (respectful)
- Target: 200 records in ~8-10 minutes
- MUST NOT block on slow responses (timeout 30 seconds)

**NFR-1.3: Data Processing**
- MUST process 1,000 records through all stages in under 1 minute
- Cleaning: <0.1 seconds per record
- Deduplication: <5 seconds for 1,000 records
- Merging: <2 seconds for 1,000 records

**NFR-1.4: Excel Export**
- MUST export 1,000 records in under 30 seconds
- Target: <0.03 seconds per record

**NFR-1.5: Total Pipeline**
- Full pipeline (1,000 API + 200 scraped): MUST complete in under 15 minutes
- Breakdown: 2min API + 10min scraping + 1min processing + 0.5min export = ~13.5 min

**NFR-1.6: Memory Usage**
- MUST operate with 2 GB RAM for 1,000 records
- MUST operate with 4 GB RAM for 10,000 records
- MUST NOT cause memory errors or swapping

### NFR-2: Reliability

**NFR-2.1: Data Integrity**
- MUST NOT lose data during processing
- MUST preserve original values (no overwrites)
- MUST validate data at each stage
- Data loss tolerance: 0%

**NFR-2.2: Network Resilience**
- MUST retry failed requests (3 attempts)
- MUST handle timeouts gracefully
- Success rate target: 95%+ (excluding source outages)

**NFR-2.3: Scraping Success Rate**
- Target: 90%+ of scraping attempts successful
- MUST continue pipeline even if scraping fails
- MUST log all failures with reasons

**NFR-2.4: Checkpoint Recovery**
- MUST save progress periodically
- MUST support resuming from any checkpoint
- Recovery success rate: 100%

### NFR-3: Usability

**NFR-3.1: Installation**
- MUST install successfully in under 5 minutes
- MUST work on Windows, macOS, Linux
- MUST provide clear installation instructions
- Installation success rate target: 95%+

**NFR-3.2: Command-Line Interface**
- MUST have intuitive parameter names
- MUST provide helpful error messages
- MUST show progress indicators
- Learning curve target: <5 minutes to first successful run

**NFR-3.3: Output Quality**
- Excel file MUST open without errors
- Formatting MUST render correctly in Excel, Google Sheets, LibreOffice
- Hyperlinks MUST work
- Charts/conditional formatting MUST display properly

**NFR-3.4: Documentation**
- README MUST enable new user to run pipeline in under 15 minutes
- Documentation completeness target: 100% of features documented
- Examples provided for all major use cases

### NFR-4: Maintainability

**NFR-4.1: Code Quality**
- MUST follow PEP 8 style guide
- Linting errors: 0 (via flake8)
- Type hint coverage: 80%+ of functions
- Docstring coverage: 100% of public functions/classes

**NFR-4.2: Modularity**
- MUST have clear separation of concerns
- Each module MUST have single responsibility
- Coupling: Low (modules should be loosely coupled)
- Cohesion: High (related functionality grouped together)

**NFR-4.3: Configuration**
- MUST separate configuration from code
- MUST NOT hardcode values
- Configuration changes MUST NOT require code changes

**NFR-4.4: Testing**
- Unit test coverage: 70%+ overall
- Critical modules: 85%+ coverage (cleaner, deduplicator)
- Integration tests: Full pipeline test included
- All tests MUST pass before commit

**NFR-4.5: Logging**
- MUST provide sufficient detail for debugging
- Log messages MUST be clear and actionable
- Performance overhead: <5% of total runtime

### NFR-5: Security

**NFR-5.1: Credentials**
- MUST NOT store credentials in code
- MUST use environment variables or .env file
- .env file MUST be in .gitignore

**NFR-5.2: Data Privacy**
- MUST only collect public records data
- MUST NOT log sensitive data (only metadata)
- Output files MUST NOT contain private information beyond public records

**NFR-5.3: Dependencies**
- MUST use reputable libraries only
- MUST NOT have known security vulnerabilities
- MUST keep dependencies updated

### NFR-6: Compliance

**NFR-6.1: Legal Requirements**
- MUST only scrape public, non-authenticated sites
- MUST respect robots.txt (100% compliance)
- MUST implement rate limiting (minimum 2 seconds)
- MUST NOT bypass authentication or CAPTCHAs
- MUST identify via user agent

**NFR-6.2: Terms of Service**
- MUST check ToS for each data source
- MUST NOT violate explicit prohibitions
- MUST document legal basis for data collection

**NFR-6.3: Data Usage**
- MUST include legal disclaimer in documentation
- MUST advise users of their responsibilities
- MUST note data is for research/educational purposes

### NFR-7: Portability

**NFR-7.1: Platform Support**
- MUST run on Windows 10+, macOS 10.14+, Ubuntu 20.04+
- MUST handle path separators correctly (os.path)
- MUST NOT use platform-specific commands

**NFR-7.2: Python Version**
- MUST support Python 3.8, 3.9, 3.10, 3.11
- MUST NOT use features only in Python 3.12+
- MUST declare minimum version in setup

**NFR-7.3: Dependencies**
- MUST use cross-platform libraries only
- MUST pin major versions (avoid breaking changes)
- MUST minimize dependency count

### NFR-8: Scalability

**NFR-8.1: Data Volume**
- MUST handle 10,000 records without degradation
- SHOULD handle 50,000 records with acceptable performance
- For >10,000 records: MUST split output files

**NFR-8.2: Processing Strategy**
- MUST support batch processing
- SHOULD support parallel processing (future)
- Memory usage MUST scale linearly with data size

**NFR-8.3: Extensibility**
- MUST support adding new data sources
- New source addition: <4 hours for developer
- Architecture MUST accommodate future enhancements:
  - Database storage (PostgreSQL)
  - Geocoding integration
  - Additional export formats (CSV, JSON)
  - REST API endpoints

---

## Data Requirements

### DR-1: Input Data Sources

**DR-1.1: Wake County API**
- Endpoint: `https://data.wake.gov/resource/qyjm-ubyn.json`
- Format: JSON
- Authentication: None
- Expected Response Structure:
```json
[
  {
    "owner": "SMITH JOHN",
    "physical_address": "123 MAIN ST",
    "reid": "1234567890",
    "total_value": "250000",
    "deed_book": "12345",
    "deed_page": "123",
    ...
  }
]
```

**DR-1.2: Orange County Assessor**
- URL: https://www.orangecountync.gov/departments/tax_assessor
- Format: HTML (requires parsing)
- Authentication: None
- Access: Form submission with parcel ID
- Expected Fields Available:
  - Owner name and mailing address
  - Property address (street, city, state, ZIP)
  - Parcel ID
  - Property type and class
  - Square footage
  - Year built
  - Number of bedrooms/bathrooms
  - Sale date and price
  - Assessed value
  - Tax amount
  - Deed book and page

### DR-2: Common Data Schema

**DR-2.1: Required Fields**
All records MUST have:
- `parcel_id` (string, max 20 characters)
- `owner_name` (string, max 200 characters)
- `property_address` (string, max 200 characters)

**DR-2.2: Optional Fields**
Records MAY have:
- `owner_name_normalized` (string, max 200)
- `property_address_normalized` (string, max 200)
- `unit_number` (string, max 20)
- `city` (string, max 100)
- `state` (string, exactly 2 characters)
- `zip` (string, max 10 characters, format: 12345 or 12345-6789)
- `county` (string, max 100)
- `assessed_value` (float, non-negative)
- `sale_price` (float, non-negative)
- `sale_date` (date, format: YYYY-MM-DD)
- `square_footage` (integer, non-negative)
- `year_built` (integer, range: 1600-current_year)
- `bedrooms` (integer, range: 0-50)
- `bathrooms` (float, range: 0-50, allows 2.5)
- `property_type` (string, max 50)
- `deed_book` (string, max 20)
- `deed_page` (string, max 20)

**DR-2.3: Metadata Fields**
All records MUST have:
- `owner_type` (string, values: "individual" | "entity")
- `data_source` (string, values: "api_only" | "scraped_only" | "merged")
- `source_url` (string, max 500, valid URL)
- `quality_score` (integer, range: 0-100)
- `enrichment_level` (string, values: "basic" | "enhanced" | "complete")
- `fetch_timestamp` (datetime, ISO 8601 format)
- `notes` (string, max 1000)

**DR-2.4: Deduplication Fields**
Records flagged as duplicates MUST have:
- `is_duplicate` (boolean)
- `duplicate_of` (string, parcel_id of kept record)
- `dedup_reason` (string, max 100)

### DR-3: Data Quality Standards

**DR-3.1: Completeness**
- Required fields: 100% populated for valid records
- Target overall completeness: 80%+ of all fields

**DR-3.2: Accuracy**
- Owner names: Must match source exactly
- Addresses: Must match source exactly
- Normalization: Must be reversible

**DR-3.3: Consistency**
- Same parcel_id MUST have same property address
- Format consistency: All dates YYYY-MM-DD, all currencies as float

**DR-3.4: Validity**
- ZIP codes: Must be 5 or 9 digits
- State codes: Must be valid US state abbreviations
- Dates: Must not be in future
- Numeric fields: Must be non-negative where applicable

### DR-4: Output Data Format

**DR-4.1: Excel Specifications**
- File extension: .xlsx
- Maximum rows per sheet: 1,048,576 (Excel limit)
- Practical limit: 10,000 rows per file
- Character encoding: UTF-8
- Number format: US locale (comma thousands separator, period decimal)
- Date format: MM/DD/YYYY
- Currency format: $#,##0.00

**DR-4.2: Alternative Formats (Future)**
- CSV: UTF-8, comma-delimited, quoted strings
- JSON: UTF-8, pretty-printed, arrays of objects
- Database: PostgreSQL-compatible schema

---

## Testing Requirements

### TR-1: Unit Testing

**TR-1.1: Coverage Targets**
- Overall: 70% minimum
- `cleaner.py`: 90% minimum (critical)
- `deduplicator.py`: 85% minimum (critical)
- `validator.py`: 80% minimum
- `merger.py`: 80% minimum
- `fetchers/`: 70% minimum

**TR-1.2: Test Cases Required**

**Name Normalization:**
- ✅ "smith, john" → "JOHN SMITH"
- ✅ "SMITH, JOHN MICHAEL" → "JOHN MICHAEL SMITH"
- ✅ "ABC Properties L.L.C." → "ABC PROPERTIES LLC"
- ✅ "XYZ Corporation Inc." → "XYZ CORP"
- ✅ "Smith Family Trust" → "SMITH FAMILY TRUST"
- ✅ "  Extra   Spaces  " → "EXTRA SPACES"
- ✅ Empty string handling
- ✅ None handling
- ✅ Special characters: "O'Brien & Sons" → "OBRIEN & SONS"

**Address Normalization:**
- ✅ "123 Main Street" → "123 MAIN ST"
- ✅ "456 Oak Ave Apt 2" → "456 OAK AVE" + unit "2"
- ✅ "789 North Elm Road" → "789 N ELM RD"
- ✅ "100 S.E. Park Drive" → "100 SE PARK DR"
- ✅ Multiple spaces
- ✅ Unit variations: APT, APARTMENT, UNIT, STE, #
- ✅ Empty string handling
- ✅ PO Box detection

**Deduplication:**
- ✅ Exact duplicates detected (same normalized address)
- ✅ Fuzzy matches detected (90%+ name, 95%+ address)
- ✅ False positives prevented (same address, different city)
- ✅ Cross-source matching by parcel_id
- ✅ Conflict detection (different owner names)

**Validation:**
- ✅ Missing required fields flagged
- ✅ Empty strings flagged
- ✅ Invalid data types flagged
- ✅ Out of range values flagged
- ✅ Pattern matching (PO Boxes, invalid ZIP codes)

### TR-2: Integration Testing

**TR-2.1: Full Pipeline Test**
```
Test: test_full_pipeline_small()
Steps:
1. Fetch 10 API records (mocked)
2. Scrape 5 records (mocked)
3. Process through all stages
4. Verify Excel file created
5. Verify record counts match
6. Verify no data loss
Expected Duration: <10 seconds
```

**TR-2.2: Error Recovery Test**
```
Test: test_checkpoint_recovery()
Steps:
1. Start pipeline
2. Simulate interruption after scraping
3. Verify checkpoint saved
4. Resume from checkpoint
5. Verify pipeline completes successfully
```

**TR-2.3: Data Source Test**
```
Test: test_api_connection()
Steps:
1. Make real API request (limit=1)
2. Verify response structure
3. Verify can parse fields
Note: This is a smoke test, not run in CI
```

### TR-3: Manual Testing

**TR-3.1: Output Verification**
- [ ] Open Excel in Microsoft Excel (Windows & Mac)
- [ ] Open Excel in Google Sheets
- [ ] Open Excel in LibreOffice Calc
- [ ] Verify formatting renders correctly
- [ ] Click 20 random source URLs
- [ ] Verify conditional formatting works
- [ ] Verify color coding is visible

**TR-3.2: Data Accuracy**
- [ ] Manually verify 20 random records against source websites
- [ ] Check owner names not corrupted
- [ ] Check addresses not truncated
- [ ] Check quality scores reasonable
- [ ] Check notes are helpful

**TR-3.3: Performance Testing**
- [ ] Run with 100 records, measure time
- [ ] Run with 1,000 records, measure time
- [ ] Run with 10,000 records, measure time & memory
- [ ] Verify no memory leaks (monitor RAM usage)

**TR-3.4: Usability Testing**
- [ ] Give to someone unfamiliar with project
- [ ] Ask them to install and run using only README
- [ ] Document any confusion or errors
- [ ] Time to first successful run (target: <15 min)

---

## Deployment Requirements

### DEP-1: Local Deployment

**DEP-1.1: Installation Steps**
1. Clone repository
2. Create virtual environment (venv or conda)
3. Install Python dependencies (`pip install -r requirements.txt`)
4. Install Playwright browsers (`playwright install chromium`)
5. Run test command to verify setup
6. Run pipeline with demo settings

**DEP-1.2: Dependencies**
- All dependencies MUST be in requirements.txt
- Pin major versions: `package>=1.0.0,<2.0.0`
- Development dependencies in separate file: requirements-dev.txt

**DEP-1.3: Directory Creation**
- data/, data/raw/, data/processed/, data/output/, logs/, data/checkpoints/
- MUST create automatically if missing
- MUST NOT fail if directories exist

### DEP-2: Google Colab Deployment

**DEP-2.1: Notebook Requirements**
- MUST run top-to-bottom without modification
- MUST install all dependencies in first cell
- MUST NOT require manual file uploads (use repo clone)
- MUST work in free Colab tier

**DEP-2.2: Session Limits**
- Runtime limit: 12 hours (Colab free tier)
- Pipeline MUST complete well within limit (target: <15 min)
- RAM limit: ~12 GB (Colab free tier)
- Pipeline MUST NOT exceed RAM limit

**DEP-2.3: File Handling**
- Output files MUST be downloadable via `files.download()`
- Option to save to Google Drive (user must mount)
- Temporary files MUST be cleaned up

**DEP-2.4: Sharing**
- Notebook MUST be publicly accessible (or by link)
- MUST include "Open in Colab" badge in README
- MUST work for users without Google account (viewer mode)

### DEP-3: Version Control

**DEP-3.1: Git Requirements**
- Meaningful commit messages (conventional commits style)
- .gitignore MUST exclude:
  - `*.xlsx` (output files)
  - `*.csv` (except sample files)
  - `*.html` (scraped pages)
  - `__pycache__/`, `*.pyc`
  - `.env`
  - `venv/`, `env/`, `.venv/`
  - `logs/`
  - `data/raw/`, `data/processed/`, `data/output/`
  - `.DS_Store`, `Thumbs.db`

**DEP-3.2: Branching Strategy**
- `main` - stable, working code only
- `develop` - active development
- Feature branches: `feature/description`
- Bug fix branches: `fix/description`

**DEP-3.3: Releases**
- Tag stable versions: v1.0.0, v1.1.0, etc.
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Create GitHub release with changelog

---

## Documentation Requirements

### DOC-1: User Documentation

**DOC-1.1: README.md Must Include:**
- [ ] Project title and description (2-3 sentences)
- [ ] Legal disclaimer (prominent, at top)
- [ ] Key features (bullet list)
- [ ] Data sources with legal status
- [ ] Quick start (Colab + local)
- [ ] Sample output with screenshot/table
- [ ] Configuration options
- [ ] Usage examples (5+ scenarios)
- [ ] Troubleshooting common issues
- [ ] Contributing guidelines
- [ ] License information
- [ ] Author contact information

**DOC-1.2: LEGAL_COMPLIANCE.md Must Include:**
- [ ] Detailed explanation of each data source
- [ ] Legal basis (statutes, licenses)
- [ ] Screenshots of relevant ToS sections
- [ ] robots.txt content for scraped sites
- [ ] Rate limiting strategy
- [ ] Responsible scraping principles
- [ ] When NOT to use this project
- [ ] Disclaimer template for users

**DOC-1.3: CHANGELOG.md Must Include:**
- Version history with dates
- Added, changed, deprecated, removed, fixed, security sections
- Migration notes for breaking changes

### DOC-2: Developer Documentation

**DOC-2.1: Code Documentation:**
- All public functions MUST have docstrings
- Docstring format: Google style
- Include: Description, Args, Returns, Raises, Example
- Complex algorithms MUST have inline comments

**DOC-2.2: Architecture Documentation:**
- Pipeline flow diagram (visual)
- Module dependency diagram
- Data flow diagram (source → output)
- Configuration system explanation

**DOC-2.3: API Documentation (if applicable):**
- Class and method signatures
- Parameter descriptions with types
- Return value descriptions
- Example usage code

---

## Maintenance Requirements

### MAINT-1: Monitoring

**MAINT-1.1: Logging**
- All logs saved to `logs/` directory
- Log retention: 30 days
- Log rotation: Daily
- Archive old logs (compress)

**MAINT-1.2: Metrics to Track:**
- API success rate
- Scraping success rate
- Average execution time
- Data quality scores (trend over time)
- Error rates by type

### MAINT-2: Updates

**MAINT-2.1: Data Source Monitoring:**
- Check source websites quarterly for changes
- Update selectors if site structure changes
- Test API endpoints monthly
- Document changes in CHANGELOG

**MAINT-2.2: Dependency Updates:**
- Review security advisories monthly
- Update patch versions as released
- Test before updating major versions
- Document breaking changes

### MAINT-3: Support

**MAINT-3.1: Issue Tracking:**
- GitHub Issues enabled
- Issue templates provided:
  - Bug report
  - Feature request
  - Question
- Response time: 7 days for initial response

**MAINT-3.2: Documentation Updates:**
- Update README when features added/changed
- Update requirements.txt when dependencies change
- Update legal docs if sources change
- Keep examples up to date

---

## Acceptance Criteria

### AC-1: Functional Completeness
- [ ] All FR-1 through FR-10 implemented
- [ ] All command-line arguments work
- [ ] All output sheets generated correctly
- [ ] All data quality checks functional

### AC-2: Performance Standards
- [ ] Full pipeline completes in <15 minutes (1000 API + 200 scraped)
- [ ] Memory usage <4 GB for 10,000 records
- [ ] No performance degradation up to 10,000 records

### AC-3: Quality Standards
- [ ] Test coverage >= 70%
- [ ] All tests passing
- [ ] No linting errors (flake8)
- [ ] Code formatted (black)
- [ ] Manual verification passed (20 random records)

### AC-4: Documentation Standards
- [ ] README complete and accurate
- [ ] Legal compliance documented
- [ ] All code has docstrings
- [ ] Examples provided for all features
- [ ] New user can run pipeline in <15 minutes

### AC-5: Legal Compliance
- [ ] Only public data sources used
- [ ] robots.txt respected
- [ ] Rate limiting implemented (2+ seconds)
- [ ] User agent identifies project
- [ ] Legal disclaimers prominent

### AC-6: Usability
- [ ] Excel opens without errors in Excel, Google Sheets, LibreOffice
- [ ] Hyperlinks work
- [ ] Formatting renders correctly
- [ ] Error messages are clear and actionable
- [ ] Colab notebook runs without modification

---

**END OF REQUIREMENTS.MD**

**This document defines all technical and functional requirements for the Property Owner Extraction Pipeline. All requirements are mandatory unless marked as "SHOULD" or "MAY".**

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Status:** Specification Complete
