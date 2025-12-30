#!/usr/bin/env python3
"""
Data Combiner - Interactive CLI
Combine Socrata and Comptroller data intelligently
With GPU acceleration and data quality features
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.processors.data_combiner import DataCombiner, SmartDataCombiner
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import (
    SOCRATA_EXPORT_DIR,
    COMPTROLLER_EXPORT_DIR,
    COMBINED_EXPORT_DIR,
    POLISHED_EXPORT_DIR,
    PLACES_DETAILS_EXPORT_DIR,
    FINAL_EXPORT_DIR
)

# Import utility modules
from src.scrapers.gpu_accelerator import get_gpu_accelerator
from src.processors.data_validator import DataValidator
from src.utils.helpers import format_bytes, flatten_dict, merge_dicts

console = Console()
logger = get_logger(__name__)


class DataCombinerCLI:
    """Interactive CLI for data combination with GPU acceleration"""
    
    def __init__(self):
        self.combiner = SmartDataCombiner()
        self.exporter = FileExporter(COMBINED_EXPORT_DIR)
        # Initialize GPU accelerator and validator
        self.gpu = get_gpu_accelerator()
        self.validator = DataValidator()
        self.last_combined_data = None
        
    def show_banner(self):
        """Show welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║            DATA COMBINER - MERGE & ENRICH DATA           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
        
        # Show GPU status
        if self.gpu.gpu_available:
            console.print(f"✓ GPU Acceleration: Enabled ({self.gpu.device_name if hasattr(self.gpu, 'device_name') else 'Available'})", style="green")
        else:
            console.print("⚠ GPU Acceleration: Not available (using CPU)", style="yellow")
    
    def show_main_menu(self) -> str:
        """Display main menu"""
        console.print("\n" + "="*60, style="bold")
        console.print("MAIN MENU", style="bold cyan")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        
        table.add_row("1", "Combine JSON files (Socrata + Comptroller)")
        table.add_row("2", "Combine CSV files (Socrata + Comptroller)")
        table.add_row("3", "Combine Excel files (Socrata + Comptroller)")
        table.add_row("", "")
        table.add_row("4", "Auto-detect and combine latest exports")
        table.add_row("5", "Manual file path combination")
        table.add_row("", "")
        # Master combine option
        table.add_row("6", "🌟 MASTER COMBINE ALL (merge all datasets)")
        table.add_row("", "")
        # GPU-accelerated options
        table.add_row("7", "🚀 GPU-Accelerated Combine (faster for large datasets)")
        table.add_row("", "")
        # Data quality options
        table.add_row("8", "📊 View Data Quality Report")
        table.add_row("9", "🧹 Clean & Validate Combined Data")
        table.add_row("", "")
        table.add_row("10", "View combination statistics")
        table.add_row("11", "View GPU/Memory Stats")
        table.add_row("", "")
        # Manual granular combine options
        table.add_row("12", "📂 Manual Combine Options (9 granular options)")
        table.add_row("", "")
        # Google Places combine option
        table.add_row("13", "🌍 Combine Google Places with Polished Data")
        table.add_row("", "")
        table.add_row("0", "Exit")
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
    def get_latest_file(self, directory: Path, pattern: str) -> Path:
        """Get latest file matching pattern"""
        files = list(directory.glob(pattern))
        if not files:
            return None
        
        # Sort by modification time
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files[0]
    
    def show_file_selector(self, directory: Path, pattern: str, label: str) -> Path:
        """Show file selection menu with file size info"""
        files = list(directory.glob(pattern))
        
        if not files:
            console.print(f"\n⚠ No {label} files found in {directory}", style="yellow")
            return None
        
        console.print(f"\n[bold]Available {label} files:[/bold]")
        
        table = Table()
        table.add_column("#", style="cyan", width=4)
        table.add_column("Filename", style="white")
        table.add_column("Size", style="yellow")
        table.add_column("Modified", style="green")
        
        for i, file in enumerate(files[:20], 1):
            file_size = file.stat().st_size
            mod_time = datetime.fromtimestamp(file.stat().st_mtime)
            
            table.add_row(
                str(i),
                file.name,
                format_bytes(file_size),  # Using helpers.format_bytes
                mod_time.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        
        choice = Prompt.ask(
            f"\nSelect {label} file",
            choices=[str(i) for i in range(1, min(len(files), 20) + 1)]
        )
        
        return files[int(choice) - 1]
    
    def combine_files(self, file_format: str):
        """Combine files of specific format"""
        console.print(f"\n[bold]Combining {file_format.upper()} files...[/bold]")
        
        # Get file pattern
        patterns = {
            'json': '*.json',
            'csv': '*.csv',
            'excel': '*.xlsx'
        }
        pattern = patterns.get(file_format)
        
        # Select Socrata file
        socrata_file = self.show_file_selector(
            SOCRATA_EXPORT_DIR, 
            pattern, 
            f"Socrata {file_format.upper()}"
        )
        
        if not socrata_file:
            return
        
        # Select Comptroller file
        comptroller_file = self.show_file_selector(
            COMPTROLLER_EXPORT_DIR,
            pattern,
            f"Comptroller {file_format.upper()}"
        )
        
        if not comptroller_file:
            return
        
        # Load and combine
        self._load_and_combine(socrata_file, comptroller_file, file_format)
    
    def auto_combine_latest(self):
        """Auto-detect and combine latest exports"""
        console.print("\n[bold]Auto-detecting latest exports...[/bold]")
        
        # Try JSON first
        socrata_json = self.get_latest_file(SOCRATA_EXPORT_DIR, '*.json')
        comptroller_json = self.get_latest_file(COMPTROLLER_EXPORT_DIR, '*.json')
        
        if socrata_json and comptroller_json:
            console.print(f"✓ Found Socrata JSON: {socrata_json.name} ({format_bytes(socrata_json.stat().st_size)})", style="green")
            console.print(f"✓ Found Comptroller JSON: {comptroller_json.name} ({format_bytes(comptroller_json.stat().st_size)})", style="green")
            
            if Confirm.ask("\nCombine these files?", default=True):
                self._load_and_combine(socrata_json, comptroller_json, 'json')
                return
        
        # Try CSV
        socrata_csv = self.get_latest_file(SOCRATA_EXPORT_DIR, '*.csv')
        comptroller_csv = self.get_latest_file(COMPTROLLER_EXPORT_DIR, '*.csv')
        
        if socrata_csv and comptroller_csv:
            console.print(f"✓ Found Socrata CSV: {socrata_csv.name} ({format_bytes(socrata_csv.stat().st_size)})", style="green")
            console.print(f"✓ Found Comptroller CSV: {comptroller_csv.name} ({format_bytes(comptroller_csv.stat().st_size)})", style="green")
            
            if Confirm.ask("\nCombine these files?", default=True):
                self._load_and_combine(socrata_csv, comptroller_csv, 'csv')
                return
        
        console.print("⚠ Could not find matching export files", style="yellow")
    
    def manual_combine(self):
        """Manual file path combination"""
        console.print("\n[bold]Manual File Combination[/bold]")
        
        socrata_path = Prompt.ask("Enter Socrata file path")
        comptroller_path = Prompt.ask("Enter Comptroller file path")
        
        socrata_file = Path(socrata_path)
        comptroller_file = Path(comptroller_path)
        
        if not socrata_file.exists():
            console.print(f"⚠ Socrata file not found: {socrata_file}", style="yellow")
            return
        
        if not comptroller_file.exists():
            console.print(f"⚠ Comptroller file not found: {comptroller_file}", style="yellow")
            return
        
        # Detect format
        format_map = {
            '.json': 'json',
            '.csv': 'csv',
            '.xlsx': 'excel',
            '.xls': 'excel'
        }
        
        file_format = format_map.get(socrata_file.suffix.lower(), 'json')
        
        self._load_and_combine(socrata_file, comptroller_file, file_format)
    
    def master_combine_all(self):
        """
        MASTER COMBINE ALL - Full Pipeline
        
        Step 1: Merge ALL Socrata JSON/CSV/Excel files → Master Socrata data
        Step 2: Merge ALL Comptroller JSON/CSV/Excel files → Master Comptroller data
        Step 3: Combine Master Socrata + Master Comptroller by taxpayer ID
        Step 4: Export combined data in all formats
        """
        console.print("\n[bold]🌟 MASTER COMBINE ALL[/bold]")
        console.print("This will merge ALL datasets and create master combined exports.\n")
        
        console.print("[bold]Pipeline:[/bold]")
        console.print("  1. Merge all Socrata files (JSON) → Master Socrata dataset")
        console.print("  2. Merge all Comptroller files (JSON) → Master Comptroller dataset")
        console.print("  3. Combine by taxpayer ID → Final enriched dataset")
        console.print("  4. Export to JSON, CSV, and Excel\n")
        
        if not Confirm.ask("Proceed with Master Combine?", default=True):
            return
        
        # Step 1: Merge all Socrata JSON files
        console.print("\n[cyan]Step 1/4: Merging all Socrata files...[/cyan]")
        socrata_data = self._merge_all_json_files(Path(SOCRATA_EXPORT_DIR), "Socrata")
        
        if not socrata_data:
            console.print("⚠ No Socrata data found", style="yellow")
            return
        
        console.print(f"✓ Master Socrata dataset: {len(socrata_data):,} records", style="green")
        
        # Step 2: Merge all Comptroller JSON files
        console.print("\n[cyan]Step 2/4: Merging all Comptroller files...[/cyan]")
        comptroller_data = self._merge_all_json_files(Path(COMPTROLLER_EXPORT_DIR), "Comptroller")
        
        if not comptroller_data:
            console.print("⚠ No Comptroller data found", style="yellow")
            return
        
        console.print(f"✓ Master Comptroller dataset: {len(comptroller_data):,} records", style="green")
        
        # Step 3: Combine by taxpayer ID
        console.print("\n[cyan]Step 3/4: Combining datasets by taxpayer ID...[/cyan]")
        
        try:
            combined_data = self.combiner.combine_by_taxpayer_id(
                socrata_data,
                comptroller_data
            )
            
            console.print(f"✓ Combined dataset: {len(combined_data):,} unique records", style="green bold")
            
        except Exception as e:
            console.print(f"Error combining: {e}", style="red")
            logger.error(f"Master combine error: {e}")
            return
        
        # Step 4: Export to all formats
        console.print("\n[cyan]Step 4/4: Exporting master combined data...[/cyan]")
        
        try:
            # Export with fixed "master_combined" filename (append mode)
            paths = self.exporter.append_or_create_all_formats(combined_data, "master_combined")
            
            for fmt, path in paths.items():
                console.print(f"✓ {fmt.upper()}: {path}", style="green")
            
            self.last_combined_data = combined_data
            
            console.print("\n" + "="*60, style="green")
            console.print("🎉 MASTER COMBINE ALL COMPLETE!", style="green bold")
            console.print("="*60, style="green")
            
            # Summary
            console.print("\n[bold]Summary:[/bold]")
            console.print(f"  • Socrata records merged: {len(socrata_data):,}")
            console.print(f"  • Comptroller records merged: {len(comptroller_data):,}")
            console.print(f"  • Final combined records: {len(combined_data):,}")
            console.print(f"  • Output: exports/combined/master_combined.*")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red")
            logger.error(f"Master export error: {e}")
    
    def _merge_all_json_files(self, directory: Path, source_name: str) -> list:
        """
        Merge all JSON files from a directory into one dataset.
        Uses deduplication by taxpayer ID to avoid duplicates.
        
        Args:
            directory: Path to directory containing JSON files
            source_name: Name for logging (e.g., "Socrata", "Comptroller")
            
        Returns:
            List of merged records (deduplicated by taxpayer ID)
        """
        from src.utils.helpers import extract_taxpayer_id_from_record
        
        # Find all JSON files (exclude checksum files)
        json_files = [f for f in directory.glob("*.json") if '.checksum' not in f.name]
        
        if not json_files:
            console.print(f"  No JSON files found in {directory}", style="yellow")
            return []
        
        console.print(f"  Found {len(json_files)} {source_name} JSON files")
        
        merged_data = []
        seen_ids = set()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Merging {source_name} files...", total=len(json_files))
            
            for filepath in json_files:
                try:
                    data = self.exporter.auto_load(filepath)
                    
                    for record in data:
                        # Deduplicate by taxpayer ID
                        taxpayer_id = extract_taxpayer_id_from_record(record)
                        
                        if taxpayer_id:
                            if taxpayer_id not in seen_ids:
                                seen_ids.add(taxpayer_id)
                                merged_data.append(record)
                        else:
                            # No taxpayer ID - include anyway but may have duplicates
                            merged_data.append(record)
                    
                    progress.advance(task)
                    
                except Exception as e:
                    logger.warning(f"Could not load {filepath.name}: {e}")
                    progress.advance(task)
                    continue
        
        console.print(f"  Merged {len(merged_data):,} unique records from {len(json_files)} files")
        return merged_data
    
    def show_manual_combine_menu(self):
        """Show submenu for manual granular combine options"""
        console.print("\n" + "="*60, style="bold")
        console.print("📂 MANUAL COMBINE OPTIONS", style="bold cyan")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        
        table.add_row("", "[bold]Socrata Only:[/bold]")
        table.add_row("1", "Combine all Socrata JSON files")
        table.add_row("2", "Combine all Socrata CSV files")
        table.add_row("3", "Combine all Socrata Excel files")
        table.add_row("", "")
        table.add_row("", "[bold]Comptroller Only:[/bold]")
        table.add_row("4", "Combine all Comptroller JSON files")
        table.add_row("5", "Combine all Comptroller CSV files")
        table.add_row("6", "Combine all Comptroller Excel files")
        table.add_row("", "")
        table.add_row("", "[bold]Cross-Source (by Taxpayer ID):[/bold]")
        table.add_row("7", "Combine all JSON (Socrata + Comptroller)")
        table.add_row("8", "Combine all CSV (Socrata + Comptroller)")
        table.add_row("9", "Combine all Excel (Socrata + Comptroller)")
        table.add_row("", "")
        table.add_row("0", "Back to Main Menu")
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
    def handle_manual_combine(self):
        """Handle manual combine submenu"""
        while True:
            choice = self.show_manual_combine_menu()
            
            if choice == "0":
                break
            elif choice == "1":
                self.combine_single_source("socrata", "json")
            elif choice == "2":
                self.combine_single_source("socrata", "csv")
            elif choice == "3":
                self.combine_single_source("socrata", "excel")
            elif choice == "4":
                self.combine_single_source("comptroller", "json")
            elif choice == "5":
                self.combine_single_source("comptroller", "csv")
            elif choice == "6":
                self.combine_single_source("comptroller", "excel")
            elif choice == "7":
                self.combine_cross_source("json")
            elif choice == "8":
                self.combine_cross_source("csv")
            elif choice == "9":
                self.combine_cross_source("excel")
            else:
                console.print("Invalid option", style="red")
    
    def _merge_all_files_by_format(self, directory: Path, file_format: str, source_name: str) -> list:
        """
        Merge all files of a specific format from a directory.
        
        Args:
            directory: Path to directory
            file_format: 'json', 'csv', or 'excel'
            source_name: Name for logging
            
        Returns:
            List of merged records (deduplicated by taxpayer ID)
        """
        from src.utils.helpers import extract_taxpayer_id_from_record
        
        # Get file pattern
        pattern_map = {
            'json': '*.json',
            'csv': '*.csv',
            'excel': '*.xlsx'
        }
        pattern = pattern_map.get(file_format, '*.json')
        
        # Find files (exclude checksum files)
        files = [f for f in directory.glob(pattern) if '.checksum' not in f.name]
        
        if not files:
            console.print(f"  No {file_format.upper()} files found in {directory}", style="yellow")
            return []
        
        console.print(f"  Found {len(files)} {source_name} {file_format.upper()} files")
        
        merged_data = []
        seen_ids = set()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Merging {source_name} {file_format.upper()}...", total=len(files))
            
            for filepath in files:
                try:
                    data = self.exporter.auto_load(filepath)
                    
                    for record in data:
                        taxpayer_id = extract_taxpayer_id_from_record(record)
                        
                        if taxpayer_id:
                            if taxpayer_id not in seen_ids:
                                seen_ids.add(taxpayer_id)
                                merged_data.append(record)
                        else:
                            merged_data.append(record)
                    
                    progress.advance(task)
                    
                except Exception as e:
                    logger.warning(f"Could not load {filepath.name}: {e}")
                    progress.advance(task)
                    continue
        
        console.print(f"  Merged {len(merged_data):,} unique records")
        return merged_data
    
    def combine_single_source(self, source: str, file_format: str):
        """
        Combine all files of one format from one source.
        
        Args:
            source: 'socrata' or 'comptroller'
            file_format: 'json', 'csv', or 'excel'
        """
        console.print(f"\n[bold]Combining all {source.title()} {file_format.upper()} files...[/bold]\n")
        
        # Get directory
        directory = Path(SOCRATA_EXPORT_DIR) if source == "socrata" else Path(COMPTROLLER_EXPORT_DIR)
        
        # Merge all files
        merged_data = self._merge_all_files_by_format(directory, file_format, source.title())
        
        if not merged_data:
            console.print("⚠ No data to combine", style="yellow")
            return
        
        console.print(f"\n✓ Total: {len(merged_data):,} records", style="green bold")
        
        # Export with distinct filename
        # Format: merged_{source}_{format} (e.g., merged_socrata_json)
        base_filename = f"merged_{source}_{file_format}"
        
        if Confirm.ask("\nExport merged data?", default=True):
            paths = self.exporter.append_or_create_all_formats(merged_data, base_filename)
            for fmt, path in paths.items():
                console.print(f"✓ {fmt.upper()}: {path}", style="green")
            
            console.print(f"\n✓ Merged {source.title()} {file_format.upper()} complete!", style="green bold")
    
    def combine_cross_source(self, file_format: str):
        """
        Combine files of one format from BOTH Socrata and Comptroller.
        Merges by taxpayer ID.
        
        Args:
            file_format: 'json', 'csv', or 'excel'
        """
        console.print(f"\n[bold]Combining all {file_format.upper()} files (Socrata + Comptroller)...[/bold]\n")
        
        # Step 1: Merge Socrata
        console.print("[cyan]Step 1/3: Merging Socrata files...[/cyan]")
        socrata_data = self._merge_all_files_by_format(
            Path(SOCRATA_EXPORT_DIR), file_format, "Socrata"
        )
        
        if not socrata_data:
            console.print("⚠ No Socrata data found", style="yellow")
            return
        
        console.print(f"✓ Socrata: {len(socrata_data):,} records", style="green")
        
        # Step 2: Merge Comptroller
        console.print("\n[cyan]Step 2/3: Merging Comptroller files...[/cyan]")
        comptroller_data = self._merge_all_files_by_format(
            Path(COMPTROLLER_EXPORT_DIR), file_format, "Comptroller"
        )
        
        if not comptroller_data:
            console.print("⚠ No Comptroller data found", style="yellow")
            return
        
        console.print(f"✓ Comptroller: {len(comptroller_data):,} records", style="green")
        
        # Step 3: Combine by taxpayer ID
        console.print("\n[cyan]Step 3/3: Combining by taxpayer ID...[/cyan]")
        
        try:
            combined_data = self.combiner.combine_by_taxpayer_id(
                socrata_data,
                comptroller_data
            )
            
            console.print(f"✓ Combined: {len(combined_data):,} unique records", style="green bold")
            
        except Exception as e:
            console.print(f"Error combining: {e}", style="red")
            return
        
        # Export with distinct filename
        # Format: combined_all_{format} (e.g., combined_all_json)
        base_filename = f"combined_all_{file_format}"
        
        if Confirm.ask("\nExport combined data?", default=True):
            paths = self.exporter.append_or_create_all_formats(combined_data, base_filename)
            for fmt, path in paths.items():
                console.print(f"✓ {fmt.upper()}: {path}", style="green")
            
            self.last_combined_data = combined_data
            console.print(f"\n✓ Cross-source {file_format.upper()} combine complete!", style="green bold")
    
    def gpu_accelerated_combine(self):
        """GPU-accelerated combination for large datasets"""
        console.print("\n[bold]🚀 GPU-Accelerated Combine[/bold]")
        
        if not self.gpu.gpu_available:
            console.print("⚠ GPU not available, will use optimized CPU merging", style="yellow")
        else:
            console.print("✓ GPU acceleration enabled", style="green")
        
        # Auto-detect files
        socrata_json = self.get_latest_file(SOCRATA_EXPORT_DIR, '*.json')
        comptroller_json = self.get_latest_file(COMPTROLLER_EXPORT_DIR, '*.json')
        
        if not socrata_json or not comptroller_json:
            console.print("⚠ Could not find JSON export files", style="yellow")
            return
        
        console.print(f"\nSocrata: {socrata_json.name} ({format_bytes(socrata_json.stat().st_size)})")
        console.print(f"Comptroller: {comptroller_json.name} ({format_bytes(comptroller_json.stat().st_size)})")
        
        if not Confirm.ask("\nProceed with GPU merge?", default=True):
            return
        
        try:
            # Load data
            console.print("\n[bold]Loading files...[/bold]")
            socrata_data = self.exporter.auto_load(socrata_json)
            comptroller_data = self.exporter.auto_load(comptroller_json)
            
            console.print(f"✓ Loaded {len(socrata_data):,} Socrata records", style="green")
            console.print(f"✓ Loaded {len(comptroller_data):,} Comptroller records", style="green")
            
            # GPU merge
            console.print("\n[bold]Performing GPU-accelerated merge...[/bold]")
            
            combined_data = self.gpu.merge_datasets_gpu(
                socrata_data,
                comptroller_data,
                on='taxpayer_id'
            )
            
            console.print(f"✓ Merged into {len(combined_data):,} records", style="green bold")
            
            # Store for later use
            self.last_combined_data = combined_data
            
            # Show stats
            self._show_merge_stats(socrata_data, comptroller_data, combined_data)
            
            # Export
            if Confirm.ask("\nExport combined data?", default=True):
                self.export_combined_data(combined_data, 'json')
                
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"GPU merge error: {e}")
    
    def _load_and_combine(self, socrata_file: Path, comptroller_file: Path, file_format: str):
        """Load and combine files"""
        try:
            # Load data
            console.print(f"\n[bold]Loading files...[/bold]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task1 = progress.add_task(f"Loading {socrata_file.name}...", total=None)
                socrata_data = self.exporter.auto_load(socrata_file)
                progress.update(task1, completed=True)
                
                task2 = progress.add_task(f"Loading {comptroller_file.name}...", total=None)
                comptroller_data = self.exporter.auto_load(comptroller_file)
                progress.update(task2, completed=True)
            
            console.print(f"✓ Loaded {len(socrata_data):,} Socrata records", style="green")
            console.print(f"✓ Loaded {len(comptroller_data):,} Comptroller records", style="green")
            
            # Combine data
            console.print("\n[bold]Combining data...[/bold]")
            
            combined_data = self.combiner.combine_by_taxpayer_id(
                socrata_data,
                comptroller_data
            )
            
            console.print(f"✓ Combined into {len(combined_data):,} records", style="green bold")
            
            # Store for later use
            self.last_combined_data = combined_data
            
            # Show statistics
            stats = self.combiner.get_combination_stats(combined_data)
            self.display_stats(stats)
            
            # Export
            if Confirm.ask("\nExport combined data?", default=True):
                self.export_combined_data(combined_data, file_format)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Combination error: {e}")
    
    def _show_merge_stats(self, socrata_data: list, comptroller_data: list, merged_data: list):
        """Show merge statistics"""
        table = Table(title="Merge Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Socrata Records", f"{len(socrata_data):,}")
        table.add_row("Comptroller Records", f"{len(comptroller_data):,}")
        table.add_row("Merged Records", f"{len(merged_data):,}")
        
        console.print("\n")
        console.print(table)
    
    def view_data_quality_report(self):
        """View data quality report for combined data"""
        console.print("\n[bold]📊 Data Quality Report[/bold]")
        
        if not self.last_combined_data:
            # Try to load most recent combined file
            combined_file = self.get_latest_file(COMBINED_EXPORT_DIR, '*.json')
            if not combined_file:
                console.print("⚠ No combined data available. Combine files first.", style="yellow")
                return
            
            console.print(f"Loading {combined_file.name}...")
            self.last_combined_data = self.exporter.auto_load(combined_file)
        
        console.print(f"\nAnalyzing {len(self.last_combined_data):,} records...")
        
        # Generate quality report
        report = self.validator.get_data_quality_report(self.last_combined_data)
        
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
        console.print("\n[bold]Field Completeness:[/bold]")
        completeness_table = Table()
        completeness_table.add_column("Field", style="cyan")
        completeness_table.add_column("Completeness", style="green", justify="right")
        
        # Sort by completeness
        sorted_fields = sorted(
            report['field_completeness'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]  # Top 15 fields
        
        for field, pct in sorted_fields:
            completeness_table.add_row(field, f"{pct:.1f}%")
        
        console.print(completeness_table)
    
    def clean_and_validate_data(self):
        """Clean and validate combined data"""
        console.print("\n[bold]🧹 Clean & Validate Data[/bold]")
        
        if not self.last_combined_data:
            combined_file = self.get_latest_file(COMBINED_EXPORT_DIR, '*.json')
            if not combined_file:
                console.print("⚠ No combined data available. Combine files first.", style="yellow")
                return
            
            console.print(f"Loading {combined_file.name}...")
            self.last_combined_data = self.exporter.auto_load(combined_file)
        
        original_count = len(self.last_combined_data)
        console.print(f"\nCleaning {original_count:,} records...")
        
        # Clean data
        cleaned_data = self.validator.clean_dataset(self.last_combined_data)
        
        # Standardize field names
        console.print("Standardizing field names...")
        standardized_data = self.validator.standardize_dataset(cleaned_data)
        
        # Validate
        console.print("Validating data...")
        validation_report = self.validator.validate_dataset(standardized_data)
        
        console.print(f"\n✓ Cleaned and validated {len(standardized_data):,} records", style="green bold")
        console.print(f"  Valid: {validation_report['valid_records']:,} ({validation_report['validation_rate']:.1f}%)")
        console.print(f"  Invalid: {validation_report['invalid_records']:,}")
        
        self.last_combined_data = standardized_data
        
        # Export cleaned data
        if Confirm.ask("\nExport cleaned data?", default=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            paths = self.exporter.export_all_formats(standardized_data, f"combined_cleaned_{timestamp}")
            for fmt, path in paths.items():
                console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
    
    def display_stats(self, stats: dict):
        """Display combination statistics"""
        table = Table(title="Combination Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")
        
        table.add_row(
            "Total Records",
            f"{stats['total_records']:,}",
            "100.0%"
        )
        table.add_row(
            "With Socrata Data",
            f"{stats['with_socrata_data']:,}",
            f"{stats['coverage_socrata']:.1f}%"
        )
        table.add_row(
            "With Comptroller Data",
            f"{stats['with_comptroller_data']:,}",
            f"{stats['coverage_comptroller']:.1f}%"
        )
        table.add_row(
            "With Both Sources",
            f"{stats['with_both_sources']:,}",
            f"{stats['coverage_both']:.1f}%"
        )
        table.add_row(
            "Only Socrata",
            f"{stats['only_socrata']:,}",
            ""
        )
        table.add_row(
            "Only Comptroller",
            f"{stats['only_comptroller']:,}",
            ""
        )
        
        console.print("\n")
        console.print(table)
    
    def show_gpu_stats(self):
        """Show GPU and memory statistics"""
        console.print("\n[bold]GPU/Memory Statistics[/bold]")
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("GPU Available", "✓ Yes" if self.gpu.gpu_available else "✗ No")
        table.add_row("GPU Enabled", "✓ Yes" if self.gpu.use_gpu else "✗ No")
        
        if self.gpu.use_gpu:
            mem_info = self.gpu.get_gpu_memory_info()
            if mem_info.get('available'):
                table.add_row("GPU Memory Used", f"{mem_info.get('used_mb', 0):.0f} MB")
                table.add_row("GPU Memory Total", f"{mem_info.get('total_mb', 0):.0f} MB")
        
        console.print("\n")
        console.print(table)
    
    def export_combined_data(self, data: list, file_format: str):
        """Export combined data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"combined_data_{timestamp}"
        
        console.print(f"\n[bold]Exporting {len(data):,} records...[/bold]")
        
        try:
            if file_format == 'json':
                path = self.exporter.export_json(data, f"{base_filename}.json")
                console.print(f"✓ Exported JSON: {path}", style="green")
                
            elif file_format == 'csv':
                path = self.exporter.export_csv(data, f"{base_filename}.csv")
                console.print(f"✓ Exported CSV: {path}", style="green")
                
            elif file_format == 'excel':
                path = self.exporter.export_excel(data, f"{base_filename}.xlsx")
                console.print(f"✓ Exported Excel: {path}", style="green")
            
            # Also export in all formats
            if Confirm.ask("Export in all formats?", default=True):
                paths = self.exporter.export_all_formats(data, base_filename)
                for fmt, path in paths.items():
                    console.print(f"✓ Exported {fmt.upper()}: {path}", style="green")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red bold")
    
    def combine_google_places_with_polished(self):
        """
        Combine Google Places details with Polished data
        
        - Matches by taxpayer_id
        - Adds places details to polished records
        - Records without places details remain unchanged
        - Exports to exports/final/
        """
        console.print("\n[bold cyan]🌍 Combine Google Places with Polished Data[/bold cyan]")
        console.print("[dim]Merge Google Places details into polished taxpayer records[/dim]\n")
        
        # Step 1: Select polished file
        console.print("[bold]Step 1: Select Polished Data File[/bold]")
        polished_file = self.show_file_selector(POLISHED_EXPORT_DIR, "*.json", "Polished JSON")
        if not polished_file:
            console.print("[yellow]No file selected[/yellow]")
            return
        
        # Step 2: Select places details file
        console.print("\n[bold]Step 2: Select Google Places Details File[/bold]")
        places_file = self.show_file_selector(PLACES_DETAILS_EXPORT_DIR, "*.json", "Places Details JSON")
        if not places_file:
            console.print("[yellow]No file selected[/yellow]")
            return
        
        # Load data
        console.print(f"\n[dim]Loading {polished_file.name}...[/dim]")
        import json
        try:
            with open(polished_file, 'r', encoding='utf-8') as f:
                polished_data = json.load(f)
            if isinstance(polished_data, dict) and 'data' in polished_data:
                polished_data = polished_data['data']
        except Exception as e:
            console.print(f"[red]Error loading polished file: {e}[/red]")
            return
        
        console.print(f"[dim]Loading {places_file.name}...[/dim]")
        try:
            with open(places_file, 'r', encoding='utf-8') as f:
                places_data = json.load(f)
            if isinstance(places_data, dict) and 'data' in places_data:
                places_data = places_data['data']
        except Exception as e:
            console.print(f"[red]Error loading places file: {e}[/red]")
            return
        
        console.print(f"\n[green]✓ Loaded {len(polished_data):,} polished records[/green]")
        console.print(f"[green]✓ Loaded {len(places_data):,} places details records[/green]")
        
        # Build places lookup by taxpayer_id
        console.print("\n[dim]Building places lookup index...[/dim]")
        places_lookup = {}
        for place in places_data:
            taxpayer_id = place.get('taxpayer_id')
            if taxpayer_id and place.get('details_status') == 'success':
                places_lookup[str(taxpayer_id)] = place
        
        console.print(f"[green]✓ {len(places_lookup):,} valid places details indexed[/green]")
        
        # Merge data
        console.print("\n[dim]Combining data...[/dim]")
        combined_data = []
        enriched_count = 0
        unchanged_count = 0
        
        # Fields to add from places details
        places_fields = [
            'name', 'formatted_address', 'formatted_phone_number',
            'international_phone_number', 'website', 'url', 'rating',
            'user_ratings_total', 'business_status', 'types',
            'opening_hours', 'geometry', 'vicinity', 'price_level',
            'reviews', 'photos', 'place_id'
        ]
        
        for record in polished_data:
            # Get taxpayer ID from record
            taxpayer_id = record.get('taxpayer_number') or record.get('taxpayer_id')
            
            # Create a copy of the record
            combined_record = record.copy()
            
            # Check if we have places data for this taxpayer
            if taxpayer_id and str(taxpayer_id) in places_lookup:
                places_info = places_lookup[str(taxpayer_id)]
                
                # Add places fields with 'google_' prefix to avoid conflicts
                for field in places_fields:
                    if field in places_info:
                        combined_record[f'google_{field}'] = places_info[field]
                
                combined_record['google_places_enriched'] = True
                enriched_count += 1
            else:
                combined_record['google_places_enriched'] = False
                unchanged_count += 1
            
            combined_data.append(combined_record)
        
        # Show results
        console.print("\n")
        table = Table(title="Combination Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Total Polished Records", f"{len(polished_data):,}")
        table.add_row("Records Enriched with Places", f"{enriched_count:,}")
        table.add_row("Records Unchanged", f"{unchanged_count:,}")
        table.add_row("Total Combined Records", f"{len(combined_data):,}")
        
        console.print(table)
        
        # Store for stats
        self.last_combined_data = combined_data
        
        # Export
        if Confirm.ask("\nExport combined data to exports/final/?", default=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"final_combined_{timestamp}"
            
            # Create exporter for final directory
            final_exporter = FileExporter(FINAL_EXPORT_DIR)
            
            console.print(f"\n[bold]Exporting {len(combined_data):,} records to exports/final/...[/bold]")
            
            try:
                json_path = final_exporter.export_json(combined_data, f"{base_filename}.json")
                console.print(f"[green]✓ Exported JSON: {json_path.name}[/green]")
                
                csv_path = final_exporter.export_csv(combined_data, f"{base_filename}.csv")
                console.print(f"[green]✓ Exported CSV: {csv_path.name}[/green]")
                
                excel_path = final_exporter.export_excel(combined_data, f"{base_filename}.xlsx")
                console.print(f"[green]✓ Exported Excel: {excel_path.name}[/green]")
                
                console.print(f"\n[bold green]✓ Successfully exported {len(combined_data):,} records to exports/final/[/bold green]")
                
            except Exception as e:
                console.print(f"[red]Export error: {e}[/red]")
                logger.error(f"Export failed: {e}")
    
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
                    self.combine_files('json')
                    
                elif choice == "2":
                    self.combine_files('csv')
                    
                elif choice == "3":
                    self.combine_files('excel')
                    
                elif choice == "4":
                    self.auto_combine_latest()
                    
                elif choice == "5":
                    self.manual_combine()
                    
                elif choice == "6":
                    self.master_combine_all()
                    
                elif choice == "7":
                    self.gpu_accelerated_combine()
                    
                elif choice == "8":
                    self.view_data_quality_report()
                    
                elif choice == "9":
                    self.clean_and_validate_data()
                    
                elif choice == "10":
                    if self.last_combined_data:
                        stats = self.combiner.get_combination_stats(self.last_combined_data)
                        self.display_stats(stats)
                    else:
                        console.print("\nLoad combined file first", style="yellow")
                    
                elif choice == "11":
                    self.show_gpu_stats()
                    
                elif choice == "12":
                    self.handle_manual_combine()
                    
                elif choice == "13":
                    self.combine_google_places_with_polished()
                    
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
    cli = DataCombinerCLI()
    cli.run()