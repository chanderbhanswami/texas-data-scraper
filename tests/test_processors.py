"""
Unit tests for data processors
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.data_combiner import DataCombiner
from src.processors.deduplicator import Deduplicator


class TestDataCombiner:
    """Test data combiner"""
    
    @pytest.fixture
    def combiner(self):
        """Create combiner instance"""
        return DataCombiner()
    
    @pytest.fixture
    def sample_socrata_data(self):
        """Sample Socrata data"""
        return [
            {'taxpayer_id': '123', 'name': 'Company A', 'city': 'Austin'},
            {'taxpayer_id': '456', 'name': 'Company B', 'city': 'Dallas'}
        ]
    
    @pytest.fixture
    def sample_comptroller_data(self):
        """Sample Comptroller data"""
        return [
            {'taxpayer_id': '123', 'status': 'Active', 'year': '2024'},
            {'taxpayer_id': '789', 'status': 'Inactive', 'year': '2023'}
        ]
    
    def test_combiner_initialization(self, combiner):
        """Test combiner initializes"""
        assert combiner is not None
    
    def test_combine_by_taxpayer_id(self, combiner, sample_socrata_data, 
                                     sample_comptroller_data):
        """Test data combination"""
        combined = combiner.combine_by_taxpayer_id(
            sample_socrata_data,
            sample_comptroller_data
        )
        
        assert combined is not None
        assert isinstance(combined, list)
        assert len(combined) == 3  # All unique taxpayer IDs
    
    def test_get_combination_stats(self, combiner, sample_socrata_data,
                                    sample_comptroller_data):
        """Test statistics generation"""
        combined = combiner.combine_by_taxpayer_id(
            sample_socrata_data,
            sample_comptroller_data
        )
        
        stats = combiner.get_combination_stats(combined)
        
        assert 'total_records' in stats
        assert 'with_socrata_data' in stats
        assert 'with_comptroller_data' in stats
        assert stats['total_records'] == 3


class TestDeduplicator:
    """Test deduplicator"""
    
    @pytest.fixture
    def deduplicator(self):
        """Create deduplicator instance"""
        return Deduplicator()
    
    @pytest.fixture
    def sample_data_with_duplicates(self):
        """Sample data with duplicates"""
        return [
            {'taxpayer_id': '123', 'name': 'Company A'},
            {'taxpayer_id': '456', 'name': 'Company B'},
            {'taxpayer_id': '123', 'name': 'Company A Duplicate'},
            {'taxpayer_id': '789', 'name': 'Company C'}
        ]
    
    def test_deduplicator_initialization(self, deduplicator):
        """Test deduplicator initializes"""
        assert deduplicator is not None
        assert deduplicator.strategy == 'taxpayer_id'
    
    def test_deduplicate_by_taxpayer_id(self, deduplicator, 
                                         sample_data_with_duplicates):
        """Test deduplication"""
        unique, duplicates = deduplicator.deduplicate(sample_data_with_duplicates)
        
        assert len(unique) == 3  # Only unique taxpayer IDs
        assert len(duplicates) == 1  # One duplicate found
    
    def test_get_duplicate_groups(self, deduplicator, sample_data_with_duplicates):
        """Test duplicate grouping"""
        groups = deduplicator.get_duplicate_groups(sample_data_with_duplicates)
        
        assert '123' in groups  # Taxpayer ID with duplicates
        assert len(groups['123']) == 2  # Two records with same ID
    
    def test_deduplication_stats(self, deduplicator):
        """Test statistics calculation"""
        stats = deduplicator.get_deduplication_stats(100, 80, 20)
        
        assert stats['original_count'] == 100
        assert stats['unique_count'] == 80
        assert stats['duplicate_count'] == 20
        assert stats['deduplication_rate'] == 20.0


class TestOutletEnricher:
    """Test outlet enricher (v1.4.0)"""
    
    @pytest.fixture
    def enricher(self):
        """Create enricher instance"""
        from src.processors.outlet_enricher import OutletEnricher
        return OutletEnricher()
    
    @pytest.fixture
    def sample_socrata_data(self):
        """Sample Socrata data with multiple outlets"""
        return [
            {
                'taxpayer_id': '123',
                'taxpayer_name': 'Company A',
                'outlet_number': '001',
                'outlet_address': '100 Main St',
                'outlet_city': 'Austin',
                'outlet_naics_code': '722511'
            },
            {
                'taxpayer_id': '123',
                'taxpayer_name': 'Company A',
                'outlet_number': '002',
                'outlet_address': '200 Oak Ave',
                'outlet_city': 'Dallas',
                'outlet_naics_code': '722511'
            },
            {
                'taxpayer_id': '456',
                'taxpayer_name': 'Company B',
                'outlet_number': '001',
                'outlet_address': '300 Elm St',
                'outlet_city': 'Houston',
                'outlet_naics_code': '445110'
            }
        ]
    
    @pytest.fixture
    def sample_deduplicated_data(self):
        """Sample deduplicated data"""
        return [
            {'taxpayer_id': '123', 'taxpayer_name': 'Company A'},
            {'taxpayer_id': '456', 'taxpayer_name': 'Company B'}
        ]
    
    def test_enricher_initialization(self, enricher):
        """Test enricher initializes"""
        assert enricher is not None
    
    def test_extract_outlets(self, enricher, sample_socrata_data):
        """Test outlet extraction from Socrata data"""
        outlets = enricher.extract_outlets(sample_socrata_data)
        
        assert outlets is not None
        assert isinstance(outlets, dict)
        assert '123' in outlets
        assert len(outlets['123']) == 2  # Two outlets for taxpayer 123
        assert len(outlets['456']) == 1  # One outlet for taxpayer 456
    
    def test_enrich_with_outlets(self, enricher, sample_socrata_data, 
                                  sample_deduplicated_data):
        """Test enrichment of deduplicated data with outlets"""
        outlets = enricher.extract_outlets(sample_socrata_data)
        enriched = enricher.enrich_with_outlets(sample_deduplicated_data, outlets)
        
        assert enriched is not None
        assert len(enriched) == 2
        
        # Check that outlets were added
        company_a = next(r for r in enriched if r['taxpayer_id'] == '123')
        assert 'outlets' in company_a
        assert len(company_a['outlets']) == 2
    
    def test_outlet_fields_extracted(self, enricher, sample_socrata_data):
        """Test that correct outlet fields are extracted"""
        outlets = enricher.extract_outlets(sample_socrata_data)
        
        outlet = outlets['123'][0]
        assert 'outlet_number' in outlet
        assert 'outlet_address' in outlet
        assert 'outlet_city' in outlet
        assert 'outlet_naics_code' in outlet


class TestAdvancedOutletEnricher:
    """Test advanced outlet enricher with GPU support (v1.4.0)"""
    
    @pytest.fixture
    def enricher(self):
        """Create advanced enricher instance"""
        from src.processors.outlet_enricher import AdvancedOutletEnricher
        return AdvancedOutletEnricher(use_gpu=False)
    
    def test_advanced_enricher_initialization(self, enricher):
        """Test advanced enricher initializes"""
        assert enricher is not None
        assert enricher.gpu is not None
    
    def test_enricher_stats(self, enricher):
        """Test statistics retrieval"""
        stats = enricher.get_enricher_stats()
        
        assert 'gpu_enabled' in stats
        assert stats['gpu_enabled'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])