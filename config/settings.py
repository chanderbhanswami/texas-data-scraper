"""
Configuration management for Texas Data Scraper
"""
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = BASE_DIR / os.getenv('EXPORT_DIR', 'exports')
LOG_DIR = BASE_DIR / os.getenv('LOG_DIR', 'logs')
CACHE_DIR = BASE_DIR / os.getenv('CACHE_DIR', '.cache')

# Create directories if they don't exist
for directory in [EXPORT_DIR, LOG_DIR, CACHE_DIR]:
    directory.mkdir(exist_ok=True)

# Export subdirectories
SOCRATA_EXPORT_DIR = EXPORT_DIR / 'socrata'
COMPTROLLER_EXPORT_DIR = EXPORT_DIR / 'comptroller'
COMBINED_EXPORT_DIR = EXPORT_DIR / 'combined'
DEDUPLICATED_EXPORT_DIR = EXPORT_DIR / 'deduplicated'

for directory in [SOCRATA_EXPORT_DIR, COMPTROLLER_EXPORT_DIR, COMBINED_EXPORT_DIR, DEDUPLICATED_EXPORT_DIR]:
    directory.mkdir(exist_ok=True)


class SocrataConfig:
    """Socrata API Configuration"""
    BASE_URL = os.getenv('SOCRATA_BASE_URL', 'https://data.texas.gov/resource')
    APP_TOKEN = os.getenv('SOCRATA_APP_TOKEN', '')
    
    # Dataset IDs
    FRANCHISE_TAX_DATASET = os.getenv('SOCRATA_FRANCHISE_TAX_DATASET', '3d5u-4z8j')
    SALES_TAX_DATASET = os.getenv('SOCRATA_SALES_TAX_DATASET', '3rmv-7xhn')
    MIXED_BEVERAGE_DATASET = os.getenv('SOCRATA_MIXED_BEVERAGE_DATASET', 'na7f-r8iv')
    TAX_REGISTRATIONS_DATASET = os.getenv('SOCRATA_TAX_REGISTRATIONS_DATASET', '8fma-5jfv')
    
    # Rate limits
    RATE_LIMIT_NO_TOKEN = int(os.getenv('SOCRATA_RATE_LIMIT_NO_TOKEN', 1000))
    RATE_LIMIT_WITH_TOKEN = int(os.getenv('SOCRATA_RATE_LIMIT_WITH_TOKEN', 50000))
    
    @property
    def rate_limit(self) -> int:
        """Return appropriate rate limit based on token availability"""
        return self.RATE_LIMIT_WITH_TOKEN if self.APP_TOKEN else self.RATE_LIMIT_NO_TOKEN
    
    @property
    def has_token(self) -> bool:
        """Check if API token is configured"""
        return bool(self.APP_TOKEN)


class ComptrollerConfig:
    """Comptroller API Configuration"""
    BASE_URL = os.getenv('COMPTROLLER_BASE_URL', 
                         'https://api.comptroller.texas.gov/public-data/v1/public')
    API_KEY = os.getenv('COMPTROLLER_API_KEY', '')
    
    # Endpoints
    FRANCHISE_TAX_ENDPOINT = f"{BASE_URL}/franchise-tax"
    FRANCHISE_TAX_LIST_ENDPOINT = f"{BASE_URL}/franchise-tax-list"
    
    # Rate limits
    RATE_LIMIT = int(os.getenv('COMPTROLLER_RATE_LIMIT', 100))
    
    @property
    def has_api_key(self) -> bool:
        """Check if API key is configured"""
        return bool(self.API_KEY)


class RateLimitConfig:
    """Rate limiting configuration"""
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 0.1))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', 5))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))


class BatchProcessingConfig:
    """Batch processing configuration"""
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
    CONCURRENT_REQUESTS = int(os.getenv('CONCURRENT_REQUESTS', 5))


class GPUConfig:
    """GPU acceleration configuration"""
    USE_GPU = os.getenv('USE_GPU', 'true').lower() == 'true'
    GPU_DEVICE_ID = int(os.getenv('GPU_DEVICE_ID', 0))
    GPU_MEMORY_LIMIT = int(os.getenv('GPU_MEMORY_LIMIT', 10240))
    
    @staticmethod
    def is_gpu_available() -> bool:
        """Check if GPU is available"""
        if not GPUConfig.USE_GPU:
            return False
        
        try:
            import cupy as cp
            # Test GPU availability
            cp.cuda.Device(GPUConfig.GPU_DEVICE_ID).compute_capability
            return True
        except Exception:
            return False


class ExportConfig:
    """Export configuration"""
    FORMATS = os.getenv('EXPORT_FORMATS', 'json,csv,excel').split(',')
    COMPRESS = os.getenv('COMPRESS_EXPORTS', 'false').lower() == 'true'


class LogConfig:
    """Logging configuration"""
    LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', 100)) * 1024 * 1024  # Convert to bytes
    BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))


class DataProcessingConfig:
    """Data processing configuration"""
    DEDUP_STRATEGY = os.getenv('DEDUP_STRATEGY', 'taxpayer_id')
    FIELD_PRIORITY = os.getenv('FIELD_PRIORITY', 'comptroller')
    VALIDATE_DATA = os.getenv('VALIDATE_DATA', 'true').lower() == 'true'


class CacheConfig:
    """Caching configuration"""
    ENABLED = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    EXPIRY_HOURS = int(os.getenv('CACHE_EXPIRY', 24))


class AdvancedConfig:
    """Advanced configuration"""
    USER_AGENT = os.getenv('USER_AGENT', 'Texas-Data-Scraper/1.0')
    VERIFY_SSL = os.getenv('VERIFY_SSL', 'true').lower() == 'true'
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


# Initialize configuration instances
socrata_config = SocrataConfig()
comptroller_config = ComptrollerConfig()
rate_limit_config = RateLimitConfig()
batch_config = BatchProcessingConfig()
gpu_config = GPUConfig()
export_config = ExportConfig()
log_config = LogConfig()
data_config = DataProcessingConfig()
cache_config = CacheConfig()
advanced_config = AdvancedConfig()


def validate_configuration() -> List[str]:
    """Validate configuration and return list of warnings/errors"""
    issues = []
    
    if not socrata_config.has_token:
        issues.append("⚠️  No Socrata API token configured - rate limit will be 1k/hour instead of 50k/hour")
    
    if not comptroller_config.has_api_key:
        issues.append("⚠️  No Comptroller API key configured - some features may be limited")
    
    if gpu_config.USE_GPU and not gpu_config.is_gpu_available():
        issues.append("⚠️  GPU acceleration enabled but GPU not available - will fall back to CPU")
    
    return issues


def print_configuration():
    """Print current configuration"""
    print("\n" + "="*60)
    print("TEXAS DATA SCRAPER - CONFIGURATION")
    print("="*60)
    
    print("\n📡 SOCRATA API:")
    print(f"  Token: {'✓ Configured' if socrata_config.has_token else '✗ Not configured'}")
    print(f"  Rate Limit: {socrata_config.rate_limit:,} requests/hour")
    
    print("\n🏛️  COMPTROLLER API:")
    print(f"  API Key: {'✓ Configured' if comptroller_config.has_api_key else '✗ Not configured'}")
    print(f"  Rate Limit: {comptroller_config.RATE_LIMIT} requests/minute")
    
    print("\n🎮 GPU ACCELERATION:")
    print(f"  Enabled: {'Yes' if gpu_config.USE_GPU else 'No'}")
    if gpu_config.USE_GPU:
        print(f"  Available: {'Yes' if gpu_config.is_gpu_available() else 'No'}")
        print(f"  Device: {gpu_config.GPU_DEVICE_ID}")
    
    print("\n📤 EXPORT SETTINGS:")
    print(f"  Formats: {', '.join(export_config.FORMATS)}")
    print(f"  Directory: {EXPORT_DIR}")
    
    print("\n⚙️  PROCESSING:")
    print(f"  Batch Size: {batch_config.BATCH_SIZE}")
    print(f"  Concurrent Requests: {batch_config.CONCURRENT_REQUESTS}")
    
    # Show warnings
    issues = validate_configuration()
    if issues:
        print("\n⚠️  WARNINGS:")
        for issue in issues:
            print(f"  {issue}")
    
    print("\n" + "="*60 + "\n")