# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-27

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