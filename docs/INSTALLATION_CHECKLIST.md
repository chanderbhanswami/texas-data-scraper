# Installation Checklist - Texas Data Scraper

Follow these steps to ensure proper installation:

## ✅ Pre-Installation

- [ ] Python 3.8 or higher installed
  ```bash
  python --version
  ```

- [ ] pip installed and updated
  ```bash
  pip --version
  pip install --upgrade pip
  ```

- [ ] Git installed (if cloning from repository)
  ```bash
  git --version
  ```

- [ ] (Optional) NVIDIA GPU with CUDA support
  ```bash
  nvidia-smi
  ```

## ✅ Step 1: Project Setup

- [ ] Clone/download project
  ```bash
  git clone <repo-url>
  cd texas-data-scraper
  ```

- [ ] Run setup script
  ```bash
  python setup_project.py
  ```

- [ ] Verify directory structure created
  ```
  ✓ config/
  ✓ src/api/
  ✓ src/scrapers/
  ✓ src/processors/
  ✓ src/exporters/
  ✓ src/utils/
  ✓ scripts/
  ✓ exports/
  ✓ logs/
  ```

## ✅ Step 2: Virtual Environment

- [ ] Create virtual environment
  ```bash
  python -m venv venv
  ```

- [ ] Activate virtual environment
  ```bash
  # Windows
  venv\Scripts\activate
  
  # Linux/Mac
  source venv/bin/activate
  ```

- [ ] Verify activation
  ```bash
  which python  # Should show venv path
  ```

## ✅ Step 3: Install Dependencies

- [ ] Install core dependencies
  ```bash
  pip install -r requirements.txt
  ```

- [ ] Verify core installation
  ```bash
  pip list | grep requests
  pip list | grep pandas
  pip list | grep rich
  ```

- [ ] (Optional) Install GPU dependencies
  ```bash
  pip install -r requirements-gpu.txt
  ```

- [ ] (Optional) Verify GPU installation
  ```bash
  python -c "import cupy; print('CuPy version:', cupy.__version__)"
  python -c "import cudf; print('cuDF available')"
  ```

## ✅ Step 4: Configuration

- [ ] Copy environment template
  ```bash
  cp config/.env.example .env
  ```

- [ ] Get Socrata API Token
  - Visit: https://data.texas.gov/profile/edit/developer_settings
  - Create account if needed
  - Generate app token
  - Copy token

- [ ] Get Comptroller API Key
  - Visit: https://comptroller.texas.gov/transparency/open-data/
  - Request API key
  - Copy key

- [ ] Edit .env file
  ```bash
  nano .env  # or use your preferred editor
  ```

- [ ] Add API credentials to .env
  ```bash
  SOCRATA_APP_TOKEN=your_socrata_token_here
  COMPTROLLER_API_KEY=your_comptroller_key_here
  ```

- [ ] Configure GPU settings (if applicable)
  ```bash
  USE_GPU=true
  GPU_DEVICE_ID=0
  GPU_MEMORY_LIMIT=10240
  ```

- [ ] Save .env file

## ✅ Step 5: Verification

- [ ] Run API endpoint tests
  ```bash
  python scripts/api_tester.py
  ```

- [ ] Verify test results
  ```
  Expected:
  ✓ Socrata API: 7/7 tests passed
  ✓ Comptroller API: 5/5 tests passed
  ```

- [ ] Check configuration
  ```bash
  python -c "from config.settings import print_configuration; print_configuration()"
  ```

- [ ] Verify exports directories exist
  ```bash
  ls -la exports/
  ```

- [ ] Verify logs directory exists
  ```bash
  ls -la logs/
  ```

## ✅ Step 6: Test Run

- [ ] Run Socrata scraper
  ```bash
  python scripts/socrata_scraper.py
  ```

- [ ] Download small test dataset
  - Select option: 2 (custom limit)
  - Enter limit: 100
  - Export: Yes

- [ ] Verify export files created
  ```bash
  ls -lh exports/socrata/
  ```

- [ ] Check file contents
  ```bash
  # View first few lines of JSON
  head -n 20 exports/socrata/*.json
  ```

## ✅ Step 7: Full Pipeline Test

- [ ] Download Socrata data (100 records)
  ```bash
  python scripts/socrata_scraper.py
  # Option 2, limit 100
  ```

- [ ] Process with Comptroller scraper
  ```bash
  python scripts/comptroller_scraper.py
  # Option 1 (auto-detect)
  ```

- [ ] Combine data
  ```bash
  python scripts/data_combiner.py
  # Option 4 (auto-detect)
  ```

- [ ] Deduplicate
  ```bash
  python scripts/deduplicator.py
  # Option 4 (deduplicate all)
  ```

- [ ] Enrich with outlet data (v1.4.0)
  ```bash
  python scripts/outlet_enricher.py
  # Option 1 (Auto-Enrich)
  ```

- [ ] Get Google Places data (v1.5.0)
  ```bash
  python scripts/google_places_scraper.py
  # Option 1 (Auto-Find Place IDs)
  # Option 5 (Auto-Get Details)
  # Then Data Combiner Option 13 to merge
  ```

- [ ] Verify final output
  ```bash
  ls -lh exports/final/
  # Or if skipping Google Places:
  ls -lh exports/polished/
  # Or if skipping enricher:
  ls -lh exports/deduplicated/
  ```

## ✅ Troubleshooting Checks

### If API Tests Fail:

- [ ] Check internet connection
  ```bash
  ping google.com
  ```

- [ ] Verify API keys in .env
  ```bash
  cat .env | grep API
  ```

- [ ] Check API key format (no extra spaces)

- [ ] Test API URLs directly
  ```bash
  curl "https://data.texas.gov/resource/3d5u-4z8j.json?$limit=1"
  ```

### If Import Errors Occur:

- [ ] Verify virtual environment is activated
  ```bash
  which python
  ```

- [ ] Reinstall requirements
  ```bash
  pip install --force-reinstall -r requirements.txt
  ```

- [ ] Check Python version
  ```bash
  python --version  # Must be 3.8+
  ```

### If GPU Not Available:

- [ ] Check CUDA installation
  ```bash
  nvidia-smi
  nvcc --version
  ```

- [ ] Verify CuPy installation
  ```bash
  python -c "import cupy; cupy.cuda.runtime.getDeviceProperties(0)"
  ```

- [ ] Set USE_GPU=false in .env if not needed

### If Memory Errors:

- [ ] Reduce batch size in .env
  ```bash
  BATCH_SIZE=50
  ```

- [ ] Reduce GPU memory limit
  ```bash
  GPU_MEMORY_LIMIT=8192
  ```

- [ ] Use smaller datasets for testing

## ✅ Post-Installation

- [ ] Read README.md
- [ ] Read QUICK_START.md
- [ ] Review PROJECT_SUMMARY.md
- [ ] Check logs directory for errors
  ```bash
  tail -f logs/texas_scraper_*.log
  ```

- [ ] (Optional) Set up scheduled scraping
- [ ] (Optional) Create backup of .env file
- [ ] (Optional) Add project to IDE/editor

## 📋 Final Verification Checklist

- [ ] ✓ All dependencies installed
- [ ] ✓ API keys configured
- [ ] ✓ Environment variables set
- [ ] ✓ Directory structure created
- [ ] ✓ API tests passing
- [ ] ✓ Test run successful
- [ ] ✓ Export files generated
- [ ] ✓ Logs working
- [ ] ✓ GPU detected (if applicable)
- [ ] ✓ No import errors

## 🎉 Installation Complete!

If all checkboxes are checked, you're ready to start scraping!

### Quick Start:
```bash
# Start with socrata scraper
python scripts/socrata_scraper.py
```

### Need Help?
- Check [README.md](README.md) for detailed docs
- Check [QUICK_START.md](QUICK_START.md) for quick guide
- Review logs in `logs/` directory
- Run `python scripts/api_tester.py` to diagnose issues

---

**Installation Time Estimate:** 10-15 minutes

**Happy Scraping! 🚀**