#!/usr/bin/env python3
"""
Project Setup Script
Creates all necessary directories and files for the Texas Data Scraper
"""
import os
from pathlib import Path


def create_directory_structure():
    """Create all required directories"""
    directories = [
        'config',
        'src/api',
        'src/scrapers',
        'src/processors',
        'src/exporters',
        'src/utils',
        'scripts',
        'tests',
        'exports/socrata',
        'exports/comptroller',
        'exports/combined',
        'exports/deduplicated',
        'exports/polished',  # v1.4.0: Outlet-enriched data
        'exports/batch',
        'logs',
        '.cache',
        '.cache/progress',  # v1.1.0: Progress checkpoints
        '.cache/comptroller'  # v1.4.0: Comptroller API cache
    ]
    
    print("Creating directory structure...")
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created: {directory}")


def create_init_files():
    """Create __init__.py files for all packages"""
    init_files = [
        'config/__init__.py',
        'src/__init__.py',
        'src/api/__init__.py',
        'src/scrapers/__init__.py',
        'src/processors/__init__.py',
        'src/exporters/__init__.py',
        'src/utils/__init__.py',
        'tests/__init__.py'
    ]
    
    print("\nCreating __init__.py files...")
    for init_file in init_files:
        path = Path(init_file)
        if not path.exists():
            path.write_text('"""Package initialization"""\n')
            print(f"  ✓ Created: {init_file}")
        else:
            print(f"  ⊙ Exists: {init_file}")


def create_gitkeep_files():
    """Create .gitkeep files for empty directories"""
    gitkeep_dirs = [
        'exports',
        'exports/socrata',
        'exports/comptroller',
        'exports/combined',
        'exports/deduplicated',
        'exports/polished',  # v1.4.0
        'exports/batch',
        'logs',
        '.cache',
        '.cache/progress',
        '.cache/comptroller'  # v1.4.0
    ]
    
    print("\nCreating .gitkeep files...")
    for directory in gitkeep_dirs:
        gitkeep = Path(directory) / '.gitkeep'
        if not gitkeep.exists():
            gitkeep.write_text('')
            print(f"  ✓ Created: {gitkeep}")
        else:
            print(f"  ⊙ Exists: {gitkeep}")


def create_env_file():
    """Create .env file from example if it doesn't exist"""
    env_example = Path('config/.env.example')
    env_file = Path('.env')
    
    print("\nSetting up environment file...")
    
    if env_file.exists():
        print(f"  ⊙ .env already exists")
        return
    
    if env_example.exists():
        # Copy example to .env
        content = env_example.read_text()
        env_file.write_text(content)
        print(f"  ✓ Created .env from example")
        print(f"  ⚠  Remember to add your API keys!")
    else:
        print(f"  ⚠  .env.example not found, skipping")


def create_helpers_file():
    """Create helpers.py utility file"""
    helpers_path = Path('src/utils/helpers.py')
    
    print("\nCreating helper utilities...")
    
    if helpers_path.exists():
        print(f"  ⊙ helpers.py already exists")
        return
    
    helpers_content = '''"""
Helper utility functions
"""
from typing import Any, Dict, List
import json


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """
    Flatten nested dictionary
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(dictionary: Dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary value
    
    Args:
        dictionary: Dictionary to traverse
        *keys: Keys to traverse
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default


def format_bytes(bytes: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def validate_taxpayer_id(taxpayer_id: str) -> bool:
    """
    Validate taxpayer ID format
    
    Args:
        taxpayer_id: Taxpayer ID to validate
        
    Returns:
        True if valid format
    """
    if not taxpayer_id:
        return False
    
    # Remove any non-numeric characters
    cleaned = ''.join(c for c in str(taxpayer_id) if c.isdigit())
    
    # Check length (typically 9-11 digits)
    return 9 <= len(cleaned) <= 11
'''
    
    helpers_path.write_text(helpers_content)
    print(f"  ✓ Created: src/utils/helpers.py")


def verify_structure():
    """Verify all critical files exist"""
    critical_files = [
        'requirements.txt',
        'requirements-gpu.txt',
        'README.md',
        'QUICK_START.md',
        'setup.py',
        '.gitignore',
        'CHANGELOG.md',
        'CONTRIBUTING.md',
        'LICENSE',
        'Makefile',
        'config/settings.py',
        'src/api/socrata_client.py',
        'src/api/comptroller_client.py',
        'src/api/rate_limiter.py',
        'src/scrapers/gpu_accelerator.py',
        'src/scrapers/socrata_scraper.py',
        'src/scrapers/comptroller_scraper.py',
        'src/processors/data_combiner.py',
        'src/processors/deduplicator.py',
        'src/processors/data_validator.py',
        'src/exporters/file_exporter.py',
        'src/utils/logger.py',
        'src/utils/helpers.py',
        'src/utils/checksum.py',         # v1.1.0
        'src/utils/progress_manager.py', # v1.1.0
        'scripts/socrata_scraper.py',
        'scripts/comptroller_scraper.py',
        'scripts/data_combiner.py',
        'scripts/deduplicator.py',
        'scripts/api_tester.py',
        'scripts/batch_processor.py'
    ]
    
    print("\nVerifying project structure...")
    
    missing = []
    for file in critical_files:
        if not Path(file).exists():
            missing.append(file)
            print(f"  ✗ Missing: {file}")
        else:
            print(f"  ✓ Found: {file}")
    
    if missing:
        print(f"\n⚠  Warning: {len(missing)} files are missing!")
        print("   These files need to be created manually or copied from artifacts.")
    else:
        print("\n✓ All critical files present!")


def main():
    """Main setup function"""
    print("="*70)
    print("TEXAS DATA SCRAPER - PROJECT SETUP (v1.2.0)")
    print("="*70)
    print()
    
    # Create structure
    create_directory_structure()
    create_init_files()
    create_gitkeep_files()
    create_env_file()
    create_helpers_file()
    
    # Verify
    verify_structure()
    
    # Final instructions
    print("\n" + "="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Edit .env file and add your API keys")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run API tests: python scripts/api_tester.py")
    print("4. Start scraping: python scripts/socrata_scraper.py")
    print()
    print("For more info, see README.md or QUICK_START.md")
    print()


if __name__ == "__main__":
    main()