# Texas Data Scraper - Makefile
# Common tasks automation

.PHONY: help setup install install-gpu test clean run lint format docs

# Default target
help:
	@echo "Texas Data Scraper - Available Commands:"
	@echo ""
	@echo "  make setup          - Setup project structure"
	@echo "  make install        - Install dependencies"
	@echo "  make install-gpu    - Install GPU dependencies"
	@echo "  make test           - Run tests"
	@echo "  make test-cov       - Run tests with coverage"
	@echo "  make clean          - Clean generated files"
	@echo "  make run            - Run master script"
	@echo "  make lint           - Check code style"
	@echo "  make format         - Format code"
	@echo "  make api-test       - Test API endpoints"
	@echo ""

# Setup project
setup:
	@echo "Setting up project structure..."
	python setup_project.py
	@echo "✓ Setup complete!"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✓ Installation complete!"

# Install GPU dependencies
install-gpu: install
	@echo "Installing GPU dependencies..."
	pip install -r requirements-gpu.txt
	@echo "✓ GPU dependencies installed!"

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "✓ Tests complete!"

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	@echo "✓ Cleanup complete!"

# Run master script
run:
	@echo "Starting Texas Data Scraper..."
	python run.py

# Run API tests
api-test:
	@echo "Testing API endpoints..."
	python scripts/api_tester.py

# Lint code
lint:
	@echo "Checking code style..."
	flake8 src/ scripts/ tests/ --max-line-length=100
	@echo "✓ Linting complete!"

# Format code
format:
	@echo "Formatting code..."
	black src/ scripts/ tests/
	@echo "✓ Formatting complete!"

# Type checking
typecheck:
	@echo "Running type checker..."
	mypy src/ --ignore-missing-imports
	@echo "✓ Type checking complete!"

# Run Socrata scraper
socrata:
	@echo "Starting Socrata scraper..."
	python scripts/socrata_scraper.py

# Run Comptroller scraper
comptroller:
	@echo "Starting Comptroller scraper..."
	python scripts/comptroller_scraper.py

# Run data combiner
combine:
	@echo "Starting data combiner..."
	python scripts/data_combiner.py

# Run deduplicator
dedupe:
	@echo "Starting deduplicator..."
	python scripts/deduplicator.py

# Run batch processor
batch:
	@echo "Starting batch processor..."
	python scripts/batch_processor.py

# Run outlet enricher (v1.4.0)
outlet-enrich:
	@echo "Starting outlet enricher..."
	python scripts/outlet_enricher.py

# Run Google Places scraper (v1.5.0)
google-places:
	@echo "Starting Google Places scraper..."
	python scripts/google_places_scraper.py

# Full pipeline: Socrata → Comptroller → Combine → Dedupe → Outlet → Places → Final
full-pipeline:
	@echo "Running full data pipeline..."
	@echo "Step 1: Socrata"
	@echo "  Run: python scripts/socrata_scraper.py"
	@echo "Step 2: Comptroller"
	@echo "  Run: python scripts/comptroller_scraper.py"
	@echo "Step 3: Combine"
	@echo "  Run: python scripts/data_combiner.py (Option 4 or 6)"
	@echo "Step 4: Deduplicate"
	@echo "  Run: python scripts/deduplicator.py (Option 4)"
	@echo "Step 5: Outlet Enricher (v1.4.0)"
	@echo "  Run: python scripts/outlet_enricher.py (Option 1)"
	@echo "Step 6: Google Places (v1.5.0)"
	@echo "  Run: python scripts/google_places_scraper.py (Options 1+5)"
	@echo "Step 7: Final Combine (v1.5.0)"
	@echo "  Run: python scripts/data_combiner.py (Option 13)"
	@echo ""
	@echo "Or use 'make run' and select Option 11 (Full Pipeline)"

# View logs
logs:
	@echo "Viewing latest logs..."
	tail -f logs/texas_scraper_$$(date +%Y-%m-%d).log

# View errors
errors:
	@echo "Viewing error logs..."
	tail -f logs/errors_$$(date +%Y-%m-%d).log

# Check configuration
config:
	@echo "Current configuration:"
	@python -c "from config.settings import print_configuration; print_configuration()"

# Create .env from example
env:
	@if [ ! -f .env ]; then \
		cp config/.env.example .env; \
		echo "✓ Created .env from example"; \
		echo "⚠ Remember to add your API keys!"; \
	else \
		echo "⊙ .env already exists"; \
	fi

# Full setup (first time)
first-time: env setup install
	@echo ""
	@echo "✓ First-time setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and add your API keys"
	@echo "  2. Run 'make api-test' to verify"
	@echo "  3. Run 'make run' to start"
	@echo ""

# Development setup
dev-setup: first-time
	@echo "Installing development dependencies..."
	pip install pytest black flake8 mypy pytest-cov
	@echo "✓ Development environment ready!"

# Quick test run
quick-test:
	@echo "Running quick test..."
	@python -c "from src.api.socrata_client import SocrataClient; print('✓ Import successful')"
	@python -c "from src.api.comptroller_client import ComptrollerClient; print('✓ Import successful')"
	@python -c "from src.scrapers.gpu_accelerator import GPUAccelerator; print('✓ Import successful')"
	@echo "✓ Quick test passed!"

# Check for updates
check:
	@echo "Checking system..."
	@python --version
	@pip list | grep -E "requests|pandas|rich|pytest" || echo "Some packages not installed"
	@echo "✓ System check complete!"

# Generate documentation
docs:
	@echo "Documentation available in:"
	@echo "  - README.md"
	@echo "  - QUICK_START.md"
	@echo "  - INSTALLATION_CHECKLIST.md"
	@echo "  - DEPLOYMENT_GUIDE.md"

# Install pre-commit hooks (optional)
hooks:
	@echo "Installing pre-commit hooks..."
	@echo "#!/bin/bash" > .git/hooks/pre-commit
	@echo "make format" >> .git/hooks/pre-commit
	@echo "make lint" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ Pre-commit hooks installed!"

# Package for distribution
package:
	@echo "Creating distribution package..."
	python setup.py sdist bdist_wheel
	@echo "✓ Package created in dist/"

# All quality checks
quality: format lint typecheck test
	@echo "✓ All quality checks passed!"
```

---

## Usage Examples

```bash
# First time setup
make first-time

# Install everything including GPU support
make install-gpu

# Run tests
make test

# Run with coverage
make test-cov

# Format and lint code
make format
make lint

# Run the application
make run

# Run specific scrapers
make socrata
make comptroller
make combine
make dedupe
make outlet-enrich      # v1.4.0
make google-places      # v1.5.0

# View logs
make logs
make errors

# Quick system check
make quick-test

# Clean all generated files
make clean

# Run all quality checks
make quality

# Show full pipeline steps
make full-pipeline
```