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


# =============================================================================
# SMART FIELD DETECTION AND NORMALIZATION (v1.1.0)
# =============================================================================

# Comprehensive list of taxpayer ID field name variations
TAXPAYER_ID_FIELDS = [
    'taxpayer_id',
    'taxpayer_number', 
    'taxpayerid',
    'taxpayernumber',
    'taxpayerId',
    'taxpayerID',
    'TaxpayerID',
    'TaxpayerNumber',
    'TAXPAYER_ID',
    'TAXPAYER_NUMBER',
    'tax_payer_number',
    'tax_payer_id',
    'taxpayer_no',
    'taxpayerno',
    'txpayer_id',
    'txpayer_number',
    'tp_id',
    'tp_number',
    'id',
]

# Semantic field mapping - maps various field names to canonical names
# Format: canonical_name -> [list of variations]
FIELD_SYNONYMS = {
    # Address fields
    'zip_code': [
        'zipcode', 'zip', 'zipnumber', 'zip_number', 'postalcode', 
        'postal_code', 'postcode', 'post_code', 'zip_cd', 'zipcd'
    ],
    'city': [
        'city_name', 'cityname', 'town', 'municipality', 'location_city'
    ],
    'state': [
        'state_code', 'statecode', 'state_name', 'statename', 'st', 'state_cd'
    ],
    'street_address': [
        'address', 'street', 'address1', 'address_1', 'street_address_1',
        'address_line_1', 'addressline1', 'mailing_address', 'physical_address'
    ],
    'address_2': [
        'address2', 'address_line_2', 'addressline2', 'suite', 'unit', 'apt'
    ],
    
    # Business information
    'business_name': [
        'businessname', 'company_name', 'companyname', 'entity_name',
        'entityname', 'legal_name', 'legalname', 'taxpayer_name', 
        'taxpayername', 'name', 'dba', 'doing_business_as'
    ],
    'phone': [
        'phone_number', 'phonenumber', 'telephone', 'tel', 'phone_no',
        'contact_phone', 'business_phone', 'primary_phone'
    ],
    'email': [
        'email_address', 'emailaddress', 'e_mail', 'contact_email',
        'business_email', 'primary_email'
    ],
    
    # Registration fields
    'registration_date': [
        'reg_date', 'regdate', 'date_registered', 'registration_dt',
        'register_date', 'reg_dt', 'filing_date', 'filingdate'
    ],
    'status': [
        'entity_status', 'entitystatus', 'account_status', 'accountstatus',
        'filing_status', 'filingstatus', 'active_status', 'current_status'
    ],
    
    # ID fields
    'taxpayer_id': [
        'taxpayer_number', 'taxpayerid', 'taxpayernumber', 'taxpayerId',
        'taxpayerID', 'TaxpayerID', 'TaxpayerNumber', 'TAXPAYER_ID',
        'TAXPAYER_NUMBER', 'tax_payer_number', 'tax_payer_id', 'taxpayer_no',
        'txpayer_id', 'txpayer_number', 'tp_id', 'tp_number'
    ],
    'file_number': [
        'filenumber', 'file_no', 'fileno', 'filing_number', 'filingnumber'
    ],
}

# Build reverse lookup: variation -> canonical name
_FIELD_NORMALIZATION_MAP = {}
for canonical, variations in FIELD_SYNONYMS.items():
    for variation in variations:
        _FIELD_NORMALIZATION_MAP[variation.lower()] = canonical
        _FIELD_NORMALIZATION_MAP[variation] = canonical


def normalize_field_name(field_name: str) -> str:
    """
    Normalize a field name to its canonical form
    
    Args:
        field_name: Original field name (any case/format)
        
    Returns:
        Canonical field name or original if no mapping exists
        
    Examples:
        normalize_field_name('zipcode') -> 'zip_code'
        normalize_field_name('TaxpayerNumber') -> 'taxpayer_id'
        normalize_field_name('businessName') -> 'business_name'
    """
    if not field_name:
        return field_name
    
    # Check exact match first
    if field_name in _FIELD_NORMALIZATION_MAP:
        return _FIELD_NORMALIZATION_MAP[field_name]
    
    # Check lowercase match
    lower_name = field_name.lower()
    if lower_name in _FIELD_NORMALIZATION_MAP:
        return _FIELD_NORMALIZATION_MAP[lower_name]
    
    # No mapping found - convert camelCase to snake_case at least
    return camel_to_snake(field_name)


def camel_to_snake(name: str) -> str:
    """
    Convert camelCase or PascalCase to snake_case
    
    Args:
        name: CamelCase string
        
    Returns:
        snake_case string
    """
    # Insert underscore before uppercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Handle consecutive uppercase letters
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def find_taxpayer_id_field(record: Dict) -> Optional[str]:
    """
    Find the taxpayer ID field name in a record (case-insensitive)
    
    Args:
        record: Data record dictionary
        
    Returns:
        The actual field name containing taxpayer ID, or None
    """
    if not record:
        return None
    
    # Get all field names in the record (lowercase for comparison)
    record_fields_lower = {k.lower(): k for k in record.keys()}
    
    # Check each possible taxpayer ID field name
    for id_field in TAXPAYER_ID_FIELDS:
        # Check lowercase match
        if id_field.lower() in record_fields_lower:
            actual_field = record_fields_lower[id_field.lower()]
            if record.get(actual_field):  # Make sure it has a value
                return actual_field
    
    return None


def extract_taxpayer_id_from_record(record: Dict) -> Optional[str]:
    """
    Extract and clean taxpayer ID from a record (case-insensitive field matching)
    
    Args:
        record: Data record dictionary
        
    Returns:
        Cleaned taxpayer ID or None
    """
    field_name = find_taxpayer_id_field(record)
    
    if field_name:
        raw_value = record.get(field_name)
        return clean_taxpayer_id(str(raw_value))
    
    return None


def normalize_record_fields(record: Dict, 
                            normalize_keys: bool = True,
                            lowercase_keys: bool = False) -> Dict:
    """
    Normalize all field names in a record to canonical forms
    
    Args:
        record: Original record
        normalize_keys: Apply semantic normalization
        lowercase_keys: Convert all keys to lowercase
        
    Returns:
        Record with normalized field names
    """
    if not record:
        return record
    
    normalized = {}
    
    for key, value in record.items():
        if normalize_keys:
            new_key = normalize_field_name(key)
        elif lowercase_keys:
            new_key = key.lower()
        else:
            new_key = key
        
        # Handle key conflicts - prefer non-empty values
        if new_key in normalized:
            # Keep the existing value if new one is empty
            if not value and normalized[new_key]:
                continue
        
        normalized[new_key] = value
    
    return normalized


def find_matching_fields(record1: Dict, record2: Dict) -> Dict[str, str]:
    """
    Find semantically matching fields between two records
    
    Args:
        record1: First record
        record2: Second record
        
    Returns:
        Dictionary mapping record1 field names to matching record2 field names
    """
    matches = {}
    
    # Normalize both records' field names
    norm1 = {normalize_field_name(k): k for k in record1.keys()}
    norm2 = {normalize_field_name(k): k for k in record2.keys()}
    
    # Find matches
    for canonical, original1 in norm1.items():
        if canonical in norm2:
            matches[original1] = norm2[canonical]
    
    return matches


def get_field_value_by_semantic_name(record: Dict, semantic_name: str) -> Optional[Any]:
    """
    Get field value by semantic name (tries all known variations)
    
    Args:
        record: Data record
        semantic_name: Canonical field name (e.g., 'zip_code')
        
    Returns:
        Field value or None
    """
    if not record or not semantic_name:
        return None
    
    # Build list of names to try
    names_to_try = [semantic_name]
    
    if semantic_name in FIELD_SYNONYMS:
        names_to_try.extend(FIELD_SYNONYMS[semantic_name])
    
    # Also try the semantic name in different cases
    names_to_try.extend([
        semantic_name.upper(),
        semantic_name.title(),
        semantic_name.replace('_', ''),
    ])
    
    # Get lowercase record keys for matching
    record_lower = {k.lower(): (k, v) for k, v in record.items()}
    
    for name in names_to_try:
        # Try exact match first
        if name in record:
            return record[name]
        
        # Try lowercase match
        if name.lower() in record_lower:
            return record_lower[name.lower()][1]
    
    return None


def smart_merge_records(record1: Dict, record2: Dict, 
                        priority: str = 'record2') -> Dict:
    """
    Smart merge two records with semantic field matching
    
    Args:
        record1: First record (typically Socrata)
        record2: Second record (typically Comptroller)
        priority: Which record to prioritize for conflicts ('record1' or 'record2')
        
    Returns:
        Merged record with normalized field names
    """
    # Normalize both records
    norm1 = normalize_record_fields(record1)
    norm2 = normalize_record_fields(record2)
    
    # Merge based on priority
    if priority == 'record2':
        merged = {**norm1, **norm2}
    else:
        merged = {**norm2, **norm1}
    
    # Ensure key fields are preserved
    merged['_source_record1_fields'] = list(record1.keys())
    merged['_source_record2_fields'] = list(record2.keys())
    
    return merged
