"""
Unit tests for Socrata API client
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.socrata_client import SocrataClient
from config.settings import socrata_config


class TestSocrataClient:
    """Test Socrata API client"""
    
    @pytest.fixture
    def client(self):
        """Create client instance"""
        return SocrataClient()
    
    def test_client_initialization(self, client):
        """Test client initializes correctly"""
        assert client is not None
        assert client.base_url == socrata_config.BASE_URL
        assert client.app_token == socrata_config.APP_TOKEN
    
    def test_get_headers(self, client):
        """Test header generation"""
        headers = client._get_headers()
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        
        if socrata_config.has_token:
            assert 'X-App-Token' in headers
    
    def test_build_url(self, client):
        """Test URL building"""
        url = client._build_url('test-dataset')
        assert url.endswith('test-dataset.json')
    
    @pytest.mark.skipif(not socrata_config.has_token, 
                       reason="Requires Socrata API token")
    def test_get_franchise_tax(self, client):
        """Test franchise tax data retrieval"""
        data = client.get_franchise_tax_holders(limit=5)
        assert data is not None
        assert isinstance(data, list)
        assert len(data) <= 5
    
    @pytest.mark.skipif(not socrata_config.has_token,
                       reason="Requires Socrata API token")
    def test_search_by_city(self, client):
        """Test search by city"""
        data = client.search_by_city("Austin", limit=5)
        assert data is not None
        assert isinstance(data, list)
    
    def test_rate_limiter_stats(self, client):
        """Test rate limiter statistics"""
        stats = client.rate_limiter.get_stats()
        assert 'requests_made' in stats
        assert 'max_requests' in stats
        assert 'requests_remaining' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])