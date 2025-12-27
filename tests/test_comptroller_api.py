"""
Unit tests for Comptroller API client
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.comptroller_client import ComptrollerClient
from config.settings import comptroller_config


class TestComptrollerClient:
    """Test Comptroller API client"""
    
    @pytest.fixture
    def client(self):
        """Create client instance"""
        return ComptrollerClient()
    
    def test_client_initialization(self, client):
        """Test client initializes correctly"""
        assert client is not None
        assert client.base_url == comptroller_config.BASE_URL
        assert client.api_key == comptroller_config.API_KEY
    
    def test_get_headers(self, client):
        """Test header generation"""
        headers = client._get_headers()
        assert 'User-Agent' in headers
        assert 'Accept' in headers
        
        if comptroller_config.has_api_key:
            assert 'Authorization' in headers
    
    @pytest.mark.skipif(not comptroller_config.has_api_key,
                       reason="Requires Comptroller API key")
    def test_get_franchise_tax_details(self, client):
        """Test franchise tax details retrieval"""
        # Test with a non-existent ID (should return None gracefully)
        details = client.get_franchise_tax_details("99999999999")
        assert details is None or isinstance(details, dict)
    
    @pytest.mark.skipif(not comptroller_config.has_api_key,
                       reason="Requires Comptroller API key")
    def test_get_franchise_tax_list(self, client):
        """Test franchise tax list retrieval"""
        results = client.get_franchise_tax_list(name="TEST")
        assert isinstance(results, list)
    
    def test_rate_limiter_stats(self, client):
        """Test rate limiter statistics"""
        stats = client.rate_limiter.get_stats()
        assert 'requests_made' in stats
        assert 'max_requests' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])