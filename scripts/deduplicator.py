#!/usr/bin/env python3
"""
Deduplicator - Interactive CLI
Remove duplicate records from datasets
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.processors.deduplicator import Deduplicator, AdvancedDeduplicator
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from config.settings import COMBINED_EXPORT_DIR, DEDUPLICATED_EXPORT_DIR

console = Console()
logger = get_logger(__name__)


class DeduplicatorCLI:
    """Interactive CLI for data deduplication"""
    
    def __init__(self):
        self.deduplicator = AdvancedDeduplicator()
        self.exporter = FileExporter(DEDUPLICATED_EXPORT_DIR)
        self.input_exporter = FileExporter(COMBINED_EXPORT_DIR)
        
    def show_banner(self):
        """Show welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          DATA DEDUPLICATOR - CLEAN & POLISH DATA         ║
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
        
        table.add_row("1", "Deduplicate JSON file")
        table.add_row("2", "Deduplicate CSV file")
        table.add_row("3", "Deduplicate Excel file")
        table.add_row("", "")
        table.add_row("4", "Deduplicate all files in combined exports")
        table.add_row("5", "Manual file path deduplication")
        table.add_row("", "")
        table.add_row("6", "Advanced: Deduplicate with merge")
        table.add_row("7", "Advanced: Deduplicate by confidence")
        table.add_row("", "")
        table.add_row("8", "Change deduplication strategy")
        table.add_row("", "")
        table.add_row("0", "Exit")
        
        console.print(table)
        
        # Show current strategy
        console.print(f"\nCurrent Strategy: [cyan]{self.deduplicator.strategy}[/cyan]")
        
        choice = Prompt.ask("\nSelect an option", default="0")
        return choice
    
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
    
    def deduplicate_file(self, file_format: str):
        """Deduplicate file of specific format"""
        patterns = {
            'json': '*.json',
            'csv': '*.csv',
            'excel': '*.xlsx'
        }
        pattern = patterns.get(file_format)
        
        # Select file
        file_path = self.show_file_selector(
            COMBINED_EXPORT_DIR,
            pattern,
            f"{file_format.upper()}"
        )
        
        if not file_path:
            return
        
        # Load, deduplicate, and export
        self._process_file(file_path, file_format)
    
    def deduplicate_all_combined(self):
        """Deduplicate all files in combined exports directory"""
        console.print("\n[bold]Deduplicating all combined exports...[/bold]")
        
        formats = {
            'json': '*.json',
            'csv': '*.csv',
            'excel': '*.xlsx'
        }
        
        processed_count = 0
        
        for format_name, pattern in formats.items():
            files = list(COMBINED_EXPORT_DIR.glob(pattern))
            
            for file_path in files:
                console.print(f"\n[cyan]Processing: {file_path.name}[/cyan]")
                try:
                    self._process_file(file_path, format_name, auto=True)
                    processed_count += 1
                except Exception as e:
                    console.print(f"Error: {e}", style="red")
                    logger.error(f"Error processing {file_path}: {e}")
        
        console.print(f"\n✓ Processed {processed_count} files", style="green bold")
    
    def manual_deduplicate(self):
        """Manual file path deduplication"""
        file_path = Prompt.ask("\nEnter file path")
        
        file_path = Path(file_path)
        if not file_path.exists():
            console.print(f"⚠ File not found: {file_path}", style="yellow")
            return
        
        # Detect format
        format_map = {
            '.json': 'json',
            '.csv': 'csv',
            '.xlsx': 'excel',
            '.xls': 'excel'
        }
        
        file_format = format_map.get(file_path.suffix.lower(), 'json')
        
        self._process_file(file_path, file_format)
    
    def _process_file(self, file_path: Path, file_format: str, auto: bool = False):
        """Process file: load, deduplicate, export"""
        try:
            # Load data
            if not auto:
                console.print(f"\n[bold]Loading {file_path.name}...[/bold]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading...", total=None)
                data = self.input_exporter.auto_load(file_path)
                progress.update(task, completed=True)
            
            if not auto:
                console.print(f"✓ Loaded {len(data):,} records", style="green")
            
            # Deduplicate
            if not auto:
                console.print("\n[bold]Deduplicating...[/bold]")
            
            unique_data, duplicates = self.deduplicator.deduplicate(data)
            
            # Show statistics
            stats = self.deduplicator.get_deduplication_stats(
                len(data),
                len(unique_data),
                len(duplicates)
            )
            
            if not auto:
                self.display_stats(stats)
            else:
                console.print(f"  Removed {len(duplicates):,} duplicates ({stats['deduplication_rate']:.1f}%)", style="yellow")
            
            # Export
            if not auto:
                if Confirm.ask("\nExport deduplicated data?", default=True):
                    self.export_deduplicated(unique_data, file_path.stem, file_format)
                    
                if duplicates and Confirm.ask("Export duplicates for review?", default=False):
                    self.export_duplicates(duplicates, file_path.stem, file_format)
            else:
                self.export_deduplicated(unique_data, file_path.stem, file_format)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
            logger.error(f"Processing error: {e}")
    
    def display_stats(self, stats: dict):
        """Display deduplication statistics"""
        table = Table(title="Deduplication Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Original Records", f"{stats['original_count']:,}")
        table.add_row("Unique Records", f"{stats['unique_count']:,}")
        table.add_row("Duplicates Removed", f"{stats['duplicate_count']:,}")
        table.add_row("Deduplication Rate", f"{stats['deduplication_rate']:.2f}%")
        table.add_row("Size Reduction", f"{stats['reduction_percentage']:.2f}%")
        
        console.print("\n")
        console.print(table)
    
    def export_deduplicated(self, data: list, base_name: str, file_format: str):
        """Export deduplicated data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_deduplicated_{timestamp}"
        
        try:
            if file_format == 'json':
                path = self.exporter.export_json(data, f"{filename}.json")
            elif file_format == 'csv':
                path = self.exporter.export_csv(data, f"{filename}.csv")
            elif file_format == 'excel':
                path = self.exporter.export_excel(data, f"{filename}.xlsx")
            
            console.print(f"✓ Exported deduplicated data: {path}", style="green")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red bold")
    
    def export_duplicates(self, duplicates: list, base_name: str, file_format: str):
        """Export duplicate records for review"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_duplicates_{timestamp}"
        
        try:
            if file_format == 'json':
                path = self.exporter.export_json(duplicates, f"{filename}.json")
            elif file_format == 'csv':
                path = self.exporter.export_csv(duplicates, f"{filename}.csv")
            elif file_format == 'excel':
                path = self.exporter.export_excel(duplicates, f"{filename}.xlsx")
            
            console.print(f"✓ Exported duplicates: {path}", style="green")
            
        except Exception as e:
            console.print(f"Export error: {e}", style="red bold")
    
    def deduplicate_with_merge(self):
        """Deduplicate with merge strategy"""
        console.print("\n[bold]Deduplicate with Merge[/bold]")
        console.print("This will merge duplicate records into single comprehensive records\n")
        
        file_path = Prompt.ask("Enter file path")
        file_path = Path(file_path)
        
        if not file_path.exists():
            console.print(f"⚠ File not found", style="yellow")
            return
        
        try:
            # Load data
            console.print(f"\n[bold]Loading {file_path.name}...[/bold]")
            data = self.input_exporter.auto_load(file_path)
            console.print(f"✓ Loaded {len(data):,} records", style="green")
            
            # Deduplicate with merge
            console.print("\n[bold]Deduplicating and merging...[/bold]")
            merged_data = self.deduplicator.deduplicate_with_merge(data)
            
            console.print(f"✓ Reduced to {len(merged_data):,} records", style="green bold")
            
            # Export
            if Confirm.ask("\nExport merged data?", default=True):
                format_map = {
                    '.json': 'json',
                    '.csv': 'csv',
                    '.xlsx': 'excel'
                }
                file_format = format_map.get(file_path.suffix.lower(), 'json')
                self.export_deduplicated(merged_data, f"{file_path.stem}_merged", file_format)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def deduplicate_by_confidence(self):
        """Deduplicate keeping most complete records"""
        console.print("\n[bold]Deduplicate by Confidence[/bold]")
        console.print("Keeps the most complete record from each duplicate group\n")
        
        file_path = Prompt.ask("Enter file path")
        file_path = Path(file_path)
        
        if not file_path.exists():
            console.print(f"⚠ File not found", style="yellow")
            return
        
        try:
            # Load data
            console.print(f"\n[bold]Loading {file_path.name}...[/bold]")
            data = self.input_exporter.auto_load(file_path)
            console.print(f"✓ Loaded {len(data):,} records", style="green")
            
            # Deduplicate by confidence
            console.print("\n[bold]Deduplicating by confidence...[/bold]")
            best_data = self.deduplicator.deduplicate_by_confidence(data)
            
            console.print(f"✓ Reduced to {len(best_data):,} records", style="green bold")
            
            # Export
            if Confirm.ask("\nExport results?", default=True):
                format_map = {
                    '.json': 'json',
                    '.csv': 'csv',
                    '.xlsx': 'excel'
                }
                file_format = format_map.get(file_path.suffix.lower(), 'json')
                self.export_deduplicated(best_data, f"{file_path.stem}_best", file_format)
            
        except Exception as e:
            console.print(f"Error: {e}", style="red bold")
    
    def change_strategy(self):
        """Change deduplication strategy"""
        console.print("\n[bold]Deduplication Strategies:[/bold]")
        console.print("1. taxpayer_id - Remove duplicates by taxpayer ID (fastest)")
        console.print("2. exact - Remove exact duplicate records")
        console.print("3. fuzzy - Fuzzy matching on key fields")
        
        choice = Prompt.ask("\nSelect strategy", choices=["1", "2", "3"])
        
        strategies = {
            "1": "taxpayer_id",
            "2": "exact",
            "3": "fuzzy"
        }
        
        new_strategy = strategies[choice]
        self.deduplicator = AdvancedDeduplicator(strategy=new_strategy)
        
        console.print(f"\n✓ Strategy changed to: {new_strategy}", style="green")
    
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
                    self.deduplicate_file('json')
                    
                elif choice == "2":
                    self.deduplicate_file('csv')
                    
                elif choice == "3":
                    self.deduplicate_file('excel')
                    
                elif choice == "4":
                    self.deduplicate_all_combined()
                    
                elif choice == "5":
                    self.manual_deduplicate()
                    
                elif choice == "6":
                    self.deduplicate_with_merge()
                    
                elif choice == "7":
                    self.deduplicate_by_confidence()
                    
                elif choice == "8":
                    self.change_strategy()
                    
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
    cli = DeduplicatorCLI()
    cli.run()