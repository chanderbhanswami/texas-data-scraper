#!/usr/bin/env python3
"""
Socrata Data Scraper - Interactive CLI
Scrape data from Texas Open Data Portal (Socrata)
With GPU acceleration and advanced features
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

# Use wrapper class instead of direct API client
from src.scrapers.socrata_scraper import SocrataScraper, BulkSocrataScraper
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from src.processors.data_validator import DataValidator
from src.utils.helpers import format_bytes, clean_taxpayer_id
from config.settings import (
    socrata_config, 
    print_configuration,
    SOCRATA_EXPORT_DIR
)

console = Console()
logger = get_logger(__name__)


class SocrataScraperCLI:
    """Interactive CLI for Socrata data scraping with GPU support"""
    
    def __init__(self):
        # Use SocrataScraper wrapper with GPU acceleration
        self.scraper = SocrataScraper(use_async=False, use_gpu=True)
        self.bulk_scraper = BulkSocrataScraper()  # For bulk operations
        self.exporter = FileExporter(SOCRATA_EXPORT_DIR)
        self.validator = DataValidator()  # Add validator
        self.last_data = None
        self.last_source = None
        
    def show_banner(self):
        """Show welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         TEXAS OPEN DATA PORTAL - SOCRATA SCRAPER         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
        
        # Show API token status
        if socrata_config.has_token:
            console.print("✓ API Token: Configured", style="green")
            console.print(f"  Rate Limit: {socrata_config.rate_limit:,} requests/hour", style="green")
        else:
            console.print("⚠ API Token: Not configured", style="yellow")
            console.print(f"  Rate Limit: {socrata_config.rate_limit:,} requests/hour (limited)", style="yellow")
            console.print("  Configure token in .env for 50k requests/hour\n", style="yellow")
        
        # Show GPU status
        if self.scraper.gpu.gpu_available:
            console.print(f"✓ GPU Acceleration: Enabled ({self.scraper.gpu.device_name})", style="green")
        else:
            console.print("⚠ GPU Acceleration: Not available (using CPU)", style="yellow")
    
    def show_main_menu(self) -> str:
        """Display main menu and get user choice"""
        console.print("\n" + "="*60, style="bold")
        console.print("MAIN MENU", style="bold cyan")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        
        # Dataset downloads
        table.add_row("1", "Franchise Tax Permit Holders (full dataset)")
        table.add_row("2", "Franchise Tax Permit Holders (custom limit)")
        table.add_row("3", "Sales Tax Permit Holders (full dataset)")
        table.add_row("4", "Sales Tax Permit Holders (custom limit)")
        table.add_row("5", "Mixed Beverage Tax Permit Holders (full dataset)")
        table.add_row("6", "Mixed Beverage Tax Permit Holders (custom limit)")
        table.add_row("", "")
        
        # Search options
        table.add_row("7", "Search by Business Name")
        table.add_row("8", "Search by Legal Name")
        table.add_row("9", "Search by DBA/Alternative Names")
        table.add_row("10", "Search by City")
        table.add_row("11", "Search by ZIP Code")
        table.add_row("12", "Search by Registered Agent")
        table.add_row("13", "Search by Officer Name")
        table.add_row("14", "Custom SoQL Query")
        table.add_row("", "")
        
        # Advanced options (NEW)
        table.add_row("15", "🚀 Multi-Dataset Download (all at once)")
        table.add_row("16", "📊 Incremental Scrape (new records only)")
        table.add_row("17", "🔍 Search Across All Datasets")
        table.add_row("", "")
        
        # Utilities
        table.add_row("18", "View Dataset Metadata")
        table.add_row("19", "Export Last Downloaded Data")
        table.add_row("20", "View Rate Limiter Stats")
        table.add_row("21", "View GPU/Scraper Stats")
        table.add_row("", "")
        # Data quality options
        table.add_row("22", "📊 Validate & Clean Downloaded Data")
        table.add_row("23", "🧹 View Data Quality Report")
        table.add_row("", "")
        table.add_row("0", "Exit")
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
    def get_dataset_choice(self) -> str:
        """Get dataset choice from user"""
        console.print("\nSelect Dataset:", style="bold")
        console.print("1. Franchise Tax")
        console.print("2. Sales Tax")
        console.print("3. Mixed Beverage Tax")
        
        choice = Prompt.ask("Dataset", choices=["1", "2", "3"], default="1")
        
        datasets = {
            "1": socrata_config.FRANCHISE_TAX_DATASET,
            "2": socrata_config.SALES_TAX_DATASET,
            "3": socrata_config.MIXED_BEVERAGE_DATASET
        }
        
        return datasets[choice]
    
    def download_full_dataset(self, dataset_name: str, dataset_id: str):
        """Download full dataset using scraper wrapper"""
        console.print(f"\n[bold]Downloading {dataset_name} (full dataset)...[/bold]")
        
        if self.scraper.gpu.use_gpu:
            console.print("🚀 GPU acceleration enabled for post-processing", style="cyan")
        
        try:
            # Use the scraper wrapper with progress callback
            def progress_callback(current, total):
                pass  # Rich progress bar handles this
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task("Downloading...", total=None)
                
                # Use scraper wrapper instead of direct client
                data = self.scraper.scrape_dataset(
                    dataset_id,
                    limit=None,  # Full dataset
                    batch_size=1000,
                    progress_callback=progress_callback
                )
                
                progress.update(task, completed=True)
            
            if data:
                self.last_data = data
                self.last_source = dataset_name
                
                console.print(f"\n✓ Downloaded {len(data):,} records", style="green bold")
                
                # Auto-export
                if Confirm.ask("Export data now?", default=True):
                    self.export_data(data, dataset_name)
            else:
                console.print("No data found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Download error: {e}")
    
    def download_custom_limit(self, dataset_name: str, dataset_id: str):
        """Download dataset with custom limit"""
        limit = IntPrompt.ask(f"\nEnter number of records to download", default=1000)
        
        console.print(f"\n[bold]Downloading {dataset_name} ({limit:,} records)...[/bold]")
        
        try:
            # Use scraper wrapper
            data = self.scraper.scrape_dataset(
                dataset_id,
                limit=limit,
                batch_size=1000
            )
            
            if data:
                self.last_data = data
                self.last_source = dataset_name
                
                console.print(f"\n✓ Downloaded {len(data):,} records", style="green bold")
                
                if Confirm.ask("Export data now?", default=True):
                    self.export_data(data, dataset_name)
            else:
                console.print("No data found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Download error: {e}")
    
    def search_data(self, search_type: str, field: str):
        """Generic search function"""
        search_value = Prompt.ask(f"\nEnter {search_type}")
        dataset_id = self.get_dataset_choice()
        
        limit_choice = Prompt.ask("\nLimit results? (y/n)", choices=["y", "n"], default="n")
        limit = IntPrompt.ask("Number of results", default=100) if limit_choice == "y" else None
        
        console.print(f"\n[bold]Searching for {search_type}: {search_value}...[/bold]")
        
        try:
            # Use client through scraper
            data = self.scraper.client.search(dataset_id, field, search_value, limit)
            
            if data:
                self.last_data = data
                self.last_source = f"{search_type}_search"
                
                console.print(f"\n✓ Found {len(data):,} records", style="green bold")
                
                # Show sample
                if Confirm.ask("Show sample records?", default=True):
                    self.show_sample_data(data)
                
                if Confirm.ask("Export results?", default=True):
                    self.export_data(data, f"{search_type}_search")
            else:
                console.print("No results found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Search error: {e}")
    
    def multi_dataset_download(self):
        """Download multiple datasets at once (NEW)"""
        console.print("\n[bold]🚀 Multi-Dataset Download[/bold]")
        console.print("This will download multiple datasets concurrently\n")
        
        # Select datasets
        console.print("Select datasets to download:")
        download_franchise = Confirm.ask("  Franchise Tax?", default=True)
        download_sales = Confirm.ask("  Sales Tax?", default=True)
        download_mixed = Confirm.ask("  Mixed Beverage?", default=False)
        
        dataset_ids = []
        if download_franchise:
            dataset_ids.append(socrata_config.FRANCHISE_TAX_DATASET)
        if download_sales:
            dataset_ids.append(socrata_config.SALES_TAX_DATASET)
        if download_mixed:
            dataset_ids.append(socrata_config.MIXED_BEVERAGE_DATASET)
        
        if not dataset_ids:
            console.print("No datasets selected", style="yellow")
            return
        
        limit = IntPrompt.ask("\nRecords per dataset (0 for all)", default=1000)
        limit = None if limit == 0 else limit
        
        console.print(f"\n[bold]Downloading {len(dataset_ids)} datasets...[/bold]")
        
        try:
            # Use bulk scraper for multiple datasets
            results = self.scraper.scrape_multiple_datasets(
                dataset_ids,
                limit_per_dataset=limit
            )
            
            total_records = sum(len(data) for data in results.values())
            console.print(f"\n✓ Downloaded {total_records:,} total records", style="green bold")
            
            # Export each dataset
            if Confirm.ask("Export all datasets?", default=True):
                for dataset_id, data in results.items():
                    if data:
                        dataset_name = self._get_dataset_name(dataset_id)
                        self.export_data(data, dataset_name)
                        
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Multi-dataset error: {e}")
    
    def incremental_scrape(self):
        """Incremental scrape - only new records (NEW)"""
        console.print("\n[bold]📊 Incremental Scrape[/bold]")
        console.print("Only download records not in existing export\n")
        
        # Select existing file
        export_dir = Path(SOCRATA_EXPORT_DIR)
        json_files = list(export_dir.glob("*.json"))
        
        if not json_files:
            console.print("No existing exports found. Run a full download first.", style="yellow")
            return
        
        # Show file selector
        console.print("Select existing export to compare against:")
        for i, f in enumerate(json_files[:10], 1):
            console.print(f"  {i}. {f.name}")
        
        choice = Prompt.ask("File number", choices=[str(i) for i in range(1, min(len(json_files), 10) + 1)])
        existing_file = json_files[int(choice) - 1]
        
        # Load existing IDs
        console.print(f"\nLoading existing data from {existing_file.name}...")
        existing_data = self.exporter.auto_load(existing_file)
        
        existing_ids = set()
        for record in existing_data:
            tid = record.get('taxpayer_id') or record.get('taxpayer_number')
            if tid:
                existing_ids.add(str(tid).strip())
        
        console.print(f"✓ Found {len(existing_ids):,} existing IDs", style="green")
        
        # Get dataset
        dataset_id = self.get_dataset_choice()
        
        # Incremental scrape
        console.print("\n[bold]Scraping new records only...[/bold]")
        
        try:
            new_data = self.scraper.incremental_scrape(
                dataset_id,
                existing_ids=existing_ids,
                id_field='taxpayer_number',
                batch_size=1000
            )
            
            if new_data:
                self.last_data = new_data
                self.last_source = "incremental"
                
                console.print(f"\n✓ Found {len(new_data):,} new records", style="green bold")
                
                if Confirm.ask("Export new records?", default=True):
                    self.export_data(new_data, "incremental_new_records")
            else:
                console.print("No new records found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Incremental scrape error: {e}")
    
    def search_across_datasets(self):
        """Search across all datasets (NEW)"""
        console.print("\n[bold]🔍 Search Across All Datasets[/bold]")
        
        query = Prompt.ask("Enter search term")
        field = Prompt.ask("Search field", default="taxpayer_name")
        limit = IntPrompt.ask("Results per dataset", default=50)
        
        dataset_ids = [
            socrata_config.FRANCHISE_TAX_DATASET,
            socrata_config.SALES_TAX_DATASET,
            socrata_config.MIXED_BEVERAGE_DATASET
        ]
        
        console.print(f"\n[bold]Searching '{query}' across all datasets...[/bold]")
        
        try:
            results = self.scraper.search_across_datasets(
                query=query,
                dataset_ids=dataset_ids,
                field=field,
                limit_per_dataset=limit
            )
            
            total_matches = sum(len(data) for data in results.values())
            console.print(f"\n✓ Found {total_matches:,} total matches", style="green bold")
            
            # Show breakdown
            for dataset_id, matches in results.items():
                dataset_name = self._get_dataset_name(dataset_id)
                console.print(f"  {dataset_name}: {len(matches)} matches")
            
            # Combine all results
            all_matches = []
            for matches in results.values():
                all_matches.extend(matches)
            
            if all_matches:
                self.last_data = all_matches
                self.last_source = "cross_dataset_search"
                
                if Confirm.ask("\nExport all results?", default=True):
                    self.export_data(all_matches, "cross_dataset_search")
                    
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def show_sample_data(self, data: list, sample_size: int = 5):
        """Show sample records"""
        console.print(f"\n[bold]Sample Records (showing {min(sample_size, len(data))} of {len(data):,}):[/bold]")
        
        for i, record in enumerate(data[:sample_size], 1):
            console.print(f"\n--- Record {i} ---", style="cyan")
            for key, value in list(record.items())[:8]:  # Show first 8 fields
                console.print(f"  {key}: {value}")
    
    def export_data(self, data: list, source_name: str):
        """Export data to multiple formats"""
        if not data:
            console.print("No data to export", style="yellow")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{source_name}_{timestamp}"
        
        console.print(f"\n[bold]Exporting {len(data):,} records...[/bold]")
        
        try:
            # Export JSON
            json_path = self.exporter.export_json(data, f"{base_filename}.json")
            console.print(f"✓ Exported JSON to {json_path}", style="green")
            
            # Export CSV
            csv_path = self.exporter.export_csv(data, f"{base_filename}.csv")
            console.print(f"✓ Exported CSV to {csv_path}", style="green")
            
            # Export Excel
            excel_path = self.exporter.export_excel(data, f"{base_filename}.xlsx")
            console.print(f"✓ Exported Excel to {excel_path}", style="green")
            
            console.print(f"\n✓ All exports complete!", style="green bold")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red bold")
            logger.error(f"Export error: {e}")
    
    def view_metadata(self):
        """View dataset metadata"""
        dataset_id = self.get_dataset_choice()
        
        console.print(f"\n[bold]Fetching metadata for {dataset_id}...[/bold]")
        
        try:
            metadata = self.scraper.client.get_dataset_metadata(dataset_id)
            
            if metadata:
                console.print("\n[bold]Dataset Information:[/bold]", style="cyan")
                console.print(f"Name: {metadata.get('name', 'N/A')}")
                console.print(f"Description: {metadata.get('description', 'N/A')}")
                console.print(f"Rows: {metadata.get('rowsUpdatedAt', 'N/A')}")
                console.print(f"Updated: {metadata.get('rowsUpdatedAt', 'N/A')}")
            else:
                console.print("Could not fetch metadata", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def show_rate_limiter_stats(self):
        """Show rate limiter statistics"""
        stats = self.scraper.client.rate_limiter.get_stats()
        
        table = Table(title="Rate Limiter Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Requests Made", f"{stats['requests_made']:,}")
        table.add_row("Max Requests", f"{stats['max_requests']:,}")
        table.add_row("Requests Remaining", f"{stats['requests_remaining']:,}")
        table.add_row("Window Reset In", f"{stats['window_reset_in']:.1f}s")
        
        console.print("\n")
        console.print(table)
    
    def show_scraper_stats(self):
        """Show scraper and GPU statistics (NEW)"""
        stats = self.scraper.get_scraper_stats()
        
        table = Table(title="Scraper Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Client Type", stats['client_type'])
        table.add_row("GPU Enabled", "✓ Yes" if stats['gpu_enabled'] else "✗ No")
        table.add_row("GPU Available", "✓ Yes" if stats['gpu_available'] else "✗ No")
        
        if stats.get('gpu_memory'):
            mem = stats['gpu_memory']
            table.add_row("GPU Memory Used", f"{mem.get('used_mb', 0):.0f} MB")
            table.add_row("GPU Memory Total", f"{mem.get('total_mb', 0):.0f} MB")
        
        console.print("\n")
        console.print(table)
        
        # Rate limiter stats
        rl_stats = stats['rate_limiter']
        table2 = Table(title="Rate Limiter")
        table2.add_column("Metric", style="cyan")
        table2.add_column("Value", style="green")
        
        table2.add_row("Requests Made", str(rl_stats['requests_made']))
        table2.add_row("Requests Remaining", str(rl_stats['requests_remaining']))
        
        console.print(table2)
    
    def _get_dataset_name(self, dataset_id: str) -> str:
        """Get human-readable dataset name"""
        names = {
            socrata_config.FRANCHISE_TAX_DATASET: "franchise_tax",
            socrata_config.SALES_TAX_DATASET: "sales_tax",
            socrata_config.MIXED_BEVERAGE_DATASET: "mixed_beverage"
        }
        return names.get(dataset_id, dataset_id)
    
    def validate_and_clean_data(self):
        """Validate and clean last downloaded data"""
        console.print("\n[bold]📊 Validate & Clean Data[/bold]")
        
        if not self.last_data:
            console.print("⚠ No data available. Download data first.", style="yellow")
            return
        
        console.print(f"\nCleaning {len(self.last_data):,} records...")
        
        # Clean data
        cleaned_data = self.validator.clean_dataset(self.last_data)
        
        # Standardize field names
        console.print("Standardizing field names...")
        standardized_data = self.validator.standardize_dataset(cleaned_data)
        
        # Validate
        console.print("Validating...")
        report = self.validator.validate_dataset(standardized_data)
        
        console.print(f"\n✓ Cleaned and validated {len(standardized_data):,} records", style="green bold")
        console.print(f"  Valid: {report['valid_records']:,} ({report['validation_rate']:.1f}%)")
        console.print(f"  Invalid: {report['invalid_records']:,}")
        
        self.last_data = standardized_data
        
        # Export
        if Confirm.ask("\nExport cleaned data?", default=True):
            self.export_data(standardized_data, f"{self.last_source or 'data'}_cleaned")
    
    def view_data_quality_report(self):
        """View data quality report for last downloaded data"""
        console.print("\n[bold]🧹 Data Quality Report[/bold]")
        
        if not self.last_data:
            console.print("⚠ No data available. Download data first.", style="yellow")
            return
        
        console.print(f"\nAnalyzing {len(self.last_data):,} records...")
        
        # Generate quality report
        report = self.validator.get_data_quality_report(self.last_data)
        
        # Display report
        table = Table(title="Data Quality Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Records", f"{report['total_records']:,}")
        table.add_row("Duplicate Records", f"{report['duplicate_count']:,}")
        table.add_row("Duplicate Rate", f"{report['duplicate_rate']:.2f}%")
        table.add_row("Valid Records", f"{report['validation_results']['valid_records']:,}")
        table.add_row("Invalid Records", f"{report['validation_results']['invalid_records']:,}")
        table.add_row("Validation Rate", f"{report['validation_results']['validation_rate']:.1f}%")
        
        console.print("\n")
        console.print(table)
        
        # Field completeness
        console.print("\n[bold]Field Completeness (Top 10):[/bold]")
        completeness_table = Table()
        completeness_table.add_column("Field", style="cyan")
        completeness_table.add_column("Completeness", style="green", justify="right")
        
        sorted_fields = sorted(
            report['field_completeness'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for field, pct in sorted_fields:
            completeness_table.add_row(field, f"{pct:.1f}%")
        
        console.print(completeness_table)
    
    def run(self):
        """Main CLI loop"""
        self.show_banner()
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "0":
                    console.print("\nGoodbye! 👋", style="bold cyan")
                    break
                    
                elif choice == "1":
                    self.download_full_dataset("franchise_tax", socrata_config.FRANCHISE_TAX_DATASET)
                    
                elif choice == "2":
                    self.download_custom_limit("franchise_tax", socrata_config.FRANCHISE_TAX_DATASET)
                    
                elif choice == "3":
                    self.download_full_dataset("sales_tax", socrata_config.SALES_TAX_DATASET)
                    
                elif choice == "4":
                    self.download_custom_limit("sales_tax", socrata_config.SALES_TAX_DATASET)
                    
                elif choice == "5":
                    self.download_full_dataset("mixed_beverage", socrata_config.MIXED_BEVERAGE_DATASET)
                    
                elif choice == "6":
                    self.download_custom_limit("mixed_beverage", socrata_config.MIXED_BEVERAGE_DATASET)
                    
                elif choice == "7":
                    self.search_data("Business Name", "taxpayer_name")
                    
                elif choice == "8":
                    self.search_data("Legal Name", "legal_name")
                    
                elif choice == "9":
                    self.search_data("DBA Name", "dba_name")
                    
                elif choice == "10":
                    self.search_data("City", "taxpayer_city")
                    
                elif choice == "11":
                    self.search_data("ZIP Code", "taxpayer_zip")
                    
                elif choice == "12":
                    self.search_data("Registered Agent", "agent_name")
                    
                elif choice == "13":
                    self.search_data("Officer Name", "officer_name")
                    
                elif choice == "14":
                    console.print("\nCustom SoQL Query - Coming soon!", style="yellow")
                    
                elif choice == "15":
                    self.multi_dataset_download()
                    
                elif choice == "16":
                    self.incremental_scrape()
                    
                elif choice == "17":
                    self.search_across_datasets()
                    
                elif choice == "18":
                    self.view_metadata()
                    
                elif choice == "19":
                    if self.last_data:
                        self.export_data(self.last_data, self.last_source or "data")
                    else:
                        console.print("\nNo data available to export", style="yellow")
                    
                elif choice == "20":
                    self.show_rate_limiter_stats()
                    
                elif choice == "21":
                    self.show_scraper_stats()
                    
                elif choice == "22":
                    self.validate_and_clean_data()
                    
                elif choice == "23":
                    self.view_data_quality_report()
                    
                else:
                    console.print("\nInvalid option", style="red")
                    
            except KeyboardInterrupt:
                console.print("\n\nOperation cancelled by user", style="yellow")
                if Confirm.ask("Exit program?", default=False):
                    break
            except Exception as e:
                console.print(f"\nUnexpected error: {e}", style="red bold")
                logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    cli = SocrataScraperCLI()
    cli.run()