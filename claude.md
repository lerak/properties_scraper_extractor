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
  - ✅ Rate limited (2-3 seconds between requests)
  - ✅ Limited volume (200-300 records, not exhaustive)
  - ✅ Identifies as educational/research via user agent

### 🚫 What This Project Does NOT Do
- ❌ Scrape paywalled or subscription property data services
- ❌ Overwhelm servers (respectful rate limiting always)

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
source venv/bin/activate  # On Windows: venv\Scripts
