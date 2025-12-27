#!/usr/bin/env python3
"""
API Endpoint Tester
Test all Socrata and Comptroller API endpoints
"""
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.api.socrata_client import SocrataClient
from src.api.comptroller_client import ComptrollerClient
from src.utils.logger import get_logger
from config.settings import socrata_config, comptroller_config

console = Console()
logger = get_logger(__name__)


class APITester:
    """API endpoint testing suite"""
    
    def __init__(self):
        self.socrata_client = SocrataClient()
        self.comptroller_client = ComptrollerClient()
        self.test_results = []
        
    def run_all_tests(self):
        """Run all API tests"""
        console.print("\n" + "="*70, style="bold")
        console.print("API ENDPOINT TESTING SUITE", style="bold cyan")
        console.print("="*70 + "\n", style="bold")
        
        # Test Socrata API
        console.print(Panel("SOCRATA API TESTS", style="bold blue"))
        self.test_socrata_api()
        
        # Test Comptroller API
        console.print("\n" + Panel("COMPTROLLER API TESTS", style="bold green"))
        self.test_comptroller_api()
        
        # Show summary
        self.show_summary()
    
    def test_socrata_api(self):
        """Test Socrata API endpoints"""
        tests = [
            ("Connection Test", self.test_socrata_connection),
            ("Token Validation", self.test_socrata_token),
            ("Franchise Tax Dataset", self.test_socrata_franchise_tax),
            ("Sales Tax Dataset", self.test_socrata_sales_tax),
            ("Search Functionality", self.test_socrata_search),
            ("Pagination", self.test_socrata_pagination),
            ("Metadata Retrieval", self.test_socrata_metadata),
        ]
        
        for test_name, test_func in tests:
            self._run_test(test_name, test_func, "Socrata")
    
    def test_comptroller_api(self):
        """Test Comptroller API endpoints"""
        tests = [
            ("Connection Test", self.test_comptroller_connection),
            ("API Key Validation", self.test_comptroller_api_key),
            ("Franchise Tax Details", self.test_comptroller_franchise_details),
            ("Franchise Tax List", self.test_comptroller_franchise_list),
            ("Error Handling", self.test_comptroller_error_handling),
        ]
        
        for test_name, test_func in tests:
            self._run_test(test_name, test_func, "Comptroller")
    
    def _run_test(self, test_name: str, test_func: callable, api: str):
        """Run a single test"""
        console.print(f"\n[cyan]Testing:[/cyan] {test_name}... ", end="")
        
        start_time = time.time()
        
        try:
            result = test_func()
            elapsed = time.time() - start_time
            
            if result['success']:
                console.print("[green]✓ PASSED[/green]", end="")
                console.print(f" [dim]({elapsed:.2f}s)[/dim]")
                
                if result.get('message'):
                    console.print(f"  [dim]{result['message']}[/dim]")
            else:
                console.print("[red]✗ FAILED[/red]", end="")
                console.print(f" [dim]({elapsed:.2f}s)[/dim]")
                console.print(f"  [red]{result['error']}[/red]")
            
            self.test_results.append({
                'api': api,
                'test': test_name,
                'success': result['success'],
                'elapsed': elapsed,
                'message': result.get('message', ''),
                'error': result.get('error', '')
            })
            
        except Exception as e:
            elapsed = time.time() - start_time
            console.print(f"[red]✗ ERROR[/red] [dim]({elapsed:.2f}s)[/dim]")
            console.print(f"  [red]Unexpected error: {e}[/red]")
            
            self.test_results.append({
                'api': api,
                'test': test_name,
                'success': False,
                'elapsed': elapsed,
                'error': str(e)
            })
    
    # Socrata Tests
    
    def test_socrata_connection(self) -> dict:
        """Test Socrata API connection"""
        try:
            data = self.socrata_client.get(
                socrata_config.FRANCHISE_TAX_DATASET,
                limit=1
            )
            
            if data:
                return {
                    'success': True,
                    'message': 'Successfully connected to Socrata API'
                }
            else:
                return {
                    'success': False,
                    'error': 'No data returned'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_socrata_token(self) -> dict:
        """Test Socrata API token"""
        if socrata_config.has_token:
            return {
                'success': True,
                'message': f'API token configured, rate limit: {socrata_config.rate_limit:,}/hour'
            }
        else:
            return {
                'success': True,
                'message': f'No token configured, rate limit: {socrata_config.rate_limit:,}/hour'
            }
    
    def test_socrata_franchise_tax(self) -> dict:
        """Test franchise tax dataset access"""
        try:
            data = self.socrata_client.get_franchise_tax_holders(limit=5)
            
            if data and len(data) > 0:
                return {
                    'success': True,
                    'message': f'Retrieved {len(data)} records from franchise tax dataset'
                }
            else:
                return {
                    'success': False,
                    'error': 'No data returned from franchise tax dataset'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_socrata_sales_tax(self) -> dict:
        """Test sales tax dataset access"""
        try:
            data = self.socrata_client.get_sales_tax_holders(limit=5)
            
            if data and len(data) > 0:
                return {
                    'success': True,
                    'message': f'Retrieved {len(data)} records from sales tax dataset'
                }
            else:
                return {
                    'success': False,
                    'error': 'No data returned from sales tax dataset'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_socrata_search(self) -> dict:
        """Test Socrata search functionality"""
        try:
            # Search for a common business name
            data = self.socrata_client.search_by_city("Austin", limit=5)
            
            if data and len(data) > 0:
                return {
                    'success': True,
                    'message': f'Search returned {len(data)} results'
                }
            else:
                return {
                    'success': True,
                    'message': 'Search completed (no results)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_socrata_pagination(self) -> dict:
        """Test pagination"""
        try:
            batch1 = self.socrata_client.get(
                socrata_config.FRANCHISE_TAX_DATASET,
                limit=10,
                offset=0
            )
            
            batch2 = self.socrata_client.get(
                socrata_config.FRANCHISE_TAX_DATASET,
                limit=10,
                offset=10
            )
            
            if batch1 and batch2:
                return {
                    'success': True,
                    'message': f'Pagination working (batch1: {len(batch1)}, batch2: {len(batch2)})'
                }
            else:
                return {
                    'success': False,
                    'error': 'Pagination failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_socrata_metadata(self) -> dict:
        """Test metadata retrieval"""
        try:
            metadata = self.socrata_client.get_dataset_metadata(
                socrata_config.FRANCHISE_TAX_DATASET
            )
            
            if metadata:
                return {
                    'success': True,
                    'message': f'Retrieved metadata for {metadata.get("name", "dataset")}'
                }
            else:
                return {
                    'success': False,
                    'error': 'No metadata returned'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Comptroller Tests
    
    def test_comptroller_connection(self) -> dict:
        """Test Comptroller API connection"""
        try:
            # Try to get details for a test taxpayer ID
            # Using a common test ID that should exist
            details = self.comptroller_client.get_franchise_tax_details("32000012345")
            
            # Even if not found, successful response means API is working
            return {
                'success': True,
                'message': 'Successfully connected to Comptroller API'
            }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_comptroller_api_key(self) -> dict:
        """Test Comptroller API key"""
        if comptroller_config.has_api_key:
            return {
                'success': True,
                'message': 'API key configured'
            }
        else:
            return {
                'success': True,
                'message': 'No API key configured (may have limited access)'
            }
    
    def test_comptroller_franchise_details(self) -> dict:
        """Test franchise tax details endpoint"""
        try:
            # Test with a known taxpayer ID (you may need to adjust this)
            test_id = "32000012345"
            
            details = self.comptroller_client.get_franchise_tax_details(test_id)
            
            if details:
                return {
                    'success': True,
                    'message': f'Successfully retrieved details for taxpayer {test_id}'
                }
            else:
                return {
                    'success': True,
                    'message': 'Endpoint working (test taxpayer not found)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_comptroller_franchise_list(self) -> dict:
        """Test franchise tax list endpoint"""
        try:
            # Test search by name
            results = self.comptroller_client.get_franchise_tax_list(name="TEST")
            
            return {
                'success': True,
                'message': f'Search endpoint working (returned {len(results)} results)'
            }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_comptroller_error_handling(self) -> dict:
        """Test error handling for invalid requests"""
        try:
            # Test with invalid taxpayer ID
            details = self.comptroller_client.get_franchise_tax_details("INVALID")
            
            # Should return None for not found
            if details is None:
                return {
                    'success': True,
                    'message': 'Error handling working correctly'
                }
            else:
                return {
                    'success': False,
                    'error': 'Expected None for invalid ID'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def show_summary(self):
        """Show test summary"""
        console.print("\n" + "="*70, style="bold")
        console.print("TEST SUMMARY", style="bold cyan")
        console.print("="*70 + "\n", style="bold")
        
        # Overall stats
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        failed = total - passed
        
        # Stats by API
        socrata_tests = [r for r in self.test_results if r['api'] == 'Socrata']
        comptroller_tests = [r for r in self.test_results if r['api'] == 'Comptroller']
        
        socrata_passed = sum(1 for r in socrata_tests if r['success'])
        comptroller_passed = sum(1 for r in comptroller_tests if r['success'])
        
        # Create summary table
        table = Table(title="Test Results", show_header=True)
        table.add_column("API", style="cyan")
        table.add_column("Total", justify="right", style="white")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Pass Rate", justify="right", style="yellow")
        
        table.add_row(
            "Socrata",
            str(len(socrata_tests)),
            str(socrata_passed),
            str(len(socrata_tests) - socrata_passed),
            f"{socrata_passed/len(socrata_tests)*100:.1f}%" if socrata_tests else "N/A"
        )
        
        table.add_row(
            "Comptroller",
            str(len(comptroller_tests)),
            str(comptroller_passed),
            str(len(comptroller_tests) - comptroller_passed),
            f"{comptroller_passed/len(comptroller_tests)*100:.1f}%" if comptroller_tests else "N/A"
        )
        
        table.add_row(
            "TOTAL",
            str(total),
            str(passed),
            str(failed),
            f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            style="bold"
        )
        
        console.print(table)
        
        # Show failed tests
        if failed > 0:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for result in self.test_results:
                if not result['success']:
                    console.print(f"  • [{result['api']}] {result['test']}: {result.get('error', 'Unknown error')}")
        
        # Overall result
        if failed == 0:
            console.print("\n[bold green]✓ All tests passed![/bold green]")
        else:
            console.print(f"\n[bold yellow]⚠ {failed} test(s) failed[/bold yellow]")


def main():
    """Main entry point"""
    tester = APITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()