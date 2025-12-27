# Deployment Guide - Texas Data Scraper

## 🚀 Production Deployment Checklist

### ✅ Pre-Deployment

- [ ] All tests passing (`pytest tests/`)
- [ ] API keys obtained and tested
- [ ] GPU drivers installed (if using GPU)
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Configuration validated
- [ ] Exports directories created
- [ ] Logs directory configured

### 📋 Deployment Steps

#### 1. System Requirements

```bash
# Verify Python version
python --version  # Must be 3.8+

# Check disk space
df -h  # Need at least 10GB free

# Check memory
free -h  # Recommended 8GB+ RAM
```

#### 2. Clone and Setup

```bash
# Clone repository
git clone <repo-url>
cd texas-data-scraper

# Run automated setup
python setup_project.py

# Verify structure
ls -la config/ src/ scripts/ tests/
```

#### 3. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# For GPU support
pip install -r requirements-gpu.txt
```

#### 4. Configuration

```bash
# Copy environment template
cp config/.env.example .env

# Edit configuration
nano .env

# Required settings:
# - SOCRATA_APP_TOKEN (optional but recommended)
# - COMPTROLLER_API_KEY (required)
# - USE_GPU (true/false)
```

#### 5. Verification

```bash
# Test API connections
python scripts/api_tester.py

# Expected output:
# ✓ Socrata API: 7/7 tests passed
# ✓ Comptroller API: 5/5 tests passed

# Test imports
python -c "from src.api.socrata_client import SocrataClient; print('OK')"

# Check GPU (if enabled)
python -c "from src.scrapers.gpu_accelerator import get_gpu_accelerator; print(get_gpu_accelerator().gpu_available)"
```

#### 6. Initial Test Run

```bash
# Run master script
python run.py

# Select option 8 (Quick Start Workflow)
# This will test the complete pipeline
```

### 🔧 Production Configuration

#### Environment Variables

**Minimum Required:**
```bash
COMPTROLLER_API_KEY=your_key_here
```

**Recommended:**
```bash
SOCRATA_APP_TOKEN=your_token_here
COMPTROLLER_API_KEY=your_key_here

# Rate limiting
REQUEST_DELAY=0.1
MAX_RETRIES=3

# Batch processing
BATCH_SIZE=100
CONCURRENT_REQUESTS=5

# GPU (if available)
USE_GPU=true
GPU_DEVICE_ID=0
GPU_MEMORY_LIMIT=10240

# Logging
LOG_LEVEL=INFO
```

**Production Optimization:**
```bash
# For high-volume scraping
SOCRATA_RATE_LIMIT_WITH_TOKEN=50000
COMPTROLLER_RATE_LIMIT=100
CONCURRENT_REQUESTS=10
BATCH_SIZE=500

# For stability
MAX_RETRIES=5
REQUEST_DELAY=0.2

# For large datasets
GPU_MEMORY_LIMIT=10240
CACHE_ENABLED=true
```

### 🔒 Security Best Practices

1. **API Keys**
   - Never commit `.env` to version control
   - Use environment-specific configurations
   - Rotate keys regularly
   - Limit key permissions

2. **File Permissions**
   ```bash
   chmod 600 .env
   chmod 755 scripts/*.py
   ```

3. **Logging**
   - Review logs regularly
   - Set log rotation limits
   - Don't log sensitive data
   - Keep error logs separate

### 📊 Monitoring

#### Log Files

```bash
# View real-time logs
tail -f logs/texas_scraper_$(date +%Y-%m-%d).log

# Check for errors
tail -f logs/errors_$(date +%Y-%m-%d).log

# Monitor disk usage
du -sh exports/
du -sh logs/
```

#### Performance Monitoring

```bash
# Check memory usage
ps aux | grep python

# Monitor network
netstat -an | grep ESTABLISHED

# GPU monitoring (if applicable)
nvidia-smi -l 1
```

### 🔄 Maintenance

#### Daily Tasks

- [ ] Check logs for errors
- [ ] Verify API rate limits not exceeded
- [ ] Monitor disk space
- [ ] Review processing statistics

#### Weekly Tasks

- [ ] Rotate/compress old logs
- [ ] Backup export data
- [ ] Update dependencies (security patches)
- [ ] Review and clean cache

#### Monthly Tasks

- [ ] Full system health check
- [ ] Dependency updates
- [ ] Performance optimization review
- [ ] API key rotation

### 📈 Scaling for Production

#### Small Scale (< 10k records/day)

```bash
BATCH_SIZE=100
CONCURRENT_REQUESTS=5
USE_GPU=false
```

#### Medium Scale (10k - 100k records/day)

```bash
BATCH_SIZE=500
CONCURRENT_REQUESTS=10
USE_GPU=true
GPU_MEMORY_LIMIT=8192
```

#### Large Scale (100k+ records/day)

```bash
BATCH_SIZE=1000
CONCURRENT_REQUESTS=15
USE_GPU=true
GPU_MEMORY_LIMIT=10240
ENABLE_CACHE=true

# Consider:
# - Multiple API keys for parallel processing
# - Distributed processing
# - Database integration
```

### 🐛 Troubleshooting

#### Common Issues

**Rate Limit Errors:**
```bash
# Reduce concurrent requests
CONCURRENT_REQUESTS=3
REQUEST_DELAY=0.5

# Or get Socrata token for higher limits
```

**Memory Errors:**
```bash
# Reduce batch sizes
BATCH_SIZE=50

# Lower GPU memory limit
GPU_MEMORY_LIMIT=6144

# Disable GPU if causing issues
USE_GPU=false
```

**Connection Timeouts:**
```bash
# Increase timeout
REQUEST_TIMEOUT=60

# Enable retries
MAX_RETRIES=5
RETRY_DELAY=10
```

### 🔄 Backup Strategy

#### What to Backup

1. **Configuration**
   ```bash
   cp .env .env.backup
   tar -czf config_backup.tar.gz config/
   ```

2. **Export Data**
   ```bash
   tar -czf exports_$(date +%Y%m%d).tar.gz exports/
   ```

3. **Logs (if needed)**
   ```bash
   tar -czf logs_$(date +%Y%m).tar.gz logs/
   ```

#### Backup Schedule

- **Daily**: Active export data
- **Weekly**: Logs and configuration
- **Monthly**: Complete system backup

### 📞 Support & Maintenance

#### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "=== Texas Data Scraper Health Check ==="
echo ""

# Check Python
python --version

# Check disk space
df -h | grep -E "/$|/home"

# Check logs for errors
echo "Recent errors:"
tail -5 logs/errors_*.log

# Check API connectivity
python scripts/api_tester.py

echo ""
echo "=== Health Check Complete ==="
```

#### Monitoring Script

```bash
#!/bin/bash
# monitor.sh

while true; do
    clear
    echo "=== Texas Data Scraper Monitor ==="
    echo ""
    echo "Disk Usage:"
    du -sh exports/ logs/
    echo ""
    echo "Latest Exports:"
    ls -lht exports/deduplicated/ | head -5
    echo ""
    echo "Recent Log Entries:"
    tail -3 logs/texas_scraper_*.log
    echo ""
    sleep 30
done
```

### 🎯 Production Optimization

#### Performance Tuning

1. **Enable Caching**
   ```bash
   ENABLE_CACHE=true
   CACHE_EXPIRY=24  # hours
   ```

2. **Optimize Batch Sizes**
   - Test different batch sizes
   - Monitor memory usage
   - Adjust based on network speed

3. **GPU Optimization**
   - Match GPU memory to your card
   - Monitor GPU utilization
   - Adjust batch sizes for GPU

4. **Network Optimization**
   - Use concurrent requests wisely
   - Implement proper rate limiting
   - Handle retries intelligently

### ✅ Production Readiness Checklist

- [ ] All dependencies installed
- [ ] API keys configured and tested
- [ ] Logging configured and working
- [ ] Error handling tested
- [ ] Rate limiting verified
- [ ] Backup strategy implemented
- [ ] Monitoring in place
- [ ] Documentation reviewed
- [ ] Team trained on usage
- [ ] Emergency contacts defined

### 📝 Deployment Notes

**Date Deployed:** _________________

**Deployed By:** _________________

**Configuration:**
- Python Version: _________________
- GPU Enabled: Yes / No
- API Keys: Configured / Not Configured
- Rate Limits: _________________

**Notes:**
_________________________________
_________________________________
_________________________________

---

## 🎉 Ready for Production!

Once all items are checked, your Texas Data Scraper is production-ready!

**Support:** Check logs/, README.md, or review inline documentation