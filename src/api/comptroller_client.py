"""
Comptroller API Client for Texas Taxpayer Data
"""
import requests
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from src.api.rate_limiter import RateLimiter, AsyncRateLimiter, BackoffRetry
from src.utils.logger import get_logger
from config.settings import comptroller_config, rate_limit_config, advanced_config

logger = get_logger(__name__)


class ComptrollerClient:
    """Client for Texas Comptroller API"""
    
    def __init__(self):
        self.base_url = comptroller_config.BASE_URL
        self.api_key = comptroller_config.API_KEY
        self.rate_limiter = RateLimiter(
            max_requests=comptroller_config.RATE_LIMIT,
            time_window=60,  # Per minute
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
        
        if self.api_key:
            # Texas Comptroller API uses x-api-key header
            headers['x-api-key'] = self.api_key
        
        return headers
    
    def get_franchise_tax_details(self, taxpayer_id: str) -> Optional[Dict]:
        """
        Get detailed franchise tax information for a taxpayer
        
        Args:
            taxpayer_id: Taxpayer identification number
            
        Returns:
            Taxpayer details or None if not found
        """
        url = f"{comptroller_config.FRANCHISE_TAX_ENDPOINT}/{taxpayer_id}"
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            logger.debug(f"Fetching franchise tax details for {taxpayer_id}")
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=rate_limit_config.REQUEST_TIMEOUT,
                verify=advanced_config.VERIFY_SSL
            )
            
            self.rate_limiter.record_request()
            
            if response.status_code == 404:
                logger.warning(f"Taxpayer {taxpayer_id} not found")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Retrieved details for {taxpayer_id}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching details for {taxpayer_id}: {e}")
            return None
    
    def get_franchise_tax_list(self, taxpayer_id: Optional[str] = None,
                                name: Optional[str] = None,
                                file_number: Optional[str] = None) -> List[Dict]:
        """
        Get franchise tax account status (FTAS) records
        
        Args:
            taxpayer_id: Taxpayer identification number
            name: Business name
            file_number: File number
            
        Returns:
            List of FTAS records
        """
        url = comptroller_config.FRANCHISE_TAX_LIST_ENDPOINT
        
        # Build query parameters
        params = {}
        if taxpayer_id:
            params['taxpayerId'] = taxpayer_id
        if name:
            params['name'] = name
        if file_number:
            params['fileNumber'] = file_number
        
        if not params:
            logger.error("At least one parameter (taxpayer_id, name, or file_number) is required")
            return []
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            logger.debug(f"Fetching FTAS records with params: {params}")
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=rate_limit_config.REQUEST_TIMEOUT,
                verify=advanced_config.VERIFY_SSL
            )
            
            self.rate_limiter.record_request()
            
            if response.status_code == 404:
                logger.warning(f"No FTAS records found for {params}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Handle both single dict and list responses
            if isinstance(data, dict):
                data = [data]
            
            logger.debug(f"Retrieved {len(data)} FTAS records")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching FTAS records: {e}")
            return []
    
    def get_complete_taxpayer_info(self, taxpayer_id: str) -> Dict[str, Any]:
        """
        Get complete information for a taxpayer (details + FTAS)
        
        Args:
            taxpayer_id: Taxpayer identification number
            
        Returns:
            Combined taxpayer information
        """
        logger.info(f"Fetching complete info for taxpayer {taxpayer_id}")
        
        # Get details
        details = self.get_franchise_tax_details(taxpayer_id)
        
        # Get FTAS records
        ftas_records = self.get_franchise_tax_list(taxpayer_id=taxpayer_id)
        
        # Combine data
        result = {
            'taxpayer_id': taxpayer_id,
            'details': details,
            'ftas_records': ftas_records,
            'has_details': details is not None,
            'has_ftas': len(ftas_records) > 0
        }
        
        return result
    
    def batch_get_taxpayer_info(self, taxpayer_ids: List[str]) -> List[Dict]:
        """
        Get information for multiple taxpayers
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            
        Returns:
            List of taxpayer information
        """
        results = []
        total = len(taxpayer_ids)
        
        logger.info(f"Starting batch fetch for {total} taxpayers")
        
        for i, taxpayer_id in enumerate(taxpayer_ids, 1):
            try:
                info = self.get_complete_taxpayer_info(taxpayer_id)
                results.append(info)
                
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{total} taxpayers processed")
                    
            except Exception as e:
                logger.error(f"Error processing taxpayer {taxpayer_id}: {e}")
                results.append({
                    'taxpayer_id': taxpayer_id,
                    'error': str(e),
                    'details': None,
                    'ftas_records': []
                })
        
        logger.info(f"Batch fetch complete: {len(results)} taxpayers processed")
        return results


class AsyncComptrollerClient:
    """Async client for Texas Comptroller API"""
    
    def __init__(self):
        self.base_url = comptroller_config.BASE_URL
        self.api_key = comptroller_config.API_KEY
        self.rate_limiter = AsyncRateLimiter(
            max_requests=comptroller_config.RATE_LIMIT,
            time_window=60,
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
        
        if self.api_key:
            # Texas Comptroller API uses x-api-key header
            headers['x-api-key'] = self.api_key
        
        return headers
    
    async def get_franchise_tax_details(self, taxpayer_id: str) -> Optional[Dict]:
        """Async get detailed franchise tax information with network retry"""
        url = f"{comptroller_config.FRANCHISE_TAX_ENDPOINT}/{taxpayer_id}"
        
        max_retries = rate_limit_config.MAX_RETRIES
        base_delay = rate_limit_config.RETRY_DELAY
        
        for attempt in range(max_retries + 1):
            await self.rate_limiter.wait_if_needed()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT),
                        ssl=advanced_config.VERIFY_SSL
                    ) as response:
                        await self.rate_limiter.record_request()
                        
                        if response.status == 404:
                            return None
                        
                        response.raise_for_status()
                        return await response.json()
                        
            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError, OSError) as e:
                # Network errors - retry with backoff
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Network error for {taxpayer_id}, retry {attempt + 1}/{max_retries} in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Error fetching details for {taxpayer_id} after {max_retries} retries: {e}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching details for {taxpayer_id}: {e}")
                return None
        
        return None
    
    async def get_franchise_tax_list(self, taxpayer_id: Optional[str] = None,
                                     name: Optional[str] = None,
                                     file_number: Optional[str] = None) -> List[Dict]:
        """Async get franchise tax account status records with network retry"""
        url = comptroller_config.FRANCHISE_TAX_LIST_ENDPOINT
        
        params = {}
        if taxpayer_id:
            params['taxpayerId'] = taxpayer_id
        if name:
            params['name'] = name
        if file_number:
            params['fileNumber'] = file_number
        
        if not params:
            return []
        
        max_retries = rate_limit_config.MAX_RETRIES
        base_delay = rate_limit_config.RETRY_DELAY
        
        for attempt in range(max_retries + 1):
            await self.rate_limiter.wait_if_needed()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=self._get_headers(),
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT),
                        ssl=advanced_config.VERIFY_SSL
                    ) as response:
                        await self.rate_limiter.record_request()
                        
                        if response.status == 404:
                            return []
                        
                        response.raise_for_status()
                        data = await response.json()
                        
                        if isinstance(data, dict):
                            data = [data]
                        
                        return data
                        
            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError, OSError) as e:
                # Network errors - retry with backoff
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Network error for FTAS {taxpayer_id}, retry {attempt + 1}/{max_retries} in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Error fetching FTAS records after {max_retries} retries: {e}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching FTAS records: {e}")
                return []
        
        return []
    
    async def get_complete_taxpayer_info(self, taxpayer_id: str) -> Dict[str, Any]:
        """Async get complete taxpayer information"""
        # Fetch both endpoints concurrently
        details_task = self.get_franchise_tax_details(taxpayer_id)
        ftas_task = self.get_franchise_tax_list(taxpayer_id=taxpayer_id)
        
        details, ftas_records = await asyncio.gather(details_task, ftas_task)
        
        return {
            'taxpayer_id': taxpayer_id,
            'details': details,
            'ftas_records': ftas_records,
            'has_details': details is not None,
            'has_ftas': len(ftas_records) > 0
        }
    
    async def batch_get_taxpayer_info(self, taxpayer_ids: List[str],
                                      max_concurrent: int = None) -> List[Dict]:
        """
        Async batch get taxpayer information with concurrency control
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            max_concurrent: Maximum concurrent requests (defaults to config setting)
            
        Returns:
            List of taxpayer information
        """
        # Use config values if not specified
        if max_concurrent is None:
            max_concurrent = comptroller_config.CONCURRENT_REQUESTS
        chunk_size = comptroller_config.CHUNK_SIZE
        request_delay = comptroller_config.REQUEST_DELAY
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def fetch_with_semaphore(taxpayer_id: str):
            async with semaphore:
                try:
                    result = await self.get_complete_taxpayer_info(taxpayer_id)
                    # Add delay to respect rate limit
                    await asyncio.sleep(request_delay)
                    return result
                except Exception as e:
                    logger.error(f"Error processing {taxpayer_id}: {e}")
                    return {
                        'taxpayer_id': taxpayer_id,
                        'error': str(e),
                        'details': None,
                        'ftas_records': []
                    }
        
        logger.info(f"Starting async batch fetch for {len(taxpayer_ids)} taxpayers (concurrent={max_concurrent}, chunk={chunk_size}, delay={request_delay}s)")
        
        # Process in smaller chunks to avoid overwhelming rate limiter
        for i in range(0, len(taxpayer_ids), chunk_size):
            chunk = taxpayer_ids[i:i+chunk_size]
            tasks = [fetch_with_semaphore(tid) for tid in chunk]
            chunk_results = await asyncio.gather(*tasks)
            results.extend(chunk_results)
            
            # Log progress
            processed = min(i + chunk_size, len(taxpayer_ids))
            logger.info(f"Progress: {processed}/{len(taxpayer_ids)} taxpayers processed")
        
        logger.info(f"Async batch fetch complete: {len(results)} taxpayers processed")
        return results