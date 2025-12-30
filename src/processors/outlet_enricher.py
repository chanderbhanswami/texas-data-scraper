"""
Outlet Data Enricher - Extract and merge outlet data from duplicate records
With GPU acceleration support
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path
import json
from src.utils.logger import get_logger
from src.utils.helpers import generate_hash

# Try to import GPU accelerator
try:
    from src.scrapers.gpu_accelerator import get_gpu_accelerator
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logger = get_logger(__name__)

# Outlet fields to extract from duplicate records
OUTLET_FIELDS = [
    'outlet_number',
    'outlet_name',
    'outlet_address',
    'outlet_city',
    'outlet_state',
    'outlet_zip_code',
    'outlet_county_code',
    'outlet_naics_code',
    'outlet_inside_outside_city_limits_indicator',
    'outlet_permit_issue_date',
    'outlet_first_sales_date'
]

# Taxpayer ID fields (different sources use different names)
TAXPAYER_ID_FIELDS = ['taxpayer_id', 'taxpayer_number', 'TAXPAYER_NUMBER']


class OutletEnricher:
    """Extract outlet data from duplicates and enrich deduplicated records"""
    
    def __init__(self):
        """Initialize the outlet enricher"""
        self.gpu = get_gpu_accelerator() if GPU_AVAILABLE else None
        self.stats = {
            'total_socrata_records': 0,
            'unique_taxpayers': 0,
            'taxpayers_with_outlets': 0,
            'total_outlets_found': 0,
            'records_enriched': 0,
            'records_unchanged': 0
        }
        logger.info("Initialized OutletEnricher")
    
    def _get_taxpayer_id(self, record: Dict) -> Optional[str]:
        """Extract taxpayer ID from record (handles different field names)"""
        for field in TAXPAYER_ID_FIELDS:
            if field in record:
                value = record[field]
                if value:
                    return str(value).strip()
        return None
    
    def _has_outlet_fields(self, record: Dict) -> bool:
        """Check if record has any outlet fields"""
        for field in OUTLET_FIELDS:
            if field in record and record[field]:
                return True
        return False
    
    def _extract_outlet_data(self, record: Dict) -> Dict:
        """Extract outlet fields from a record"""
        outlet = {}
        for field in OUTLET_FIELDS:
            if field in record and record[field]:
                outlet[field] = record[field]
        return outlet
    
    def find_outlet_data(self, socrata_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Find all outlet data from Socrata records by taxpayer ID
        
        Args:
            socrata_data: List of Socrata records
            
        Returns:
            Dictionary mapping taxpayer_id to list of outlet records
        """
        logger.info(f"Extracting outlet data from {len(socrata_data)} Socrata records")
        self.stats['total_socrata_records'] = len(socrata_data)
        
        # Group records by taxpayer ID
        taxpayer_records = defaultdict(list)
        for record in socrata_data:
            tid = self._get_taxpayer_id(record)
            if tid:
                taxpayer_records[tid].append(record)
        
        self.stats['unique_taxpayers'] = len(taxpayer_records)
        
        # Extract outlet data from each group
        outlet_data = {}
        for tid, records in taxpayer_records.items():
            outlets = []
            for record in records:
                if self._has_outlet_fields(record):
                    outlet = self._extract_outlet_data(record)
                    outlet['taxpayer_id'] = tid
                    outlets.append(outlet)
            
            if outlets:
                outlet_data[tid] = outlets
        
        self.stats['taxpayers_with_outlets'] = len(outlet_data)
        self.stats['total_outlets_found'] = sum(len(v) for v in outlet_data.values())
        
        logger.info(f"Found {self.stats['total_outlets_found']} outlets for {self.stats['taxpayers_with_outlets']} taxpayers")
        
        return outlet_data
    
    def enrich_records(self, 
                       dedup_data: List[Dict], 
                       outlet_data: Dict[str, List[Dict]],
                       overwrite: bool = False) -> List[Dict]:
        """
        Enrich deduplicated records with outlet data
        
        Args:
            dedup_data: Deduplicated records to enrich
            outlet_data: Outlet data by taxpayer ID
            overwrite: If True, overwrite existing outlet data
            
        Returns:
            Enriched records
        """
        logger.info(f"Enriching {len(dedup_data)} records with outlet data")
        
        enriched = []
        enriched_count = 0
        unchanged_count = 0
        
        for record in dedup_data:
            tid = self._get_taxpayer_id(record)
            new_record = record.copy()
            
            if tid and tid in outlet_data:
                # Check if record already has outlet data
                has_existing = self._has_outlet_fields(record)
                
                if not has_existing or overwrite:
                    # Get the outlets for this taxpayer
                    taxpayer_outlets = outlet_data[tid]
                    
                    # Store all outlets as a list
                    new_record['outlets'] = taxpayer_outlets
                    
                    # Also copy first outlet's fields to top-level for backwards compatibility
                    if taxpayer_outlets:
                        first_outlet = taxpayer_outlets[0]
                        for field in OUTLET_FIELDS:
                            if field in first_outlet:
                                new_record[field] = first_outlet[field]
                    
                    enriched_count += 1
                else:
                    unchanged_count += 1
            else:
                unchanged_count += 1
            
            enriched.append(new_record)
        
        self.stats['records_enriched'] = enriched_count
        self.stats['records_unchanged'] = unchanged_count
        
        logger.info(f"Enriched {enriched_count} records, {unchanged_count} unchanged")
        
        return enriched
    
    def process(self, 
                socrata_data: List[Dict], 
                dedup_data: List[Dict],
                overwrite: bool = False) -> Tuple[List[Dict], Dict]:
        """
        Full processing pipeline: extract outlets and enrich records
        
        Args:
            socrata_data: Original Socrata data (may have duplicates)
            dedup_data: Deduplicated data to enrich
            overwrite: If True, overwrite existing outlet data
            
        Returns:
            Tuple of (enriched_data, stats)
        """
        # Step 1: Extract outlet data from Socrata
        outlet_data = self.find_outlet_data(socrata_data)
        
        # Step 2: Enrich deduplicated records
        enriched = self.enrich_records(dedup_data, outlet_data, overwrite)
        
        return enriched, self.stats
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self.stats.copy()


class AdvancedOutletEnricher(OutletEnricher):
    """Advanced outlet enricher with GPU acceleration and enhanced merging"""
    
    def __init__(self):
        super().__init__()
        logger.info("Initialized AdvancedOutletEnricher")
    
    def merge_outlet_details(self, outlets: List[Dict]) -> Dict:
        """
        Merge multiple outlet records into a single comprehensive record
        
        Args:
            outlets: List of outlet records
            
        Returns:
            Merged outlet with most complete data
        """
        if not outlets:
            return {}
        
        if len(outlets) == 1:
            return outlets[0]
        
        # Score each outlet by completeness
        def score(outlet):
            return sum(1 for f in OUTLET_FIELDS if f in outlet and outlet[f])
        
        # Sort by completeness (most complete first)
        sorted_outlets = sorted(outlets, key=score, reverse=True)
        
        # Start with most complete and fill gaps
        merged = sorted_outlets[0].copy()
        for outlet in sorted_outlets[1:]:
            for field in OUTLET_FIELDS:
                if field not in merged or not merged[field]:
                    if field in outlet and outlet[field]:
                        merged[field] = outlet[field]
        
        return merged
    
    def enrich_with_merged_outlets(self,
                                   dedup_data: List[Dict],
                                   outlet_data: Dict[str, List[Dict]],
                                   store_all: bool = True) -> List[Dict]:
        """
        Enrich records with merged outlet data
        
        Args:
            dedup_data: Data to enrich
            outlet_data: Outlet data by taxpayer ID
            store_all: If True, also store all outlets as a list
            
        Returns:
            Enriched records
        """
        enriched = []
        
        for record in dedup_data:
            tid = self._get_taxpayer_id(record)
            new_record = record.copy()
            
            if tid and tid in outlet_data:
                outlets = outlet_data[tid]
                
                # Merge outlets into single most-complete record
                merged_outlet = self.merge_outlet_details(outlets)
                
                # Copy merged fields to top-level
                for field in OUTLET_FIELDS:
                    if field in merged_outlet:
                        new_record[field] = merged_outlet[field]
                
                # Optionally store all outlets
                if store_all and len(outlets) > 1:
                    new_record['all_outlets'] = outlets
                    new_record['outlet_count'] = len(outlets)
            
            enriched.append(new_record)
        
        return enriched
    
    def enrich_with_gpu(self, 
                        dedup_data: List[Dict],
                        outlet_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        GPU-accelerated enrichment for large datasets
        
        Args:
            dedup_data: Data to enrich
            outlet_data: Outlet data by taxpayer ID
            
        Returns:
            Enriched records
        """
        if not self.gpu or not self.gpu.gpu_available:
            logger.warning("GPU not available, falling back to CPU")
            return self.enrich_with_merged_outlets(dedup_data, outlet_data)
        
        try:
            import cupy as cp
            import numpy as np
            
            logger.info("Using GPU-accelerated outlet enrichment")
            
            # Extract taxpayer IDs for matching
            dedup_tids = [self._get_taxpayer_id(r) or '' for r in dedup_data]
            outlet_tids = set(outlet_data.keys())
            
            # Create match mask using GPU
            match_mask = cp.array([tid in outlet_tids for tid in dedup_tids])
            match_indices = cp.where(match_mask)[0].get()
            
            logger.info(f"GPU found {len(match_indices)} records to enrich")
            
            # Enrich matched records
            enriched = dedup_data.copy()
            for idx in match_indices:
                tid = dedup_tids[idx]
                if tid in outlet_data:
                    outlets = outlet_data[tid]
                    merged = self.merge_outlet_details(outlets)
                    
                    new_record = enriched[idx].copy()
                    for field in OUTLET_FIELDS:
                        if field in merged:
                            new_record[field] = merged[field]
                    
                    if len(outlets) > 1:
                        new_record['all_outlets'] = outlets
                        new_record['outlet_count'] = len(outlets)
                    
                    enriched[idx] = new_record
            
            return enriched
            
        except Exception as e:
            logger.error(f"GPU enrichment failed: {e}, falling back to CPU")
            return self.enrich_with_merged_outlets(dedup_data, outlet_data)
