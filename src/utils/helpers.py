"""
Helper utility functions for Texas Data Scraper
"""
from typing import Any, Dict, List, Optional, Union
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path


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
        elif isinstance(v, list):
            # Convert list to string representation
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: Dict, sep: str = '_') -> Dict:
    """
    Unflatten a flattened dictionary
    
    Args:
        d: Flattened dictionary
        sep: Separator used in keys
        
    Returns:
        Nested dictionary
    """
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


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


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_bytes(bytes_value: Union[int, float]) -> str:
    """
    Format bytes to human readable string
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_number(num: Union[int, float], decimals: int = 2) -> str:
    """
    Format number with thousands separators
    
    Args:
        num: Number to format
        decimals: Decimal places
        
    Returns:
        Formatted string
    """
    if isinstance(num, int):
        return f"{num:,}"
    else:
        return f"{num:,.{decimals}f}"


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
    
    # Check length (typically 9-11 digits for Texas)
    return 9 <= len(cleaned) <= 11


def clean_taxpayer_id(taxpayer_id: str) -> Optional[str]:
    """
    Clean and validate taxpayer ID
    
    Args:
        taxpayer_id: Raw taxpayer ID
        
    Returns:
        Cleaned ID or None if invalid
    """
    if not taxpayer_id:
        return None
    
    # Extract only digits
    cleaned = ''.join(c for c in str(taxpayer_id) if c.isdigit())
    
    # Validate length
    if 9 <= len(cleaned) <= 11:
        return cleaned
    
    return None


def validate_zip_code(zip_code: str) -> bool:
    """Validate ZIP code format"""
    if not zip_code:
        return False
    
    # Clean ZIP code
    cleaned = str(zip_code).strip().replace('-', '')
    
    # Check format (5 or 9 digits)
    return len(cleaned) in [5, 9] and cleaned.isdigit()


def format_zip_code(zip_code: str) -> Optional[str]:
    """
    Format ZIP code to standard format
    
    Args:
        zip_code: Raw ZIP code
        
    Returns:
        Formatted ZIP (5 digits or 5+4 format)
    """
    if not zip_code:
        return None
    
    # Extract digits
    digits = ''.join(c for c in str(zip_code) if c.isdigit())
    
    if len(digits) == 5:
        return digits
    elif len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) > 5:
        return digits[:5]
    
    return None


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove all non-digit characters
    digits = ''.join(c for c in str(phone) if c.isdigit())
    
    # US phone numbers are 10 digits
    return len(digits) == 10


def format_phone(phone: str) -> Optional[str]:
    """
    Format phone number
    
    Args:
        phone: Raw phone number
        
    Returns:
        Formatted phone (XXX) XXX-XXXX
    """
    if not phone:
        return None
    
    # Extract digits
    digits = ''.join(c for c in str(phone) if c.isdigit())
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    
    return digits if digits else None


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    # Simple email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))


def generate_hash(data: Union[str, Dict, List]) -> str:
    """
    Generate MD5 hash of data
    
    Args:
        data: Data to hash
        
    Returns:
        MD5 hash string
    """
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True)
    
    return hashlib.md5(str(data).encode()).hexdigest()


def generate_file_hash(filepath: Path) -> str:
    """Generate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    return hash_md5.hexdigest()


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """Convert Unix timestamp to datetime"""
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp"""
    return int(dt.timestamp())


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse string to datetime"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string
    
    Args:
        dt: Datetime object
        
    Returns:
        String like "2 hours ago"
    """
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def estimate_time_remaining(completed: int, total: int, elapsed_seconds: float) -> str:
    """
    Estimate time remaining for process
    
    Args:
        completed: Completed items
        total: Total items
        elapsed_seconds: Elapsed time in seconds
        
    Returns:
        Formatted time remaining string
    """
    if completed == 0:
        return "calculating..."
    
    rate = completed / elapsed_seconds
    remaining = total - completed
    remaining_seconds = remaining / rate
    
    if remaining_seconds < 60:
        return f"{int(remaining_seconds)}s"
    elif remaining_seconds < 3600:
        minutes = int(remaining_seconds / 60)
        return f"{minutes}m"
    else:
        hours = int(remaining_seconds / 3600)
        minutes = int((remaining_seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def merge_dicts(*dicts: Dict, deep: bool = False) -> Dict:
    """
    Merge multiple dictionaries
    
    Args:
        *dicts: Dictionaries to merge
        deep: Deep merge nested dicts
        
    Returns:
        Merged dictionary
    """
    result = {}
    
    for d in dicts:
        if deep:
            for key, value in d.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value, deep=True)
                else:
                    result[key] = value
        else:
            result.update(d)
    
    return result


def remove_empty_values(d: Dict) -> Dict:
    """Remove None and empty string values from dict"""
    return {
        k: v for k, v in d.items()
        if v is not None and v != ''
    }


def extract_numbers(text: str) -> List[int]:
    """Extract all numbers from text"""
    return [int(n) for n in re.findall(r'\d+', text)]


def extract_emails(text: str) -> List[str]:
    """Extract all email addresses from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from text"""
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(pattern, text)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem use
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized


def ensure_extension(filename: str, extension: str) -> str:
    """
    Ensure filename has correct extension
    
    Args:
        filename: Original filename
        extension: Desired extension (with or without dot)
        
    Returns:
        Filename with correct extension
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    if not filename.endswith(extension):
        return filename + extension
    
    return filename


def get_file_size(filepath: Path) -> int:
    """Get file size in bytes"""
    return filepath.stat().st_size if filepath.exists() else 0


def create_directory(path: Path) -> Path:
    """Create directory if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_files(directory: Path, pattern: str = "*", recursive: bool = False) -> List[Path]:
    """
    List files in directory
    
    Args:
        directory: Directory path
        pattern: Glob pattern
        recursive: Search recursively
        
    Returns:
        List of file paths
    """
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def calculate_percentage(part: Union[int, float], total: Union[int, float], 
                         decimals: int = 2) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    
    return round((part / total) * 100, decimals)


def clamp(value: Union[int, float], min_value: Union[int, float], 
          max_value: Union[int, float]) -> Union[int, float]:
    """Clamp value between min and max"""
    return max(min_value, min(value, max_value))


def is_valid_path(path: str) -> bool:
    """Check if path string is valid"""
    try:
        Path(path)
        return True
    except (ValueError, OSError):
        return False


def retry_on_exception(func: callable, max_retries: int = 3, 
                       delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Retry function on exception
    
    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        delay: Delay between retries
        exceptions: Exceptions to catch
        
    Returns:
        Function result
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (attempt + 1))
    
    return None