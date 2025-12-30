"""
Unit tests for Google Places API client
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.google_places_client import GooglePlacesClient, AsyncGooglePlacesClient


class TestGooglePlacesClient:
    """Test Google Places API client"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.FIND_PLACE_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        mock.PLACE_DETAILS_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
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
        
        assert query == 'Test Company'
    
    @patch('requests.Session.get')
    def test_find_place_success(self, mock_get, client):
        """Test successful place finding"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'OK',
            'candidates': [{'place_id': 'test_place_id_123'}]
        }
        mock_get.return_value = mock_response
        
        result = client.find_place('Test Company Austin TX')
        
        assert result is not None
        assert result['place_id'] == 'test_place_id_123'
    
    @patch('requests.Session.get')
    def test_find_place_no_results(self, mock_get, client):
        """Test find place with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ZERO_RESULTS',
            'candidates': []
        }
        mock_get.return_value = mock_response
        
        result = client.find_place('NonExistent Company XYZ')
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_get_place_details_success(self, mock_get, client):
        """Test successful place details retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'OK',
            'result': {
                'place_id': 'test_place_id_123',
                'name': 'Test Business',
                'formatted_phone_number': '(512) 555-1234',
                'website': 'https://testbusiness.com',
                'rating': 4.5
            }
        }
        mock_get.return_value = mock_response
        
        result = client.get_place_details('test_place_id_123')
        
        assert result is not None
        assert result['name'] == 'Test Business'
        assert result['formatted_phone_number'] == '(512) 555-1234'
        assert result['website'] == 'https://testbusiness.com'
        assert result['rating'] == 4.5
    
    def test_default_fields(self, client):
        """Test default fields configuration"""
        fields = client.default_fields
        
        assert 'name' in fields
        assert 'formatted_address' in fields
        assert 'formatted_phone_number' in fields
        assert 'website' in fields
        assert 'rating' in fields
        assert 'opening_hours' in fields


class TestAsyncGooglePlacesClient:
    """Test async Google Places API client"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.FIND_PLACE_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        mock.PLACE_DETAILS_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
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


class TestGooglePlacesClientValidation:
    """Test input validation"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config"""
        mock = Mock()
        mock.API_KEY = 'test_api_key'
        mock.FIND_PLACE_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        mock.PLACE_DETAILS_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
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
        
        assert query == ''
    
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
            {'taxpayer_id': '123', 'place_id': 'place_123'},
            {'taxpayer_id': '789', 'place_id': 'place_789'}
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
        assert matched[0]['place_id'] == 'place_123'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
