"""
Data Validation Utilities
Validate and clean scraped data
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Validate and clean data"""
    
    def __init__(self):
        self.validation_rules = {}
        self.errors = []
        self.warnings = []
        
    def validate_taxpayer_id(self, taxpayer_id: str) -> bool:
        """
        Validate taxpayer ID format
        
        Args:
            taxpayer_id: Taxpayer ID to validate
            
        Returns:
            True if valid
        """
        if not taxpayer_id:
            return False
        
        # Remove non-numeric characters
        cleaned = ''.join(c for c in str(taxpayer_id) if c.isdigit())
        
        # Check length (typically 9-11 digits for Texas)
        if not (9 <= len(cleaned) <= 11):
            return False
        
        return True
    
    def validate_zip_code(self, zip_code: str) -> bool:
        """Validate ZIP code format"""
        if not zip_code:
            return False
        
        # Clean ZIP code
        cleaned = str(zip_code).strip().replace('-', '')
        
        # Check format (5 or 9 digits)
        return len(cleaned) in [5, 9] and cleaned.isdigit()
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False
        
        # Remove all non-digit characters
        digits = ''.join(c for c in str(phone) if c.isdigit())
        
        # US phone numbers are 10 digits
        return len(digits) == 10
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        # Simple email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(email)))
    
    def validate_date(self, date_str: str, format: str = "%Y-%m-%d") -> bool:
        """Validate date format"""
        if not date_str:
            return False
        
        try:
            datetime.strptime(str(date_str), format)
            return True
        except ValueError:
            return False
    
    def validate_record(self, record: Dict, required_fields: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate a single record
        
        Args:
            record: Record to validate
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in record or not record[field]:
                    errors.append(f"Missing required field: {field}")
        
        # Validate taxpayer ID if present
        if 'taxpayer_id' in record:
            if not self.validate_taxpayer_id(record['taxpayer_id']):
                errors.append("Invalid taxpayer ID format")
        
        # Validate ZIP code if present
        if 'zip' in record or 'taxpayer_zip' in record:
            zip_field = 'zip' if 'zip' in record else 'taxpayer_zip'
            if record[zip_field] and not self.validate_zip_code(record[zip_field]):
                errors.append(f"Invalid ZIP code: {record[zip_field]}")
        
        # Validate email if present
        if 'email' in record:
            if record['email'] and not self.validate_email(record['email']):
                errors.append(f"Invalid email: {record['email']}")
        
        return len(errors) == 0, errors
    
    def validate_dataset(self, data: List[Dict], 
                         required_fields: List[str] = None) -> Dict[str, Any]:
        """
        Validate entire dataset
        
        Args:
            data: List of records
            required_fields: Required fields
            
        Returns:
            Validation report
        """
        total = len(data)
        valid = 0
        invalid = 0
        record_errors = []
        
        logger.info(f"Validating {total} records...")
        
        for i, record in enumerate(data):
            is_valid, errors = self.validate_record(record, required_fields)
            
            if is_valid:
                valid += 1
            else:
                invalid += 1
                record_errors.append({
                    'record_index': i,
                    'errors': errors,
                    'record': record
                })
        
        report = {
            'total_records': total,
            'valid_records': valid,
            'invalid_records': invalid,
            'validation_rate': (valid / total * 100) if total > 0 else 0,
            'errors': record_errors[:100]  # Limit to first 100 errors
        }
        
        logger.info(f"Validation complete: {valid}/{total} valid ({report['validation_rate']:.1f}%)")
        
        return report
    
    def clean_record(self, record: Dict) -> Dict:
        """
        Clean a single record
        
        Args:
            record: Record to clean
            
        Returns:
            Cleaned record
        """
        cleaned = record.copy()
        
        # Clean taxpayer ID
        if 'taxpayer_id' in cleaned and cleaned['taxpayer_id']:
            cleaned['taxpayer_id'] = ''.join(
                c for c in str(cleaned['taxpayer_id']) if c.isdigit()
            )
        
        # Clean ZIP code
        for zip_field in ['zip', 'taxpayer_zip', 'zip_code']:
            if zip_field in cleaned and cleaned[zip_field]:
                # Extract first 5 digits
                digits = ''.join(c for c in str(cleaned[zip_field]) if c.isdigit())
                cleaned[zip_field] = digits[:5] if len(digits) >= 5 else digits
        
        # Clean phone numbers
        for phone_field in ['phone', 'telephone', 'phone_number']:
            if phone_field in cleaned and cleaned[phone_field]:
                digits = ''.join(c for c in str(cleaned[phone_field]) if c.isdigit())
                if len(digits) == 10:
                    # Format as (XXX) XXX-XXXX
                    cleaned[phone_field] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                else:
                    cleaned[phone_field] = digits
        
        # Trim whitespace from all string fields
        for key, value in cleaned.items():
            if isinstance(value, str):
                cleaned[key] = value.strip()
        
        # Remove empty string values
        cleaned = {k: v for k, v in cleaned.items() if v != ''}
        
        return cleaned
    
    def clean_dataset(self, data: List[Dict]) -> List[Dict]:
        """
        Clean entire dataset
        
        Args:
            data: List of records
            
        Returns:
            Cleaned records
        """
        logger.info(f"Cleaning {len(data)} records...")
        
        cleaned_data = []
        for record in data:
            cleaned = self.clean_record(record)
            cleaned_data.append(cleaned)
        
        logger.info("Cleaning complete")
        
        return cleaned_data
    
    def standardize_field_names(self, record: Dict, 
                                 field_mapping: Dict[str, str] = None) -> Dict:
        """
        Standardize field names
        
        Args:
            record: Record to standardize
            field_mapping: Custom field name mappings
            
        Returns:
            Record with standardized field names
        """
        # Default mappings
        default_mapping = {
            'taxpayerid': 'taxpayer_id',
            'taxpayernumber': 'taxpayer_id',
            'taxpayer_number': 'taxpayer_id',
            'businessname': 'business_name',
            'taxpayer_name': 'business_name',
            'zipcode': 'zip',
            'zip_code': 'zip',
            'taxpayer_zip': 'zip',
            'phonenumber': 'phone',
            'phone_number': 'phone'
        }
        
        # Merge with custom mapping
        if field_mapping:
            default_mapping.update(field_mapping)
        
        standardized = {}
        
        for key, value in record.items():
            # Convert to lowercase for matching
            key_lower = key.lower().replace(' ', '_')
            
            # Apply mapping
            new_key = default_mapping.get(key_lower, key)
            standardized[new_key] = value
        
        return standardized
    
    def standardize_dataset(self, data: List[Dict],
                            field_mapping: Dict[str, str] = None) -> List[Dict]:
        """Standardize field names across dataset"""
        logger.info(f"Standardizing field names for {len(data)} records...")
        
        standardized = []
        for record in data:
            std_record = self.standardize_field_names(record, field_mapping)
            standardized.append(std_record)
        
        logger.info("Standardization complete")
        
        return standardized
    
    def detect_duplicates(self, data: List[Dict], 
                         key_field: str = 'taxpayer_id') -> List[Dict]:
        """
        Detect duplicate records
        
        Args:
            data: Dataset
            key_field: Field to check for duplicates
            
        Returns:
            List of duplicate records
        """
        seen = {}
        duplicates = []
        
        for record in data:
            if key_field in record:
                key = record[key_field]
                if key in seen:
                    duplicates.append(record)
                else:
                    seen[key] = record
        
        logger.info(f"Found {len(duplicates)} duplicate records")
        
        return duplicates
    
    def get_data_quality_report(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Generate comprehensive data quality report
        
        Args:
            data: Dataset
            
        Returns:
            Quality report
        """
        total = len(data)
        
        # Field completeness
        field_counts = {}
        for record in data:
            for field in record:
                if field not in field_counts:
                    field_counts[field] = 0
                if record[field]:
                    field_counts[field] += 1
        
        field_completeness = {
            field: (count / total * 100) 
            for field, count in field_counts.items()
        }
        
        # Duplicates
        duplicates = self.detect_duplicates(data)
        
        # Validation
        validation_report = self.validate_dataset(data)
        
        report = {
            'total_records': total,
            'field_completeness': field_completeness,
            'duplicate_count': len(duplicates),
            'duplicate_rate': (len(duplicates) / total * 100) if total > 0 else 0,
            'validation_results': validation_report
        }
        
        return report