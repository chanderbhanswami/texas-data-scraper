"""
Google Places Scraper Module
Core scraping logic for Google Places API
With progress persistence for resumable operations
"""
from typing import List, Dict, Optional, Callable
import asyncio
import json
from pathlib import Path
from src.api.google_places_client import GooglePlacesClient, AsyncGooglePlacesClient, DEFAULT_PLACE_DETAILS_FIELDS
from src.utils.logger import get_logger
from src.scrapers.gpu_accelerator import get_gpu_accelerator
from config.settings import google_places_config, CACHE_DIR

# Import progress manager
try:
    from src.utils.progress_manager import ProgressManager, get_all_saved_progress
    PROGRESS_AVAILABLE = True
except ImportError:
    PROGRESS_AVAILABLE = False

logger = get_logger(__name__)


class GooglePlacesScraper:
    """Main scraper class for Google Places data"""
    
    def __init__(self, use_async: bool = True, use_gpu: bool = None):
        """
        Initialize scraper
        
        Args:
            use_async: Use async client (recommended)
            use_gpu: Use GPU acceleration
        """
        self.use_async = use_async
        
        if use_async:
            self.client = AsyncGooglePlacesClient()
        else:
            self.client = GooglePlacesClient()
        
        # GPU acceleration
        if use_gpu is None:
            self.gpu = get_gpu_accelerator()
        else:
            self.gpu = get_gpu_accelerator() if use_gpu else None
        
        # Stats tracking
        self.stats = {
            'total_records': 0,
            'places_found': 0,
            'places_not_found': 0,
            'errors': 0,
            'details_fetched': 0
        }
        
        logger.info(f"Initialized GooglePlacesScraper (async={use_async})")
    
    def find_place_ids(self,
                       records: List[Dict],
                       batch_size: int = None,
                       progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Find place IDs for records
        
        Args:
            records: List of records with business info
            batch_size: Batch size for processing
            progress_callback: Function to call with progress updates
            
        Returns:
            List of results with place_ids
        """
        if batch_size is None:
            batch_size = google_places_config.CHUNK_SIZE
        
        self.stats['total_records'] = len(records)
        
        if self.use_async:
            return self._async_find_place_ids(records, batch_size, progress_callback)
        else:
            return self._sync_find_place_ids(records, batch_size, progress_callback)
    
    def _sync_find_place_ids(self,
                             records: List[Dict],
                             batch_size: int,
                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Synchronous place ID finding"""
        results = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_results = self.client.batch_find_places(batch)
            results.extend(batch_results)
            
            # Update stats
            for r in batch_results:
                if r.get('match_status') == 'found':
                    self.stats['places_found'] += 1
                elif r.get('match_status') == 'not_found':
                    self.stats['places_not_found'] += 1
                else:
                    self.stats['errors'] += 1
            
            if progress_callback:
                progress_callback(len(results), len(records))
        
        return results
    
    def _async_find_place_ids(self,
                              records: List[Dict],
                              batch_size: int,
                              progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Async place ID finding with batching"""
        async def run():
            all_results = []
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                batch_results = await self.client.batch_find_places(batch)
                all_results.extend(batch_results)
                
                # Update stats
                for r in batch_results:
                    if r.get('match_status') == 'found':
                        self.stats['places_found'] += 1
                    elif r.get('match_status') == 'not_found':
                        self.stats['places_not_found'] += 1
                    else:
                        self.stats['errors'] += 1
                
                if progress_callback:
                    progress_callback(len(all_results), len(records))
                
                # Small delay between batches
                await asyncio.sleep(google_places_config.REQUEST_DELAY)
            
            return all_results
        
        return asyncio.run(run())
    
    def get_place_details(self,
                          place_ids_data: List[Dict],
                          fields: List[str] = None,
                          batch_size: int = None,
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Get details for place IDs
        
        Args:
            place_ids_data: List of dicts with place_id and taxpayer_id
            fields: Fields to request
            batch_size: Batch size for processing
            progress_callback: Progress callback
            
        Returns:
            List of place details
        """
        if batch_size is None:
            batch_size = google_places_config.CHUNK_SIZE
        
        # Filter to only records with place_ids
        valid_records = [r for r in place_ids_data if r.get('place_id')]
        
        if self.use_async:
            return self._async_get_details(valid_records, fields, batch_size, progress_callback)
        else:
            return self._sync_get_details(valid_records, fields, batch_size, progress_callback)
    
    def _sync_get_details(self,
                          place_ids_data: List[Dict],
                          fields: List[str],
                          batch_size: int,
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Synchronous details fetching"""
        results = []
        
        for i, data in enumerate(place_ids_data):
            place_id = data.get('place_id')
            taxpayer_id = data.get('taxpayer_id')
            
            details = self.client.get_place_details(place_id, fields)
            
            if details:
                details['taxpayer_id'] = taxpayer_id
                details['details_status'] = 'success'
                results.append(details)
                self.stats['details_fetched'] += 1
            else:
                results.append({
                    'taxpayer_id': taxpayer_id,
                    'place_id': place_id,
                    'details_status': 'error'
                })
                self.stats['errors'] += 1
            
            if progress_callback:
                progress_callback(i + 1, len(place_ids_data))
        
        return results
    
    def _async_get_details(self,
                           place_ids_data: List[Dict],
                           fields: List[str],
                           batch_size: int,
                           progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Async details fetching with batching"""
        async def run():
            all_results = []
            
            for i in range(0, len(place_ids_data), batch_size):
                batch = place_ids_data[i:i + batch_size]
                batch_results = await self.client.batch_get_details(batch, fields)
                all_results.extend(batch_results)
                
                # Update stats
                for r in batch_results:
                    if r.get('details_status') == 'success':
                        self.stats['details_fetched'] += 1
                    else:
                        self.stats['errors'] += 1
                
                if progress_callback:
                    progress_callback(len(all_results), len(place_ids_data))
                
                # Small delay between batches
                await asyncio.sleep(google_places_config.REQUEST_DELAY)
            
            return all_results
        
        return asyncio.run(run())
    
    def get_scraper_stats(self) -> Dict:
        """Get scraper statistics"""
        return self.stats.copy()


class SmartGooglePlacesScraper(GooglePlacesScraper):
    """Smart scraper with persistent disk caching and optimization"""
    
    def __init__(self):
        super().__init__(use_async=True, use_gpu=True)
        
        # Disk-based cache directory
        self.cache_dir = CACHE_DIR / 'google_places'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Place IDs cache
        self.place_ids_cache_dir = self.cache_dir / 'place_ids'
        self.place_ids_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Details cache
        self.details_cache_dir = self.cache_dir / 'details'
        self.details_cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized SmartGooglePlacesScraper with persistent cache at {self.cache_dir}")
    
    def _get_cached_place_id(self, taxpayer_id: str) -> Optional[Dict]:
        """Get cached place ID for a taxpayer"""
        cache_file = self.place_ids_cache_dir / f"{taxpayer_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _save_cached_place_id(self, taxpayer_id: str, data: Dict):
        """Save place ID to cache"""
        cache_file = self.place_ids_cache_dir / f"{taxpayer_id}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache place ID for {taxpayer_id}: {e}")
    
    def _get_cached_details(self, place_id: str) -> Optional[Dict]:
        """Get cached details for a place"""
        cache_file = self.details_cache_dir / f"{place_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _save_cached_details(self, place_id: str, data: Dict):
        """Save details to cache"""
        cache_file = self.details_cache_dir / f"{place_id}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache details for {place_id}: {e}")
    
    def find_place_ids_with_cache(self,
                                  records: List[Dict],
                                  progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Find place IDs with disk caching
        
        Args:
            records: Records to process
            progress_callback: Progress callback
            
        Returns:
            List of results with place_ids
        """
        results = []
        to_process = []
        
        # Check cache first
        for record in records:
            taxpayer_id = record.get('taxpayer_number', '') or record.get('taxpayer_id', '')
            cached = self._get_cached_place_id(taxpayer_id)
            
            if cached:
                results.append(cached)
            else:
                to_process.append(record)
        
        logger.info(f"Found {len(results)} cached place IDs, processing {len(to_process)} new records")
        
        if to_process:
            # Process uncached records
            new_results = self.find_place_ids(
                to_process,
                progress_callback=progress_callback
            )
            
            # Save to cache
            for result in new_results:
                taxpayer_id = result.get('taxpayer_id')
                if taxpayer_id:
                    self._save_cached_place_id(taxpayer_id, result)
                results.append(result)
        
        return results
    
    def get_details_with_cache(self,
                               place_ids_data: List[Dict],
                               fields: List[str] = None,
                               progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Get place details with disk caching
        
        Args:
            place_ids_data: List of dicts with place_id and taxpayer_id
            fields: Fields to request
            progress_callback: Progress callback
            
        Returns:
            List of place details
        """
        results = []
        to_process = []
        
        # Check cache first
        for data in place_ids_data:
            place_id = data.get('place_id')
            if not place_id:
                results.append({
                    'taxpayer_id': data.get('taxpayer_id'),
                    'details_status': 'no_place_id'
                })
                continue
            
            cached = self._get_cached_details(place_id)
            if cached:
                cached['taxpayer_id'] = data.get('taxpayer_id')
                results.append(cached)
            else:
                to_process.append(data)
        
        logger.info(f"Found {len(results) - len([r for r in results if r.get('details_status') == 'no_place_id'])} cached details, processing {len(to_process)} new records")
        
        if to_process:
            # Process uncached records
            new_results = self.get_place_details(
                to_process,
                fields=fields,
                progress_callback=progress_callback
            )
            
            # Save to cache
            for result in new_results:
                place_id = result.get('place_id')
                if place_id and result.get('details_status') == 'success':
                    self._save_cached_details(place_id, result)
                results.append(result)
        
        return results
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        place_ids_cached = len(list(self.place_ids_cache_dir.glob('*.json')))
        details_cached = len(list(self.details_cache_dir.glob('*.json')))
        
        return {
            'place_ids_cached': place_ids_cached,
            'details_cached': details_cached,
            'cache_directory': str(self.cache_dir)
        }
    
    def clear_cache(self, cache_type: str = 'all'):
        """
        Clear cache
        
        Args:
            cache_type: 'place_ids', 'details', or 'all'
        """
        if cache_type in ['place_ids', 'all']:
            for f in self.place_ids_cache_dir.glob('*.json'):
                f.unlink()
            logger.info("Cleared place IDs cache")
        
        if cache_type in ['details', 'all']:
            for f in self.details_cache_dir.glob('*.json'):
                f.unlink()
            logger.info("Cleared details cache")
