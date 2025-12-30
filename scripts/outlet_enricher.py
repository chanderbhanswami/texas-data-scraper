#!/usr/bin/env python3
"""
Outlet Enricher - Interactive CLI
Extract outlet data from Socrata duplicates and enrich deduplicated records
With GPU acceleration and data validation
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.processors.outlet_enricher import OutletEnricher, AdvancedOutletEnricher, OUTLET_FIELDS
from src.exporters.file_exporter import FileExporter
from src.processors.data_validator import DataValidator
from src.utils.logger import get_logger
from src.scrapers.gpu_accelerator import get_gpu_accelerator
from src.utils.helpers import format_bytes

from config.settings import (
    SOCRATA_EXPORT_DIR,
    DEDUPLICATED_EXPORT_DIR,
    POLISHED_EXPORT_DIR
)

console = Console()
logger = get_logger(__name__)


class OutletEnricherCLI:
    """Interactive CLI for outlet data enrichment"""
    
    def __init__(self):
        self.enricher = AdvancedOutletEnricher()
        self.exporter = FileExporter(POLISHED_EXPORT_DIR)
        self.validator = DataValidator()
        self.gpu = get_gpu_accelerator()
        logger.info("Initialized OutletEnricherCLI")
    
    def show_banner(self):
        """Show welcome banner"""
        banner = Panel(
            """[bold cyan]Outlet Data Enricher[/bold cyan]
[dim]Extract outlet fields from Socrata duplicates[/dim]
[dim]and enrich your deduplicated data[/dim]

[green]Pipeline: Socrata → Deduplicated → Polished[/green]""",
            title="🏭 Outlet Enricher",
            border_style="cyan"
        )
        console.print(banner)
        
        # Show GPU status
        if self.gpu.gpu_available:
            console.print(f"[green]✓ GPU acceleration enabled[/green]")
        else:
            console.print(f"[yellow]○ GPU not available, using CPU[/yellow]")
    
    def show_main_menu(self):
        """Display main menu"""
        menu = Table(show_header=False, box=None, padding=(0, 2))
        menu.add_column("Option", style="cyan")
        menu.add_column("Description")
        
        menu.add_row("1", "🚀 Auto-Enrich (Recommended)")
        menu.add_row("2", "📁 Select Specific Files")
        menu.add_row("3", "📊 Preview Outlet Data")
        menu.add_row("4", "🔍 View Outlet Fields Info")
        menu.add_row("5", "💾 Export Formats Selection")
        menu.add_row("6", "📈 Show Processing Stats")
        menu.add_row("", "")
        menu.add_row("0", "🚪 Exit")
        
        panel = Panel(menu, title="Main Menu", border_style="blue")
        console.print(panel)
    
    def show_file_selector(self, directory: Path, pattern: str, label: str):
        """Show file selection menu"""
        files = sorted(directory.glob(pattern))
        
        if not files:
            console.print(f"[yellow]No {label} files found in {directory}[/yellow]")
            return None
        
        console.print(f"\n[cyan]Available {label} Files:[/cyan]")
        table = Table(show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("File", style="white")
        table.add_column("Size", style="green", justify="right")
        table.add_column("Modified", style="dim")
        
        for i, f in enumerate(files, 1):
            size = format_bytes(f.stat().st_size)
            modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(str(i), f.name, size, modified)
        
        console.print(table)
        
        try:
            choice = console.input("\nSelect file number (0 to cancel): ")
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(files):
                return files[idx - 1]
        except ValueError:
            pass
        
        console.print("[red]Invalid selection[/red]")
        return None
    
    def load_json_file(self, file_path: Path) -> list:
        """Load JSON file"""
        import json
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            console.print(f"[red]Error loading {file_path}: {e}[/red]")
            return []
    
    def auto_enrich(self):
        """Automatic enrichment pipeline"""
        console.print("\n[cyan]🚀 Auto-Enrich Pipeline[/cyan]")
        console.print("[dim]Socrata → Deduplicated → Polished[/dim]\n")
        
        # Step 1: Select Socrata file
        console.print("[bold]Step 1: Select Socrata source file[/bold]")
        socrata_file = self.show_file_selector(SOCRATA_EXPORT_DIR, "*.json", "Socrata JSON")
        if not socrata_file:
            console.print("[yellow]No Socrata file selected[/yellow]")
            return
        
        # Step 2: Select Deduplicated file
        console.print("\n[bold]Step 2: Select Deduplicated file to enrich[/bold]")
        dedup_file = self.show_file_selector(DEDUPLICATED_EXPORT_DIR, "*.json", "Deduplicated JSON")
        if not dedup_file:
            console.print("[yellow]No Deduplicated file selected[/yellow]")
            return
        
        # Load data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading Socrata data...", total=None)
            socrata_data = self.load_json_file(socrata_file)
            progress.update(task, description=f"Loaded {len(socrata_data):,} Socrata records")
            
            task = progress.add_task("Loading Deduplicated data...", total=None)
            dedup_data = self.load_json_file(dedup_file)
            progress.update(task, description=f"Loaded {len(dedup_data):,} Deduplicated records")
        
        if not socrata_data or not dedup_data:
            console.print("[red]Failed to load data files[/red]")
            return
        
        console.print(f"\n[green]✓ Loaded {len(socrata_data):,} Socrata records[/green]")
        console.print(f"[green]✓ Loaded {len(dedup_data):,} Deduplicated records[/green]")
        
        # Process
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting outlet data...", total=None)
            outlet_data = self.enricher.find_outlet_data(socrata_data)
            progress.update(task, description=f"Found {len(outlet_data):,} taxpayers with outlets")
            
            task = progress.add_task("Enriching records...", total=None)
            
            # Use GPU if available
            if self.gpu.gpu_available:
                enriched = self.enricher.enrich_with_gpu(dedup_data, outlet_data)
            else:
                enriched = self.enricher.enrich_with_merged_outlets(dedup_data, outlet_data)
            
            progress.update(task, description=f"Enriched {len(enriched):,} records")
        
        # Show stats
        stats = self.enricher.get_stats()
        self.display_stats(stats)
        
        # Export
        self._export_enriched(enriched, dedup_file.stem)
    
    def select_files_enrich(self):
        """Manual file selection and enrichment"""
        console.print("\n[cyan]📁 Manual File Selection[/cyan]\n")
        
        socrata_file = self.show_file_selector(SOCRATA_EXPORT_DIR, "*.json", "Socrata JSON")
        if not socrata_file:
            return
        
        dedup_file = self.show_file_selector(DEDUPLICATED_EXPORT_DIR, "*.json", "Deduplicated JSON")
        if not dedup_file:
            return
        
        socrata_data = self.load_json_file(socrata_file)
        dedup_data = self.load_json_file(dedup_file)
        
        if not socrata_data or not dedup_data:
            return
        
        # Process
        enriched, stats = self.enricher.process(socrata_data, dedup_data)
        self.display_stats(stats)
        self._export_enriched(enriched, dedup_file.stem)
    
    def preview_outlet_data(self):
        """Preview outlet data from Socrata file"""
        console.print("\n[cyan]📊 Preview Outlet Data[/cyan]\n")
        
        socrata_file = self.show_file_selector(SOCRATA_EXPORT_DIR, "*.json", "Socrata JSON")
        if not socrata_file:
            return
        
        socrata_data = self.load_json_file(socrata_file)
        if not socrata_data:
            return
        
        outlet_data = self.enricher.find_outlet_data(socrata_data)
        
        console.print(f"\n[green]Found {len(outlet_data):,} taxpayers with outlet data[/green]")
        
        # Show sample
        console.print("\n[bold]Sample Outlet Data (first 5):[/bold]")
        for i, (tid, outlets) in enumerate(list(outlet_data.items())[:5]):
            console.print(f"\n[cyan]Taxpayer: {tid}[/cyan] ({len(outlets)} outlet(s))")
            for outlet in outlets[:2]:
                table = Table(show_header=False, box=None, padding=(0, 1))
                table.add_column("Field", style="dim")
                table.add_column("Value")
                for field in OUTLET_FIELDS[:6]:  # Show first 6 fields
                    if field in outlet:
                        table.add_row(field, str(outlet[field])[:50])
                console.print(table)
    
    def show_outlet_fields_info(self):
        """Show information about outlet fields"""
        console.print("\n[cyan]🔍 Outlet Fields Information[/cyan]\n")
        
        table = Table(title="Outlet Fields Extracted", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Field Name", style="white")
        table.add_column("Description", style="dim")
        
        descriptions = {
            'outlet_number': 'Outlet/location number',
            'outlet_name': 'Business outlet name',
            'outlet_address': 'Street address',
            'outlet_city': 'City',
            'outlet_state': 'State (usually TX)',
            'outlet_zip_code': 'ZIP code',
            'outlet_county_code': 'Texas county code',
            'outlet_naics_code': 'NAICS industry code',
            'outlet_inside_outside_city_limits_indicator': 'City limits indicator (Y/N)',
            'outlet_permit_issue_date': 'Permit issue date',
            'outlet_first_sales_date': 'First sales date'
        }
        
        for i, field in enumerate(OUTLET_FIELDS, 1):
            table.add_row(str(i), field, descriptions.get(field, ''))
        
        console.print(table)
    
    def export_format_selection(self):
        """Select export formats"""
        console.print("\n[cyan]💾 Export Formats[/cyan]\n")
        console.print("Current export directory: [green]exports/polished[/green]")
        console.print("\nAvailable formats:")
        console.print("  1. JSON (recommended)")
        console.print("  2. CSV")
        console.print("  3. Excel")
        console.print("  4. All formats")
    
    def display_stats(self, stats: dict):
        """Display processing statistics"""
        console.print("\n")
        table = Table(title="📈 Processing Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Socrata Records", f"{stats.get('total_socrata_records', 0):,}")
        table.add_row("Unique Taxpayers", f"{stats.get('unique_taxpayers', 0):,}")
        table.add_row("Taxpayers with Outlets", f"{stats.get('taxpayers_with_outlets', 0):,}")
        table.add_row("Total Outlets Found", f"{stats.get('total_outlets_found', 0):,}")
        table.add_row("Records Enriched", f"{stats.get('records_enriched', 0):,}")
        table.add_row("Records Unchanged", f"{stats.get('records_unchanged', 0):,}")
        
        console.print(table)
    
    def _export_enriched(self, data: list, base_name: str):
        """Export enriched data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"polished_{base_name}_{timestamp}"
        
        console.print(f"\n[cyan]Exporting to exports/polished/[/cyan]")
        
        try:
            # Export JSON
            json_path = self.exporter.export_json(data, export_name)
            console.print(f"[green]✓ JSON: {json_path.name}[/green]")
            
            # Export CSV
            csv_path = self.exporter.export_csv(data, export_name)
            console.print(f"[green]✓ CSV: {csv_path.name}[/green]")
            
            # Export Excel
            excel_path = self.exporter.export_excel(data, export_name)
            console.print(f"[green]✓ Excel: {excel_path.name}[/green]")
            
            console.print(f"\n[bold green]✓ Exported {len(data):,} polished records[/bold green]")
            
        except Exception as e:
            console.print(f"[red]Export error: {e}[/red]")
            logger.error(f"Export failed: {e}")
    
    def run(self):
        """Main CLI loop"""
        self.show_banner()
        
        while True:
            self.show_main_menu()
            
            try:
                choice = console.input("\nSelect option: ").strip()
                
                if choice == '0':
                    confirm = console.input("Exit? [y/n] (n): ").strip().lower()
                    if confirm == 'y':
                        console.print("[cyan]Goodbye![/cyan]")
                        break
                elif choice == '1':
                    self.auto_enrich()
                elif choice == '2':
                    self.select_files_enrich()
                elif choice == '3':
                    self.preview_outlet_data()
                elif choice == '4':
                    self.show_outlet_fields_info()
                elif choice == '5':
                    self.export_format_selection()
                elif choice == '6':
                    stats = self.enricher.get_stats()
                    if any(stats.values()):
                        self.display_stats(stats)
                    else:
                        console.print("[yellow]No processing stats yet. Run enrichment first.[/yellow]")
                else:
                    console.print("[yellow]Invalid option[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled[/yellow]")
                confirm = console.input("Exit? [y/n] (n): ").strip().lower()
                if confirm == 'y':
                    break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"CLI error: {e}")


if __name__ == "__main__":
    cli = OutletEnricherCLI()
    cli.run()
