# Texas Government Data Scraper Toolkit

## Project Structure

```
texas-data-scraper/
│
├── .cache/                           # Cache directory
│   └── progress/                     # Progress checkpoints for resume
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
│   └── socrata_scraper.py            # Main Socrata scraper CLI
│
├── src/
│   ├── __init__.py                   # Source package initialization
│   │
│   ├── api/
│   │   ├── __init__.py               # API package initialization
│   │   ├── comptroller_client.py     # Comptroller API client
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
│   │   └── deduplicator.py           # Remove duplicates
│   │
│   ├── scrapers/
│   │   ├── __init__.py               # Scrapers package initialization
│   │   ├── comptroller_scraper.py    # Comptroller data scraper
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

### 10. Future Pipeline (Planned)
- **Phase 1** (Current): Socrata + Comptroller data scraping ✅
- **Phase 2** (Planned): Google Places API integration for business details
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