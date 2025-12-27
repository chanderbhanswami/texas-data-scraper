# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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