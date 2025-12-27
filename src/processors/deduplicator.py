"""
Data Deduplicator - Remove duplicate records
With GPU acceleration support
"""
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import hashlib
from src.utils.logger import get_logger
from src.utils.helpers import generate_hash

# Try to import GPU accelerator
try:
    from src.scrapers.gpu_accelerator import get_gpu_accelerator
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logger = get_logger(__name__)


class Deduplicator:
    """Remove duplicate records from datasets"""
    
    def __init__(self, strategy: str = 'taxpayer_id'):
        """
        Initialize deduplicator
        
        Args:
            strategy: Deduplication strategy ('taxpayer_id', 'exact', 'fuzzy')
        """
        self.strategy = strategy
        
    def deduplicate(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Remove duplicates from data
        
        Args:
            data: List of records
            
        Returns:
            Tuple of (deduplicated_data, duplicates)
        """
        logger.info(f"Starting deduplication with strategy: {self.strategy}")
        logger.info(f"Input records: {len(data)}")
        
        if self.strategy == 'taxpayer_id':
            return self._deduplicate_by_taxpayer_id(data)
        elif self.strategy == 'exact':
            return self._deduplicate_exact(data)
        elif self.strategy == 'fuzzy':
            return self._deduplicate_fuzzy(data)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, using taxpayer_id")
            return self._deduplicate_by_taxpayer_id(data)
    
    def _deduplicate_by_taxpayer_id(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Deduplicate by taxpayer ID (keep first occurrence)
        
        Args:
            data: List of records
            
        Returns:
            Tuple of (unique_records, duplicates)
        """
        seen_ids = set()
        unique_records = []
        duplicates = []
        
        # Possible taxpayer ID field names
        id_fields = [
            'taxpayer_id',
            'taxpayer_number',
            'taxpayerid',
            'taxpayernumber',
            'tax_payer_number'
        ]
        
        for record in data:
            taxpayer_id = None
            
            # Find taxpayer ID
            for field in id_fields:
                if field in record and record[field]:
                    taxpayer_id = str(record[field]).strip()
                    break
            
            if not taxpayer_id:
                # No ID found, keep record
                unique_records.append(record)
                continue
            
            if taxpayer_id in seen_ids:
                duplicates.append(record)
            else:
                seen_ids.add(taxpayer_id)
                unique_records.append(record)
        
        logger.info(f"Unique records: {len(unique_records)}")
        logger.info(f"Duplicates removed: {len(duplicates)}")
        
        return unique_records, duplicates
    
    def _deduplicate_exact(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Deduplicate by exact record match
        
        Args:
            data: List of records
            
        Returns:
            Tuple of (unique_records, duplicates)
        """
        seen_hashes = set()
        unique_records = []
        duplicates = []
        
        for record in data:
            # Create hash of entire record
            record_hash = self._hash_record(record)
            
            if record_hash in seen_hashes:
                duplicates.append(record)
            else:
                seen_hashes.add(record_hash)
                unique_records.append(record)
        
        logger.info(f"Unique records: {len(unique_records)}")
        logger.info(f"Duplicates removed: {len(duplicates)}")
        
        return unique_records, duplicates
    
    def _deduplicate_fuzzy(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Deduplicate with fuzzy matching on key fields
        
        Args:
            data: List of records
            
        Returns:
            Tuple of (unique_records, duplicates)
        """
        # Key fields for fuzzy matching
        key_fields = ['taxpayer_id', 'name', 'business_name', 'taxpayer_name']
        
        seen_keys = {}
        unique_records = []
        duplicates = []
        
        for record in data:
            # Extract key values
            key_values = []
            for field in key_fields:
                if field in record and record[field]:
                    value = str(record[field]).strip().lower()
                    key_values.append(value)
            
            if not key_values:
                unique_records.append(record)
                continue
            
            # Create fuzzy key
            fuzzy_key = '|'.join(sorted(key_values))
            
            if fuzzy_key in seen_keys:
                duplicates.append(record)
            else:
                seen_keys[fuzzy_key] = record
                unique_records.append(record)
        
        logger.info(f"Unique records: {len(unique_records)}")
        logger.info(f"Duplicates removed: {len(duplicates)}")
        
        return unique_records, duplicates
    
    def _hash_record(self, record: Dict) -> str:
        """Create hash of record for exact matching"""
        # Sort keys for consistent hashing
        sorted_items = sorted(record.items())
        record_str = str(sorted_items)
        return hashlib.md5(record_str.encode()).hexdigest()
    
    def get_duplicate_groups(self, data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group duplicate records together
        
        Args:
            data: List of records
            
        Returns:
            Dictionary mapping taxpayer_id to list of duplicate records
        """
        groups = defaultdict(list)
        
        id_fields = [
            'taxpayer_id',
            'taxpayer_number',
            'taxpayerid',
            'taxpayernumber'
        ]
        
        for record in data:
            taxpayer_id = None
            
            for field in id_fields:
                if field in record and record[field]:
                    taxpayer_id = str(record[field]).strip()
                    break
            
            if taxpayer_id:
                groups[taxpayer_id].append(record)
        
        # Keep only groups with duplicates
        duplicate_groups = {
            tid: records 
            for tid, records in groups.items() 
            if len(records) > 1
        }
        
        return duplicate_groups
    
    def merge_duplicates(self, duplicates: List[Dict]) -> Dict:
        """
        Merge duplicate records into a single record
        
        Args:
            duplicates: List of duplicate records
            
        Returns:
            Merged record
        """
        if not duplicates:
            return {}
        
        # Start with first record
        merged = duplicates[0].copy()
        
        # Merge fields from other records (prefer non-empty values)
        for record in duplicates[1:]:
            for key, value in record.items():
                if key not in merged or not merged[key]:
                    merged[key] = value
                elif value and len(str(value)) > len(str(merged[key])):
                    # Prefer longer values (usually more complete)
                    merged[key] = value
        
        # Add metadata
        merged['_merged_from_count'] = len(duplicates)
        
        return merged
    
    def get_deduplication_stats(self, 
                                 original_count: int,
                                 unique_count: int,
                                 duplicate_count: int) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            'original_count': original_count,
            'unique_count': unique_count,
            'duplicate_count': duplicate_count,
            'deduplication_rate': (duplicate_count / original_count * 100) if original_count > 0 else 0,
            'reduction_percentage': ((original_count - unique_count) / original_count * 100) if original_count > 0 else 0
        }


class AdvancedDeduplicator(Deduplicator):
    """Advanced deduplicator with field-specific logic"""
    
    def deduplicate_with_merge(self, data: List[Dict]) -> List[Dict]:
        """
        Deduplicate and merge duplicate records
        
        Args:
            data: List of records
            
        Returns:
            Deduplicated and merged records
        """
        logger.info("Deduplicating with merge strategy")
        
        # Get duplicate groups
        groups = self.get_duplicate_groups(data)
        
        logger.info(f"Found {len(groups)} groups with duplicates")
        
        # Track which records are duplicates
        duplicate_ids = set()
        for tid, records in groups.items():
            for record in records:
                # Use hash as ID
                record_hash = self._hash_record(record)
                duplicate_ids.add(record_hash)
        
        # Separate unique and duplicate records
        unique_records = []
        duplicate_records = defaultdict(list)
        
        for record in data:
            record_hash = self._hash_record(record)
            
            # Get taxpayer ID
            taxpayer_id = None
            for field in ['taxpayer_id', 'taxpayer_number', 'taxpayerid']:
                if field in record and record[field]:
                    taxpayer_id = str(record[field]).strip()
                    break
            
            if taxpayer_id and taxpayer_id in groups:
                duplicate_records[taxpayer_id].append(record)
            else:
                unique_records.append(record)
        
        # Merge duplicate groups
        for taxpayer_id, duplicates in duplicate_records.items():
            merged = self.merge_duplicates(duplicates)
            unique_records.append(merged)
        
        logger.info(f"Final record count after merge: {len(unique_records)}")
        
        return unique_records
    
    def deduplicate_by_confidence(self, data: List[Dict]) -> List[Dict]:
        """
        Deduplicate keeping record with highest completeness/confidence
        
        Args:
            data: List of records
            
        Returns:
            Deduplicated records
        """
        groups = self.get_duplicate_groups(data)
        
        # Keep records with most non-empty fields
        best_records = {}
        
        for taxpayer_id, duplicates in groups.items():
            # Score each record by completeness
            best_record = max(duplicates, key=lambda r: self._completeness_score(r))
            best_records[taxpayer_id] = best_record
        
        # Collect all records
        seen_ids = set(best_records.keys())
        result = list(best_records.values())
        
        # Add non-duplicate records
        for record in data:
            taxpayer_id = None
            for field in ['taxpayer_id', 'taxpayer_number', 'taxpayerid']:
                if field in record and record[field]:
                    taxpayer_id = str(record[field]).strip()
                    break
            
            if taxpayer_id not in seen_ids:
                result.append(record)
        
        return result
    
    def _completeness_score(self, record: Dict) -> int:
        """Calculate completeness score for a record"""
        score = 0
        
        for value in record.values():
            if value:
                score += 1
                # Bonus for longer values
                if isinstance(value, str) and len(value) > 10:
                    score += 1
        
        return score
    
    def deduplicate_with_gpu(self, data: List[Dict], key_field: str = 'taxpayer_id') -> List[Dict]:
        """
        GPU-accelerated deduplication
        
        Args:
            data: List of records
            key_field: Field to deduplicate by
            
        Returns:
            Deduplicated records
        """
        if not GPU_AVAILABLE:
            logger.info("GPU not available, using CPU deduplication")
            unique, _ = self.deduplicate(data)
            return unique
        
        try:
            gpu = get_gpu_accelerator()
            
            if not gpu.use_gpu:
                logger.info("GPU disabled, using CPU deduplication")
                unique, _ = self.deduplicate(data)
                return unique
            
            logger.info("Using GPU-accelerated deduplication")
            
            # GPU deduplication
            unique_data = gpu.deduplicate_gpu(data, key_field=key_field)
            
            logger.info(f"GPU deduplicated: {len(data)} -> {len(unique_data)} records")
            
            return unique_data
            
        except Exception as e:
            logger.error(f"GPU deduplication failed: {e}, falling back to CPU")
            unique, _ = self.deduplicate(data)
            return unique
    
    def hash_based_deduplicate(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Hash-based exact deduplication using helpers.generate_hash
        
        Args:
            data: List of records
            
        Returns:
            Tuple of (unique_records, duplicates)
        """
        logger.info("Using hash-based deduplication")
        
        seen_hashes = {}
        unique_records = []
        duplicates = []
        
        for record in data:
            record_hash = generate_hash(record)  # Use helpers.generate_hash
            
            if record_hash not in seen_hashes:
                seen_hashes[record_hash] = record
                unique_records.append(record)
            else:
                duplicates.append(record)
        
        logger.info(f"Hash dedup: {len(unique_records)} unique, {len(duplicates)} duplicates")
        
        return unique_records, duplicates