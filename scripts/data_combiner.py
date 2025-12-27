#!/usr/bin/env python3
"""
Data Combiner - Interactive CLI
Combine Socrata and Comptroller data intelligently
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
    COMBINED_EXPORT_DIR
)

console = Console()
logger = get_logger(__name__)


class DataCombinerCLI:
    """Interactive CLI for data combination"""
    
    def __init__(self):
        self.combiner = SmartDataCombiner()
        self.exporter = FileExporter(COMBINED_EXPORT_DIR)
        
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
        table.add_row("6", "View combination statistics")
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
        """Show file selection menu"""
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
            console.print(f"✓ Found Socrata JSON: {socrata_json.name}", style="green")
            console.print(f"✓ Found Comptroller JSON: {comptroller_json.name}", style="green")
            
            if Confirm.ask("\nCombine these files?", default=True):
                self._load_and_combine(socrata_json, comptroller_json, 'json')
                return
        
        # Try CSV
        socrata_csv = self.get_latest_file(SOCRATA_EXPORT_DIR, '*.csv')
        comptroller_csv = self.get_latest_file(COMPTROLLER_EXPORT_DIR, '*.csv')
        
        if socrata_csv and comptroller_csv:
            console.print(f"✓ Found Socrata CSV: {socrata_csv.name}", style="green")
            console.print(f"✓ Found Comptroller CSV: {comptroller_csv.name}", style="green")
            
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
            
            # Show statistics
            stats = self.combiner.get_combination_stats(combined_data)
            self.display_stats(stats)
            
            # Export
            if Confirm.ask("\nExport combined data?", default=True):
                self.export_combined_data(combined_data, file_format)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Combination error: {e}")
    
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
                    console.print("\nLoad combined file first", style="yellow")
                    
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