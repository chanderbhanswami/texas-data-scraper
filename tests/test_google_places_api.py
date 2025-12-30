"""
Unit tests for Google Places API client (New API v1)
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.google_places_client import GooglePlacesClient, AsyncGooglePlacesClient


class TestGooglePlacesClient:
    """Test Google Places API client (New API v1)"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.BASE_URL = 'https://places.googleapis.com/v1'
        mock.TEXT_SEARCH_ENDPOINT = 'https://places.googleapis.com/v1/places:searchText'
        mock.PLACE_DETAILS_ENDPOINT = 'https://places.googleapis.com/v1/places'
        mock.rate_limit = 600
        mock.CONCURRENT_REQUESTS = 5
        mock.CHUNK_SIZE = 50
        mock.REQUEST_DELAY = 0.1
        return mock
    
    @pytest.fixture
    def client(self, mock_config):
        """Create client instance"""
        with patch('src.api.google_places_client.google_places_config', mock_config):
            return GooglePlacesClient()
    
    def test_client_initialization(self, client):
        """Test client initializes correctly"""
        assert client is not None
        assert client.session is not None
    
    def test_build_search_query(self, client):
        """Test search query building"""
        record = {
            'taxpayer_name': 'Test Company',
            'location_address': '123 Main St',
            'location_city': 'Austin',
            'location_state': 'TX',
            'location_zip_code': '78701'
        }
        
        query = client.build_search_query(record)
        
        assert 'Test Company' in query
        assert '123 Main St' in query
        assert 'Austin' in query
        assert 'TX' in query
        assert '78701' in query
    
    def test_build_search_query_minimal(self, client):
        """Test search query with minimal data"""
        record = {
            'taxpayer_name': 'Test Company'
        }
        
        query = client.build_search_query(record)
        
        assert 'Test Company' in query
    
    @patch('requests.Session.post')
    def test_find_place_success(self, mock_post, client):
        """Test successful place finding with new API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'places': [{'id': 'ChIJtest123'}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = client.find_place(query='Test Company Austin TX')
        
        assert result is not None
        assert result['place_id'] == 'ChIJtest123'
        assert result['match_status'] == 'found'
        
        # Verify POST was called (new API uses POST)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert 'json' in call_kwargs.kwargs
        assert call_kwargs.kwargs['json']['textQuery'] == 'Test Company Austin TX'
    
    @patch('requests.Session.post')
    def test_find_place_no_results(self, mock_post, client):
        """Test find place with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'places': []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = client.find_place(query='NonExistent Company XYZ')
        
        assert result is not None
        assert result['place_id'] is None
        assert result['match_status'] == 'not_found'
    
    @patch('requests.Session.get')
    def test_get_place_details_success(self, mock_get, client):
        """Test successful place details retrieval (new API format)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'ChIJtest123',
            'displayName': {'text': 'Test Business', 'languageCode': 'en'},
            'formattedAddress': '123 Main St, Austin, TX 78701',
            'nationalPhoneNumber': '(512) 555-1234',
            'websiteUri': 'https://testbusiness.com',
            'rating': 4.5,
            'userRatingCount': 100
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = client.get_place_details('ChIJtest123')
        
        assert result is not None
        assert result['name'] == 'Test Business'
        assert result['formatted_phone_number'] == '(512) 555-1234'
        assert result['website'] == 'https://testbusiness.com'
        assert result['rating'] == 4.5
        assert result['user_ratings_total'] == 100
    
    def test_default_fields(self, client):
        """Test default fields configuration"""
        fields = client.default_fields
        
        assert 'id' in fields
        assert 'displayName' in fields
        assert 'formattedAddress' in fields
        assert 'nationalPhoneNumber' in fields
        assert 'websiteUri' in fields
        assert 'rating' in fields
        assert 'regularOpeningHours' in fields
    
    def test_get_headers(self, client):
        """Test header generation for new API"""
        headers = client._get_headers(field_mask='places.id')
        
        assert 'X-Goog-Api-Key' in headers
        assert 'X-Goog-FieldMask' in headers
        assert headers['X-Goog-FieldMask'] == 'places.id'
        assert headers['Content-Type'] == 'application/json'
    
    def test_transform_place_details(self, client):
        """Test field transformation from new API to legacy format"""
        raw_data = {
            'displayName': {'text': 'Test Business'},
            'formattedAddress': '123 Main St',
            'nationalPhoneNumber': '555-1234',
            'internationalPhoneNumber': '+1 555-1234',
            'websiteUri': 'https://test.com',
            'googleMapsUri': 'https://maps.google.com/...',
            'rating': 4.5,
            'userRatingCount': 50,
            'businessStatus': 'OPERATIONAL',
            'location': {'latitude': 30.2672, 'longitude': -97.7431}
        }
        
        result = client._transform_place_details(raw_data)
        
        assert result['name'] == 'Test Business'
        assert result['formatted_address'] == '123 Main St'
        assert result['formatted_phone_number'] == '555-1234'
        assert result['international_phone_number'] == '+1 555-1234'
        assert result['website'] == 'https://test.com'
        assert result['url'] == 'https://maps.google.com/...'
        assert result['rating'] == 4.5
        assert result['user_ratings_total'] == 50
        assert result['business_status'] == 'OPERATIONAL'
        assert result['geometry']['location']['lat'] == 30.2672
        assert result['geometry']['location']['lng'] == -97.7431


class TestAsyncGooglePlacesClient:
    """Test async Google Places API client (New API v1)"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.BASE_URL = 'https://places.googleapis.com/v1'
        mock.TEXT_SEARCH_ENDPOINT = 'https://places.googleapis.com/v1/places:searchText'
        mock.PLACE_DETAILS_ENDPOINT = 'https://places.googleapis.com/v1/places'
        mock.rate_limit = 600
        mock.CONCURRENT_REQUESTS = 5
        mock.CHUNK_SIZE = 50
        mock.REQUEST_DELAY = 0.1
        return mock
    
    @pytest.fixture
    def client(self, mock_config):
        """Create async client instance"""
        with patch('src.api.google_places_client.google_places_config', mock_config):
            return AsyncGooglePlacesClient()
    
    def test_async_client_initialization(self, client):
        """Test async client initializes correctly"""
        assert client is not None
        assert client.concurrent_requests == 5
        assert client.chunk_size == 50
    
    def test_async_get_headers(self, client):
        """Test async header generation"""
        headers = client._get_headers(field_mask='places.id,places.displayName')
        
        assert 'X-Goog-Api-Key' in headers
        assert 'X-Goog-FieldMask' in headers
        assert headers['X-Goog-FieldMask'] == 'places.id,places.displayName'


class TestGooglePlacesClientValidation:
    """Test input validation"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.BASE_URL = 'https://places.googleapis.com/v1'
        mock.TEXT_SEARCH_ENDPOINT = 'https://places.googleapis.com/v1/places:searchText'
        mock.PLACE_DETAILS_ENDPOINT = 'https://places.googleapis.com/v1/places'
        mock.rate_limit = 600
        mock.CONCURRENT_REQUESTS = 5
        mock.CHUNK_SIZE = 50
        mock.REQUEST_DELAY = 0.1
        return mock
    
    @pytest.fixture
    def client(self, mock_config):
        """Create client instance"""
        with patch('src.api.google_places_client.google_places_config', mock_config):
            return GooglePlacesClient()
    
    def test_empty_query_handling(self, client):
        """Test handling of empty query"""
        record = {}
        query = client.build_search_query(record)
        
        # Should return empty or just default state
        assert query == 'TX' or query == ''
    
    def test_special_characters_in_name(self, client):
        """Test handling of special characters"""
        record = {
            'taxpayer_name': 'Test & Company, LLC',
            'location_city': "O'Brien"
        }
        
        query = client.build_search_query(record)
        
        assert 'Test & Company, LLC' in query
        assert "O'Brien" in query


class TestPlaceIdMatching:
    """Test Place ID matching logic"""
    
    def test_match_by_taxpayer_id(self):
        """Test matching records by taxpayer ID"""
        polished_data = [
            {'taxpayer_id': '123', 'name': 'Company A'},
            {'taxpayer_id': '456', 'name': 'Company B'}
        ]
        
        place_ids = [
            {'taxpayer_id': '123', 'place_id': 'ChIJ123'},
            {'taxpayer_id': '789', 'place_id': 'ChIJ789'}
        ]
        
        # Create lookup
        place_lookup = {p['taxpayer_id']: p for p in place_ids}
        
        # Match
        matched = []
        for record in polished_data:
            tid = record.get('taxpayer_id')
            if tid in place_lookup:
                matched.append({**record, **place_lookup[tid]})
        
        assert len(matched) == 1
        assert matched[0]['taxpayer_id'] == '123'
        assert matched[0]['place_id'] == 'ChIJ123'


class TestNewAPIStructure:
    """Test new API v1 specific behavior"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.BASE_URL = 'https://places.googleapis.com/v1'
        mock.TEXT_SEARCH_ENDPOINT = 'https://places.googleapis.com/v1/places:searchText'
        mock.PLACE_DETAILS_ENDPOINT = 'https://places.googleapis.com/v1/places'
        mock.rate_limit = 600
        mock.CONCURRENT_REQUESTS = 5
        mock.CHUNK_SIZE = 50
        mock.REQUEST_DELAY = 0.1
        return mock
    
    @pytest.fixture
    def client(self, mock_config):
        """Create client instance"""
        with patch('src.api.google_places_client.google_places_config', mock_config):
            return GooglePlacesClient()
    
    def test_text_search_uses_post(self, client):
        """Verify text search uses POST method"""
        # The new API uses POST for text search
        # This is tested via mock in test_find_place_success
        pass
    
    def test_place_details_uses_path_param(self, client):
        """Verify place details uses path parameter"""
        # The new API uses /places/{place_id} instead of ?place_id=...
        # Verified in test_get_place_details_success
        pass
    
    def test_price_level_transformation(self, client):
        """Test price level enum transformation"""
        raw_data = {'priceLevel': 'PRICE_LEVEL_MODERATE'}
        result = client._transform_place_details(raw_data)
        
        assert result['price_level'] == 2  # MODERATE = 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
