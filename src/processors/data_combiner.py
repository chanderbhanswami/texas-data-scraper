"""
Data Combiner - Merge Socrata and Comptroller data
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from src.utils.logger import get_logger
from config.settings import data_config

logger = get_logger(__name__)


class DataCombiner:
    """Combine data from multiple sources"""
    
    def __init__(self, field_priority: str = 'comptroller'):
        """
        Initialize data combiner
        
        Args:
            field_priority: Which source to prioritize for conflicts ('comptroller' or 'socrata')
        """
        self.field_priority = field_priority or data_config.FIELD_PRIORITY
        
    def combine_by_taxpayer_id(self, 
                                socrata_data: List[Dict],
                                comptroller_data: List[Dict]) -> List[Dict]:
        """
        Combine Socrata and Comptroller data by taxpayer ID
        
        Args:
            socrata_data: Data from Socrata API
            comptroller_data: Data from Comptroller API
            
        Returns:
            Combined data with merged fields
        """
        logger.info("Starting data combination...")
        logger.info(f"Socrata records: {len(socrata_data)}")
        logger.info(f"Comptroller records: {len(comptroller_data)}")
        
        # Index Socrata data by taxpayer ID
        socrata_index = self._index_by_taxpayer_id(socrata_data, 'socrata')
        
        # Index Comptroller data by taxpayer ID
        comptroller_index = self._index_by_taxpayer_id(comptroller_data, 'comptroller')
        
        # Get all unique taxpayer IDs
        all_taxpayer_ids = set(socrata_index.keys()) | set(comptroller_index.keys())
        
        logger.info(f"Unique taxpayer IDs: {len(all_taxpayer_ids)}")
        
        # Combine data
        combined_data = []
        
        for taxpayer_id in all_taxpayer_ids:
            socrata_record = socrata_index.get(taxpayer_id, {})
            comptroller_record = comptroller_index.get(taxpayer_id, {})
            
            # Merge records
            merged_record = self._merge_records(
                socrata_record,
                comptroller_record,
                taxpayer_id
            )
            
            combined_data.append(merged_record)
        
        logger.info(f"Combined {len(combined_data)} records")
        
        return combined_data
    
    def _index_by_taxpayer_id(self, data: List[Dict], source: str) -> Dict[str, Dict]:
        """
        Index data by taxpayer ID
        
        Args:
            data: List of records
            source: Data source name
            
        Returns:
            Dictionary mapping taxpayer ID to record
        """
        index = {}
        
        # Possible taxpayer ID field names
        id_fields = [
            'taxpayer_id',
            'taxpayer_number',
            'taxpayerid',
            'taxpayernumber',
            'tax_payer_number',
            'taxpayer_no',
            'id'
        ]
        
        for record in data:
            taxpayer_id = None
            
            # Find taxpayer ID in record
            for field in id_fields:
                if field in record and record[field]:
                    taxpayer_id = str(record[field]).strip()
                    break
            
            if taxpayer_id:
                # Add source prefix to all fields
                prefixed_record = {f"{source}_{k}": v for k, v in record.items()}
                prefixed_record['taxpayer_id'] = taxpayer_id
                prefixed_record['data_source'] = source
                
                index[taxpayer_id] = prefixed_record
            else:
                logger.warning(f"No taxpayer ID found in {source} record")
        
        return index
    
    def _merge_records(self, 
                       socrata_record: Dict,
                       comptroller_record: Dict,
                       taxpayer_id: str) -> Dict:
        """
        Merge two records with field priority
        
        Args:
            socrata_record: Socrata data
            comptroller_record: Comptroller data
            taxpayer_id: Taxpayer ID
            
        Returns:
            Merged record
        """
        merged = {
            'taxpayer_id': taxpayer_id,
            'has_socrata_data': bool(socrata_record),
            'has_comptroller_data': bool(comptroller_record)
        }
        
        # Determine merge order based on priority
        if self.field_priority == 'comptroller':
            # Add Socrata fields first, then Comptroller (overwrites conflicts)
            merged.update(socrata_record)
            merged.update(comptroller_record)
        else:
            # Add Comptroller fields first, then Socrata (overwrites conflicts)
            merged.update(comptroller_record)
            merged.update(socrata_record)
        
        # Always preserve taxpayer_id and metadata
        merged['taxpayer_id'] = taxpayer_id
        merged['has_socrata_data'] = bool(socrata_record)
        merged['has_comptroller_data'] = bool(comptroller_record)
        
        return merged
    
    def combine_with_field_mapping(self,
                                    socrata_data: List[Dict],
                                    comptroller_data: List[Dict],
                                    field_map: Dict[str, str]) -> List[Dict]:
        """
        Combine data with custom field mapping
        
        Args:
            socrata_data: Socrata data
            comptroller_data: Comptroller data
            field_map: Mapping of field names (socrata_field -> comptroller_field)
            
        Returns:
            Combined data
        """
        # Apply field mapping to Socrata data
        mapped_socrata = []
        for record in socrata_data:
            mapped = {}
            for old_field, new_field in field_map.items():
                if old_field in record:
                    mapped[new_field] = record[old_field]
                else:
                    mapped[old_field] = record.get(old_field)
            
            # Add unmapped fields
            for field, value in record.items():
                if field not in field_map:
                    mapped[field] = value
            
            mapped_socrata.append(mapped)
        
        # Combine with standard method
        return self.combine_by_taxpayer_id(mapped_socrata, comptroller_data)
    
    def get_combination_stats(self, combined_data: List[Dict]) -> Dict[str, Any]:
        """
        Get statistics about combined data
        
        Args:
            combined_data: Combined data
            
        Returns:
            Statistics dictionary
        """
        total = len(combined_data)
        with_socrata = sum(1 for r in combined_data if r.get('has_socrata_data'))
        with_comptroller = sum(1 for r in combined_data if r.get('has_comptroller_data'))
        with_both = sum(1 for r in combined_data if r.get('has_socrata_data') and r.get('has_comptroller_data'))
        only_socrata = sum(1 for r in combined_data if r.get('has_socrata_data') and not r.get('has_comptroller_data'))
        only_comptroller = sum(1 for r in combined_data if r.get('has_comptroller_data') and not r.get('has_socrata_data'))
        
        return {
            'total_records': total,
            'with_socrata_data': with_socrata,
            'with_comptroller_data': with_comptroller,
            'with_both_sources': with_both,
            'only_socrata': only_socrata,
            'only_comptroller': only_comptroller,
            'coverage_socrata': (with_socrata / total * 100) if total > 0 else 0,
            'coverage_comptroller': (with_comptroller / total * 100) if total > 0 else 0,
            'coverage_both': (with_both / total * 100) if total > 0 else 0
        }
    
    def enrich_data(self, 
                    base_data: List[Dict],
                    enrichment_data: List[Dict],
                    join_field: str = 'taxpayer_id') -> List[Dict]:
        """
        Enrich base data with additional data
        
        Args:
            base_data: Base dataset
            enrichment_data: Data to enrich with
            join_field: Field to join on
            
        Returns:
            Enriched data
        """
        # Index enrichment data
        enrichment_index = {
            str(record[join_field]): record 
            for record in enrichment_data 
            if join_field in record
        }
        
        enriched = []
        for record in base_data:
            enriched_record = record.copy()
            
            join_value = str(record.get(join_field, ''))
            if join_value in enrichment_index:
                # Add enrichment fields with prefix
                for key, value in enrichment_index[join_value].items():
                    if key != join_field:
                        enriched_record[f'enriched_{key}'] = value
            
            enriched.append(enriched_record)
        
        return enriched


class SmartDataCombiner(DataCombiner):
    """Enhanced data combiner with smart field resolution"""
    
    def _merge_records(self, 
                       socrata_record: Dict,
                       comptroller_record: Dict,
                       taxpayer_id: str) -> Dict:
        """
        Smart merge with field conflict resolution
        """
        merged = super()._merge_records(socrata_record, comptroller_record, taxpayer_id)
        
        # Resolve specific field conflicts intelligently
        merged = self._resolve_name_conflicts(merged, socrata_record, comptroller_record)
        merged = self._resolve_address_conflicts(merged, socrata_record, comptroller_record)
        merged = self._resolve_date_conflicts(merged, socrata_record, comptroller_record)
        
        return merged
    
    def _resolve_name_conflicts(self, merged: Dict, 
                                 socrata: Dict, 
                                 comptroller: Dict) -> Dict:
        """Resolve business name conflicts"""
        name_fields = ['name', 'business_name', 'taxpayer_name', 'legal_name']
        
        names = []
        for record in [socrata, comptroller]:
            for field in name_fields:
                if field in record and record[field]:
                    names.append(record[field])
        
        if names:
            # Use longest name (usually most complete)
            merged['resolved_business_name'] = max(names, key=len)
        
        return merged
    
    def _resolve_address_conflicts(self, merged: Dict,
                                    socrata: Dict,
                                    comptroller: Dict) -> Dict:
        """Resolve address conflicts"""
        # Prefer most recent or most complete address
        address_fields = ['address', 'street_address', 'taxpayer_address']
        
        for record, source in [(comptroller, 'comptroller'), (socrata, 'socrata')]:
            for field in address_fields:
                if field in record and record[field]:
                    merged['resolved_address'] = record[field]
                    merged['resolved_address_source'] = source
                    break
        
        return merged
    
    def _resolve_date_conflicts(self, merged: Dict,
                                socrata: Dict,
                                comptroller: Dict) -> Dict:
        """Resolve date conflicts by using most recent"""
        # Prefer Comptroller dates as they're more current
        date_fields = ['filing_date', 'registration_date', 'effective_date']
        
        for field in date_fields:
            if f'comptroller_{field}' in merged:
                merged[f'resolved_{field}'] = merged[f'comptroller_{field}']
            elif f'socrata_{field}' in merged:
                merged[f'resolved_{field}'] = merged[f'socrata_{field}']
        
        return merged