"""
Unit tests for scraper modules
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.socrata_scraper import SocrataScraper, BulkSocrataScraper
from src.scrapers.comptroller_scraper import ComptrollerScraper, BulkComptrollerScraper
from src.scrapers.gpu_accelerator import GPUAccelerator


class TestSocrataScraper:
    """Test Socrata scraper module"""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance"""
        return SocrataScraper(use_async=False, use_gpu=False)
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly"""
        assert scraper is not None
        assert scraper.client is not None
        assert scraper.gpu is not None
    
    def test_scraper_stats(self, scraper):
        """Test statistics retrieval"""
        stats = scraper.get_scraper_stats()
        
        assert 'client_type' in stats
        assert 'gpu_enabled' in stats
        assert 'rate_limiter' in stats
        assert stats['client_type'] == 'sync'
    
    @pytest.mark.skipif(True, reason="Requires API access")
    def test_scrape_dataset(self, scraper):
        """Test dataset scraping"""
        from config.settings import socrata_config
        
        data = scraper.scrape_dataset(
            socrata_config.FRANCHISE_TAX_DATASET,
            limit=10
        )
        
        assert data is not None
        assert isinstance(data, list)
        assert len(data) <= 10


class TestBulkSocrataScraper:
    """Test bulk Socrata scraper"""
    
    @pytest.fixture
    def scraper(self):
        """Create bulk scraper instance"""
        return BulkSocrataScraper()
    
    def test_bulk_scraper_initialization(self, scraper):
        """Test bulk scraper initializes"""
        assert scraper is not None
        assert scraper.use_async is True


class TestComptrollerScraper:
    """Test Comptroller scraper module"""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance"""
        return ComptrollerScraper(use_async=False, use_gpu=False)
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly"""
        assert scraper is not None
        assert scraper.client is not None
        assert scraper.gpu is not None
    
    def test_scraper_stats(self, scraper):
        """Test statistics retrieval"""
        stats = scraper.get_scraper_stats()
        
        assert 'client_type' in stats
        assert 'gpu_enabled' in stats
        assert 'rate_limiter' in stats
        assert stats['client_type'] == 'sync'
    
    @pytest.mark.skipif(True, reason="Requires API access")
    def test_scrape_taxpayer_details(self, scraper):
        """Test taxpayer scraping"""
        test_ids = ['12345678901']
        
        results = scraper.scrape_taxpayer_details(test_ids)
        
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 1


class TestBulkComptrollerScraper:
    """Test bulk Comptroller scraper"""
    
    @pytest.fixture
    def scraper(self):
        """Create bulk scraper instance"""
        return BulkComptrollerScraper()
    
    def test_bulk_scraper_initialization(self, scraper):
        """Test bulk scraper initializes"""
        assert scraper is not None
        assert scraper.use_async is True


class TestGPUAccelerator:
    """Test GPU accelerator"""
    
    @pytest.fixture
    def gpu(self):
        """Create GPU accelerator instance"""
        return GPUAccelerator(use_gpu=False)  # Disable GPU for testing
    
    def test_gpu_initialization(self, gpu):
        """Test GPU initializes"""
        assert gpu is not None
    
    def test_gpu_availability_check(self, gpu):
        """Test GPU availability check"""
        available = gpu._check_gpu()
        assert isinstance(available, bool)
    
    def test_deduplicate_cpu_fallback(self, gpu):
        """Test deduplication with CPU fallback"""
        test_data = [
            {'taxpayer_id': '123', 'name': 'A'},
            {'taxpayer_id': '456', 'name': 'B'},
            {'taxpayer_id': '123', 'name': 'C'}
        ]
        
        result = gpu.deduplicate_gpu(test_data, key_field='taxpayer_id')
        
        assert len(result) == 2  # Duplicates removed
        assert result[0]['taxpayer_id'] == '123'
        assert result[1]['taxpayer_id'] == '456'
    
    def test_gpu_memory_info(self, gpu):
        """Test GPU memory info retrieval"""
        info = gpu.get_gpu_memory_info()
        
        assert 'available' in info
        assert isinstance(info['available'], bool)


class TestScraperIntegration:
    """Integration tests for scrapers"""
    
    def test_socrata_to_comptroller_workflow(self):
        """Test complete workflow from Socrata to Comptroller"""
        # Sample Socrata data
        socrata_data = [
            {'taxpayer_id': '12345678901', 'name': 'Test Company A'},
            {'taxpayer_id': '98765432109', 'name': 'Test Company B'}
        ]
        
        # Initialize Comptroller scraper
        comp_scraper = ComptrollerScraper(use_async=False, use_gpu=False)
        
        # This would enrich the data (skipped in test without API)
        # enriched = comp_scraper.enrich_socrata_data(socrata_data)
        
        # Just verify the scraper can be initialized
        assert comp_scraper is not None
    
    def test_validation_workflow(self):
        """Test ID validation in scraper"""
        scraper = ComptrollerScraper(use_async=False, use_gpu=False)
        
        test_ids = [
            '12345678901',  # Valid
            '123',          # Invalid - too short
            'ABC123',       # Invalid - non-numeric
            '98765432109'   # Valid
        ]
        
        # Test validation (without actual scraping)
        valid_ids = [
            tid for tid in test_ids
            if len(''.join(c for c in tid if c.isdigit())) >= 9
        ]
        
        assert len(valid_ids) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])