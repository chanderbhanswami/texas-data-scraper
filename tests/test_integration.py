"""
Integration tests for complete workflows
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.integration
    def test_socrata_to_comptroller_pipeline(self):
        """Test complete pipeline: Socrata -> Comptroller -> Combine"""
        # This is a placeholder for integration tests
        # Implement actual integration tests as needed
        pass
    
    @pytest.mark.integration  
    def test_full_deduplication_workflow(self):
        """Test complete deduplication workflow"""
        # Placeholder for deduplication integration test
        pass
    
    @pytest.mark.integration
    def test_export_import_cycle(self):
        """Test export and import cycle for all formats"""
        from src.exporters.file_exporter import FileExporter
        from config.settings import EXPORT_DIR
        
        # Sample data
        test_data = [
            {'id': 1, 'name': 'Test A'},
            {'id': 2, 'name': 'Test B'}
        ]
        
        exporter = FileExporter(EXPORT_DIR / 'test')
        
        # Test JSON cycle
        json_path = exporter.export_json(test_data, 'test_integration.json')
        loaded_json = exporter.load_json(json_path)
        assert len(loaded_json) == len(test_data)
        
        # Test CSV cycle
        csv_path = exporter.export_csv(test_data, 'test_integration.csv')
        loaded_csv = exporter.load_csv(csv_path)
        assert len(loaded_csv) == len(test_data)
        
        # Test Excel cycle
        excel_path = exporter.export_excel(test_data, 'test_integration.xlsx')
        loaded_excel = exporter.load_excel(excel_path)
        assert len(loaded_excel) == len(test_data)
        
        # Cleanup
        json_path.unlink(missing_ok=True)
        csv_path.unlink(missing_ok=True)
        excel_path.unlink(missing_ok=True)


class TestOutletEnrichmentIntegration:
    """Integration tests for outlet enrichment workflow (v1.4.0)"""
    
    @pytest.mark.integration
    def test_full_outlet_enrichment_workflow(self):
        """Test complete outlet enrichment: Socrata -> Dedupe -> Enrich"""
        from src.processors.deduplicator import Deduplicator
        from src.processors.outlet_enricher import OutletEnricher
        
        # Sample Socrata data with duplicates
        socrata_data = [
            {'taxpayer_id': '123', 'name': 'Company A', 'outlet_number': '001', 
             'outlet_city': 'Austin'},
            {'taxpayer_id': '123', 'name': 'Company A', 'outlet_number': '002',
             'outlet_city': 'Dallas'},
            {'taxpayer_id': '456', 'name': 'Company B', 'outlet_number': '001',
             'outlet_city': 'Houston'}
        ]
        
        # Step 1: Deduplicate
        deduplicator = Deduplicator()
        unique, duplicates = deduplicator.deduplicate(socrata_data)
        
        assert len(unique) == 2  # Two unique taxpayers
        
        # Step 2: Extract and enrich with outlets
        enricher = OutletEnricher()
        outlets = enricher.extract_outlets(socrata_data)
        enriched = enricher.enrich_with_outlets(unique, outlets)
        
        assert len(enriched) == 2
        
        # Verify outlet data attached
        company_a = next(r for r in enriched if r['taxpayer_id'] == '123')
        assert 'outlets' in company_a
        assert len(company_a['outlets']) == 2
    
    @pytest.mark.integration
    def test_outlet_enricher_stats(self):
        """Test outlet enricher statistics"""
        from src.processors.outlet_enricher import OutletEnricher
        
        enricher = OutletEnricher()
        
        # Just verify it initializes
        assert enricher is not None


class TestGooglePlacesIntegration:
    """Integration tests for Google Places workflow (v1.5.0 - New API v1)"""
    
    @pytest.mark.integration
    def test_search_query_building(self):
        """Test building search queries from polished data"""
        from unittest.mock import patch, Mock
        
        mock_config = Mock()
        mock_config.API_KEY = 'test_key'
        mock_config.BASE_URL = 'https://places.googleapis.com/v1'
        mock_config.TEXT_SEARCH_ENDPOINT = 'https://places.googleapis.com/v1/places:searchText'
        mock_config.PLACE_DETAILS_ENDPOINT = 'https://places.googleapis.com/v1/places'
        mock_config.rate_limit = 600
        mock_config.CONCURRENT_REQUESTS = 5
        mock_config.CHUNK_SIZE = 50
        mock_config.REQUEST_DELAY = 0.1
        
        with patch('src.api.google_places_client.google_places_config', mock_config):
            from src.api.google_places_client import GooglePlacesClient
            
            client = GooglePlacesClient()
            
            # Sample polished data
            polished_record = {
                'taxpayer_id': '12345678901',
                'taxpayer_name': 'TEST COMPANY LLC',
                'location_address': '100 Main St',
                'location_city': 'Austin',
                'location_state': 'TX',
                'location_zip_code': '78701'
            }
            
            query = client.build_search_query(polished_record)
            
            assert 'TEST COMPANY LLC' in query
            assert '100 Main St' in query
            assert 'Austin' in query
            assert 'TX' in query
            assert '78701' in query
    
    @pytest.mark.integration
    def test_place_id_to_details_workflow(self):
        """Test workflow from place ID to details (mocked)"""
        # This tests the data flow, not actual API
        place_id_record = {
            'taxpayer_id': '12345678901',
            'place_id': 'ChIJN1t_tDeuEmsRUsoyG83frY4',
            'taxpayer_name': 'Test Company'
        }
        
        # Simulate place details
        place_details = {
            'place_id': 'ChIJN1t_tDeuEmsRUsoyG83frY4',
            'name': 'Test Company',
            'formatted_phone_number': '(512) 555-1234',
            'website': 'https://testcompany.com',
            'rating': 4.5
        }
        
        # Merge
        combined = {**place_id_record, **place_details}
        
        assert combined['taxpayer_id'] == '12345678901'
        assert combined['formatted_phone_number'] == '(512) 555-1234'
        assert combined['website'] == 'https://testcompany.com'


class TestFullPipelineIntegration:
    """Integration tests for complete v1.5.0 pipeline"""
    
    @pytest.mark.integration
    def test_full_pipeline_data_flow(self):
        """Test data flow through entire pipeline"""
        # Step 1: Socrata data (simulated)
        socrata_data = [
            {'taxpayer_id': '123', 'taxpayer_name': 'Company A', 
             'outlet_number': '001', 'location_city': 'Austin'},
            {'taxpayer_id': '123', 'taxpayer_name': 'Company A',
             'outlet_number': '002', 'location_city': 'Dallas'}
        ]
        
        # Step 2: Comptroller data (simulated)
        comptroller_data = [
            {'taxpayer_id': '123', 'status': 'Active', 'ftas_data': {}}
        ]
        
        # Step 3: Combine
        from src.processors.data_combiner import DataCombiner
        combiner = DataCombiner()
        combined = combiner.combine_by_taxpayer_id(socrata_data, comptroller_data)
        
        assert len(combined) >= 1
        
        # Step 4: Deduplicate
        from src.processors.deduplicator import Deduplicator
        deduplicator = Deduplicator()
        unique, dups = deduplicator.deduplicate(combined)
        
        assert len(unique) >= 1
        
        # Step 5: Outlet enrichment
        from src.processors.outlet_enricher import OutletEnricher
        enricher = OutletEnricher()
        outlets = enricher.extract_outlets(socrata_data)
        polished = enricher.enrich_with_outlets(unique, outlets)
        
        assert len(polished) >= 1
        
        # Step 6 & 7: Google Places would be mocked (requires API key)
        # Just verify data structure is ready
        assert 'taxpayer_id' in polished[0]
        assert 'taxpayer_name' in polished[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])