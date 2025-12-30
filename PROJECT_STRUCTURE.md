# Texas Government Data Scraper Toolkit

## Project Structure

```
texas-data-scraper/
│
├── .cache/                           # Cache directory
│   ├── progress/                     # Progress checkpoints for resume
│   ├── comptroller/                  # Comptroller API response cache (v1.4.0)
│   └── google_places/                # Google Places API cache (v1.5.0)
│       ├── place_ids/                # Cached place ID lookups
│       └── details/                  # Cached place details
│
├── config/
│   ├── __init__.py                   # Config package initialization
│   ├── settings.py                   # Configuration management
│   └── .env.example                  # Environment variables template
│
├── docs/
│   ├── ABSOLUTELY_FINAL_SUMMARY.md   # Final project summary
│   ├── DEPLOYMENT_GUIDE.md           # Deployment instructions
│   ├── FINAL_COMPLETE_CHECKLIST.md   # Complete feature checklist
│   ├── INSTALLATION_CHECKLIST.md     # Installation guide
│   └── QUICK_START.md                # Quick start guide
│
├── exports/                          # Output directory for exported data
│   ├── combined/                     # Combined data exports
│   ├── comptroller/                  # Comptroller data exports
│   ├── deduplicated/                 # Deduplicated data exports
│   ├── polished/                     # Outlet-enriched data exports (v1.4.0)
│   ├── place_ids/                    # Google Place IDs exports (v1.5.0)
│   ├── places_details/               # Google Places details exports (v1.5.0)
│   ├── final/                        # Final combined data exports (v1.5.0)
│   └── socrata/                      # Socrata data exports
│
├── logs/                             # Log files directory
│
├── scripts/
│   ├── api_tester.py                 # API endpoint testing
│   ├── batch_processor.py            # Batch processing CLI
│   ├── comptroller_scraper.py        # Main Comptroller scraper CLI
│   ├── data_combiner.py              # Data combination CLI
│   ├── deduplicator.py               # Deduplication CLI
│   ├── google_places_scraper.py      # Google Places API CLI (v1.5.0)
│   ├── outlet_enricher.py            # Outlet data enrichment CLI (v1.4.0)
│   └── socrata_scraper.py            # Main Socrata scraper CLI
│
├── src/
│   ├── __init__.py                   # Source package initialization
│   │
│   ├── api/
│   │   ├── __init__.py               # API package initialization
│   │   ├── comptroller_client.py     # Comptroller API client
│   │   ├── google_places_client.py   # Google Places API client (v1.5.0)
│   │   ├── rate_limiter.py           # Rate limiting logic
│   │   └── socrata_client.py         # Socrata API client
│   │
│   ├── exporters/
│   │   ├── __init__.py               # Exporters package initialization
│   │   └── file_exporter.py          # Export to JSON/CSV/Excel
│   │
│   ├── processors/
│   │   ├── __init__.py               # Processors package initialization
│   │   ├── data_combiner.py          # Combine Socrata + Comptroller data
│   │   ├── data_validator.py         # Data validation
│   │   ├── deduplicator.py           # Remove duplicates
│   │   └── outlet_enricher.py        # Outlet data enrichment (v1.4.0)
│   │
│   ├── scrapers/
│   │   ├── __init__.py               # Scrapers package initialization
│   │   ├── comptroller_scraper.py    # Comptroller data scraper
│   │   ├── google_places_scraper.py  # Google Places scraper (v1.5.0)
│   │   ├── gpu_accelerator.py        # GPU acceleration utilities
│   │   └── socrata_scraper.py        # Socrata data scraper
│   │
│   └── utils/
│       ├── __init__.py               # Utils package initialization
│       ├── checksum.py               # File checksum verification
│       ├── helpers.py                # Helper functions
│       ├── logger.py                 # Logging utilities
│       ├── menu.py                   # Interactive CLI menu
│       └── progress_manager.py       # Progress persistence for downloads
│
├── tests/
│   ├── __init__.py                   # Tests package initialization
│   ├── test_comptroller_api.py       # Comptroller API tests
│   ├── test_google_places_api.py     # Google Places API tests
│   ├── test_integration.py           # Integration tests
│   ├── test_processors.py            # Processor tests
│   ├── test_scrapers.py              # Scraper tests
│   └── test_socrata_api.py           # Socrata API tests
│
├── .env                              # Environment variables (gitignored)
├── .gitignore                        # Git ignore file
├── CHANGELOG.md                      # Project changelog
├── CONTRIBUTING.md                   # Contribution guidelines
├── LICENSE                           # Project license
├── Makefile                          # Make commands for automation
├── PROJECT_STRUCTURE.md              # This file - project structure docs
├── PROJECT_SUMMARY.md                # Detailed project summary
├── README.md                         # Main documentation
├── requirements.txt                  # Python dependencies
├── requirements-gpu.txt              # GPU-specific dependencies
├── run.py                            # Main entry point runner
├── setup.py                          # Package setup
└── setup_project.py                  # Project setup/initialization script
```

## Key Features

### 1. **Socrata Data Scraper**
- Interactive menu with 15+ search options
- Full dataset downloads with pagination
- Custom limit downloads
- Search by: business name, legal name, DBA, city, zip, agent, officer
- Auto-export to JSON/CSV/Excel
- Token management (1k default, 50k with API key)

### 2. **Comptroller Data Scraper**
- Automatic taxpayer ID extraction from Socrata exports
- Batch processing with progress tracking
- Dual endpoint data retrieval (details + FTAS records)
- Individual taxpayer lookup (terminal-only)
- Smart rate limiting

### 3. **Data Combiner**
- Intelligent merging by taxpayer ID
- Field prioritization (Comptroller > Socrata)
- Deduplication during merge
- Separate JSON/CSV/Excel processing

### 4. **Deduplicator**
- Format-specific deduplication
- Maintains data integrity
- Comprehensive duplicate detection
- Final polished output

### 5. **GPU Acceleration**
- CUDA-accelerated data processing
- Parallel batch processing
- Optimized for RTX 3060
- Fallback to CPU if GPU unavailable

### 6. **Testing Suite**
- API endpoint validation
- Unit tests for all components
- Integration tests
- Performance benchmarks

### 7. **Additional Features**
- Comprehensive logging
- Progress bars and status updates
- Error handling and recovery
- Configuration management
- Retry logic with exponential backoff
- Data validation and cleaning
- Timestamp tracking
- File format detection

### 8. Resilience Features (v1.1.0)
- Progress checkpoint persistence
- Resume interrupted downloads
- Export checksum verification
- Data integrity protection

### 9. Smart Data Handling (v1.2.0)
- **Smart Field Detection**
  - Case-insensitive taxpayer ID matching (20+ field variations)
  - Semantic field normalization (`zipcode` → `zip_code`)
  - Auto-detection works across all datasets
- **Global Auto-Deduplication**
  - Automatically skips already-scraped records
  - Works across multiple dataset scrapes
  - Builds master index from all existing exports
- **Append-to-Existing Exports**
  - New records appended to existing files
  - Single consolidated file per dataset
  - No more multiple timestamped files

### 10. Bulk Operations & Master Combine (v1.3.0)
- **Process ALL Socrata Files** (Comptroller Scraper)
  - Menu option 3: Bulk process all datasets at once
  - Uses JSON-only to avoid CSV/Excel duplication
- **Separate Comptroller Files Per Dataset**
  - Source-specific filenames: `comptroller_franchise_tax.*`
  - Clear traceability per source dataset
- **Master Combine All** (Data Combiner Option 6)
  - Full pipeline: merge all Socrata → merge all Comptroller → combine by taxpayer ID
  - Output: `master_combined.*` (JSON, CSV, Excel)
- **9 Manual Combine Options** (Data Combiner Option 12)
  - Granular control: Socrata only, Comptroller only, or cross-source
  - Distinct filenames: `merged_socrata_json.*`, `combined_all_csv.*`, etc.

### 11. Outlet Enrichment & Caching (v1.4.0)
- **Outlet Data Enricher** (New Script!)
  - `scripts/outlet_enricher.py` - Interactive CLI
  - `src/processors/outlet_enricher.py` - Core processor
  - Extracts outlet fields from duplicate Socrata records
  - Enriches deduplicated data with outlet info (address, NAICS, permits)
  - New export directory: `exports/polished/`
- **Persistent Disk Caching** (Comptroller Scraper)
  - Cache saves to `.cache/comptroller/` as JSON files
  - Survives script restarts - truly resumable!
  - Option 3 "With Caching" now persists across sessions
- **Network Retry with Exponential Backoff**
  - Automatic retry on network errors (DNS, connection failures)
  - Up to 3 retries with increasing delays (5s, 10s, 20s)
  - Prevents data loss during internet outages
- **Configurable Comptroller Settings**
  - `COMPTROLLER_CONCURRENT_REQUESTS` - Concurrent API calls
  - `COMPTROLLER_CHUNK_SIZE` - Batch size
  - `COMPTROLLER_REQUEST_DELAY` - Delay between requests

### 12. Google Places API Integration (v1.5.0)
- **Google Places Scraper** (New Script!)
  - `scripts/google_places_scraper.py` - Interactive CLI with 11 menu options
  - `src/api/google_places_client.py` - Sync/Async API clients
  - `src/scrapers/google_places_scraper.py` - Scraper with disk caching
  - Two-step workflow: Find Place IDs → Get Place Details
  - New export directories:
    - `exports/place_ids/` - Place IDs matched to taxpayers
    - `exports/places_details/` - Full Google Places data
    - `exports/final/` - Polished + Places combined
- **Fields Extracted from Google Places**
  - Phone numbers, website, Google Maps URL
  - Ratings, reviews, business status
  - Opening hours, categories, coordinates
- **Data Combiner Option 13** - Combine Google Places with polished data
- **Configurable Settings**
  - `GOOGLE_PLACES_API_KEY` - Your API key
  - `GOOGLE_PLACES_BILLING` - true/false for rate limits
  - `GOOGLE_PLACES_RATE_LIMIT_*` - Rate limiting

### 13. Future Pipeline (Roadmap)
- **Phase 1** (Complete): Socrata + Comptroller data scraping ✅
- **Phase 2** (Complete): Google Places API integration ✅
- **Phase 3** (Planned): Clearbit API for company enrichment (emails, contacts, social media)
- **Phase 4** (Planned): Unified company profile generation

## Directory Details

### `/config`
Contains configuration files including settings management and environment variable templates.

### `/docs`
Documentation files including quick start guide, deployment guide, installation checklist, and project summaries.

### `/exports`
Output directory organized by data source type:
- `combined/` - Merged Socrata + Comptroller data
- `comptroller/` - Raw Comptroller API data
- `deduplicated/` - Processed duplicate-free data
- `socrata/` - Raw Socrata API data

### `/scripts`
Command-line interface scripts for running various operations:
- `api_tester.py` - Test API endpoints
- `batch_processor.py` - Process data in batches
- `comptroller_scraper.py` - Scrape Comptroller data
- `data_combiner.py` - Combine data sources
- `deduplicator.py` - Remove duplicates
- `socrata_scraper.py` - Scrape Socrata data

### `/src/api`
API client implementations for external data sources with rate limiting.

### `/src/exporters`
Export functionality for multiple formats (JSON, CSV, Excel).

### `/src/processors`
Data processing modules for combining, validating, and deduplicating data.

### `/src/scrapers`
Web scraper implementations with optional GPU acceleration.

### `/src/utils`
Utility functions including logging, CLI menu, and helper functions.

### `/tests`
Comprehensive test suite covering APIs, scrapers, processors, and integration tests.

## Root Files

| File | Description |
|------|-------------|
| `.env` | Environment variables (API keys, config) |
| `.gitignore` | Git ignore patterns |
| `CHANGELOG.md` | Version history and changes |
| `CONTRIBUTING.md` | Contribution guidelines |
| `LICENSE` | MIT License |
| `Makefile` | Automation commands |
| `PROJECT_STRUCTURE.md` | This file |
| `PROJECT_SUMMARY.md` | Detailed project summary |
| `README.md` | Main documentation |
| `requirements.txt` | Python dependencies |
| `requirements-gpu.txt` | GPU dependencies (CUDA) |
| `run.py` | Main entry point |
| `setup.py` | Package installation setup |
| `setup_project.py` | Project initialization |