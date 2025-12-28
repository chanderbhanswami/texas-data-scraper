"""
Socrata API Client for Texas Open Data Portal
"""
import requests
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
from src.api.rate_limiter import RateLimiter, AsyncRateLimiter, BackoffRetry
from src.utils.logger import get_logger
from config.settings import socrata_config, rate_limit_config, advanced_config, batch_config

logger = get_logger(__name__)


class SocrataClient:
    """Client for Socrata Open Data API"""
    
    def __init__(self):
        self.base_url = socrata_config.BASE_URL
        self.app_token = socrata_config.APP_TOKEN
        self.rate_limiter = RateLimiter(
            max_requests=socrata_config.rate_limit,
            time_window=3600,
            delay=rate_limit_config.REQUEST_DELAY
        )
        self.retry_handler = BackoffRetry(
            max_retries=rate_limit_config.MAX_RETRIES,
            base_delay=rate_limit_config.RETRY_DELAY
        )
        self.session = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'User-Agent': advanced_config.USER_AGENT,
            'Accept': 'application/json'
        }
        
        if self.app_token:
            headers['X-App-Token'] = self.app_token
        
        return headers
    
    def _build_url(self, dataset_id: str) -> str:
        """Build API URL for dataset"""
        return f"{self.base_url}/{dataset_id}.json"
    
    def get(self, dataset_id: str, params: Optional[Dict] = None, 
            limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Get data from Socrata dataset
        
        Args:
            dataset_id: Dataset identifier
            params: Query parameters (SoQL)
            limit: Maximum number of records
            offset: Starting offset
            
        Returns:
            List of records
        """
        url = self._build_url(dataset_id)
        
        # Build query parameters
        query_params = params or {}
        if limit:
            query_params['$limit'] = limit
        if offset:
            query_params['$offset'] = offset
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            logger.info(f"Fetching data from {dataset_id} (offset: {offset}, limit: {limit})")
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=query_params,
                timeout=rate_limit_config.REQUEST_TIMEOUT,
                verify=advanced_config.VERIFY_SSL
            )
            
            self.rate_limiter.record_request()
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data)} records")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data: {e}")
            raise
    
    def get_all(self, dataset_id: str, params: Optional[Dict] = None, 
                batch_size: int = None) -> List[Dict]:
        """
        Get all data from dataset with pagination
        
        Args:
            dataset_id: Dataset identifier
            params: Query parameters
            batch_size: Records per request (None = use config default)
            
        Returns:
            All records from dataset
        """
        # Use config default if not specified
        if batch_size is None:
            batch_size = batch_config.BATCH_SIZE
            
        all_data = []
        offset = 0
        
        logger.info(f"Starting full dataset download: {dataset_id} (batch_size={batch_size})")
        
        while True:
            batch = self.get(dataset_id, params=params, limit=batch_size, offset=offset)
            
            if not batch:
                break
            
            all_data.extend(batch)
            offset += len(batch)
            
            logger.info(f"Progress: {len(all_data)} records downloaded")
            
            # Break if we got fewer records than requested (end of data)
            if len(batch) < batch_size:
                break
        
        logger.info(f"Download complete: {len(all_data)} total records")
        return all_data
    
    def search(self, dataset_id: str, field: str, value: str, 
               limit: Optional[int] = None) -> List[Dict]:
        """
        Search dataset by field value
        
        Args:
            dataset_id: Dataset identifier
            field: Field name to search
            value: Search value
            limit: Maximum records to return
            
        Returns:
            Matching records
        """
        # Build SoQL WHERE clause (case-insensitive)
        # Texas data is stored in UPPERCASE, so we uppercase both sides
        params = {
            '$where': f"UPPER({field}) LIKE UPPER('%{value}%')"
        }
        
        if limit:
            return self.get(dataset_id, params=params, limit=limit)
        else:
            return self.get_all(dataset_id, params=params)
    
    def get_franchise_tax_holders(self, limit: Optional[int] = None) -> List[Dict]:
        """Get franchise tax permit holders"""
        dataset_id = socrata_config.FRANCHISE_TAX_DATASET
        
        if limit:
            return self.get(dataset_id, limit=limit)
        else:
            return self.get_all(dataset_id)
    
    def get_sales_tax_holders(self, limit: Optional[int] = None) -> List[Dict]:
        """Get sales tax permit holders"""
        dataset_id = socrata_config.SALES_TAX_DATASET
        
        if limit:
            return self.get(dataset_id, limit=limit)
        else:
            return self.get_all(dataset_id)
    
    def search_by_business_name(self, name: str, dataset_id: Optional[str] = None,
                                 limit: Optional[int] = None) -> List[Dict]:
        """Search by business name"""
        dataset = dataset_id or socrata_config.FRANCHISE_TAX_DATASET
        return self.search(dataset, 'taxpayer_name', name, limit)
    
    def search_by_city(self, city: str, dataset_id: Optional[str] = None,
                       limit: Optional[int] = None) -> List[Dict]:
        """Search by city"""
        dataset = dataset_id or socrata_config.FRANCHISE_TAX_DATASET
        return self.search(dataset, 'taxpayer_city', city, limit)
    
    def search_by_zip(self, zip_code: str, dataset_id: Optional[str] = None,
                      limit: Optional[int] = None) -> List[Dict]:
        """Search by ZIP code"""
        dataset = dataset_id or socrata_config.FRANCHISE_TAX_DATASET
        return self.search(dataset, 'taxpayer_zip', zip_code, limit)
    
    def get_dataset_metadata(self, dataset_id: str) -> Dict:
        """Get metadata about a dataset"""
        # Remove .json extension for metadata endpoint
        metadata_url = f"https://data.texas.gov/api/views/{dataset_id}.json"
        
        try:
            response = requests.get(
                metadata_url,
                headers=self._get_headers(),
                timeout=rate_limit_config.REQUEST_TIMEOUT,
                verify=advanced_config.VERIFY_SSL
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching metadata: {e}")
            return {}


class AsyncSocrataClient:
    """Async client for Socrata Open Data API"""
    
    def __init__(self):
        self.base_url = socrata_config.BASE_URL
        self.app_token = socrata_config.APP_TOKEN
        self.rate_limiter = AsyncRateLimiter(
            max_requests=socrata_config.rate_limit,
            time_window=3600,
            delay=rate_limit_config.REQUEST_DELAY
        )
        self.retry_handler = BackoffRetry(
            max_retries=rate_limit_config.MAX_RETRIES,
            base_delay=rate_limit_config.RETRY_DELAY
        )
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'User-Agent': advanced_config.USER_AGENT,
            'Accept': 'application/json'
        }
        
        if self.app_token:
            headers['X-App-Token'] = self.app_token
        
        return headers
    
    def _build_url(self, dataset_id: str) -> str:
        """Build API URL for dataset"""
        return f"{self.base_url}/{dataset_id}.json"
    
    async def get(self, dataset_id: str, params: Optional[Dict] = None,
                  limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """Async get data from Socrata dataset"""
        url = self._build_url(dataset_id)
        
        # Build query parameters
        query_params = params or {}
        if limit:
            query_params['$limit'] = limit
        if offset:
            query_params['$offset'] = offset
        
        # Rate limiting
        await self.rate_limiter.wait_if_needed()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT),
                    ssl=advanced_config.VERIFY_SSL
                ) as response:
                    await self.rate_limiter.record_request()
                    response.raise_for_status()
                    
                    data = await response.json()
                    logger.info(f"Retrieved {len(data)} records")
                    
                    return data
                    
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise
    
    async def get_all(self, dataset_id: str, params: Optional[Dict] = None,
                      batch_size: int = 1000) -> List[Dict]:
        """Async get all data from dataset with pagination"""
        all_data = []
        offset = 0
        
        logger.info(f"Starting async full dataset download: {dataset_id}")
        
        while True:
            batch = await self.get(dataset_id, params=params, limit=batch_size, offset=offset)
            
            if not batch:
                break
            
            all_data.extend(batch)
            offset += len(batch)
            
            logger.info(f"Progress: {len(all_data)} records downloaded")
            
            if len(batch) < batch_size:
                break
        
        logger.info(f"Download complete: {len(all_data)} total records")
        return all_data