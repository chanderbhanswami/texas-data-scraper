# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-12-30

### Added
- **Outlet Data Enricher** (New Script!)
  - `scripts/outlet_enricher.py` - Interactive CLI
  - `src/processors/outlet_enricher.py` - Core processor
  - Extracts outlet fields from duplicate Socrata records
  - Enriches deduplicated data with outlet info (address, NAICS, permits)
  - Supports multiple outlets per taxpayer
  - GPU acceleration support
  - New export directory: `exports/polished/`

- **Persistent Disk Caching** (Comptroller Scraper)
  - Cache now saves to `.cache/comptroller/` as JSON files
  - Survives script restarts - truly resumable!
  - Each taxpayer cached individually
  - Option 3 "With Caching" now persists across sessions

- **Network Retry with Exponential Backoff**
  - Automatic retry on network errors (DNS, connection failures)
  - Up to 3 retries with increasing delays (5s, 10s, 20s)
  - Prevents data loss during internet outages
  - Applies to both API endpoints

- **Configurable Comptroller Settings**
  - `COMPTROLLER_CONCURRENT_REQUESTS` - Concurrent API calls (default: 2)
  - `COMPTROLLER_CHUNK_SIZE` - Batch size (default: 25)
  - `COMPTROLLER_REQUEST_DELAY` - Delay between requests (default: 1.5s)

### Changed
- Comptroller API key header fixed: now uses `x-api-key` per official docs
- `SmartComptrollerScraper` uses disk cache instead of memory cache
- Added `POLISHED_EXPORT_DIR` to settings.py

### Technical Details
- New files:
  - `src/processors/outlet_enricher.py` - OutletEnricher, AdvancedOutletEnricher
  - `scripts/outlet_enricher.py` - OutletEnricherCLI
  - `exports/polished/.gitkeep` - Output directory
- Modified files:
  - `src/scrapers/comptroller_scraper.py` - Disk caching
  - `src/api/comptroller_client.py` - Network retry, configurable settings
  - `config/settings.py` - POLISHED_EXPORT_DIR, Comptroller settings

## [1.3.0] - 2025-12-28

### Added
- **Process ALL Socrata Files** (Comptroller Scraper)
  - New menu option 3: "📁 Process ALL Socrata Files (combined)"
  - Auto-detects all Socrata JSON files
  - Extracts unique taxpayer IDs from all files
  - Processes all at once through Comptroller API
  - Uses JSON-only to avoid CSV/Excel duplication

- **Separate Comptroller Files Per Dataset**
  - Exports now use source-specific filenames
  - `comptroller_franchise_tax_permit_holders.*`
  - `comptroller_sales_tax_permit_holders.*`
  - Clear traceability of which Comptroller data came from which Socrata source

- **Master Combine All** (Data Combiner - Option 6)
  - 🌟 Full pipeline automation
  - Step 1: Merge ALL Socrata JSON files → Master Socrata dataset
  - Step 2: Merge ALL Comptroller JSON files → Master Comptroller dataset
  - Step 3: Combine by taxpayer ID → Final enriched dataset
  - Step 4: Export to `master_combined.*` (JSON, CSV, Excel)

- **9 Manual Combine Options** (Data Combiner - Option 12)
  - Submenu with granular control over file merging
  - Options 1-3: Combine all Socrata JSON/CSV/Excel
  - Options 4-6: Combine all Comptroller JSON/CSV/Excel
  - Options 7-9: Cross-source combine by format
  - Distinct output filenames: `merged_socrata_json.*`, `combined_all_csv.*`, etc.

### Changed
- Data Combiner menu renumbered (GPU → 7, Data Quality → 8-9, Stats → 10-11)
- Comptroller menu renumbered to accommodate "Process ALL" option
- `detect_socrata_files()` now accepts `json_only` parameter to prevent duplication

### Technical Details
- New methods in `scripts/comptroller_scraper.py`:
  - `process_all_socrata_files()` - Bulk processing
  - `detect_socrata_files(json_only=True)` - Smart format detection
- New methods in `scripts/data_combiner.py`:
  - `master_combine_all()` - Full pipeline
  - `_merge_all_json_files()` - JSON-specific merging
  - `_merge_all_files_by_format()` - Any format merging
  - `combine_single_source()` - Single source merge (options 1-6)
  - `combine_cross_source()` - Cross-source merge (options 7-9)
  - `show_manual_combine_menu()` - Submenu display
  - `handle_manual_combine()` - Submenu handler

## [1.2.0] - 2025-12-27

### Added
- **Smart Field Detection** (`src/utils/helpers.py`)
  - Case-insensitive taxpayer ID field matching
  - Semantic field normalization (e.g., `zipcode` → `zip_code`)
  - `TAXPAYER_ID_FIELDS` - 20+ field name variations supported
  - `FIELD_SYNONYMS` - Maps field variations to canonical names
  - `normalize_field_name()`, `extract_taxpayer_id_from_record()`
  - `normalize_record_fields()`, `smart_merge_records()`

- **Global Auto-Deduplication** (Socrata Scraper)
  - Automatically loads ALL existing exports before scraping
  - Builds master set of already-scraped taxpayer IDs
  - Skips records that exist in ANY previous export
  - Works across multiple datasets automatically
  - Shows duplicate count during scrape

- **Append-to-Existing Export Mode** (`src/exporters/file_exporter.py`)
  - New records appended to existing files (not new timestamped files)
  - Single consolidated file per dataset
  - `append_json()`, `append_csv()`, `append_excel()` methods
  - `append_or_create_all_formats()` for all formats at once

### Changed
- Socrata CLI now auto-filters duplicates on every scrape
- Fixed filenames per dataset (no timestamps) for consolidated exports
- Comptroller CLI exports also use append mode

### Technical Details
- New functions in `helpers.py`: `camel_to_snake()`, `find_taxpayer_id_field()`, `find_matching_fields()`, `get_field_value_by_semantic_name()`
- Field normalization handles: zip_code, business_name, phone, email, registration_date, status, file_number variations

## [1.1.0] - 2025-12-27

### Added
- **Progress Persistence** (`src/utils/progress_manager.py`)
  - Auto-save progress on interruption (Ctrl+C or crash)
  - Resume interrupted downloads from checkpoints
  - Progress stored in `.cache/progress/` directory
  - Resume Session menu option in CLI scripts

- **Export Checksum Verification** (`src/utils/checksum.py`)
  - SHA-256 checksums for exported files
  - `.checksum` files generated alongside exports
  - Automatic verification on file load
  - Data integrity protection

- **Enhanced Scraper Wrappers**
  - `scrape_with_progress()` method in SmartComptrollerScraper
  - `scrape_with_progress()` method in BulkSocrataScraper
  - GPU-accelerated `combine_with_gpu()` in SmartDataCombiner
  - GPU-accelerated `deduplicate_with_gpu()` in AdvancedDeduplicator
  - Hash-based deduplication using helpers.generate_hash()

- **CLI Menu Enhancements**
  - Resume Last Session (Option 18 in Comptroller CLI)
  - View/Clear Saved Progress (Option 19 in Comptroller CLI)
  - Validate & Clean Data options in all CLI scripts
  - View Data Quality Report options
  - GPU/Memory Stats display

- **Module Integrations**
  - Integrated `gpu_accelerator` across all processors and CLI scripts
  - Integrated `data_validator` for quality reporting and cleaning
  - Integrated `helpers` functions (format_bytes, clean_taxpayer_id, generate_hash)

### Changed
- FileExporter now generates checksums by default
- Load functions verify checksums before loading
- Scraper wrappers now save progress automatically during large operations

### Technical Details
- New files: `progress_manager.py`, `checksum.py`
- Checkpoint interval: 50 records (Comptroller), 5000 records (Socrata)
- SHA-256 algorithm for file integrity

## [1.0.0] - 2025-12-27

### Added
- Initial release of Texas Data Scraper
- Socrata API client (sync + async)
- Comptroller API client (sync + async)
- GPU acceleration support (CUDA/cuDNN)
- Interactive CLI scripts (7 total)
- Data validation and cleaning
- Smart data merging
- Advanced deduplication (3 strategies)
- Multi-format export (JSON/CSV/Excel)
- Rate limiting with exponential backoff
- Comprehensive logging system
- Progress tracking
- Batch processing for large datasets
- 50+ helper utility functions
- Complete test suite
- Full documentation

### Features
- **Socrata Scraper**: 17 interactive menu options
- **Comptroller Scraper**: Batch processing with auto-detection
- **Data Combiner**: Intelligent field merging
- **Deduplicator**: taxpayer_id, exact, and fuzzy strategies
- **Batch Processor**: Handle datasets of any size
- **API Tester**: Comprehensive endpoint validation
- **Master Script**: Unified interface with workflows

### Documentation
- Complete README.md
- Quick Start Guide
- Installation Checklist
- Deployment Guide
- Project Summary
- Contributing Guidelines
- Complete File List

### Technical Details
- Python 3.8+ support
- NVIDIA GPU optimization (RTX 3060)
- Async/await for concurrent operations
- Environment-based configuration
- Modular architecture
- Production-ready error handling