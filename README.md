<div align="center">

# 🤠 Texas Government Data Scraper Toolkit

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)]()
[![CUDA](https://img.shields.io/badge/CUDA-11.8%2B-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge)](CONTRIBUTING.md)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green?style=for-the-badge)](https://github.com/chanderbhanswami/texas-data-scraper/graphs/commit-activity)

<p align="center">
  <strong>A comprehensive, production-ready toolkit for scraping and processing data from Texas government APIs</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage-guide">Usage</a> •
  <a href="#-documentation">Docs</a> •
  <a href="#-contributing">Contributing</a> •
  <a href="#-support">Support</a>
</p>

---

</div>

A comprehensive, production-ready toolkit for scraping and processing data from Texas government APIs including the Socrata Open Data Portal and Texas Comptroller API. Features GPU acceleration (CUDA/cuDNN), intelligent data merging, and automated deduplication.

## 🚀 Features

### Core Capabilities
- **Dual API Support**: Socrata Open Data Portal + Texas Comptroller API
- **GPU Acceleration**: CUDA/cuDNN optimized for NVIDIA RTX 3060
- **Interactive CLI**: User-friendly menus for all operations
- **Multi-Format Export**: JSON, CSV, and Excel with automatic formatting
- **Smart Data Merging**: Intelligent field prioritization and conflict resolution
- **Advanced Deduplication**: Multiple strategies with merge capabilities
- **Rate Limiting**: Intelligent throttling with automatic token management
- **Comprehensive Logging**: Detailed logs with rotation and compression
- **Progress Persistence**: Resume interrupted downloads from checkpoints (v1.1.0)
- **Export Verification**: SHA-256 checksums for data integrity (v1.1.0)

### Data Sources
- Franchise Tax Permit Holders
- Sales Tax Permit Holders
- Mixed Beverage Tax Permit Holders
- Tax Registration Data
- Detailed Taxpayer Information
- FTAS (Franchise Tax Account Status) Records

## 📋 Requirements

### System Requirements
- Python 3.8+
- NVIDIA GPU with CUDA support (optional, for GPU acceleration)
- CUDA Toolkit 11.8+ or 12.x
- cuDNN 8.9.x or later
- 8GB+ RAM (16GB recommended)
- 10GB+ free disk space

### API Keys (Free)
1. **Socrata API Token** (optional but recommended)
   - Increases rate limit from 1,000 to 50,000 requests/hour
   - Get at: https://data.texas.gov/profile/edit/developer_settings

2. **Texas Comptroller API Key** (required for full access)
   - Get at: https://comptroller.texas.gov/transparency/open-data/

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd texas-data-scraper
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

#### For CPU-Only Installation:
```bash
pip install -r requirements.txt
```

#### For GPU-Accelerated Installation:
```bash
# First, ensure CUDA Toolkit and cuDNN are installed
# Download from: https://developer.nvidia.com/cuda-downloads
# and: https://developer.nvidia.com/cudnn

# Then install GPU requirements
pip install -r requirements-gpu.txt
```

### 4. Configure Environment Variables
```bash
# Copy the example environment file
cp config/.env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

#### Required Environment Variables:
```bash
# Socrata API Token (optional but recommended)
SOCRATA_APP_TOKEN=your_token_here

# Comptroller API Key (required)
COMPTROLLER_API_KEY=your_key_here

# GPU Settings (if using GPU)
USE_GPU=true
GPU_DEVICE_ID=0
GPU_MEMORY_LIMIT=10240
```

### 5. Verify Installation
```bash
# Test API endpoints
python scripts/api_tester.py

# Check GPU availability (if using GPU)
python -c "import cupy; print('GPU Available:', cupy.cuda.is_available())"
```

## 📖 Usage Guide

### 1. Socrata Data Scraper

Download data from Texas Open Data Portal:

```bash
python scripts/socrata_scraper.py
```

**Interactive Menu Options:**
- Download full datasets (Franchise Tax, Sales Tax, etc.)
- Download with custom record limits
- Search by business name, city, ZIP code, agent name, etc.
- View dataset metadata
- Export data in multiple formats

**Example Workflow:**
1. Select "1" for Franchise Tax (full dataset)
2. Wait for download to complete
3. Choose "Yes" to export data
4. Files saved to `exports/socrata/` in JSON, CSV, and Excel formats

### 2. Comptroller Data Scraper

Fetch detailed taxpayer information:

```bash
python scripts/comptroller_scraper.py
```

**Features:**
- Auto-detect Socrata export files
- Batch process taxpayer IDs
- Single taxpayer lookup (terminal-only display)
- Async processing for faster results
- Combined details + FTAS records

**Example Workflow:**
1. First, run Socrata scraper to get taxpayer IDs
2. Select "1" for auto-detect Socrata files
3. Choose the most recent export
4. Select async processing method
5. Wait for batch processing
6. Export enriched data

### 3. Data Combiner

Merge Socrata and Comptroller data intelligently:

```bash
python scripts/data_combiner.py
```

**Features:**
- Smart field merging with priority (Comptroller > Socrata)
- Automatic conflict resolution
- Support for JSON, CSV, and Excel
- Auto-detect latest exports

**Example Workflow:**
1. Select "4" for auto-detect and combine
2. Confirm the detected files
3. View combination statistics
4. Export combined data

### 4. Deduplicator

Remove duplicate records and polish data:

```bash
python scripts/deduplicator.py
```

**Deduplication Strategies:**
- **taxpayer_id**: Remove duplicates by taxpayer ID (fastest)
- **exact**: Remove exact duplicate records
- **fuzzy**: Fuzzy matching on key fields

**Advanced Options:**
- Deduplicate with merge (combines duplicate records)
- Deduplicate by confidence (keeps most complete record)

**Example Workflow:**
1. Select "4" to deduplicate all combined exports
2. Review deduplication statistics
3. Files saved to `exports/deduplicated/`

### 5. API Endpoint Tester

Test all API endpoints:

```bash
python scripts/api_tester.py
```

**Tests:**
- Socrata API connection and token validation
- Comptroller API connection and key validation
- Dataset access and search functionality
- Pagination and metadata retrieval
- Error handling

## 📁 Project Structure

```
texas-data-scraper/
│
├── .cache/                           # Cache directory
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

## 🎯 Complete Workflow Example

### Full Pipeline: Socrata → Comptroller → Combine → Deduplicate

```bash
# Step 1: Download Socrata data
python scripts/socrata_scraper.py
# Select: 1 (Franchise Tax full dataset)
# Export: Yes

# Step 2: Enrich with Comptroller data
python scripts/comptroller_scraper.py
# Select: 1 (Auto-detect Socrata files)
# Choose: Latest export
# Method: 2 (Async)
# Export: Yes

# Step 3: Combine both datasets
python scripts/data_combiner.py
# Select: 4 (Auto-detect and combine)
# Export: Yes (all formats)

# Step 4: Remove duplicates
python scripts/deduplicator.py
# Select: 4 (Deduplicate all combined)
# Strategy: taxpayer_id

# Final data location: exports/deduplicated/
```

## ⚙️ Configuration

### Rate Limits

**Socrata API:**
- Without token: 1,000 requests/hour
- With token: 50,000 requests/hour

**Comptroller API:**
- 100 requests/minute (with API key)

### GPU Settings

Optimize for your RTX 3060:

```bash
# .env file
USE_GPU=true
GPU_DEVICE_ID=0
GPU_MEMORY_LIMIT=10240  # 10GB for RTX 3060 (12GB total)
```

### Batch Processing

```bash
BATCH_SIZE=100              # Records per batch
CONCURRENT_REQUESTS=5       # Simultaneous requests
```

## 🐛 Troubleshooting

### Common Issues

**1. GPU Not Detected**
```bash
# Check CUDA installation
nvidia-smi

# Verify CuPy installation
python -c "import cupy; cupy.cuda.runtime.getDeviceProperties(0)"

# If issues persist, use CPU-only mode:
USE_GPU=false
```

**2. Rate Limit Errors**
- Add Socrata API token to `.env`
- Reduce `CONCURRENT_REQUESTS` in settings
- Increase `REQUEST_DELAY`

**3. Memory Errors**
- Reduce `BATCH_SIZE`
- Lower `GPU_MEMORY_LIMIT`
- Process smaller datasets

**4. Import Errors**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# For GPU issues
pip install --force-reinstall -r requirements-gpu.txt
```

## 📊 Output Formats

All exports include:
- **JSON**: Human-readable, preserves data types
- **CSV**: Excel-compatible (UTF-8 with BOM)
- **Excel**: Formatted with headers, auto-sized columns

### File Naming Convention
```
[source]_[dataset]_[timestamp].[ext]
Example: franchise_tax_20251226_143052.json
```

## 🔒 Data Privacy & Security

- API keys stored in `.env` (gitignored)
- No data transmitted to third parties
- All processing done locally
- Logs exclude sensitive information

## 📈 Performance Tips

1. **Use GPU acceleration** for large datasets (10k+ records)
2. **Enable Socrata API token** for faster downloads
3. **Use async processing** in Comptroller scraper
4. **Batch process** large taxpayer ID lists
5. **Clear GPU memory** between large operations

## 🧪 Testing

Run the test suite:

```bash
# API endpoint tests
python scripts/api_tester.py

# Unit tests (if implemented)
pytest tests/

# Integration tests
pytest tests/test_integration.py
```

## 📝 Logging

Logs are saved to `logs/` directory:
- `texas_scraper_YYYY-MM-DD.log` - All operations
- `errors_YYYY-MM-DD.log` - Errors only
- Automatic rotation at 100MB
- Compressed archives retained

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[LICENSE](LICENSE)

## 🆘 Support

For issues or questions:
- Check troubleshooting section
- Review logs in `logs/` directory
- Check API status pages
- Create an issue on GitHub

## 🎓 Additional Resources

- [Socrata API Documentation](https://dev.socrata.com/)
- [Texas Open Data Portal](https://data.texas.gov/)
- [Texas Comptroller API](https://comptroller.texas.gov/transparency/open-data/)
- [CUDA Toolkit Documentation](https://docs.nvidia.com/cuda/)
- [cuDNN Documentation](https://docs.nvidia.com/deeplearning/cudnn/)

---

## 📸 Screenshots & Demo

<details>
<summary>Click to view screenshots</summary>

### Socrata Scraper Menu
```
╔══════════════════════════════════════════════════════════════╗
║           TEXAS DATA SCRAPER - SOCRATA MENU                  ║
╠══════════════════════════════════════════════════════════════╣
║  1. Download Franchise Tax (Full Dataset)                    ║
║  2. Download Sales Tax (Full Dataset)                        ║
║  3. Download Mixed Beverage Tax (Full Dataset)               ║
║  4. Search by Business Name                                  ║
║  5. Search by City                                           ║
║  ...                                                         ║
╚══════════════════════════════════════════════════════════════╝
```

### Data Processing Pipeline
```
Socrata API → Raw Data → Comptroller Enrichment → Merge → Deduplicate → Export
     ↓            ↓              ↓                  ↓         ↓           ↓
  50k+ records  JSON/CSV     +FTAS data         Combined   Cleaned    JSON/CSV/Excel
```

</details>

---

## 🗺️ Roadmap

See our [project roadmap](https://github.com/chanderbhanswami/texas-data-scraper/projects) for upcoming features.

### Phase 1: Core Data Pipeline ✅
- [x] Socrata Open Data Portal integration
- [x] Texas Comptroller API integration
- [x] GPU acceleration with CUDA
- [x] Multi-format export (JSON, CSV, Excel)
- [x] Data deduplication
- [x] Interactive CLI menus

### Phase 1.1: Resilience & Reliability ✅ (NEW)
- [x] Progress persistence (resume interrupted downloads)
- [x] Export checksum verification
- [x] Data validation and quality reports
- [x] GPU-accelerated merging and deduplication

### Phase 2: Business Enrichment (Planned)
- [ ] Google Places API integration
  - Business phone numbers
  - Business websites
  - Business addresses verification
  - Operating hours
- [ ] Clearbit API integration
  - Company emails
  - Social media profiles
  - Company logo and branding
  - Industry classification

### Phase 3: Advanced Features (Planned)
- [ ] Web dashboard interface
- [ ] Scheduled automatic scraping
- [ ] Email notifications
- [ ] Cloud deployment support
- [ ] API rate limit analytics
- [ ] Data visualization exports
- [ ] Unified company profile generation

---

## ❓ FAQ

<details>
<summary><strong>Q: Do I need an NVIDIA GPU to use this tool?</strong></summary>

No! GPU acceleration is optional. The toolkit automatically falls back to CPU processing if no GPU is detected. GPU acceleration is recommended for datasets with 10,000+ records.
</details>

<details>
<summary><strong>Q: Are the API keys free?</strong></summary>

Yes! Both the Socrata API token and Texas Comptroller API key are free. The Socrata token increases your rate limit from 1,000 to 50,000 requests per hour.
</details>

<details>
<summary><strong>Q: What data can I access?</strong></summary>

You can access public Texas government data including Franchise Tax Permit Holders, Sales Tax Permit Holders, Mixed Beverage Tax Permit Holders, and detailed taxpayer information through the Comptroller API.
</details>

<details>
<summary><strong>Q: Is the data up to date?</strong></summary>

The data is fetched directly from official Texas government APIs in real-time, ensuring you always get the most current publicly available information.
</details>

<details>
<summary><strong>Q: Can I use this for commercial purposes?</strong></summary>

Please review the [LICENSE](LICENSE) file and the terms of use for the Texas Open Data Portal and Comptroller API for commercial use guidelines.
</details>

---

## 🙏 Acknowledgments

- [Texas Open Data Portal](https://data.texas.gov/) - For providing open access to state data
- [Texas Comptroller of Public Accounts](https://comptroller.texas.gov/) - For the comprehensive taxpayer API
- [Socrata](https://dev.socrata.com/) - For their excellent Open Data API
- [NVIDIA](https://developer.nvidia.com/) - For CUDA toolkit and GPU acceleration support
- All [contributors](https://github.com/chanderbhanswami/texas-data-scraper/graphs/contributors) who help improve this project

---

## 📊 Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=chanderbhanswami/texas-data-scraper&type=Date)](https://star-history.com/#chanderbhanswami/texas-data-scraper&Date)

*If you find this project useful, please consider giving it a ⭐!*

</div>

---

## 📞 Contact & Social Media

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/chanderbhanswami)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/chanderbhanswami)
[![X](https://img.shields.io/badge/X-1DA1F2?style=for-the-badge&logo=x&logoColor=white)](https://x.com/Chanderbhanswa7)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://instagram.com/chanderbhan_swami)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:chanderbhanswami29@gmail.com)
[![Portfolio](https://img.shields.io/badge/Portfolio-FF5722?style=for-the-badge&logo=google-chrome&logoColor=white)](https://chanderbhanswami.github.io)

</div>

**Project Maintainer:** [Chanderbhanswami](https://github.com/chanderbhanswami)

📧 **Email:** chanderbhanswami@gmail.com

🐦 **X:** [Chanderbhanswa7](https://x.com/Chanderbhanswa7)

---

## 📝 Citation

If you use this tool in your research or project, please cite it as:

```bibtex
@software{texas_data_scraper,
  author = {Chanderbhanswami},
  title = {Texas Government Data Scraper Toolkit},
  year = {2024},
  url = {https://github.com/chanderbhanswami/texas-data-scraper}
}
```

---

<div align="center">

**Made with ❤️ in Texas**

🤠 **Happy Scraping, Y'all!** 🤠

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f?style=flat-square&logo=python)](https://www.python.org/)
[![Powered by CUDA](https://img.shields.io/badge/Powered%20by-CUDA-76B900?style=flat-square&logo=nvidia)](https://developer.nvidia.com/cuda-toolkit)

</div>