"""
Google Places API Client (New API v1) for Business Data Enrichment
Sync and Async clients with rate limiting
Uses the new Places API endpoints (places.googleapis.com/v1)
"""
import requests
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Any
from src.api.rate_limiter import RateLimiter, AsyncRateLimiter, BackoffRetry
from src.utils.logger import get_logger
from config.settings import google_places_config, rate_limit_config, advanced_config

logger = get_logger(__name__)

# Default fields to request from Place Details API (new API field names)
DEFAULT_PLACE_DETAILS_FIELDS = [
    'id',
    'displayName',
    'formattedAddress',
    'nationalPhoneNumber',
    'internationalPhoneNumber',
    'websiteUri',
    'googleMapsUri',
    'rating',
    'userRatingCount',
    'businessStatus',
    'types',
    'regularOpeningHours',
    'location',
    'priceLevel',
    'reviews',
    'photos'
]

# Minimal fields for text search (step 1 - just need place ID)
TEXT_SEARCH_FIELDS = ['places.id']


class GooglePlacesClient:
    """Sync client for Google Places API (New API v1)"""
    
    def __init__(self):
        self.base_url = google_places_config.BASE_URL
        self.api_key = google_places_config.API_KEY
        self.rate_limiter = RateLimiter(
            max_requests=google_places_config.rate_limit,
            time_window=60  # Per minute
        )
        self.session = requests.Session()
        
        if not self.api_key:
            logger.warning("Google Places API key not configured")
    
    @property
    def default_fields(self) -> List[str]:
        """Return default fields for place details"""
        return DEFAULT_PLACE_DETAILS_FIELDS
    
    def _get_headers(self, field_mask: str = None) -> Dict:
        """Build request headers with API key and field mask"""
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key
        }
        if field_mask:
            headers['X-Goog-FieldMask'] = field_mask
        return headers
    
    def build_search_query(self, record: Dict) -> str:
        """
        Build search query from record data
        
        Args:
            record: Record with business info
            
        Returns:
            Search query string
        """
        # Extract fields from various data formats
        business_name = (
            record.get('taxpayer_name', '') or 
            record.get('socrata_business_name', '') or
            record.get('business_name', '')
        )
        address = (
            record.get('location_address', '') or
            record.get('taxpayer_address', '') or
            record.get('socrata_taxpayer_address', '')
        )
        city = (
            record.get('location_city', '') or
            record.get('taxpayer_city', '') or
            record.get('socrata_taxpayer_city', '')
        )
        state = (
            record.get('location_state', '') or
            record.get('taxpayer_state', '') or
            record.get('socrata_taxpayer_state', '') or
            'TX'
        )
        zip_code = (
            record.get('location_zip_code', '') or
            record.get('taxpayer_zip', '') or
            record.get('socrata_taxpayer_zip', '')
        )
        
        # Build query: Name + Address + City + State + Zip
        query_parts = [p for p in [business_name, address, city, state, zip_code] if p]
        return ' '.join(query_parts)
    
    def find_place(self, 
                   query: str = None,
                   business_name: str = '',
                   address: str = '',
                   city: str = '',
                   state: str = '',
                   zip_code: str = '') -> Optional[Dict]:
        """
        Find a place using Text Search (new API)
        
        Args:
            query: Full search query (if provided, other args ignored)
            business_name: Business name
            address: Street address
            city: City name
            state: State code (e.g., TX)
            zip_code: ZIP code
            
        Returns:
            Place info with place_id or None if not found
        """
        # Build search query if not provided
        if not query:
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
        
        if not query.strip():
            return None
        
        self.rate_limiter.wait()
        
        try:
            # New API: POST to /v1/places:searchText
            url = f"{self.base_url}/places:searchText"
            headers = self._get_headers(field_mask='places.id')
            
            body = {
                'textQuery': query
            }
            
            response = self.session.post(
                url, 
                json=body,
                headers=headers,
                timeout=rate_limit_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            # New API response format: { "places": [{"id": "..."}] }
            if data.get('places') and len(data['places']) > 0:
                place = data['places'][0]
                return {
                    'place_id': place.get('id'),
                    'search_query': query,
                    'match_status': 'found'
                }
            else:
                logger.debug(f"No results for query: {query}")
                return {
                    'place_id': None,
                    'search_query': query,
                    'match_status': 'not_found'
                }
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.debug(f"Bad request for query: {query}")
                return {
                    'place_id': None,
                    'search_query': query,
                    'match_status': 'not_found'
                }
            logger.error(f"HTTP error finding place: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error finding place: {e}")
            return None
    
    def get_place_details(self, 
                          place_id: str,
                          fields: List[str] = None) -> Optional[Dict]:
        """
        Get detailed information for a place (new API)
        
        Args:
            place_id: Google Place ID (e.g., ChIJ...)
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
            # New API: GET /v1/places/{place_id}
            url = f"{self.base_url}/places/{place_id}"
            field_mask = ','.join(fields)
            headers = self._get_headers(field_mask=field_mask)
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=rate_limit_config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform new API response to consistent format
            result = self._transform_place_details(data)
            result['place_id'] = place_id
            return result
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Place not found: {place_id}")
            else:
                logger.error(f"HTTP error getting place details: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting place details: {e}")
            return None
    
    def _transform_place_details(self, data: Dict) -> Dict:
        """
        Transform new API response to consistent field names
        
        Args:
            data: Raw API response
            
        Returns:
            Transformed data with consistent field names
        """
        result = {}
        
        # Map new API fields to legacy-compatible names
        if 'displayName' in data:
            result['name'] = data['displayName'].get('text', '')
        if 'formattedAddress' in data:
            result['formatted_address'] = data['formattedAddress']
        if 'nationalPhoneNumber' in data:
            result['formatted_phone_number'] = data['nationalPhoneNumber']
        if 'internationalPhoneNumber' in data:
            result['international_phone_number'] = data['internationalPhoneNumber']
        if 'websiteUri' in data:
            result['website'] = data['websiteUri']
        if 'googleMapsUri' in data:
            result['url'] = data['googleMapsUri']
        if 'rating' in data:
            result['rating'] = data['rating']
        if 'userRatingCount' in data:
            result['user_ratings_total'] = data['userRatingCount']
        if 'businessStatus' in data:
            result['business_status'] = data['businessStatus']
        if 'types' in data:
            result['types'] = data['types']
        if 'regularOpeningHours' in data:
            result['opening_hours'] = data['regularOpeningHours']
        if 'location' in data:
            result['geometry'] = {
                'location': {
                    'lat': data['location'].get('latitude'),
                    'lng': data['location'].get('longitude')
                }
            }
        if 'priceLevel' in data:
            # Map price level enum to number
            price_map = {
                'PRICE_LEVEL_FREE': 0,
                'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2,
                'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4
            }
            result['price_level'] = price_map.get(data['priceLevel'], None)
        if 'reviews' in data:
            result['reviews'] = data['reviews']
        if 'photos' in data:
            result['photos'] = data['photos']
        
        return result
    
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
            query = self.build_search_query(record)
            taxpayer_id = record.get('taxpayer_number', '') or record.get('taxpayer_id', '')
            
            result = self.find_place(query=query)
            
            if result:
                result['taxpayer_id'] = taxpayer_id
                results.append(result)
            else:
                results.append({
                    'taxpayer_id': taxpayer_id,
                    'place_id': None,
                    'search_query': query,
                    'match_status': 'error'
                })
        
        return results


class AsyncGooglePlacesClient:
    """Async client for Google Places API (New API v1)"""
    
    def __init__(self):
        self.base_url = google_places_config.BASE_URL
        self.api_key = google_places_config.API_KEY
        self.rate_limiter = AsyncRateLimiter(
            max_requests=google_places_config.rate_limit,
            time_window=60  # Per minute
        )
        self.backoff = BackoffRetry(
            max_retries=rate_limit_config.MAX_RETRIES,
            base_delay=rate_limit_config.RETRY_DELAY
        )
        self.concurrent_requests = google_places_config.CONCURRENT_REQUESTS
        self.chunk_size = google_places_config.CHUNK_SIZE
        
        if not self.api_key:
            logger.warning("Google Places API key not configured")
    
    def _get_headers(self, field_mask: str = None) -> Dict:
        """Build request headers with API key and field mask"""
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key
        }
        if field_mask:
            headers['X-Goog-FieldMask'] = field_mask
        return headers
    
    def build_search_query(self, record: Dict) -> str:
        """Build search query from record data"""
        business_name = (
            record.get('taxpayer_name', '') or 
            record.get('socrata_business_name', '') or
            record.get('business_name', '')
        )
        address = (
            record.get('location_address', '') or
            record.get('taxpayer_address', '') or
            record.get('socrata_taxpayer_address', '')
        )
        city = (
            record.get('location_city', '') or
            record.get('taxpayer_city', '') or
            record.get('socrata_taxpayer_city', '')
        )
        state = (
            record.get('location_state', '') or
            record.get('taxpayer_state', '') or
            record.get('socrata_taxpayer_state', '') or
            'TX'
        )
        zip_code = (
            record.get('location_zip_code', '') or
            record.get('taxpayer_zip', '') or
            record.get('socrata_taxpayer_zip', '')
        )
        
        query_parts = [p for p in [business_name, address, city, state, zip_code] if p]
        return ' '.join(query_parts)
    
    async def find_place(self,
                         query: str = None,
                         business_name: str = '',
                         address: str = '',
                         city: str = '',
                         state: str = '',
                         zip_code: str = '') -> Optional[Dict]:
        """Async find a place using Text Search (new API)"""
        # Build search query if not provided
        if not query:
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
        
        if not query.strip():
            return None
        
        await self.rate_limiter.wait()
        
        url = f"{self.base_url}/places:searchText"
        headers = self._get_headers(field_mask='places.id')
        body = {'textQuery': query}
        
        for attempt in range(rate_limit_config.MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=body,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 400:
                            return {
                                'place_id': None,
                                'search_query': query,
                                'match_status': 'not_found'
                            }
                        response.raise_for_status()
                        data = await response.json()
                        
                        if data.get('places') and len(data['places']) > 0:
                            place = data['places'][0]
                            return {
                                'place_id': place.get('id'),
                                'search_query': query,
                                'match_status': 'found'
                            }
                        else:
                            return {
                                'place_id': None,
                                'search_query': query,
                                'match_status': 'not_found'
                            }
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                delay = self.backoff.get_delay(attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
        
        return None
    
    async def get_place_details(self,
                                place_id: str,
                                fields: List[str] = None) -> Optional[Dict]:
        """Async get detailed information for a place (new API)"""
        if not place_id:
            return None
            
        if fields is None:
            fields = DEFAULT_PLACE_DETAILS_FIELDS
        
        await self.rate_limiter.wait()
        
        url = f"{self.base_url}/places/{place_id}"
        field_mask = ','.join(fields)
        headers = self._get_headers(field_mask=field_mask)
        
        for attempt in range(rate_limit_config.MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=rate_limit_config.REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 404:
                            logger.warning(f"Place not found: {place_id}")
                            return None
                        response.raise_for_status()
                        data = await response.json()
                        
                        result = self._transform_place_details(data)
                        result['place_id'] = place_id
                        return result
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                delay = self.backoff.get_delay(attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
        
        return None
    
    def _transform_place_details(self, data: Dict) -> Dict:
        """Transform new API response to consistent field names"""
        result = {}
        
        if 'displayName' in data:
            result['name'] = data['displayName'].get('text', '')
        if 'formattedAddress' in data:
            result['formatted_address'] = data['formattedAddress']
        if 'nationalPhoneNumber' in data:
            result['formatted_phone_number'] = data['nationalPhoneNumber']
        if 'internationalPhoneNumber' in data:
            result['international_phone_number'] = data['internationalPhoneNumber']
        if 'websiteUri' in data:
            result['website'] = data['websiteUri']
        if 'googleMapsUri' in data:
            result['url'] = data['googleMapsUri']
        if 'rating' in data:
            result['rating'] = data['rating']
        if 'userRatingCount' in data:
            result['user_ratings_total'] = data['userRatingCount']
        if 'businessStatus' in data:
            result['business_status'] = data['businessStatus']
        if 'types' in data:
            result['types'] = data['types']
        if 'regularOpeningHours' in data:
            result['opening_hours'] = data['regularOpeningHours']
        if 'location' in data:
            result['geometry'] = {
                'location': {
                    'lat': data['location'].get('latitude'),
                    'lng': data['location'].get('longitude')
                }
            }
        if 'priceLevel' in data:
            price_map = {
                'PRICE_LEVEL_FREE': 0,
                'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2,
                'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4
            }
            result['price_level'] = price_map.get(data['priceLevel'], None)
        if 'reviews' in data:
            result['reviews'] = data['reviews']
        if 'photos' in data:
            result['photos'] = data['photos']
        
        return result
    
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
            max_concurrent = self.concurrent_requests
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def find_with_semaphore(record: Dict) -> Dict:
            async with semaphore:
                query = self.build_search_query(record)
                taxpayer_id = record.get('taxpayer_number', '') or record.get('taxpayer_id', '')
                
                result = await self.find_place(query=query)
                
                if result:
                    result['taxpayer_id'] = taxpayer_id
                    return result
                else:
                    return {
                        'taxpayer_id': taxpayer_id,
                        'place_id': None,
                        'search_query': query,
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
            max_concurrent = self.concurrent_requests
        
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
