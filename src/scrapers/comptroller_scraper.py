"""
Comptroller Scraper Module
Core scraping logic for Texas Comptroller API
With progress persistence for resumable operations
"""
from typing import List, Dict, Optional, Callable
import asyncio
from src.api.comptroller_client import ComptrollerClient, AsyncComptrollerClient
from src.scrapers.gpu_accelerator import get_gpu_accelerator
from src.utils.logger import get_logger
from config.settings import comptroller_config, batch_config

# Import progress manager
try:
    from src.utils.progress_manager import ProgressManager, get_all_saved_progress
    PROGRESS_AVAILABLE = True
except ImportError:
    PROGRESS_AVAILABLE = False

logger = get_logger(__name__)


class ComptrollerScraper:
    """Main scraper class for Comptroller data"""
    
    def __init__(self, use_async: bool = False, use_gpu: bool = None):
        """
        Initialize scraper
        
        Args:
            use_async: Use async client
            use_gpu: Use GPU acceleration
        """
        self.client = AsyncComptrollerClient() if use_async else ComptrollerClient()
        self.use_async = use_async
        
        # GPU accelerator
        self.gpu = get_gpu_accelerator()
        if use_gpu is not None:
            self.gpu.use_gpu = use_gpu and self.gpu.gpu_available
        
        logger.info(f"Initialized ComptrollerScraper (async={use_async}, gpu={self.gpu.use_gpu})")
    
    def scrape_taxpayer_details(self, 
                                 taxpayer_ids: List[str],
                                 batch_size: int = None,
                                 progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Scrape details for multiple taxpayers
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            batch_size: Batch size for processing
            progress_callback: Progress callback function
            
        Returns:
            List of taxpayer information
        """
        batch_size = batch_size or batch_config.BATCH_SIZE
        
        logger.info(f"Scraping details for {len(taxpayer_ids)} taxpayers")
        
        if self.use_async:
            results = asyncio.run(self._async_scrape_details(
                taxpayer_ids,
                batch_size,
                progress_callback
            ))
        else:
            results = self._sync_scrape_details(
                taxpayer_ids,
                batch_size,
                progress_callback
            )
        
        logger.info(f"Scrape complete: {len(results)} taxpayers processed")
        
        return results
    
    def _sync_scrape_details(self,
                              taxpayer_ids: List[str],
                              batch_size: int,
                              progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Synchronous scraping"""
        results = []
        
        for i, taxpayer_id in enumerate(taxpayer_ids):
            try:
                info = self.client.get_complete_taxpayer_info(taxpayer_id)
                results.append(info)
                
                if progress_callback:
                    progress_callback(i + 1, len(taxpayer_ids))
                
            except Exception as e:
                logger.error(f"Error processing {taxpayer_id}: {e}")
                results.append({
                    'taxpayer_id': taxpayer_id,
                    'error': str(e),
                    'details': None,
                    'ftas_records': []
                })
        
        return results
    
    async def _async_scrape_details(self,
                                     taxpayer_ids: List[str],
                                     batch_size: int,
                                     progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Asynchronous scraping with batching"""
        results = await self.client.batch_get_taxpayer_info(
            taxpayer_ids,
            max_concurrent=batch_config.CONCURRENT_REQUESTS
        )
        
        return results
    
    def scrape_by_name(self, 
                       business_names: List[str],
                       max_per_name: int = 10) -> Dict[str, List[Dict]]:
        """
        Scrape by business names
        
        Args:
            business_names: List of business names
            max_per_name: Max results per name
            
        Returns:
            Dictionary mapping name to results
        """
        logger.info(f"Scraping by {len(business_names)} business names")
        
        results = {}
        
        for name in business_names:
            try:
                matches = self.client.get_franchise_tax_list(name=name)
                
                if matches:
                    results[name] = matches[:max_per_name]
                    logger.info(f"Found {len(matches)} matches for '{name}'")
                    
            except Exception as e:
                logger.error(f"Error searching '{name}': {e}")
                results[name] = []
        
        total_matches = sum(len(data) for data in results.values())
        logger.info(f"Name search complete: {total_matches} total matches")
        
        return results
    
    def enrich_socrata_data(self,
                            socrata_records: List[Dict],
                            id_field: str = 'taxpayer_id',
                            progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Enrich Socrata records with Comptroller data
        
        Args:
            socrata_records: Records from Socrata
            id_field: Field containing taxpayer ID
            progress_callback: Progress callback
            
        Returns:
            Enriched records
        """
        logger.info(f"Enriching {len(socrata_records)} Socrata records")
        
        # Extract taxpayer IDs
        taxpayer_ids = []
        for record in socrata_records:
            tid = record.get(id_field)
            if tid:
                taxpayer_ids.append(str(tid).strip())
        
        logger.info(f"Extracted {len(taxpayer_ids)} taxpayer IDs")
        
        # Fetch Comptroller data
        comptroller_data = self.scrape_taxpayer_details(
            taxpayer_ids,
            progress_callback=progress_callback
        )
        
        # Create lookup dictionary
        comptroller_lookup = {
            data['taxpayer_id']: data 
            for data in comptroller_data
        }
        
        # Enrich records
        enriched = []
        for record in socrata_records:
            tid = str(record.get(id_field, '')).strip()
            
            enriched_record = record.copy()
            
            if tid in comptroller_lookup:
                comp_data = comptroller_lookup[tid]
                
                # Add Comptroller details
                if comp_data.get('details'):
                    for key, value in comp_data['details'].items():
                        enriched_record[f'comptroller_{key}'] = value
                
                # Add FTAS info
                enriched_record['comptroller_has_ftas'] = comp_data.get('has_ftas', False)
                enriched_record['comptroller_ftas_count'] = len(comp_data.get('ftas_records', []))
            
            enriched.append(enriched_record)
        
        logger.info("Enrichment complete")
        
        return enriched
    
    def scrape_with_validation(self,
                                taxpayer_ids: List[str],
                                validate_id: bool = True) -> List[Dict]:
        """
        Scrape with ID validation
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            validate_id: Validate ID format before scraping
            
        Returns:
            List of results
        """
        if validate_id:
            # Validate IDs
            valid_ids = []
            invalid_ids = []
            
            for tid in taxpayer_ids:
                cleaned = ''.join(c for c in str(tid) if c.isdigit())
                if 9 <= len(cleaned) <= 11:
                    valid_ids.append(cleaned)
                else:
                    invalid_ids.append(tid)
            
            if invalid_ids:
                logger.warning(f"Skipping {len(invalid_ids)} invalid IDs")
            
            logger.info(f"Processing {len(valid_ids)} valid IDs")
            taxpayer_ids = valid_ids
        
        return self.scrape_taxpayer_details(taxpayer_ids)
    
    def get_scraper_stats(self) -> Dict:
        """Get scraper statistics"""
        stats = {
            'client_type': 'async' if self.use_async else 'sync',
            'gpu_enabled': self.gpu.use_gpu,
            'gpu_available': self.gpu.gpu_available,
            'rate_limiter': self.client.rate_limiter.get_stats()
        }
        
        if self.gpu.use_gpu:
            stats['gpu_memory'] = self.gpu.get_gpu_memory_info()
        
        return stats


class BulkComptrollerScraper(ComptrollerScraper):
    """Optimized scraper for bulk operations"""
    
    def __init__(self):
        super().__init__(use_async=True, use_gpu=True)
        logger.info("Initialized BulkComptrollerScraper (async + GPU)")
    
    async def bulk_scrape_async(self,
                                 taxpayer_ids: List[str],
                                 include_details: bool = True,
                                 include_ftas: bool = True) -> List[Dict]:
        """
        Bulk scrape with options
        
        Args:
            taxpayer_ids: List of IDs
            include_details: Include detailed info
            include_ftas: Include FTAS records
            
        Returns:
            List of results
        """
        logger.info(f"Bulk async scrape: {len(taxpayer_ids)} taxpayers")
        
        if include_details and include_ftas:
            # Full data
            results = await self.client.batch_get_taxpayer_info(
                taxpayer_ids,
                max_concurrent=batch_config.CONCURRENT_REQUESTS
            )
        elif include_details:
            # Details only
            tasks = [
                self.client.get_franchise_tax_details(tid)
                for tid in taxpayer_ids
            ]
            details = await asyncio.gather(*tasks)
            
            results = [
                {
                    'taxpayer_id': tid,
                    'details': detail,
                    'ftas_records': [],
                    'has_details': detail is not None,
                    'has_ftas': False
                }
                for tid, detail in zip(taxpayer_ids, details)
            ]
        elif include_ftas:
            # FTAS only
            tasks = [
                self.client.get_franchise_tax_list(taxpayer_id=tid)
                for tid in taxpayer_ids
            ]
            ftas_lists = await asyncio.gather(*tasks)
            
            results = [
                {
                    'taxpayer_id': tid,
                    'details': None,
                    'ftas_records': ftas,
                    'has_details': False,
                    'has_ftas': len(ftas) > 0
                }
                for tid, ftas in zip(taxpayer_ids, ftas_lists)
            ]
        else:
            results = []
        
        logger.info(f"Bulk scrape complete: {len(results)} results")
        
        return results
    
    def bulk_scrape_sync(self,
                         taxpayer_ids: List[str],
                         include_details: bool = True,
                         include_ftas: bool = True) -> List[Dict]:
        """Synchronous wrapper for bulk scrape"""
        return asyncio.run(self.bulk_scrape_async(
            taxpayer_ids,
            include_details,
            include_ftas
        ))


class SmartComptrollerScraper(ComptrollerScraper):
    """Smart scraper with persistent disk caching and optimization"""
    
    def __init__(self):
        super().__init__(use_async=True, use_gpu=True)
        
        # Disk-based cache directory
        import os
        from pathlib import Path
        self.cache_dir = Path(os.getenv('CACHE_DIR', '.cache')) / 'comptroller'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache from disk
        self._load_cache_index()
        logger.info(f"Initialized SmartComptrollerScraper with disk cache at {self.cache_dir} ({len(self.cache_index)} cached)")
    
    def _load_cache_index(self):
        """Load list of cached taxpayer IDs from disk"""
        self.cache_index = set()
        if self.cache_dir.exists():
            for f in self.cache_dir.glob('*.json'):
                # Extract taxpayer ID from filename
                tid = f.stem
                self.cache_index.add(tid)
    
    def _get_cache_path(self, taxpayer_id: str):
        """Get cache file path for a taxpayer ID"""
        return self.cache_dir / f"{taxpayer_id}.json"
    
    def _load_from_cache(self, taxpayer_id: str) -> Optional[Dict]:
        """Load a taxpayer record from disk cache"""
        import json
        cache_file = self._get_cache_path(taxpayer_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {taxpayer_id}: {e}")
        return None
    
    def _save_to_cache(self, taxpayer_id: str, data: Dict):
        """Save a taxpayer record to disk cache"""
        import json
        cache_file = self._get_cache_path(taxpayer_id)
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            self.cache_index.add(taxpayer_id)
        except Exception as e:
            logger.warning(f"Failed to save cache for {taxpayer_id}: {e}")
    
    def scrape_with_cache(self,
                          taxpayer_ids: List[str],
                          cache_enabled: bool = True) -> List[Dict]:
        """
        Scrape with persistent disk caching support
        
        Args:
            taxpayer_ids: List of IDs
            cache_enabled: Use cache
            
        Returns:
            List of results
        """
        if not cache_enabled:
            return self.scrape_taxpayer_details(taxpayer_ids)
        
        # Check cache
        uncached_ids = []
        results = []
        
        for tid in taxpayer_ids:
            if tid in self.cache_index:
                cached_data = self._load_from_cache(tid)
                if cached_data:
                    results.append(cached_data)
                    logger.debug(f"Cache hit: {tid}")
                    continue
            uncached_ids.append(tid)
        
        logger.info(f"Cache: {len(results)} hits, {len(uncached_ids)} misses (disk cache)")
        
        # Fetch uncached
        if uncached_ids:
            new_data = self.scrape_taxpayer_details(uncached_ids)
            
            # Save each result to disk cache immediately
            for data in new_data:
                tid = data.get('taxpayer_id')
                if tid:
                    self._save_to_cache(tid, data)
            
            results.extend(new_data)
        
        return results
    
    def clear_cache(self):
        """Clear the disk cache"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        # Calculate cache size from disk files
        cache_size = 0
        for f in self.cache_dir.glob('*.json'):
            cache_size += f.stat().st_size
        
        return {
            'cached_items': len(self.cache_index),
            'cache_size_bytes': cache_size,
            'cache_directory': str(self.cache_dir)
        }
    
    def scrape_with_progress(self,
                             taxpayer_ids: List[str],
                             operation_name: str = 'comptroller_scrape',
                             checkpoint_interval: int = 50,
                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Scrape with progress persistence for resumable operations
        
        Args:
            taxpayer_ids: List of IDs to process
            operation_name: Name for this operation (for resume)
            checkpoint_interval: Save checkpoint every N records
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of results
        """
        if not PROGRESS_AVAILABLE:
            logger.warning("Progress manager not available, using standard scraping")
            return self.scrape_taxpayer_details(taxpayer_ids)
        
        # Initialize progress manager
        progress = ProgressManager(operation_name)
        
        # Check for saved progress
        if progress.has_saved_progress():
            progress.load_progress()
            remaining_ids = progress.get_remaining_ids()
            results = progress.get_partial_results()
            
            logger.info(f"Resuming from checkpoint: {len(results)} completed, {len(remaining_ids)} remaining")
        else:
            # Start fresh
            progress.start_operation(taxpayer_ids, {'total': len(taxpayer_ids)})
            remaining_ids = taxpayer_ids
            results = []
        
        try:
            # Process remaining IDs
            for i, tid in enumerate(remaining_ids):
                try:
                    info = self.client.get_complete_taxpayer_info(tid)
                    
                    # Check cache first
                    if tid in self.cache:
                        info = self.cache[tid]
                    else:
                        info = self.client.get_complete_taxpayer_info(tid)
                        self.cache[tid] = info
                    
                    results.append(info)
                    progress.mark_completed(tid, info)
                    
                    # Progress callback
                    if progress_callback:
                        total = len(taxpayer_ids)
                        done = len(results)
                        progress_callback(done, total)
                    
                    # Checkpoint
                    if (i + 1) % checkpoint_interval == 0:
                        progress.save_progress()
                        logger.debug(f"Checkpoint saved: {len(results)} records")
                        
                except Exception as e:
                    logger.error(f"Error processing {tid}: {e}")
                    error_result = {
                        'taxpayer_id': tid,
                        'error': str(e),
                        'details': None,
                        'ftas_records': []
                    }
                    results.append(error_result)
                    progress.mark_completed(tid, error_result)
            
            # Clear progress on success
            progress.clear_progress()
            logger.info(f"Scrape complete: {len(results)} records")
            
        except KeyboardInterrupt:
            # Save progress on interruption
            progress.save_progress()
            logger.warning(f"Interrupted! Progress saved: {len(results)} completed")
            raise
        
        return results
    
    def get_saved_progress(self, operation_name: str = 'comptroller_scrape') -> Optional[Dict]:
        """Get info about saved progress for an operation"""
        if not PROGRESS_AVAILABLE:
            return None
        
        progress = ProgressManager(operation_name)
        return progress.get_progress_info()
    
    def clear_saved_progress(self, operation_name: str = 'comptroller_scrape') -> bool:
        """Clear saved progress for an operation"""
        if not PROGRESS_AVAILABLE:
            return False
        
        progress = ProgressManager(operation_name)
        return progress.clear_progress()
    
    def list_all_saved_progress(self) -> List[Dict]:
        """List all saved progress sessions"""
        if not PROGRESS_AVAILABLE:
            return []
        
        return get_all_saved_progress()