# Property Owner Extraction & Deduplication Pipeline

> Automated data pipeline combining public APIs and web scraping to create enriched property owner lists for direct mail campaigns and real estate research.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yourusername/property-pipeline/blob/main/notebooks/property_pipeline.ipynb)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What This Does

This pipeline automatically:
1. **Fetches** 1,000 property records from Wake County NC public API
2. **Scrapes** 200-300 additional property details from Orange County NC assessor website
3. **Cleans** owner names and addresses (handles "SMITH, JOHN" vs "JOHN SMITH")
4. **Deduplicates** using exact + fuzzy matching algorithms
5. **Merges** data from both sources by matching parcel IDs
6. **Scores** each record's quality (0-100 based on completeness)
7. **Exports** formatted Excel workbook with 5 sheets and hyperlinked sources

**Result:** Clean, deduplicated property owner list with verified source links - ready for direct mail or analysis.

---

## ⚖️ Legal Compliance (READ FIRST)

### ✅ This Project Uses ONLY Public Data

**Wake County NC Open Data API**
- **License:** Open Data Commons (Public Domain)
- **URL:** https://data.wake.gov/
- **Status:** Explicitly designed for public programmatic access
- **Documentation:** https://dev.socrata.com/

**Orange County NC Assessor (Web Scraping)**
- **Legal Basis:** North Carolina Public Records Law (G.S. 132-1)
- **URL:** https://www.orangecountync.gov/departments/tax_assessor
- **Status:** Public search interface intended for public use
- **Compliance:** 
  - ✅ Respects robots.txt
  - ✅ Rate limited (2-3 seconds between requests)
  - ✅ Limited volume (200-300 records, not exhaustive)
  - ✅ Identifies as educational/research via user agent

### 🚫 What This Project Does NOT Do
- ❌ Scrape paywalled or subscription property data services
- ❌ Bypass authentication or CAPTCHAs
- ❌ Ignore Terms of Service
- ❌ Overwhelm servers (respectful rate limiting always)
- ❌ Scrape private or restricted databases

### 📋 Disclaimer
**This project is for educational and portfolio demonstration purposes.** Users are responsible for:
- Verifying their own legal right to use collected data
- Complying with local laws regarding data usage
- Respecting privacy when using data for outreach
- Following CAN-SPAM Act if using for email marketing

**See [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md) for detailed documentation.**

---

## 🌟 Key Features

- ✅ **Dual-Source Architecture** - Combines API speed with scraping depth
- ✅ **Intelligent Deduplication** - Exact + fuzzy matching (90%+ similarity threshold)
- ✅ **Quality Scoring System** - 0-100 score for each record's completeness
- ✅ **Source Tracking** - Every field tagged with origin (API/scraped/merged)
- ✅ **Owner Name Normalization** - Handles "LAST, FIRST", entity suffixes (LLC→LLC)
- ✅ **Address Standardization** - Street suffixes (STREET→ST), unit extraction
- ✅ **Multi-Sheet Excel Export** - Formatted with hyperlinks, color coding, statistics
- ✅ **Comprehensive Logging** - Full audit trail of operations
- ✅ **Checkpoint Recovery** - Resume interrupted pipelines
- ✅ **Google Colab Ready** - Run in browser with zero installation

---

## 🚀 Quick Start

### Option 1: Google Colab (Easiest - No Installation)

1. Click the **"Open in Colab"** badge at the top
2. Run cells from top to bottom
3. Download the generated Excel file
4. **Done!** (Takes ~5 minutes for 100 records)

### Option 2: Local Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/property-pipeline.git
cd property-pipeline

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (for web scraping)
playwright install chromium

# 5. Run demo pipeline (100 API + 20 scraped)
python main.py --limit 100 --scrape-limit 20

# Output will be in: ./data/output/property_owners_[timestamp].xlsx
```

---

## 📊 Sample Output

### Excel File Structure (5 Sheets)

#### Sheet 1: Combined Data (Main Output)

| Owner Name | Property Address | City | ZIP | Parcel ID | Assessed Value | Sale Price | Sq Ft | Year Built | Quality Score | Source | Source URL | Notes |
|------------|------------------|------|-----|-----------|----------------|------------|-------|------------|---------------|--------|------------|-------|
| SMITH JOHN | 123 MAIN ST | RALEIGH | 27601 | 1234567890 | $250,000 | $245,000 | 1,850 | 1998 | 95 | merged | [View] | Enhanced with scraped data |
| JOHNSON MARY | 456 OAK AVE | DURHAM | 27701 | 9876543210 | $180,000 | - | - | 1985 | 65 | api_only | [View] | Missing sale data |

**Features:**
- 🟦 Blue rows = API only
- 🟩 Green rows = Scraped only  
- 🟨 Yellow rows = Merged (best data from both sources)
- Clickable "View" links to original county records
- Quality scores color-coded (Green 80+, Yellow 60-79, Red 0-59)

#### Sheet 2: API Data Only
Raw baseline - all 1,000 records from Wake County API before enrichment

#### Sheet 3: Scraped Enhancements  
200-300 records with additional details obtained through web scraping

#### Sheet 4: Summary Statistics
```
Metric                          | Value
--------------------------------|------------
Total API Records Fetched       | 1,000
Total Scraped Records           | 247
Records After Validation        | 1,189
Duplicates Removed              | 58
Final Unique Records            | 1,131
Enrichment Rate                 | 21.8%
Average Quality Score (Overall) | 78.3
Average Quality Score (API)     | 71.2
Average Quality Score (Scraped) | 92.4
Average Quality Score (Merged)  | 95.1
Data Collection Time            | 12m 34s
```

#### Sheet 5: Data Quality Report
Lists records with issues:
- Missing required fields
- Low quality scores (< 60)
- Data conflicts between sources
- Scraping failures with reasons

**Download Sample:** [owners_sample.xlsx](sample_data/owners_sample.xlsx) (100 real records)

---

## 🏗️ Project Structure

```
property-pipeline/
├── config/
│   ├── settings.py              # API URLs, rate limits, thresholds
│   └── selectors.py             # CSS/XPath selectors for scraping
│
├── src/
│   ├── fetchers/
│   │   ├── api_fetcher.py       # Wake County API client
│   │   ├── web_scraper.py       # Base scraper class (Playwright)
│   │   └── orange_scraper.py    # Orange County specific scraper
│   │
│   ├── validator.py             # Data validation (required fields)
│   ├── cleaner.py               # Name & address normalization
│   ├── deduplicator.py          # Exact + fuzzy matching
│   ├── merger.py                # Cross-source data merging
│   ├── enricher.py              # Quality scoring & metadata
│   ├── exporter.py              # Excel generation with formatting
│   ├── pipeline.py              # Main orchestration
│   └── utils.py                 # Logging & helper functions
│
├── tests/
│   ├── test_cleaner.py          # Unit tests for normalization
│   ├── test_deduplicator.py     # Deduplication logic tests
│   └── test_merger.py           # Cross-source merge tests
│
├── data/
│   ├── raw/                     # Raw API responses & HTML
│   ├── processed/               # Intermediate cleaned data
│   └── output/                  # Final Excel workbooks
│
├── notebooks/
│   └── property_pipeline.ipynb  # Google Colab demo
│
├── logs/                        # Execution logs with timestamps
├── requirements.txt             # Python dependencies
├── main.py                      # CLI entry point
├── README.md                    # This file
└── LEGAL_COMPLIANCE.md          # Detailed legal documentation
```

---

## 🔧 Configuration

Edit `config/settings.py` to customize:

```python
# Data Sources
DATA_SOURCES = {
    'wake_county': {
        'api_url': 'https://data.wake.gov/resource/qyjm-ubyn.json',
        'rate_limit': 1.0,  # seconds between requests
    },
    'orange_county': {
        'base_url': 'https://www.orangecountync.gov/...',
        'rate_limit': 2.5,  # seconds between scraping requests
    }
}

# Deduplication Thresholds
DEDUP_CONFIG = {
    'fuzzy_name_threshold': 90,      # 0-100 (higher = stricter)
    'fuzzy_address_threshold': 95,   # 0-100
    'strategy': 'conservative'        # or 'aggressive'
}

# Quality Scoring
QUALITY_CONFIG = {
    'min_quality_score': 60,         # Filter out records below this
    'required_fields': ['owner_name', 'property_address', 'parcel_id']
}

# Output
OUTPUT_CONFIG = {
    'filename_template': 'property_owners_{date}_{source}.xlsx',
    'max_records_per_file': 10000,   # Split into multiple files if exceeded
    'include_raw_data_sheets': True
}
```

---

## 🎮 Usage Examples

### Basic Usage
```bash
# Demo run (100 API + 20 scraped)
python main.py

# Specify record limits
python main.py --limit 500 --scrape-limit 100

# Custom output location
python main.py --output ~/Desktop/properties.xlsx

# Skip scraping (API only)
python main.py --limit 1000 --skip-scraping
```

### Advanced Usage
```bash
# Debug mode with visible browser
python main.py --limit 10 --scrape-limit 5 --log-level DEBUG --headless False

# Resume interrupted run
python main.py --resume

# Different data source
python main.py --source cook_county --limit 500
```

### Programmatic Usage (Python)
```python
from src.pipeline import PropertyPipeline
from config.settings import Config

# Initialize
config = Config(
    source='wake_county',
    output_path='./my_properties.xlsx',
    dedup_threshold=95
)
pipeline = PropertyPipeline(config)

# Run pipeline
output_file = pipeline.run(
    limit=1000,          # API records
    scrape_limit=200     # Scraped records
)

print(f"Generated: {output_file}")

# Get statistics
stats = pipeline.get_statistics()
print(f"Enrichment rate: {stats['enrichment_rate']}%")
```

---

## 📈 Pipeline Stages Explained

```
┌─────────────────────────────────────────────────────────────┐
│  1. API FETCH (Wake County)                                 │
│     • Fetch 1,000 records via REST API                      │
│     • Pagination with retry logic                           │
│     • Takes ~90 seconds                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. WEB SCRAPING (Orange County)                            │
│     • Select 200-300 records for enrichment                 │
│     • Scrape property details (2-3 sec per property)        │
│     • Takes ~8-10 minutes                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. HARMONIZATION                                           │
│     • Map both sources to common schema                     │
│     • Standardize field names and types                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. VALIDATION                                              │
│     • Check required fields present                         │
│     • Flag suspicious data (empty names, PO boxes)          │
│     • Remove critically invalid records                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. CLEANING & NORMALIZATION                                │
│     • Owner: "SMITH, JOHN" → "JOHN SMITH"                   │
│     • Address: "123 Main Street" → "123 MAIN ST"            │
│     • Entity suffixes: "L.L.C." → "LLC"                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  6. CROSS-SOURCE MATCHING                                   │
│     • Match API + scraped by parcel_id                      │
│     • Detect conflicts (different owner names)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  7. DEDUPLICATION                                           │
│     • Exact address matching                                │
│     • Fuzzy name matching (>90% similar)                    │
│     • Remove ~5% duplicates typically                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  8. MERGING                                                 │
│     • Combine matched records (API as base)                 │
│     • Add scraped fields as enhancements                    │
│     • Track field provenance                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  9. ENRICHMENT                                              │
│     • Generate source URLs (hyperlinks)                     │
│     • Calculate quality scores (0-100)                      │
│     • Add metadata & notes                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  10. EXCEL EXPORT                                           │
│      • 5-sheet workbook with formatting                     │
│      • Hyperlinked URLs, color coding                       │
│      • Summary stats & quality report                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_cleaner.py -v

# Run with coverage report
pytest --cov=src --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

### Test Coverage Targets
- `cleaner.py`: 90%+ (critical normalization logic)
- `deduplicator.py`: 85%+ (complex matching)
- `validator.py`: 80%+
- `merger.py`: 80%+
- Overall: 70%+

---

## 🎯 Use Cases

1. **Direct Mail Campaigns**  
   Build targeted property owner lists with verified mailing addresses

2. **Real Estate Investment**  
   Identify properties matching specific criteria (value, size, age)

3. **Market Research**  
   Analyze ownership patterns, property values, sales trends

4. **Tax Assessment Analysis**  
   Compare assessed values across neighborhoods

5. **Title/Deed Research**  
   Track ownership history with deed book references

6. **Compliance Audits**  
   Verify property ownership for regulatory purposes

---

## 🚧 Limitations & Future Enhancements

### Current Limitations
- Demo limited to 1,000 API + 300 scraped records (expandable)
- Single-threaded scraping (no parallel processing)
- Excel output only (10,000 row practical limit)
- Two data sources (Wake + Orange counties only)

### Planned Enhancements
- [ ] Add 5+ more county sources (Cook IL, Maricopa AZ, Travis TX)
- [ ] PostgreSQL database storage for large datasets (100k+ records)
- [ ] Parallel/async scraping (10x speed improvement)
- [ ] Geocoding integration (add lat/long coordinates)
- [ ] Property value prediction model (ML-based)
- [ ] CSV/JSON export formats
- [ ] REST API endpoint for pipeline access
- [ ] Web dashboard for visualization
- [ ] Automated scheduling (cron jobs)
- [ ] Email notifications on completion

---

## 🤝 Contributing

Contributions welcome! To contribute:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Make changes and add tests
4. Ensure all tests pass (`pytest tests/`)
5. Commit changes (`git commit -m 'Add AmazingFeature'`)
6. Push to branch (`git push origin feature/AmazingFeature`)
7. Open Pull Request

### Contribution Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation (README, docstrings)
- Verify legal compliance for new data sources
- Run `black` formatter before committing

---

## 📚 Additional Resources

### Documentation
- [Detailed API Documentation](docs/API.md)
- [Scraping Guidelines](docs/SCRAPING.md)
- [Data Schema Reference](docs/SCHEMA.md)
- [Legal Compliance Details](LEGAL_COMPLIANCE.md)

### External Resources
- [NC Public Records Law](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_132/GS_132-1.html)
- [Wake County Open Data Portal](https://data.wake.gov/)
- [Socrata API Documentation](https://dev.socrata.com/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Web Scraping Best Practices](https://www.anthropic.com/index/robots-txt-and-ai)

---

## 🐛 Troubleshooting

### Common Issues

**Issue: API returns empty results**
```bash
# Solution: Check API endpoint is accessible
curl https://data.wake.gov/resource/qyjm-ubyn.json?$limit=1
```

**Issue: Scraping fails with timeout**
```bash
# Solution: Increase rate limit or run with visible browser to debug
python main.py --scrape-limit 5 --headless False --log-level DEBUG
```

**Issue: Excel file won't open**
```bash
# Solution: Check file size. If >10MB, split into multiple files
python main.py --limit 500 --output smaller_file.xlsx
```

**Issue: "No module named 'playwright'"**
```bash
# Solution: Install Playwright browsers
pip install playwright
playwright install chromium
```

**Issue: Deduplication removing too many records**
```bash
# Solution: Adjust threshold in config/settings.py
# Increase from 90 to 95 for stricter matching
```

For more help:
- Check [GitHub Issues](https://github.com/yourusername/property-pipeline/issues)
- Review logs in `logs/` directory
- Run with `--log-level DEBUG` for detailed output

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

**TL;DR:** You can use, modify, and distribute this code freely. Just include the original license.

---

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/yourprofile)
- Email: your.email@example.com
- Portfolio: [yourwebsite.com](https://yourwebsite.com)

---

## 🙏 Acknowledgments

- **Wake County, NC** for maintaining excellent open data infrastructure
- **Orange County, NC** for accessible public records
- **Anthropic** for Claude AI assistance during development
- **Open Source Community** for amazing Python libraries (pandas, Playwright, etc.)

---

## ⭐ Star History

If this project helped you, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/property-pipeline&type=Date)](https://star-history.com/#yourusername/property-pipeline&Date)

---

**Built with ❤️ for transparent, ethical data engineering**

*Last Updated: 2025-01-XX*
