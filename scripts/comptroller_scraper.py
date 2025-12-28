#!/usr/bin/env python3
"""
Comptroller Data Scraper - Interactive CLI
Fetch detailed taxpayer data from Texas Comptroller API
With GPU acceleration, caching, and advanced features
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

# Use wrapper classes instead of direct API clients
from src.scrapers.comptroller_scraper import ComptrollerScraper, SmartComptrollerScraper, BulkComptrollerScraper
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from src.utils.helpers import clean_taxpayer_id, format_bytes
from src.processors.data_validator import DataValidator
from src.utils.progress_manager import get_all_saved_progress
from config.settings import (
    comptroller_config,
    COMPTROLLER_EXPORT_DIR,
    SOCRATA_EXPORT_DIR,
    batch_config
)

console = Console()
logger = get_logger(__name__)


class ComptrollerScraperCLI:
    """Interactive CLI for Comptroller data scraping with GPU support"""
    
    def __init__(self):
        # Use SmartComptrollerScraper wrapper with caching and GPU
        self.scraper = SmartComptrollerScraper()
        self.bulk_scraper = BulkComptrollerScraper()
        self.exporter = FileExporter(COMPTROLLER_EXPORT_DIR)
        self.validator = DataValidator()  # Add validator
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
        
        # Show GPU status
        if self.scraper.gpu.gpu_available:
            console.print(f"✓ GPU Acceleration: Enabled ({self.scraper.gpu.device_name})", style="green")
        else:
            console.print("⚠ GPU Acceleration: Not available (using CPU)", style="yellow")
        
        # Show caching status
        console.print("✓ Smart Caching: Enabled", style="green")
    
    def show_main_menu(self) -> str:
        """Display main menu"""
        console.print("\n" + "="*60, style="bold")
        console.print("MAIN MENU", style="bold cyan")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        
        # Auto-detect options
        table.add_row("1", "Process Socrata Export (Auto-detect)")
        table.add_row("2", "Process Socrata Export (Manual path)")
        table.add_row("3", "📁 Process ALL Socrata Files (combined)")
        table.add_row("4", "Batch Process Taxpayer IDs from file")
        table.add_row("", "")
        
        # Single lookup
        table.add_row("5", "Single Taxpayer Lookup (details + FTAS)")
        table.add_row("6", "Single Taxpayer - Details Only")
        table.add_row("7", "Single Taxpayer - FTAS Only")
        table.add_row("", "")
        
        # Advanced features
        table.add_row("8", "🚀 Enrich Socrata Data Directly")
        table.add_row("9", "📊 Scrape with Validation (clean IDs)")
        table.add_row("10", "💾 Scrape with Caching (skip duplicates)")
        table.add_row("11", "🔍 Search by Business Name (batch)")
        table.add_row("", "")
        
        # Utilities
        table.add_row("12", "Export Last Retrieved Data")
        table.add_row("13", "View Rate Limiter Stats")
        table.add_row("14", "View GPU/Scraper Stats")
        table.add_row("15", "View Cache Stats")
        table.add_row("16", "Clear Cache")
        table.add_row("", "")
        # Validation options
        table.add_row("17", "📊 Validate & Clean Data")
        table.add_row("18", "🧹 View Data Quality Report")
        table.add_row("", "")
        # Recovery options
        table.add_row("19", "🔄 Resume Last Session")
        table.add_row("20", "🗑 View/Clear Saved Progress")
        table.add_row("", "")
        table.add_row("0", "Exit")
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
    def detect_socrata_files(self, json_only: bool = True) -> list:
        """
        Auto-detect Socrata export files (JSON only to avoid duplicates)
        
        Args:
            json_only: If True, only return JSON files (default)
        """
        socrata_dir = Path(SOCRATA_EXPORT_DIR)
        
        # Only get JSON files (CSV/Excel contain same data, would cause duplicates)
        json_files = [f for f in socrata_dir.glob("*.json") if '.checksum' not in f.name]
        
        # Sort by modification time (newest first)
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return json_files
    
    def show_file_selector(self, files: list):
        """Show file selection menu - returns Path or list of Paths"""
        console.print("\n[bold]Available Socrata Export JSON Files:[/bold]")
        
        table = Table()
        table.add_column("#", style="cyan", width=4)
        table.add_column("Filename", style="white")
        table.add_column("Size", style="yellow")
        table.add_column("Modified", style="green")
        
        # Add "All Files" option
        table.add_row("0", "📁 ALL FILES", "-", "-")
        
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
            "\nSelect file number (0 for all)",
            choices=["0"] + [str(i) for i in range(1, min(len(files), 20) + 1)],
            default="0"
        )
        
        if choice == "0":
            # Only return JSON files to avoid duplicates (CSV/Excel contain same data)
            json_files = [f for f in files if f.suffix == '.json']
            console.print(f"  ✓ Selected {len(json_files)} JSON files (skipping CSV to avoid duplicates)", style="green")
            return json_files  # Return list of JSON files only
        else:
            return files[int(choice) - 1]  # Return single file
    
    def extract_taxpayer_ids(self, data: list) -> list:
        """
        Extract taxpayer IDs from Socrata data using smart field detection
        (case-insensitive, handles all field name variations)
        
        Args:
            data: Socrata export data
            
        Returns:
            List of cleaned taxpayer IDs
        """
        from src.utils.helpers import extract_taxpayer_id_from_record
        
        taxpayer_ids = []
        
        for record in data:
            # Use smart extraction that handles all field name variations
            cleaned_id = extract_taxpayer_id_from_record(record)
            
            if cleaned_id and cleaned_id not in taxpayer_ids:
                taxpayer_ids.append(cleaned_id)
        
        return taxpayer_ids
    
    def process_socrata_auto(self):
        """Auto-detect and process Socrata files"""
        files = self.detect_socrata_files()
        
        if not files:
            console.print("\n⚠ No Socrata export files found", style="yellow")
            console.print(f"Expected location: {SOCRATA_EXPORT_DIR}", style="yellow")
            return
        
        # Select file(s)
        selection = self.show_file_selector(files)
        
        # Handle single file or list of files
        if isinstance(selection, list):
            # Process ALL files
            console.print(f"\n[bold]Processing {len(selection)} files...[/bold]")
            all_taxpayer_ids = set()
            
            for file in selection:
                console.print(f"  Loading {file.name}...")
                try:
                    data = self.exporter.auto_load(file)
                    ids = self.extract_taxpayer_ids(data)
                    all_taxpayer_ids.update(ids)
                    console.print(f"    ✓ {len(ids):,} IDs", style="green")
                except Exception as e:
                    console.print(f"    ⚠ Error: {e}", style="yellow")
            
            console.print(f"\n✓ Total unique IDs: {len(all_taxpayer_ids):,}", style="green bold")
            
            if not all_taxpayer_ids:
                console.print("⚠ No taxpayer IDs found in data", style="yellow")
                return
            
            # Process all IDs
            self.batch_process_taxpayer_ids(list(all_taxpayer_ids), source_name="all_socrata_files")
        else:
            # Process single file
            selected_file = selection
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
                
                # Extract source name from filename for separate export files
                source_name = selected_file.stem  # e.g., "franchise_tax_permit_holders"
                
                # Process taxpayer IDs with source tracking
                self.batch_process_taxpayer_ids(taxpayer_ids, source_name=source_name)
                
            except Exception as e:
                console.print(f"Error: {e}", style="red bold")
                logger.error(f"Processing error: {e}")
    
    def process_all_socrata_files(self):
        """Process ALL Socrata export files at once (combined)"""
        console.print("\n[bold]📁 Process ALL Socrata Files[/bold]")
        console.print("This will extract taxpayer IDs from ALL Socrata JSON exports and process them.")
        console.print("(Using JSON only to avoid duplication with CSV/Excel)\n")
        
        # Use json_only=True to avoid duplication (CSV/Excel have same data)
        files = self.detect_socrata_files(json_only=True)
        
        if not files:
            console.print("⚠ No Socrata export files found", style="yellow")
            console.print(f"Expected location: {SOCRATA_EXPORT_DIR}", style="yellow")
            return
        
        # Show what will be processed
        console.print(f"[bold]Found {len(files)} Socrata export files:[/bold]")
        total_size = 0
        for i, f in enumerate(files[:20], 1):
            size_mb = f.stat().st_size / (1024 * 1024)
            total_size += size_mb
            console.print(f"  {i}. {f.name} ({size_mb:.1f} MB)")
        
        if len(files) > 20:
            console.print(f"  ... and {len(files) - 20} more files")
        
        console.print(f"\n[bold]Total size: {total_size:.1f} MB[/bold]")
        
        if not Confirm.ask("\nProcess all these files?", default=True):
            return
        
        # Load all files and extract unique taxpayer IDs
        console.print("\n[bold]Loading all files...[/bold]")
        
        all_taxpayer_ids = set()
        total_records = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading files...", total=len(files))
            
            for filepath in files:
                try:
                    # Skip checksum files
                    if '.checksum' in filepath.name:
                        progress.advance(task)
                        continue
                    
                    data = self.exporter.auto_load(filepath)
                    total_records += len(data)
                    
                    # Extract IDs from this file
                    file_ids = self.extract_taxpayer_ids(data)
                    all_taxpayer_ids.update(file_ids)
                    
                    progress.advance(task)
                    
                except Exception as e:
                    logger.warning(f"Could not load {filepath.name}: {e}")
                    progress.advance(task)
                    continue
        
        taxpayer_ids = list(all_taxpayer_ids)
        
        console.print(f"\n✓ Loaded {total_records:,} total records from {len(files)} files", style="green")
        console.print(f"✓ Found {len(taxpayer_ids):,} unique taxpayer IDs", style="green bold")
        
        if not taxpayer_ids:
            console.print("⚠ No taxpayer IDs found in any files", style="yellow")
            return
        
        # Ask for processing limit (optional)
        if len(taxpayer_ids) > 1000:
            console.print(f"\n⚠ Large dataset: {len(taxpayer_ids):,} IDs", style="yellow")
            limit = Prompt.ask(
                "Limit processing? (0 for all)",
                default="0"
            )
            limit = int(limit) if limit.isdigit() else 0
            if limit > 0:
                taxpayer_ids = taxpayer_ids[:limit]
                console.print(f"Limited to first {limit:,} IDs", style="cyan")
        
        # Process all taxpayer IDs with combined source name
        self.batch_process_taxpayer_ids(taxpayer_ids, source_name="all_socrata_combined")
    
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
                # Use filename as source for separate export files
                source_name = filepath.stem
                self.batch_process_taxpayer_ids(taxpayer_ids, source_name=source_name)
            else:
                console.print("⚠ No taxpayer IDs found", style="yellow")
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Processing error: {e}")
    
    def batch_process_taxpayer_ids(self, taxpayer_ids: list, source_name: str = None):
        """
        Batch process taxpayer IDs using scraper wrapper
        
        Args:
            taxpayer_ids: List of taxpayer IDs to process
            source_name: Source dataset name for separate export files (optional)
        """
        console.print(f"\n[bold]Processing {len(taxpayer_ids):,} taxpayers...[/bold]")
        
        if self.scraper.gpu.use_gpu:
            console.print("🚀 GPU acceleration enabled", style="cyan")
        
        # Ask for processing method
        console.print("\nProcessing Method:")
        console.print("1. Synchronous (slower, more stable)")
        console.print("2. Asynchronous (faster, uses concurrency)")
        console.print("3. With Caching (skip already processed)")
        
        method = Prompt.ask("Select method", choices=["1", "2", "3"], default="3")
        
        try:
            if method == "3":
                # Use cached scraping
                console.print("\n[bold]Using cached scraping...[/bold]")
                results = self.scraper.scrape_with_cache(taxpayer_ids, cache_enabled=True)
            elif method == "2":
                # Async processing via bulk scraper
                console.print("\n[bold]Using async processing...[/bold]")
                results = self.bulk_scraper.bulk_scrape_sync(taxpayer_ids)
            else:
                # Sync processing
                results = self.scraper.scrape_taxpayer_details(taxpayer_ids)
            
            # Store results with source name for later export
            self.last_data = results
            self._last_source_name = source_name  # Track source for export
            
            # Show summary
            self.show_processing_summary(results)
            
            # Export with source-specific filename
            if Confirm.ask("\nExport results?", default=True):
                self.export_comptroller_data(results, source_name=source_name)
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Batch processing error: {e}")
    
    def enrich_socrata_data(self):
        """Enrich Socrata data directly (NEW)"""
        console.print("\n[bold]🚀 Enrich Socrata Data[/bold]")
        console.print("This will add Comptroller data to your Socrata export\n")
        
        files = self.detect_socrata_files()
        if not files:
            console.print("⚠ No Socrata export files found", style="yellow")
            return
        
        selected_file = self.show_file_selector(files)
        
        console.print(f"\n[bold]Loading {selected_file.name}...[/bold]")
        try:
            socrata_data = self.exporter.auto_load(selected_file)
            console.print(f"✓ Loaded {len(socrata_data):,} Socrata records", style="green")
            
            # Use scraper's enrichment feature
            console.print("\n[bold]Enriching with Comptroller data...[/bold]")
            
            enriched_data = self.scraper.enrich_socrata_data(
                socrata_data,
                id_field='taxpayer_number'
            )
            
            console.print(f"✓ Enriched {len(enriched_data):,} records", style="green bold")
            
            self.last_data = enriched_data
            
            if Confirm.ask("\nExport enriched data?", default=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"enriched_data_{timestamp}"
                
                paths = self.exporter.export_all_formats(enriched_data, base_filename)
                for fmt, path in paths.items():
                    console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
                    
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Enrichment error: {e}")
    
    def scrape_with_validation(self):
        """Scrape with ID validation (NEW)"""
        console.print("\n[bold]📊 Scrape with Validation[/bold]")
        console.print("Validates and cleans taxpayer IDs before scraping\n")
        
        files = self.detect_socrata_files()
        if not files:
            console.print("⚠ No Socrata export files found", style="yellow")
            return
        
        selected_file = self.show_file_selector(files)
        
        console.print(f"\n[bold]Loading and validating...[/bold]")
        try:
            data = self.exporter.auto_load(selected_file)
            taxpayer_ids = self.extract_taxpayer_ids(data)
            
            console.print(f"✓ Extracted {len(taxpayer_ids):,} IDs", style="green")
            
            # Use validated scraping
            results = self.scraper.scrape_with_validation(
                taxpayer_ids,
                validate_id=True
            )
            
            self.last_data = results
            self.show_processing_summary(results)
            
            if Confirm.ask("\nExport results?", default=True):
                self.export_comptroller_data(results)
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def search_by_business_name(self):
        """Search by business name (NEW)"""
        console.print("\n[bold]🔍 Search by Business Name[/bold]")
        
        names_input = Prompt.ask("Enter business names (comma-separated)")
        names = [n.strip() for n in names_input.split(",") if n.strip()]
        
        if not names:
            console.print("No names provided", style="yellow")
            return
        
        max_per_name = int(Prompt.ask("Max results per name", default="10"))
        
        console.print(f"\n[bold]Searching {len(names)} names...[/bold]")
        
        try:
            results = self.scraper.scrape_by_name(names, max_per_name=max_per_name)
            
            total_matches = sum(len(v) for v in results.values())
            console.print(f"\n✓ Found {total_matches:,} total matches", style="green bold")
            
            for name, matches in results.items():
                console.print(f"  {name}: {len(matches)} matches")
            
            # Flatten results
            all_matches = []
            for matches in results.values():
                all_matches.extend(matches)
            
            if all_matches:
                self.last_data = all_matches
                if Confirm.ask("\nExport results?", default=True):
                    self.export_comptroller_data(all_matches)
                    
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
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
        table.add_row("With Details", str(with_details), f"{with_details/total*100:.1f}%" if total > 0 else "0%")
        table.add_row("With FTAS Records", str(with_ftas), f"{with_ftas/total*100:.1f}%" if total > 0 else "0%")
        table.add_row("Errors", str(errors), f"{errors/total*100:.1f}%" if total > 0 else "0%")
        
        console.print("\n")
        console.print(table)
    
    def single_taxpayer_lookup(self):
        """Single taxpayer complete lookup (terminal only)"""
        taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
        
        console.print(f"\n[bold]Fetching data for {taxpayer_id}...[/bold]")
        
        try:
            info = self.scraper.client.get_complete_taxpayer_info(taxpayer_id)
            
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
    
    def export_comptroller_data(self, data: list, source_name: str = None):
        """
        Export comptroller data (APPENDS to existing files)
        Uses source-specific filename if source_name provided.
        
        Args:
            data: List of comptroller records
            source_name: Source Socrata dataset name (optional)
                         If provided, exports to comptroller_{source_name}.json
                         If None, exports to comptroller_data.json (generic)
        """
        # Create source-specific filename or use generic
        if source_name:
            # Clean the source name and prefix with "comptroller_"
            clean_source = source_name.lower().replace(' ', '_').replace('-', '_')
            base_filename = f"comptroller_{clean_source}"
        else:
            base_filename = "comptroller_data"
        
        console.print(f"\n[bold]Exporting {len(data):,} records (append mode)...[/bold]")
        console.print(f"Target: {base_filename}.*", style="cyan")
        
        try:
            # Flatten data for export
            flattened_data = self.flatten_comptroller_data(data)
            
            # Use append_or_create - appends to existing or creates new
            paths = self.exporter.append_or_create_all_formats(flattened_data, base_filename)
            
            for format_name, path in paths.items():
                console.print(f"✓ {format_name.upper()}: {path}", style="green")
            
            console.print(f"\n✓ Export complete! (appended to existing files)", style="green bold")
            
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
    
    def show_scraper_stats(self):
        """Show scraper and GPU statistics"""
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
    
    def show_cache_stats(self):
        """Show cache statistics"""
        stats = self.scraper.get_cache_stats()
        
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Cached Items", str(stats['cached_items']))
        table.add_row("Cache Size", f"{stats['cache_size_bytes'] / 1024:.1f} KB")
        
        console.print("\n")
        console.print(table)
    
    def validate_and_clean_data(self):
        """Validate and clean last retrieved data"""
        console.print("\n[bold]📊 Validate & Clean Data[/bold]")
        
        if not self.last_data:
            console.print("⚠ No data available. Process some data first.", style="yellow")
            return
        
        console.print(f"\nCleaning {len(self.last_data):,} records...")
        
        # Flatten for cleaning
        flat_data = self.flatten_comptroller_data(self.last_data)
        
        # Clean data
        cleaned_data = self.validator.clean_dataset(flat_data)
        
        # Standardize field names
        console.print("Standardizing field names...")
        standardized_data = self.validator.standardize_dataset(cleaned_data)
        
        # Validate
        console.print("Validating...")
        report = self.validator.validate_dataset(standardized_data)
        
        console.print(f"\n✓ Cleaned and validated {len(standardized_data):,} records", style="green bold")
        console.print(f"  Valid: {report['valid_records']:,} ({report['validation_rate']:.1f}%)")
        console.print(f"  Invalid: {report['invalid_records']:,}")
        
        # Export
        if Confirm.ask("\nExport cleaned data?", default=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paths = self.exporter.export_all_formats(standardized_data, f"comptroller_cleaned_{timestamp}")
            for fmt, path in paths.items():
                console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
    
    def view_data_quality_report(self):
        """View data quality report for last retrieved data"""
        console.print("\n[bold]🧹 Data Quality Report[/bold]")
        
        if not self.last_data:
            console.print("⚠ No data available. Process some data first.", style="yellow")
            return
        
        # Flatten for analysis
        flat_data = self.flatten_comptroller_data(self.last_data)
        
        console.print(f"\nAnalyzing {len(flat_data):,} records...")
        
        # Generate quality report
        report = self.validator.get_data_quality_report(flat_data)
        
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
    
    def resume_session(self):
        """Resume an interrupted scraping session"""
        console.print("\n[bold]🔄 Resume Last Session[/bold]")
        
        # Check for saved progress
        saved = get_all_saved_progress()
        comptroller_sessions = [s for s in saved if 'comptroller' in s.get('operation', '').lower()]
        
        if not comptroller_sessions:
            console.print("⚠ No saved sessions found", style="yellow")
            return
        
        # Show available sessions
        console.print("\n[bold]Available sessions to resume:[/bold]")
        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Operation", style="white")
        table.add_column("Completed", style="green")
        table.add_column("Pending", style="yellow")
        table.add_column("Last Checkpoint", style="dim")
        
        for i, session in enumerate(comptroller_sessions, 1):
            table.add_row(
                str(i),
                session.get('operation', 'Unknown'),
                str(session.get('completed', 0)),
                str(session.get('pending', 0)),
                session.get('last_checkpoint', 'Unknown')[:19] if session.get('last_checkpoint') else 'Unknown'
            )
        
        console.print(table)
        
        choice = Prompt.ask("Select session to resume (or 0 to cancel)", default="1")
        
        if choice == "0":
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(comptroller_sessions):
                session = comptroller_sessions[idx]
                operation_name = session.get('operation', 'comptroller_scrape')
                
                console.print(f"\n[bold]Resuming {operation_name}...[/bold]")
                
                # Resume using scraper's progress feature
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.completed}/{task.total}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Processing...", total=session.get('pending', 0) + session.get('completed', 0))
                    
                    def update_progress(current, total):
                        progress.update(task, completed=current, total=total)
                    
                    results = self.scraper.scrape_with_progress(
                        [],  # Will load from checkpoint
                        operation_name=operation_name,
                        progress_callback=update_progress
                    )
                
                if results:
                    self.last_data = results
                    console.print(f"\n✓ Resumed and completed! {len(results)} records", style="green bold")
                    
                    if Confirm.ask("Export data?", default=True):
                        self.export_comptroller_data(results)
        except (ValueError, IndexError):
            console.print("Invalid selection", style="red")
    
    def manage_saved_progress(self):
        """View and manage saved progress sessions"""
        console.print("\n[bold]🗑 Manage Saved Progress[/bold]")
        
        saved = get_all_saved_progress()
        
        if not saved:
            console.print("⚠ No saved progress found", style="yellow")
            return
        
        # Show all sessions
        console.print("\n[bold]All saved sessions:[/bold]")
        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Operation", style="white")
        table.add_column("Completed", style="green")
        table.add_column("Pending", style="yellow")
        table.add_column("Last Checkpoint", style="dim")
        
        for i, session in enumerate(saved, 1):
            table.add_row(
                str(i),
                session.get('operation', 'Unknown'),
                str(session.get('completed', 0)),
                str(session.get('pending', 0)),
                session.get('last_checkpoint', 'Unknown')[:19] if session.get('last_checkpoint') else 'Unknown'
            )
        
        console.print(table)
        
        console.print("\n[bold]Options:[/bold]")
        console.print("  [cyan]1.[/cyan] Clear specific session")
        console.print("  [cyan]2.[/cyan] Clear all sessions")
        console.print("  [cyan]0.[/cyan] Cancel")
        
        choice = Prompt.ask("Select option", default="0")
        
        if choice == "1":
            session_num = Prompt.ask("Enter session number to clear")
            try:
                idx = int(session_num) - 1
                if 0 <= idx < len(saved):
                    from src.utils.progress_manager import ProgressManager
                    pm = ProgressManager(saved[idx].get('operation', ''))
                    pm.clear_progress()
                    console.print("✓ Session cleared", style="green")
            except (ValueError, IndexError):
                console.print("Invalid selection", style="red")
        elif choice == "2":
            if Confirm.ask("Clear ALL saved progress?", default=False):
                from src.utils.progress_manager import clear_all_progress
                count = clear_all_progress()
                console.print(f"✓ Cleared {count} files", style="green")
    
    
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
                    self.process_all_socrata_files()
                    
                elif choice == "4":
                    console.print("\nBatch from file - Coming soon!", style="yellow")
                    
                elif choice == "5":
                    self.single_taxpayer_lookup()
                    
                elif choice == "6":
                    taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
                    details = self.scraper.client.get_franchise_tax_details(taxpayer_id)
                    if details:
                        console.print("\n[bold]Details:[/bold]", style="green")
                        for k, v in details.items():
                            console.print(f"  {k}: {v}")
                    else:
                        console.print("No details found", style="yellow")
                    
                elif choice == "7":
                    taxpayer_id = Prompt.ask("\nEnter Taxpayer ID")
                    ftas = self.scraper.client.get_franchise_tax_list(taxpayer_id=taxpayer_id)
                    if ftas:
                        console.print(f"\n[bold]FTAS Records ({len(ftas)}):[/bold]", style="green")
                        for i, record in enumerate(ftas, 1):
                            console.print(f"\nRecord {i}:")
                            for k, v in list(record.items())[:10]:
                                console.print(f"  {k}: {v}")
                    else:
                        console.print("No FTAS records found", style="yellow")
                    
                elif choice == "8":
                    self.enrich_socrata_data()
                    
                elif choice == "9":
                    self.scrape_with_validation()
                    
                elif choice == "10":
                    files = self.detect_socrata_files()
                    if files:
                        selected_file = self.show_file_selector(files)
                        data = self.exporter.auto_load(selected_file)
                        taxpayer_ids = self.extract_taxpayer_ids(data)
                        console.print(f"\n[bold]Processing with caching...[/bold]")
                        results = self.scraper.scrape_with_cache(taxpayer_ids)
                        self.last_data = results
                        self.show_processing_summary(results)
                        if Confirm.ask("\nExport?", default=True):
                            self.export_comptroller_data(results)
                    
                elif choice == "11":
                    self.search_by_business_name()
                    
                elif choice == "12":
                    if self.last_data:
                        self.export_comptroller_data(self.last_data)
                    else:
                        console.print("\nNo data to export", style="yellow")
                    
                elif choice == "13":
                    stats = self.scraper.client.rate_limiter.get_stats()
                    table = Table(title="Rate Limiter Stats")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    for k, v in stats.items():
                        table.add_row(k, str(v))
                    console.print("\n")
                    console.print(table)
                    
                elif choice == "14":
                    self.show_scraper_stats()
                    
                elif choice == "15":
                    self.show_cache_stats()
                    
                elif choice == "16":
                    self.scraper.clear_cache()
                    console.print("\n✓ Cache cleared", style="green")
                    
                elif choice == "17":
                    self.validate_and_clean_data()
                    
                elif choice == "18":
                    self.view_data_quality_report()
                    
                elif choice == "19":
                    self.resume_session()
                    
                elif choice == "20":
                    self.manage_saved_progress()
                    
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