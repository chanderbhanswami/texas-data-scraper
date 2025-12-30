"""
Google Places API Client for Business Data Enrichment
Sync and Async clients with rate limiting
"""
import requests
import asyncio
import aiohttp
import urllib.parse
from typing import List, Dict, Optional, Any
from src.api.rate_limiter import RateLimiter, AsyncRateLimiter, BackoffRetry
from src.utils.logger import get_logger
from config.settings import google_places_config, rate_limit_config, advanced_config

logger = get_logger(__name__)

# Default fields to request from Place Details API
DEFAULT_PLACE_DETAILS_FIELDS = [
    'name',
    'formatted_address',
    'formatted_phone_number',
    'international_phone_number',
    'website',
    'url',
    'rating',
    'user_ratings_total',
    'business_status',
    'types',
    'opening_hours',
    'geometry',
    'vicinity',
    'price_level',
    'reviews',
    'photos'
]


class GooglePlacesClient:
    """Sync client for Google Places API"""
    
    def __init__(self):
        self.base_url = google_places_config.BASE_URL
        self.api_key = google_places_config.API_KEY
        self.rate_limiter = RateLimiter(
            requests_per_minute=google_places_config.rate_limit
        )
        
        if not self.api_key:
            logger.warning("Google Places API key not configured")
    
    def _get_params(self, **kwargs) -> Dict:
        """Build request parameters with API key"""
        params = {'key': self.api_key}
        params.update(kwargs)
        return params
    
    def find_place(self, 
                   business_name: str,
                   address: str = '',
                   city: str = '',
                   state: str = '',
                   zip_code: str = '') -> Optional[Dict]:
        """
        Find a place using text search
        
        Args:
            business_name: Business name
            address: Street address
            city: City name
            state: State code (e.g., TX)
            zip_code: ZIP code
            
        Returns:
            Place info with place_id or None if not found
        """
        # Build search query: Name + Address + City + State + Zip
        query_parts = [business_name]
        if address:
            query_parts.append(address)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        if zip_code:
            query_parts.append(zip_code)
        
        query = ' '.join(query_parts)
        
        self.rate_limiter.wait()
        
        try:
            url = f"{self.base_url}/findplacefromtext/json"
            params = self._get_params(
                input=query,
                inputtype='textquery',
                fields='place_id,name,formatted_address,business_status'
            )
            
            response = requests.get(
                url, 
                params=params,
                timeout=rate_limit_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('candidates'):
                candidate = data['candidates'][0]
                return {
                    'place_id': candidate.get('place_id'),
                    'name': candidate.get('name'),
                    'formatted_address': candidate.get('formatted_address'),
                    'business_status': candidate.get('business_status'),
                    'search_query': query,
                    'match_status': 'found'
                }
            elif data.get('status') == 'ZERO_RESULTS':
                logger.debug(f"No results for query: {query}")
                return {
                    'place_id': None,
                    'search_query': query,
                    'match_status': 'not_found'
                }
            else:
                logger.warning(f"Find Place API error: {data.get('status')} - {data.get('error_message', '')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error finding place: {e}")
            return None
    
    def get_place_details(self, 
                          place_id: str,
                          fields: List[str] = None) -> Optional[Dict]:
        """
        Get detailed information for a place
        
        Args:
            place_id: Google Place ID
            fields: List of fields to request (uses defaults if not specified)
            
        Returns:
            Place details or None if error
        """
        if not place_id:
            return None
            
        if fields is None:
            fields = DEFAULT_PLACE_DETAILS_FIELDS
        
        self.rate_limiter.wait()
        
        try:
            url = f"{self.base_url}/details/json"
            params = self._get_params(
                place_id=place_id,
                fields=','.join(fields)
            )
            
            response = requests.get(
                url,
                params=params,
                timeout=rate_limit_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                result = data.get('result', {})
                result['place_id'] = place_id
                return result
            else:
                logger.warning(f"Place Details API error: {data.get('status')} - {data.get('error_message', '')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting place details: {e}")
            return None
    
    def batch_find_places(self, records: List[Dict]) -> List[Dict]:
        """
        Find place IDs for multiple records
        
        Args:
            records: List of records with business info
            
        Returns:
            List of results with place_ids
        """
        results = []
        
        for record in records:
            # Extract fields from polished data format
            business_name = record.get('socrata_business_name', '') or record.get('taxpayer_name', '')
            address = record.get('socrata_taxpayer_address', '') or record.get('taxpayer_address', '')
            city = record.get('socrata_taxpayer_city', '') or record.get('taxpayer_city', '')
            state = record.get('socrata_taxpayer_state', '') or record.get('taxpayer_state', 'TX')
            zip_code = record.get('socrata_taxpayer_zip', '') or record.get('taxpayer_zip', '')
            taxpayer_id = record.get('taxpayer_number', '') or record.get('taxpayer_id', '')
            
            result = self.find_place(
                business_name=business_name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code
            )
            
            if result:
                result['taxpayer_id'] = taxpayer_id
                results.append(result)
            else:
                results.append({
                    'taxpayer_id': taxpayer_id,
                    'place_id': None,
                    'search_query': f"{business_name} {address} {city} {state} {zip_code}".strip(),
                    'match_status': 'error'
                })
        
        return results


class AsyncGooglePlacesClient:
    """Async client for Google Places API"""
    
    def __init__(self):
        self.base_url = google_places_config.BASE_URL
        self.api_key = google_places_config.API_KEY
        self.rate_limiter = AsyncRateLimiter(
            requests_per_minute=google_places_config.rate_limit
        )
        self.backoff = BackoffRetry(
            max_retries=rate_limit_config.MAX_RETRIES,
            base_delay=rate_limit_config.RETRY_DELAY
        )
        
        if not self.api_key:
            logger.warning("Google Places API key not configured")
    
    def _get_params(self, **kwargs) -> Dict:
        """Build request parameters with API key"""
        params = {'key': self.api_key}
        params.update(kwargs)
        return params
    
    async def find_place(self,
                         business_name: str,
                         address: str = '',
                         city: str = '',
                         state: str = '',
                         zip_code: str = '') -> Optional[Dict]:
        """Async find a place using text search"""
        # Build search query
        query_parts = [business_name]
        if address:
            query_parts.append(address)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        if zip_code:
            query_parts.append(zip_code)
        
        query = ' '.join(query_parts)
        
        await self.rate_limiter.wait()
        
        url = f"{self.base_url}/findplacefromtext/json"
        params = self._get_params(
            input=query,
            inputtype='textquery',
            fields='place_id,name,formatted_address,business_status'
        )
        
        for attempt in range(rate_limit_config.MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT)
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        if data.get('status') == 'OK' and data.get('candidates'):
                            candidate = data['candidates'][0]
                            return {
                                'place_id': candidate.get('place_id'),
                                'name': candidate.get('name'),
                                'formatted_address': candidate.get('formatted_address'),
                                'business_status': candidate.get('business_status'),
                                'search_query': query,
                                'match_status': 'found'
                            }
                        elif data.get('status') == 'ZERO_RESULTS':
                            return {
                                'place_id': None,
                                'search_query': query,
                                'match_status': 'not_found'
                            }
                        else:
                            logger.warning(f"Find Place API error: {data.get('status')}")
                            return None
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                delay = self.backoff.get_delay(attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
        
        return None
    
    async def get_place_details(self,
                                place_id: str,
                                fields: List[str] = None) -> Optional[Dict]:
        """Async get detailed information for a place"""
        if not place_id:
            return None
            
        if fields is None:
            fields = DEFAULT_PLACE_DETAILS_FIELDS
        
        await self.rate_limiter.wait()
        
        url = f"{self.base_url}/details/json"
        params = self._get_params(
            place_id=place_id,
            fields=','.join(fields)
        )
        
        for attempt in range(rate_limit_config.MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT)
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        if data.get('status') == 'OK':
                            result = data.get('result', {})
                            result['place_id'] = place_id
                            return result
                        else:
                            logger.warning(f"Place Details API error: {data.get('status')}")
                            return None
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                delay = self.backoff.get_delay(attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
        
        return None
    
    async def batch_find_places(self,
                                records: List[Dict],
                                max_concurrent: int = None) -> List[Dict]:
        """
        Async batch find place IDs with concurrency control
        
        Args:
            records: List of records with business info
            max_concurrent: Max concurrent requests
            
        Returns:
            List of results with place_ids
        """
        if max_concurrent is None:
            max_concurrent = google_places_config.CONCURRENT_REQUESTS
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def find_with_semaphore(record: Dict) -> Dict:
            async with semaphore:
                # Extract fields from polished data format
                business_name = record.get('socrata_business_name', '') or record.get('taxpayer_name', '')
                address = record.get('socrata_taxpayer_address', '') or record.get('taxpayer_address', '')
                city = record.get('socrata_taxpayer_city', '') or record.get('taxpayer_city', '')
                state = record.get('socrata_taxpayer_state', '') or record.get('taxpayer_state', 'TX')
                zip_code = record.get('socrata_taxpayer_zip', '') or record.get('taxpayer_zip', '')
                taxpayer_id = record.get('taxpayer_number', '') or record.get('taxpayer_id', '')
                
                result = await self.find_place(
                    business_name=business_name,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code
                )
                
                if result:
                    result['taxpayer_id'] = taxpayer_id
                    return result
                else:
                    return {
                        'taxpayer_id': taxpayer_id,
                        'place_id': None,
                        'search_query': f"{business_name} {address} {city} {state} {zip_code}".strip(),
                        'match_status': 'error'
                    }
        
        tasks = [find_with_semaphore(record) for record in records]
        results = await asyncio.gather(*tasks)
        
        return list(results)
    
    async def batch_get_details(self,
                                place_ids_data: List[Dict],
                                fields: List[str] = None,
                                max_concurrent: int = None) -> List[Dict]:
        """
        Async batch get place details with concurrency control
        
        Args:
            place_ids_data: List of dicts with place_id and taxpayer_id
            fields: Fields to request
            max_concurrent: Max concurrent requests
            
        Returns:
            List of place details
        """
        if max_concurrent is None:
            max_concurrent = google_places_config.CONCURRENT_REQUESTS
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_with_semaphore(data: Dict) -> Dict:
            async with semaphore:
                place_id = data.get('place_id')
                taxpayer_id = data.get('taxpayer_id')
                
                if not place_id:
                    return {
                        'taxpayer_id': taxpayer_id,
                        'place_id': None,
                        'details_status': 'no_place_id'
                    }
                
                result = await self.get_place_details(place_id, fields)
                
                if result:
                    result['taxpayer_id'] = taxpayer_id
                    result['details_status'] = 'success'
                    return result
                else:
                    return {
                        'taxpayer_id': taxpayer_id,
                        'place_id': place_id,
                        'details_status': 'error'
                    }
        
        tasks = [get_with_semaphore(data) for data in place_ids_data]
        results = await asyncio.gather(*tasks)
        
        return list(results)
