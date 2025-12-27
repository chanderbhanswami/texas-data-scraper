#!/usr/bin/env python3
"""
Socrata Data Scraper - Interactive CLI
Scrape data from Texas Open Data Portal (Socrata)
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

from src.api.socrata_client import SocrataClient
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import (
    socrata_config, 
    print_configuration,
    SOCRATA_EXPORT_DIR
)

console = Console()
logger = get_logger(__name__)


class SocrataScraperCLI:
    """Interactive CLI for Socrata data scraping"""
    
    def __init__(self):
        self.client = SocrataClient()
        self.exporter = FileExporter(SOCRATA_EXPORT_DIR)
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
        
        # Utilities
        table.add_row("15", "View Dataset Metadata")
        table.add_row("16", "Export Last Downloaded Data")
        table.add_row("17", "View Rate Limiter Stats")
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
        """Download full dataset"""
        console.print(f"\n[bold]Downloading {dataset_name} (full dataset)...[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            
            try:
                data = self.client.get_all(dataset_id)
                
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
            data = self.client.get(dataset_id, limit=limit)
            
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
            data = self.client.search(dataset_id, field, search_value, limit)
            
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
            metadata = self.client.get_dataset_metadata(dataset_id)
            
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
        stats = self.client.rate_limiter.get_stats()
        
        table = Table(title="Rate Limiter Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Requests Made", f"{stats['requests_made']:,}")
        table.add_row("Max Requests", f"{stats['max_requests']:,}")
        table.add_row("Requests Remaining", f"{stats['requests_remaining']:,}")
        table.add_row("Window Reset In", f"{stats['window_reset_in']:.1f}s")
        
        console.print("\n")
        console.print(table)
    
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
                    self.view_metadata()
                    
                elif choice == "16":
                    if self.last_data:
                        self.export_data(self.last_data, self.last_source or "data")
                    else:
                        console.print("\nNo data available to export", style="yellow")
                    
                elif choice == "17":
                    self.show_rate_limiter_stats()
                    
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