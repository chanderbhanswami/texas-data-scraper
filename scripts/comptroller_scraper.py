#!/usr/bin/env python3
"""
Comptroller Data Scraper - Interactive CLI
Fetch detailed taxpayer data from Texas Comptroller API
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.panel import Panel

from src.api.comptroller_client import ComptrollerClient, AsyncComptrollerClient
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import (
    comptroller_config,
    COMPTROLLER_EXPORT_DIR,
    SOCRATA_EXPORT_DIR,
    batch_config
)

console = Console()
logger = get_logger(__name__)


class ComptrollerScraperCLI:
    """Interactive CLI for Comptroller data scraping"""
    
    def __init__(self):
        self.client = ComptrollerClient()
        self.async_client = AsyncComptrollerClient()
        self.exporter = FileExporter(COMPTROLLER_EXPORT_DIR)
        self.last_data = None
        
    def show_banner(self):
        """Show welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      TEXAS COMPTROLLER API - TAXPAYER DATA SCRAPER       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
        
        # Show API key status
        if comptroller_config.has_api_key:
            console.print("✓ API Key: Configured", style="green")
        else:
            console.print("⚠ API Key: Not configured", style="yellow")
            console.print("  Some features may be limited\n", style="yellow")
    
    def show_main_menu(self) -> str:
        """Display main menu"""
        console.print("\n" + "="*60, style="bold")
        console.print("MAIN MENU", style="bold cyan")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        
        table.add_row("1", "Process Socrata Export (Auto-detect)")
        table.add_row("2", "Process Socrata Export (Manual path)")
        table.add_row("3", "Batch Process Taxpayer IDs from file")
        table.add_row("", "")
        table.add_row("4", "Single Taxpayer Lookup (details + FTAS)")
        table.add_row("5", "Single Taxpayer - Details Only")
        table.add_row("6", "Single Taxpayer - FTAS Only")
        table.add_row("", "")
        table.add_row("7", "Export Last Retrieved Data")
        table.add_row("8", "View Rate Limiter Stats")
        table.add_row("", "")
        table.add_row("0", "Exit")
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
    def detect_socrata_files(self) -> list:
        """Auto-detect Socrata export files"""
        socrata_dir = Path(SOCRATA_EXPORT_DIR)
        
        # Find JSON and CSV files
        json_files = list(socrata_dir.glob("*.json"))
        csv_files = list(socrata_dir.glob("*.csv"))
        
        all_files = json_files + csv_files
        
        # Sort by modification time (newest first)
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return all_files
    
    def show_file_selector(self, files: list) -> Path:
        """Show file selection menu"""
        console.print("\n[bold]Available Socrata Export Files:[/bold]")
        
        table = Table()
        table.add_column("#", style="cyan", width=4)
        table.add_column("Filename", style="white")
        table.add_column("Size", style="yellow")
        table.add_column("Modified", style="green")
        
        for i, file in enumerate(files[:20], 1):  # Show max 20 files
            size_mb = file.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(file.stat().st_mtime)
            
            table.add_row(
                str(i),
                file.name,
                f"{size_mb:.2f} MB",
                mod_time.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        
        choice = Prompt.ask(
            "\nSelect file number",
            choices=[str(i) for i in range(1, min(len(files), 20) + 1)]
        )
        
        return files[int(choice) - 1]
    
    def extract_taxpayer_ids(self, data: list) -> list:
        """
        Extract taxpayer IDs from Socrata data
        
        Args:
            data: Socrata export data
            
        Returns:
            List of taxpayer IDs
        """
        taxpayer_ids = []
        
        # Common field names for taxpayer IDs
        id_fields = [
            'taxpayer_number',
            'taxpayer_id',
            'taxpayernumber',
            'taxpayerid',
            'tax_payer_number',
            'taxpayer_no',
            'id'
        ]
        
        for record in data:
            for field in id_fields:
                if field in record and record[field]:
                    tid = str(record[field]).strip()
                    if tid and tid not in taxpayer_ids:
                        taxpayer_ids.append(tid)
                    break
        
        return taxpayer_ids
    
    def process_socrata_auto(self):
        """Auto-detect and process Socrata files"""
        files = self.detect_socrata_files()
        
        if not files:
            console.print("\n⚠ No Socrata export files found", style="yellow")
            console.print(f"Expected location: {SOCRATA_EXPORT_DIR}", style="yellow")
            return
        
        # Select file
        selected_file = self.show_file_selector(files)
        
        # Load data
        console.print(f"\n[bold]Loading {selected_file.name}...[/bold]")
        try:
            data = self.exporter.auto_load(selected_file)
            console.print(f"✓ Loaded {len(data):,} records", style="green")
            
            # Extract taxpayer IDs
            taxpayer_ids = self.extract_taxpayer_ids(data)
            console.print(f"✓ Found {len(taxpayer_ids):,} taxpayer IDs", style="green")
            
            if not taxpayer_ids:
                console.print("⚠ No taxpayer IDs found in data", style="yellow")
                return
            
            # Process taxpayer IDs
            self.batch_process_taxpayer_ids(taxpayer_ids)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Processing error: {e}")
    
    def process_socrata_manual(self):
        """Process Socrata file from manual path"""
        filepath = Prompt.ask("\nEnter file path")
        
        filepath = Path(filepath)
        if not filepath.exists():
            console.print(f"⚠ File not found: {filepath}", style="yellow")
            return
        
        console.print(f"\n[bold]Loading {filepath.name}...[/bold]")
        try:
            data = self.exporter.auto_load(filepath)
            console.print(f"✓ Loaded {len(data):,} records", style="green")
            
            # Extract taxpayer IDs
            taxpayer_ids = self.extract_taxpayer_ids(data)
            console.print(f"✓ Found {len(taxpayer_ids):,} taxpayer IDs", style="green")
            
            if taxpayer_ids:
                self.batch_process_taxpayer_ids(taxpayer_ids)
            else:
                console.print("⚠ No taxpayer IDs found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Processing error: {e}")
    
    def batch_process_taxpayer_ids(self, taxpayer_ids: list):
        """Batch process taxpayer IDs"""
        console.print(f"\n[bold]Processing {len(taxpayer_ids):,} taxpayers...[/bold]")
        
        # Ask for processing method
        console.print("\nProcessing Method:")
        console.print("1. Synchronous (slower, more stable)")
        console.print("2. Asynchronous (faster, uses concurrency)")
        
        method = Prompt.ask("Select method", choices=["1", "2"], default="2")
        
        if method == "2":
            # Async processing
            results = asyncio.run(self._async_batch_process(taxpayer_ids))
        else:
            # Sync processing
            results = self._sync_batch_process(taxpayer_ids)
        
        # Store results
        self.last_data = results
        
        # Show summary
        self.show_processing_summary(results)
        
        # Export
        if Confirm.ask("\nExport results?", default=True):
            self.export_comptroller_data(results)
    
    def _sync_batch_process(self, taxpayer_ids: list) -> list:
        """Synchronous batch processing"""
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=console
        ) as progress:
            task = progress.add_task("Processing taxpayers...", total=len(taxpayer_ids))
            
            for taxpayer_id in taxpayer_ids:
                try:
                    info = self.client.get_complete_taxpayer_info(taxpayer_id)
                    results.append(info)
                except Exception as e:
                    logger.error(f"Error processing {taxpayer_id}: {e}")
                    results.append({
                        'taxpayer_id': taxpayer_id,
                        'error': str(e),
                        'details': None,
                        'ftas_records': []
                    })
                
                progress.update(task, advance=1)
        
        return results
    
    async def _async_batch_process(self, taxpayer_ids: list) -> list:
        """Asynchronous batch processing"""
        console.print(f"Using {batch_config.CONCURRENT_REQUESTS} concurrent requests")
        
        results = await self.async_client.batch_get_taxpayer_info(
            taxpayer_ids,
            max_concurrent=batch_config.CONCURRENT_REQUESTS
        )
        
        return results
    
    def show_processing_summary(self, results: list):
        """Show processing summary"""
        total = len(results)
        with_details = sum(1 for r in results if r.get('has_details'))
        with_ftas = sum(1 for r in results if r.get('has_ftas'))
        errors = sum(1 for r in results if 'error' in r)
        
        table = Table(title="Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Percentage", style="yellow")
        
        table.add_row("Total Processed", str(total), "100%")
        table.add_row("With Details", str(with_details), f"{with_details/total*100:.1f}%")
        table.add_row("With FTAS Records", str(with_ftas), f"{with_ftas/total*100:.1f}%")
        table.add_row("Errors", str(errors), f"{errors/total*100:.1f}%")
        
        console.print("\n")
        console.print(table)
    
    def single_taxpayer_lookup(self):
        """Single taxpayer complete lookup"""
        taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
        
        console.print(f"\n[bold]Fetching data for {taxpayer_id}...[/bold]")
        
        try:
            info = self.client.get_complete_taxpayer_info(taxpayer_id)
            
            # Display in terminal
            self.display_taxpayer_info(info)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def display_taxpayer_info(self, info: dict):
        """Display taxpayer information in terminal"""
        console.print("\n" + "="*60, style="bold cyan")
        console.print(f"TAXPAYER ID: {info['taxpayer_id']}", style="bold cyan")
        console.print("="*60, style="bold cyan")
        
        # Details
        if info.get('details'):
            console.print("\n[bold]Details:[/bold]", style="green")
            for key, value in info['details'].items():
                console.print(f"  {key}: {value}")
        else:
            console.print("\n⚠ No details found", style="yellow")
        
        # FTAS Records
        if info.get('ftas_records'):
            console.print(f"\n[bold]FTAS Records ({len(info['ftas_records'])}):[/bold]", style="green")
            for i, record in enumerate(info['ftas_records'], 1):
                console.print(f"\n  Record {i}:")
                for key, value in list(record.items())[:10]:
                    console.print(f"    {key}: {value}")
        else:
            console.print("\n⚠ No FTAS records found", style="yellow")
    
    def export_comptroller_data(self, data: list):
        """Export comptroller data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"comptroller_data_{timestamp}"
        
        console.print(f"\n[bold]Exporting {len(data):,} records...[/bold]")
        
        try:
            # Flatten data for export
            flattened_data = self.flatten_comptroller_data(data)
            
            # Export all formats
            paths = self.exporter.export_all_formats(flattened_data, base_filename)
            
            for format_name, path in paths.items():
                console.print(f"✓ Exported {format_name.upper()} to {path}", style="green")
            
            console.print(f"\n✓ All exports complete!", style="green bold")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red bold")
    
    def flatten_comptroller_data(self, data: list) -> list:
        """Flatten nested comptroller data for export"""
        flattened = []
        
        for record in data:
            flat_record = {
                'taxpayer_id': record.get('taxpayer_id'),
                'has_details': record.get('has_details'),
                'has_ftas': record.get('has_ftas')
            }
            
            # Add details fields
            if record.get('details'):
                for key, value in record['details'].items():
                    flat_record[f'detail_{key}'] = value
            
            # Add FTAS fields (first record only for simplicity)
            if record.get('ftas_records') and len(record['ftas_records']) > 0:
                for key, value in record['ftas_records'][0].items():
                    flat_record[f'ftas_{key}'] = value
            
            flattened.append(flat_record)
        
        return flattened
    
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
                    self.process_socrata_auto()
                    
                elif choice == "2":
                    self.process_socrata_manual()
                    
                elif choice == "3":
                    console.print("\nBatch from file - Coming soon!", style="yellow")
                    
                elif choice == "4":
                    self.single_taxpayer_lookup()
                    
                elif choice == "5":
                    taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
                    details = self.client.get_franchise_tax_details(taxpayer_id)
                    if details:
                        console.print("\n[bold]Details:[/bold]", style="green")
                        for k, v in details.items():
                            console.print(f"  {k}: {v}")
                    else:
                        console.print("No details found", style="yellow")
                    
                elif choice == "6":
                    taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
                    ftas = self.client.get_franchise_tax_list(taxpayer_id=taxpayer_id)
                    if ftas:
                        console.print(f"\n[bold]FTAS Records ({len(ftas)}):[/bold]", style="green")
                        for i, record in enumerate(ftas, 1):
                            console.print(f"\nRecord {i}:")
                            for k, v in list(record.items())[:10]:
                                console.print(f"  {k}: {v}")
                    else:
                        console.print("No FTAS records found", style="yellow")
                    
                elif choice == "7":
                    if self.last_data:
                        self.export_comptroller_data(self.last_data)
                    else:
                        console.print("\nNo data to export", style="yellow")
                    
                elif choice == "8":
                    stats = self.client.rate_limiter.get_stats()
                    table = Table(title="Rate Limiter Stats")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    for k, v in stats.items():
                        table.add_row(k, str(v))
                    console.print("\n")
                    console.print(table)
                    
                else:
                    console.print("\nInvalid option", style="red")
                    
            except KeyboardInterrupt:
                console.print("\n\nOperation cancelled", style="yellow")
                if Confirm.ask("Exit?", default=False):
                    break
            except Exception as e:
                console.print(f"\nError: {e}", style="red bold")
                logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    cli = ComptrollerScraperCLI()
    cli.run()