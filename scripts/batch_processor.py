#!/usr/bin/env python3
"""
Batch Processing Script
Process large datasets in batches with progress tracking
"""
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, IntPrompt, Confirm

from src.api.socrata_client import SocrataClient
from src.api.comptroller_client import ComptrollerClient
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import batch_config, EXPORT_DIR

console = Console()
logger = get_logger(__name__)


class BatchProcessor:
    """Batch processing utility"""
    
    def __init__(self):
        self.socrata_client = SocrataClient()
        self.comptroller_client = ComptrollerClient()
        self.exporter = FileExporter(EXPORT_DIR / 'batch')
        
    def show_banner(self):
        """Show banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              BATCH PROCESSOR - LARGE DATASETS            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
    
    def batch_download_socrata(self, dataset_id: str, total_records: int,
                                batch_size: int = 1000):
        """
        Download large Socrata dataset in batches
        
        Args:
            dataset_id: Dataset identifier
            total_records: Total records to download
            batch_size: Records per batch
        """
        all_data = []
        
        console.print(f"\n[bold]Batch downloading {total_records:,} records...[/bold]")
        console.print(f"Batch size: {batch_size:,} records\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} batches"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            num_batches = (total_records + batch_size - 1) // batch_size
            task = progress.add_task("Downloading...", total=num_batches)
            
            for offset in range(0, total_records, batch_size):
                try:
                    batch = self.socrata_client.get(
                        dataset_id,
                        limit=batch_size,
                        offset=offset
                    )
                    
                    if batch:
                        all_data.extend(batch)
                        progress.update(task, advance=1)
                    else:
                        break
                    
                    # Stop if we got fewer records than expected
                    if len(batch) < batch_size:
                        break
                        
                except Exception as e:
                    logger.error(f"Error in batch at offset {offset}: {e}")
                    console.print(f"\n⚠ Error at offset {offset}, continuing...", 
                                style="yellow")
                    progress.update(task, advance=1)
        
        console.print(f"\n✓ Downloaded {len(all_data):,} records", style="green bold")
        return all_data
    
    def batch_process_taxpayer_ids(self, taxpayer_ids: list, 
                                    batch_size: int = 100):
        """
        Process taxpayer IDs in batches
        
        Args:
            taxpayer_ids: List of taxpayer IDs
            batch_size: IDs per batch
        """
        results = []
        
        console.print(f"\n[bold]Processing {len(taxpayer_ids):,} taxpayer IDs...[/bold]")
        console.print(f"Batch size: {batch_size}\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} records"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing...", total=len(taxpayer_ids))
            
            for i in range(0, len(taxpayer_ids), batch_size):
                batch = taxpayer_ids[i:i+batch_size]
                
                for taxpayer_id in batch:
                    try:
                        info = self.comptroller_client.get_complete_taxpayer_info(
                            taxpayer_id
                        )
                        results.append(info)
                        progress.update(task, advance=1)
                        
                    except Exception as e:
                        logger.error(f"Error processing {taxpayer_id}: {e}")
                        results.append({
                            'taxpayer_id': taxpayer_id,
                            'error': str(e),
                            'details': None,
                            'ftas_records': []
                        })
                        progress.update(task, advance=1)
                
                # Brief pause between batches
                time.sleep(0.5)
        
        console.print(f"\n✓ Processed {len(results):,} records", style="green bold")
        return results
    
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
            console.print("0. Exit")
            
            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "0"])
            
            if choice == "0":
                console.print("\nGoodbye! 👋", style="cyan")
                break
                
            elif choice == "1":
                self.handle_batch_download()
                
            elif choice == "2":
                self.handle_batch_process()
                
            elif choice == "3":
                self.handle_full_pipeline()
    
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
            from config.settings import socrata_config
            dataset_id = socrata_config.FRANCHISE_TAX_DATASET
        elif dataset_choice == "2":
            from config.settings import socrata_config
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
            self.exporter.export_all_formats(data, f"batch_download_{timestamp}")
            console.print("✓ Export complete!", style="green")
    
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
            
            # Batch size
            batch_size = IntPrompt.ask("Batch size", default=100)
            
            # Process
            results = self.batch_process_taxpayer_ids(taxpayer_ids, batch_size)
            
            # Export
            if results and Confirm.ask("\nExport results?", default=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.exporter.export_all_formats(results, f"batch_process_{timestamp}")
                console.print("✓ Export complete!", style="green")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def handle_full_pipeline(self):
        """Handle full pipeline"""
        console.print("\n[bold]Full Pipeline: Download + Process[/bold]")
        
        # Download
        console.print("\n[cyan]Step 1: Download Socrata Data[/cyan]")
        
        from config.settings import socrata_config
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
        
        process_batch_size = IntPrompt.ask("Process batch size", default=100)
        
        results = self.batch_process_taxpayer_ids(taxpayer_ids, process_batch_size)
        
        # Export
        console.print("\n[cyan]Step 4: Export Results[/cyan]")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.exporter.export_all_formats(results, f"pipeline_{timestamp}")
        
        console.print("\n✓ Full pipeline complete!", style="green bold")


if __name__ == "__main__":
    processor = BatchProcessor()
    processor.run()