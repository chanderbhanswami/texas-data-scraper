#!/usr/bin/env python3
"""
Batch Processing Script
Process large datasets in batches with GPU acceleration and progress tracking
"""
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.table import Table

# Use bulk scrapers with GPU support
from src.scrapers.socrata_scraper import BulkSocrataScraper
from src.scrapers.comptroller_scraper import BulkComptrollerScraper
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import batch_config, EXPORT_DIR, socrata_config

console = Console()
logger = get_logger(__name__)


class BatchProcessor:
    """Batch processing utility with GPU acceleration"""
    
    def __init__(self):
        # Use bulk scrapers (async + GPU by default)
        self.socrata_scraper = BulkSocrataScraper()
        self.comptroller_scraper = BulkComptrollerScraper()
        self.exporter = FileExporter(EXPORT_DIR / 'batch')
        
    def show_banner(self):
        """Show banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              BATCH PROCESSOR - LARGE DATASETS            ║
║                    🚀 GPU Accelerated 🚀                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
        
        # Show GPU status
        if self.socrata_scraper.gpu.gpu_available:
            console.print(f"✓ GPU: {self.socrata_scraper.gpu.device_name}", style="green")
        else:
            console.print("⚠ GPU: Not available (using CPU)", style="yellow")
        
        console.print("✓ Mode: Async + Bulk Processing", style="green")
    
    def batch_download_socrata(self, dataset_id: str, total_records: int,
                                batch_size: int = 1000):
        """
        Download large Socrata dataset in batches with GPU acceleration
        
        Args:
            dataset_id: Dataset identifier
            total_records: Total records to download
            batch_size: Records per batch
        """
        console.print(f"\n[bold]Batch downloading {total_records:,} records...[/bold]")
        console.print(f"Batch size: {batch_size:,} records")
        
        if self.socrata_scraper.gpu.use_gpu:
            console.print("🚀 GPU acceleration enabled\n", style="cyan")
        
        try:
            # Use bulk scraper's scrape_dataset method
            data = self.socrata_scraper.scrape_dataset(
                dataset_id,
                limit=total_records,
                batch_size=batch_size
            )
            
            console.print(f"\n✓ Downloaded {len(data):,} records", style="green bold")
            return data
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            console.print(f"Error: {e}", style="red")
            return []
    
    def batch_process_taxpayer_ids(self, taxpayer_ids: list, 
                                    batch_size: int = 100):
        """
        Process taxpayer IDs in batches with async + GPU
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            batch_size: IDs per batch
        """
        console.print(f"\n[bold]Processing {len(taxpayer_ids):,} taxpayer IDs...[/bold]")
        console.print(f"Concurrent requests: {batch_config.CONCURRENT_REQUESTS}")
        
        if self.comptroller_scraper.gpu.use_gpu:
            console.print("🚀 GPU acceleration enabled\n", style="cyan")
        
        try:
            # Use bulk scraper (async by default)
            results = self.comptroller_scraper.bulk_scrape_sync(
                taxpayer_ids,
                include_details=True,
                include_ftas=True
            )
            
            console.print(f"\n✓ Processed {len(results):,} records", style="green bold")
            return results
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            console.print(f"Error: {e}", style="red")
            return []
    
    def show_stats(self):
        """Show scraper statistics"""
        console.print("\n[bold]Scraper Statistics[/bold]")
        
        # Socrata stats
        socrata_stats = self.socrata_scraper.get_scraper_stats()
        table1 = Table(title="Socrata Scraper")
        table1.add_column("Metric", style="cyan")
        table1.add_column("Value", style="green")
        table1.add_row("Client Type", socrata_stats['client_type'])
        table1.add_row("GPU Enabled", "✓ Yes" if socrata_stats['gpu_enabled'] else "✗ No")
        console.print(table1)
        
        # Comptroller stats
        comp_stats = self.comptroller_scraper.get_scraper_stats()
        table2 = Table(title="Comptroller Scraper")
        table2.add_column("Metric", style="cyan")
        table2.add_column("Value", style="green")
        table2.add_row("Client Type", comp_stats['client_type'])
        table2.add_row("GPU Enabled", "✓ Yes" if comp_stats['gpu_enabled'] else "✗ No")
        console.print(table2)
    
    def run(self):
        """Main menu"""
        self.show_banner()
        
        while True:
            console.print("\n" + "="*60, style="bold")
            console.print("BATCH PROCESSING MENU", style="bold cyan")
            console.print("="*60, style="bold")
            
            console.print("\n1. Batch download Socrata dataset")
            console.print("2. Batch process taxpayer IDs from file")
            console.print("3. Full pipeline (download + process)")
            console.print("4. Multi-dataset batch download")
            console.print("5. View scraper stats")
            console.print("0. Exit")
            
            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "0"])
            
            if choice == "0":
                console.print("\nGoodbye! 👋", style="cyan")
                break
                
            elif choice == "1":
                self.handle_batch_download()
                
            elif choice == "2":
                self.handle_batch_process()
                
            elif choice == "3":
                self.handle_full_pipeline()
                
            elif choice == "4":
                self.handle_multi_dataset()
                
            elif choice == "5":
                self.show_stats()
    
    def handle_batch_download(self):
        """Handle batch download"""
        console.print("\n[bold]Batch Download Configuration[/bold]")
        
        # Dataset selection
        console.print("\nDataset:")
        console.print("1. Franchise Tax")
        console.print("2. Sales Tax")
        console.print("3. Custom dataset ID")
        
        dataset_choice = Prompt.ask("Select", choices=["1", "2", "3"])
        
        if dataset_choice == "1":
            dataset_id = socrata_config.FRANCHISE_TAX_DATASET
        elif dataset_choice == "2":
            dataset_id = socrata_config.SALES_TAX_DATASET
        else:
            dataset_id = Prompt.ask("Enter dataset ID")
        
        # Number of records
        total_records = IntPrompt.ask("Total records to download", default=10000)
        
        # Batch size
        batch_size = IntPrompt.ask("Batch size", default=1000)
        
        # Download
        data = self.batch_download_socrata(dataset_id, total_records, batch_size)
        
        # Export
        if data and Confirm.ask("\nExport results?", default=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paths = self.exporter.export_all_formats(data, f"batch_download_{timestamp}")
            for fmt, path in paths.items():
                console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
    
    def handle_batch_process(self):
        """Handle batch processing"""
        console.print("\n[bold]Batch Processing Configuration[/bold]")
        
        filepath = Prompt.ask("Enter file path with taxpayer IDs")
        
        try:
            data = self.exporter.auto_load(Path(filepath))
            
            # Extract taxpayer IDs
            taxpayer_ids = []
            for record in data:
                for field in ['taxpayer_id', 'taxpayer_number', 'taxpayerid']:
                    if field in record and record[field]:
                        taxpayer_ids.append(str(record[field]).strip())
                        break
            
            console.print(f"✓ Found {len(taxpayer_ids):,} taxpayer IDs", style="green")
            
            # Process
            results = self.batch_process_taxpayer_ids(taxpayer_ids)
            
            # Export
            if results and Confirm.ask("\nExport results?", default=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                paths = self.exporter.export_all_formats(results, f"batch_process_{timestamp}")
                for fmt, path in paths.items():
                    console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def handle_full_pipeline(self):
        """Handle full pipeline"""
        console.print("\n[bold]Full Pipeline: Download + Process[/bold]")
        
        # Download
        console.print("\n[cyan]Step 1: Download Socrata Data[/cyan]")
        
        dataset_id = socrata_config.FRANCHISE_TAX_DATASET
        
        total_records = IntPrompt.ask("Records to download", default=5000)
        batch_size = IntPrompt.ask("Download batch size", default=1000)
        
        data = self.batch_download_socrata(dataset_id, total_records, batch_size)
        
        if not data:
            console.print("No data downloaded", style="yellow")
            return
        
        # Extract IDs
        console.print("\n[cyan]Step 2: Extract Taxpayer IDs[/cyan]")
        
        taxpayer_ids = []
        for record in data:
            for field in ['taxpayer_id', 'taxpayer_number', 'taxpayerid']:
                if field in record and record[field]:
                    taxpayer_ids.append(str(record[field]).strip())
                    break
        
        console.print(f"✓ Extracted {len(taxpayer_ids):,} IDs", style="green")
        
        # Process
        console.print("\n[cyan]Step 3: Process with Comptroller API[/cyan]")
        
        results = self.batch_process_taxpayer_ids(taxpayer_ids)
        
        # Export
        console.print("\n[cyan]Step 4: Export Results[/cyan]")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export Socrata data
        socrata_paths = self.exporter.export_all_formats(data, f"pipeline_socrata_{timestamp}")
        console.print("Socrata exports:", style="bold")
        for fmt, path in socrata_paths.items():
            console.print(f"  ✓ {fmt.upper()}: {path}", style="green")
        
        # Export Comptroller data
        comp_paths = self.exporter.export_all_formats(results, f"pipeline_comptroller_{timestamp}")
        console.print("Comptroller exports:", style="bold")
        for fmt, path in comp_paths.items():
            console.print(f"  ✓ {fmt.upper()}: {path}", style="green")
        
        console.print("\n✓ Full pipeline complete!", style="green bold")
    
    def handle_multi_dataset(self):
        """Handle multi-dataset batch download"""
        console.print("\n[bold]Multi-Dataset Batch Download[/bold]")
        console.print("Download multiple datasets concurrently\n")
        
        # Select datasets
        download_franchise = Confirm.ask("Download Franchise Tax?", default=True)
        download_sales = Confirm.ask("Download Sales Tax?", default=True)
        download_mixed = Confirm.ask("Download Mixed Beverage?", default=False)
        
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
        
        limit = IntPrompt.ask("Records per dataset (0 for all)", default=5000)
        limit = None if limit == 0 else limit
        
        console.print(f"\n[bold]Downloading {len(dataset_ids)} datasets...[/bold]")
        
        try:
            # Use bulk scraper's multi-dataset feature
            results = self.socrata_scraper.scrape_multiple_datasets(
                dataset_ids,
                limit_per_dataset=limit
            )
            
            total = sum(len(v) for v in results.values())
            console.print(f"\n✓ Downloaded {total:,} total records", style="green bold")
            
            # Export each
            if Confirm.ask("\nExport all?", default=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                for dataset_id, data in results.items():
                    if data:
                        name = self._get_dataset_name(dataset_id)
                        paths = self.exporter.export_all_formats(data, f"batch_{name}_{timestamp}")
                        console.print(f"✓ Exported {name}", style="green")
                        
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def _get_dataset_name(self, dataset_id: str) -> str:
        """Get dataset name"""
        names = {
            socrata_config.FRANCHISE_TAX_DATASET: "franchise_tax",
            socrata_config.SALES_TAX_DATASET: "sales_tax",
            socrata_config.MIXED_BEVERAGE_DATASET: "mixed_beverage"
        }
        return names.get(dataset_id, dataset_id)


if __name__ == "__main__":
    processor = BatchProcessor()
    processor.run()