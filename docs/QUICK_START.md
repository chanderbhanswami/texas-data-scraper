# Quick Start Guide - Texas Data Scraper

Get started in 5 minutes! 🚀

## ⚡ Installation (2 minutes)

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd texas-data-scraper

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp config/.env.example .env
```

## 🔑 API Keys (1 minute)

Edit `.env` file and add your keys:

```bash
# Get Socrata token at: https://data.texas.gov/profile/edit/developer_settings
SOCRATA_APP_TOKEN=your_token_here

# Get Comptroller key at: https://comptroller.texas.gov/transparency/open-data/
COMPTROLLER_API_KEY=your_key_here
```

**Note:** Socrata token is optional but highly recommended (1k vs 50k requests/hour)

## 🎯 Basic Workflow (2 minutes)

### Step 1: Download Socrata Data
```bash
python scripts/socrata_scraper.py
```
- Select: **1** (Franchise Tax full dataset) or **2** (custom limit)
- Wait for download
- Confirm export: **Yes**
- Files saved to: `exports/socrata/`

### Step 2: Enrich with Comptroller Data
```bash
python scripts/comptroller_scraper.py
```
- Select: **1** (Auto-detect Socrata files)
- Choose: Latest export file
- Method: **2** (Async - faster)
- Confirm export: **Yes**
- Files saved to: `exports/comptroller/`

### Step 3: Combine Data
```bash
python scripts/data_combiner.py
```
- Select: **4** (Auto-detect and combine latest)
- Confirm files: **Yes**
- Export all formats: **Yes**
- Files saved to: `exports/combined/`

### Step 4: Remove Duplicates
```bash
python scripts/deduplicator.py
```
- Select: **4** (Deduplicate all combined files)
- Final clean data saved to: `exports/deduplicated/`

### Step 5: Enrich with Outlet Data (Optional, v1.4.0)
```bash
python scripts/outlet_enricher.py
```
- Select: **1** (Auto-Enrich)
- Choose: Socrata source file
- Choose: Deduplicated file
- Enriched data saved to: `exports/polished/`

### Step 6: Get Google Places Data (Optional, v1.5.0)
```bash
python scripts/google_places_scraper.py
```
- Select: **1** (Auto-Find Place IDs) → export to `exports/place_ids/`
- Select: **5** (Auto-Get Details) → export to `exports/places_details/`
- Then run Data Combiner option **13** to merge with polished data
- Final data saved to: `exports/final/`

## ✅ That's It!

Your clean, enriched data is now in `exports/final/` (or `exports/polished/` or `exports/deduplicated/`) in JSON, CSV, and Excel formats!

## 📊 What You Get

After running all steps, you'll have:

```
exports/deduplicated/
├── combined_data_20251226_143052_deduplicated_20251226_143530.json
├── combined_data_20251226_143052_deduplicated_20251226_143530.csv
└── combined_data_20251226_143052_deduplicated_20251226_143530.xlsx
```

Each record contains:
- ✅ Business name and taxpayer ID
- ✅ Complete address information
- ✅ Franchise tax status and details
- ✅ FTAS records
- ✅ Registration information
- ✅ Registered agent details
- ✅ And more!

## 🎨 Advanced Features

### Search for Specific Businesses
```bash
python scripts/socrata_scraper.py
# Select: 7 (Search by Business Name)
# Enter: "Tesla"
```

### Get Single Taxpayer Info (Quick Test)
```bash
python scripts/comptroller_scraper.py
# Select: 4 (Single Taxpayer Lookup)
# Enter taxpayer ID
# Results displayed in terminal (not exported)
```

### Test API Endpoints
```bash
python scripts/api_tester.py
# Runs comprehensive API tests
# Shows connection status, rate limits, etc.
```

## 🐛 Troubleshooting

### "No API key" Warning
- Add keys to `.env` file
- Socrata token optional but recommended
- Comptroller key required for full access

### "GPU not available" Message
- Don't worry! System automatically uses CPU
- For GPU: Install CUDA and `pip install -r requirements-gpu.txt`

### Rate Limit Errors
- Add Socrata API token for 50x more requests
- Reduce concurrent requests in `.env`:
  ```bash
  CONCURRENT_REQUESTS=3
  ```

### Out of Memory
- Process smaller batches:
  ```bash
  BATCH_SIZE=50
  ```
- In Socrata scraper, use custom limit option instead of full dataset

## 💡 Pro Tips

1. **Start Small**: Use custom limits (1000 records) to test before downloading full datasets
2. **Check Logs**: View `logs/` directory for detailed operation logs
3. **Rate Limits**: Socrata token gives you 50,000 requests/hour vs 1,000 without
4. **Async Mode**: Always use async mode in Comptroller scraper for 5x speed
5. **GPU**: If you have NVIDIA GPU, enable it for 10x faster processing on large datasets

## 🎓 Next Steps

- Read full [README.md](README.md) for detailed documentation
- Explore different search options in Socrata scraper
- Try advanced deduplication strategies
- Set up scheduled scraping with cron/Task Scheduler

## 📞 Need Help?

- Check main [README.md](README.md) troubleshooting section
- Review logs in `logs/` directory
- Ensure API keys are correctly configured in `.env`

---

**Happy scraping! 🎉**