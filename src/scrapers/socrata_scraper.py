"""
Socrata Scraper Module
Core scraping logic for Socrata Open Data Portal
With progress persistence for resumable operations
"""
from typing import List, Dict, Optional, Callable
import time
from src.api.socrata_client import SocrataClient, AsyncSocrataClient
from src.scrapers.gpu_accelerator import get_gpu_accelerator
from src.utils.logger import get_logger
from config.settings import socrata_config, batch_config

# Import progress manager
try:
    from src.utils.progress_manager import ProgressManager, get_all_saved_progress
    PROGRESS_AVAILABLE = True
except ImportError:
    PROGRESS_AVAILABLE = False

logger = get_logger(__name__)


class SocrataScraper:
    """Main scraper class for Socrata data"""
    
    def __init__(self, use_async: bool = False, use_gpu: bool = None):
        """
        Initialize scraper
        
        Args:
            use_async: Use async client for concurrent requests
            use_gpu: Use GPU acceleration (None = auto-detect)
        """
        self.client = AsyncSocrataClient() if use_async else SocrataClient()
        self.use_async = use_async
        
        # GPU accelerator
        self.gpu = get_gpu_accelerator()
        if use_gpu is not None:
            self.gpu.use_gpu = use_gpu and self.gpu.gpu_available
        
        logger.info(f"Initialized SocrataScraper (async={use_async}, gpu={self.gpu.use_gpu})")
    
    def scrape_dataset(self, dataset_id: str, 
                       limit: Optional[int] = None,
                       batch_size: int = None,
                       progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Scrape complete dataset with progress tracking
        
        Args:
            dataset_id: Dataset identifier
            limit: Maximum records to fetch (None = all)
            batch_size: Records per batch (None = use config default)
            progress_callback: Callback function(current, total)
            
        Returns:
            List of records
        """
        # Use config default if not specified
        if batch_size is None:
            batch_size = batch_config.BATCH_SIZE
        
        logger.info(f"Starting scrape: dataset={dataset_id}, limit={limit}, batch_size={batch_size}")
        
        all_data = []
        offset = 0
        
        while True:
            # Determine batch limit
            remaining = None
            if limit:
                remaining = limit - len(all_data)
                if remaining <= 0:
                    break
                batch_limit = min(batch_size, remaining)
            else:
                batch_limit = batch_size
            
            # Fetch batch
            try:
                if self.use_async:
                    import asyncio
                    batch = asyncio.run(self.client.get(
                        dataset_id,
                        limit=batch_limit,
                        offset=offset
                    ))
                else:
                    batch = self.client.get(
                        dataset_id,
                        limit=batch_limit,
                        offset=offset
                    )
                
                if not batch:
                    logger.info("No more data to fetch")
                    break
                
                all_data.extend(batch)
                offset += len(batch)
                
                # Progress callback
                if progress_callback:
                    progress_callback(len(all_data), limit or len(all_data))
                
                logger.debug(f"Fetched batch: {len(batch)} records (total: {len(all_data)})")
                
                # Break if we got fewer records than requested
                if len(batch) < batch_limit:
                    logger.info("Received partial batch, ending scrape")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching batch at offset {offset}: {e}")
                raise
        
        logger.info(f"Scrape complete: {len(all_data)} records")
        
        # GPU processing if enabled
        if self.gpu.use_gpu and len(all_data) > 1000:
            logger.info("Applying GPU acceleration for post-processing")
            all_data = self._gpu_post_process(all_data)
        
        return all_data
    
    def scrape_multiple_datasets(self, dataset_ids: List[str],
                                  limit_per_dataset: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Scrape multiple datasets
        
        Args:
            dataset_ids: List of dataset identifiers
            limit_per_dataset: Max records per dataset
            
        Returns:
            Dictionary mapping dataset_id to records
        """
        logger.info(f"Scraping {len(dataset_ids)} datasets")
        
        results = {}
        
        for i, dataset_id in enumerate(dataset_ids, 1):
            logger.info(f"Processing dataset {i}/{len(dataset_ids)}: {dataset_id}")
            
            try:
                data = self.scrape_dataset(dataset_id, limit=limit_per_dataset)
                results[dataset_id] = data
                
            except Exception as e:
                logger.error(f"Failed to scrape {dataset_id}: {e}")
                results[dataset_id] = []
        
        total_records = sum(len(data) for data in results.values())
        logger.info(f"Multi-scrape complete: {total_records} total records")
        
        return results
    
    def search_across_datasets(self, 
                                query: str,
                                dataset_ids: List[str],
                                field: str = 'taxpayer_name',
                                limit_per_dataset: int = 100) -> Dict[str, List[Dict]]:
        """
        Search across multiple datasets
        
        Args:
            query: Search query
            dataset_ids: List of datasets to search
            field: Field to search in
            limit_per_dataset: Max results per dataset
            
        Returns:
            Dictionary mapping dataset_id to matching records
        """
        logger.info(f"Searching '{query}' in {len(dataset_ids)} datasets")
        
        results = {}
        
        for dataset_id in dataset_ids:
            try:
                matches = self.client.search(
                    dataset_id,
                    field,
                    query,
                    limit=limit_per_dataset
                )
                
                if matches:
                    results[dataset_id] = matches
                    logger.info(f"Found {len(matches)} matches in {dataset_id}")
                    
            except Exception as e:
                logger.error(f"Search error in {dataset_id}: {e}")
        
        total_matches = sum(len(data) for data in results.values())
        logger.info(f"Search complete: {total_matches} total matches")
        
        return results
    
    def incremental_scrape(self, 
                           dataset_id: str,
                           existing_ids: set,
                           id_field: str = 'taxpayer_id',
                           batch_size: int = 1000) -> List[Dict]:
        """
        Incremental scrape - only fetch new records
        
        Args:
            dataset_id: Dataset identifier
            existing_ids: Set of IDs already scraped
            id_field: Field containing unique ID
            batch_size: Records per batch
            
        Returns:
            List of new records only
        """
        logger.info(f"Starting incremental scrape ({len(existing_ids)} existing IDs)")
        
        new_records = []
        offset = 0
        
        while True:
            batch = self.client.get(
                dataset_id,
                limit=batch_size,
                offset=offset
            )
            
            if not batch:
                break
            
            # Filter new records
            for record in batch:
                record_id = record.get(id_field)
                if record_id and record_id not in existing_ids:
                    new_records.append(record)
            
            offset += len(batch)
            
            if len(batch) < batch_size:
                break
        
        logger.info(f"Incremental scrape complete: {len(new_records)} new records")
        
        return new_records
    
    def _gpu_post_process(self, data: List[Dict]) -> List[Dict]:
        """Apply GPU post-processing to data"""
        try:
            # GPU deduplication
            data = self.gpu.deduplicate_gpu(data, key_field='taxpayer_id')
            
            logger.info("GPU post-processing complete")
            
        except Exception as e:
            logger.warning(f"GPU post-processing failed, using CPU: {e}")
        
        return data
    
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


class BulkSocrataScraper(SocrataScraper):
    """Optimized scraper for bulk operations"""
    
    def __init__(self):
        super().__init__(use_async=True, use_gpu=True)
        logger.info("Initialized BulkSocrataScraper (async + GPU)")
    
    async def bulk_scrape_async(self, 
                                 dataset_ids: List[str],
                                 limit_per_dataset: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Async bulk scrape with concurrency
        
        Args:
            dataset_ids: List of dataset IDs
            limit_per_dataset: Limit per dataset
            
        Returns:
            Dictionary of results
        """
        import asyncio
        
        logger.info(f"Starting bulk async scrape: {len(dataset_ids)} datasets")
        
        async def fetch_dataset(dataset_id: str):
            try:
                if limit_per_dataset:
                    data = await self.client.get(dataset_id, limit=limit_per_dataset)
                else:
                    data = await self.client.get_all(dataset_id)
                
                return dataset_id, data
                
            except Exception as e:
                logger.error(f"Error scraping {dataset_id}: {e}")
                return dataset_id, []
        
        # Fetch all datasets concurrently
        tasks = [fetch_dataset(did) for did in dataset_ids]
        results_list = await asyncio.gather(*tasks)
        
        # Convert to dictionary
        results = dict(results_list)
        
        total_records = sum(len(data) for data in results.values())
        logger.info(f"Bulk scrape complete: {total_records} total records")
        
        return results
    
    def bulk_scrape_sync(self, 
                         dataset_ids: List[str],
                         limit_per_dataset: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Synchronous wrapper for bulk scrape
        
        Args:
            dataset_ids: List of dataset IDs
            limit_per_dataset: Limit per dataset
            
        Returns:
            Dictionary of results
        """
        import asyncio
        return asyncio.run(self.bulk_scrape_async(dataset_ids, limit_per_dataset))
    
    def scrape_with_progress(self,
                             dataset_id: str,
                             operation_name: str = 'socrata_scrape',
                             batch_size: int = 1000,
                             checkpoint_interval: int = 5000,
                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Scrape with progress persistence for resumable operations
        
        Args:
            dataset_id: Dataset to scrape
            operation_name: Name for this operation (for resume)
            batch_size: Records per batch
            checkpoint_interval: Save checkpoint every N records
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of records
        """
        if not PROGRESS_AVAILABLE:
            logger.warning("Progress manager not available, using standard scraping")
            return self.scrape_dataset(dataset_id)
        
        # Initialize progress manager
        progress = ProgressManager(f"{operation_name}_{dataset_id}")
        
        # Check for saved progress
        if progress.has_saved_progress():
            progress.load_progress()
            results = progress.get_partial_results()
            start_offset = len(results)
            logger.info(f"Resuming from checkpoint: {start_offset} records already fetched")
        else:
            progress.start_operation([], {'dataset_id': dataset_id})
            results = []
            start_offset = 0
        
        offset = start_offset
        
        try:
            while True:
                # Fetch batch
                try:
                    batch = self.client.get(
                        dataset_id,
                        limit=batch_size,
                        offset=offset
                    )
                    
                    if not batch:
                        logger.info("No more data to fetch")
                        break
                    
                    results.extend(batch)
                    offset += len(batch)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(len(results), None)
                    
                    # Checkpoint
                    if len(results) % checkpoint_interval < batch_size:
                        progress.partial_results = results
                        progress.save_progress()
                        logger.debug(f"Checkpoint saved: {len(results)} records")
                    
                    # Break if we got fewer records than requested
                    if len(batch) < batch_size:
                        break
                        
                except Exception as e:
                    logger.error(f"Error fetching batch at offset {offset}: {e}")
                    # Save progress before raising
                    progress.partial_results = results
                    progress.save_progress()
                    raise
            
            # Clear progress on success
            progress.clear_progress()
            logger.info(f"Scrape complete: {len(results)} records")
            
        except KeyboardInterrupt:
            # Save progress on interruption
            progress.partial_results = results
            progress.save_progress()
            logger.warning(f"Interrupted! Progress saved: {len(results)} records")
            raise
        
        return results
    
    def get_saved_progress(self, operation_name: str, dataset_id: str = '') -> Optional[Dict]:
        """Get info about saved progress for an operation"""
        if not PROGRESS_AVAILABLE:
            return None
        
        name = f"{operation_name}_{dataset_id}" if dataset_id else operation_name
        progress = ProgressManager(name)
        return progress.get_progress_info()
    
    def list_all_saved_progress(self) -> List[Dict]:
        """List all saved progress sessions"""
        if not PROGRESS_AVAILABLE:
            return []
        
        return get_all_saved_progress()