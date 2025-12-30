"""
Test suite for Texas Data Scraper

This package contains comprehensive tests for all modules:
- test_socrata_api.py - Socrata API client tests
- test_comptroller_api.py - Comptroller API client tests
- test_google_places_api.py - Google Places API tests (v1.5.0)
- test_scrapers.py - Scraper module tests (includes Google Places v1.5.0)
- test_processors.py - Data processor tests (includes OutletEnricher v1.4.0)
- test_integration.py - Integration and pipeline tests

Run all tests with: pytest tests/ -v
Run with coverage: pytest tests/ --cov=src --cov-report=html
"""

__version__ = "1.5.0"

# Test modules
__all__ = [
    'test_socrata_api',
    'test_comptroller_api',
    'test_google_places_api',
    'test_scrapers',
    'test_processors',
    'test_integration',
]