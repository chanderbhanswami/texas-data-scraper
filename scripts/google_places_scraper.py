#!/usr/bin/env python3
"""
Google Places Scraper - Interactive CLI
Find place IDs and get business details from Google Places API
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src.scrapers.google_places_scraper import GooglePlacesScraper, SmartGooglePlacesScraper
from src.api.google_places_client import DEFAULT_PLACE_DETAILS_FIELDS
from src.exporters.file_exporter import FileExporter
from src.utils.logger import get_logger
from src.utils.helpers import format_bytes

from config.settings import (
    POLISHED_EXPORT_DIR,
    PLACE_IDS_EXPORT_DIR,
    PLACES_DETAILS_EXPORT_DIR,
    google_places_config
)

console = Console()
logger = get_logger(__name__)


class GooglePlacesScraperCLI:
    """Interactive CLI for Google Places data extraction"""
    
    def __init__(self):
        self.scraper = SmartGooglePlacesScraper()
        self.place_ids_exporter = FileExporter(PLACE_IDS_EXPORT_DIR)
        self.details_exporter = FileExporter(PLACES_DETAILS_EXPORT_DIR)
        
        # Last processing results for continuation
        self.last_place_ids = []
        self.last_details = []
        
        logger.info("Initialized GooglePlacesScraperCLI")
    
    def show_banner(self):
        """Show welcome banner"""
        banner = Panel(
            """[bold cyan]Google Places Scraper[/bold cyan]
[dim]Enrich your data with Google Places business info[/dim]

[green]Pipeline: Polished → Place IDs → Place Details[/green]
[yellow]Step 1: Find Place IDs from business info[/yellow]
[yellow]Step 2: Get Details (phone, website, hours, etc.)[/yellow]""",
            title="🗺️ Google Places API",
            border_style="cyan"
        )
        console.print(banner)
        
        # Show API status
        if google_places_config.has_api_key:
            console.print(f"[green]✓ Google API key configured[/green]")
            billing_status = "Billing enabled" if google_places_config.BILLING_ENABLED else "Standard limits"
            console.print(f"[dim]  Rate limit: {google_places_config.rate_limit} QPM ({billing_status})[/dim]")
        else:
            console.print(f"[red]✗ Google API key not configured![/red]")
            console.print(f"[dim]  Add GOOGLE_PLACES_API_KEY to your .env file[/dim]")
        
        # Show cache stats
        cache_stats = self.scraper.get_cache_stats()
        console.print(f"[dim]  Cached: {cache_stats['place_ids_cached']} place IDs, {cache_stats['details_cached']} details[/dim]")
    
    def show_main_menu(self):
        """Display main menu"""
        menu = Table(show_header=False, box=None, padding=(0, 2))
        menu.add_column("Option", style="cyan")
        menu.add_column("Description")
        
        menu.add_row("", "[bold yellow]─── Step 1: Find Place IDs ───[/bold yellow]")
        menu.add_row("1", "🚀 Auto-Find Place IDs (from polished data)")
        menu.add_row("2", "📁 Select Specific Polished File")
        menu.add_row("3", "🔍 Manual Find (enter business info)")
        menu.add_row("4", "📊 Preview Polished Records")
        
        menu.add_row("", "")
        menu.add_row("", "[bold yellow]─── Step 2: Get Place Details ───[/bold yellow]")
        menu.add_row("5", "🚀 Auto-Get Details (from place_ids exports)")
        menu.add_row("6", "📁 Select Specific Place IDs File")
        menu.add_row("7", "🔍 Manual Lookup (enter place ID)")
        menu.add_row("8", "📊 Preview Place IDs")
        
        menu.add_row("", "")
        menu.add_row("", "[bold yellow]─── Utilities ───[/bold yellow]")
        menu.add_row("9", "🔧 Configure Fields to Extract")
        menu.add_row("10", "📈 Show Processing Stats")
        menu.add_row("11", "💾 Cache Management")
        
        menu.add_row("", "")
        menu.add_row("0", "🚪 Exit")
        
        panel = Panel(menu, title="Main Menu", border_style="blue")
        console.print(panel)
    
    def show_file_selector(self, directory: Path, pattern: str, label: str):
        """Show file selection menu"""
        files = sorted(directory.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not files:
            console.print(f"[yellow]No {label} files found in {directory}[/yellow]")
            return None
        
        console.print(f"\n[cyan]Available {label} Files:[/cyan]")
        table = Table(show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("File", style="white")
        table.add_column("Size", style="green", justify="right")
        table.add_column("Modified", style="dim")
        
        for i, f in enumerate(files[:15], 1):  # Limit to 15 files
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
    
    def get_processing_limit(self, total_records: int) -> int:
        """Get processing limit from user"""
        console.print(f"\n[cyan]Total records: {total_records:,}[/cyan]")
        console.print("Options:")
        console.print("  [dim]1. Process all records[/dim]")
        console.print("  [dim]2. Custom limit[/dim]")
        
        choice = console.input("\nChoose option (1/2): ").strip()
        
        if choice == '2':
            try:
                limit = console.input("Enter limit: ").strip()
                limit = int(limit)
                if 1 <= limit <= total_records:
                    return limit
            except ValueError:
                pass
            console.print("[yellow]Using all records[/yellow]")
        
        return total_records
    
    def load_json_file(self, file_path: Path) -> list:
        """Load JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            console.print(f"[red]Error loading {file_path}: {e}[/red]")
            return []
    
    # ===== Step 1: Find Place IDs =====
    
    def auto_find_place_ids(self):
        """Automatic place ID finding from polished data"""
        console.print("\n[cyan]🚀 Auto-Find Place IDs[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        # Select polished file
        polished_file = self.show_file_selector(POLISHED_EXPORT_DIR, "*.json", "Polished JSON")
        if not polished_file:
            return
        
        # Load data
        console.print(f"\n[dim]Loading {polished_file.name}...[/dim]")
        records = self.load_json_file(polished_file)
        
        if not records:
            console.print("[red]No records found in file[/red]")
            return
        
        # Get processing limit
        limit = self.get_processing_limit(len(records))
        records_to_process = records[:limit]
        
        console.print(f"\n[green]Processing {len(records_to_process):,} records...[/green]")
        
        # Process with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Finding place IDs...", total=len(records_to_process))
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            results = self.scraper.find_place_ids_with_cache(
                records_to_process,
                progress_callback=update_progress
            )
        
        self.last_place_ids = results
        
        # Show stats
        self._show_place_id_stats(results)
        
        # Export option
        if console.input("\nExport results? [y/n] (y): ").strip().lower() != 'n':
            self._export_place_ids(results, polished_file.stem)
        
        # Continue to step 2?
        if console.input("\nContinue to get place details? [y/n] (y): ").strip().lower() != 'n':
            found_results = [r for r in results if r.get('place_id')]
            if found_results:
                self._get_details_from_results(found_results)
            else:
                console.print("[yellow]No place IDs found to get details for[/yellow]")
    
    def select_file_find_place_ids(self):
        """Manual file selection for place ID finding"""
        console.print("\n[cyan]📁 Select Polished File[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        polished_file = self.show_file_selector(POLISHED_EXPORT_DIR, "*.json", "Polished JSON")
        if polished_file:
            records = self.load_json_file(polished_file)
            if records:
                limit = self.get_processing_limit(len(records))
                self._process_place_id_finding(records[:limit], polished_file.stem)
    
    def manual_find_place(self):
        """Manual place ID lookup"""
        console.print("\n[cyan]🔍 Manual Find Place[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        business_name = console.input("Business name: ").strip()
        if not business_name:
            console.print("[yellow]Business name is required[/yellow]")
            return
        
        address = console.input("Address (optional): ").strip()
        city = console.input("City (optional): ").strip()
        state = console.input("State (default: TX): ").strip() or "TX"
        zip_code = console.input("ZIP code (optional): ").strip()
        
        console.print("\n[dim]Searching...[/dim]")
        
        from src.api.google_places_client import GooglePlacesClient
        client = GooglePlacesClient()
        result = client.find_place(business_name, address, city, state, zip_code)
        
        if result:
            self._display_place_id_result(result)
        else:
            console.print("[yellow]Error searching for place[/yellow]")
    
    def preview_polished_records(self):
        """Preview records from polished file"""
        console.print("\n[cyan]📊 Preview Polished Records[/cyan]")
        
        polished_file = self.show_file_selector(POLISHED_EXPORT_DIR, "*.json", "Polished JSON")
        if not polished_file:
            return
        
        records = self.load_json_file(polished_file)
        if not records:
            return
        
        console.print(f"\n[green]Total records: {len(records):,}[/green]")
        console.print("\n[bold]Sample records (first 5):[/bold]")
        
        for i, record in enumerate(records[:5], 1):
            console.print(f"\n[cyan]Record {i}:[/cyan]")
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Field", style="dim")
            table.add_column("Value")
            
            fields = [
                ('Business Name', record.get('socrata_business_name', '')),
                ('Address', record.get('socrata_taxpayer_address', '')),
                ('City', record.get('socrata_taxpayer_city', '')),
                ('State', record.get('socrata_taxpayer_state', '')),
                ('ZIP', record.get('socrata_taxpayer_zip', '')),
                ('Taxpayer ID', record.get('taxpayer_number', ''))
            ]
            
            for field, value in fields:
                if value:
                    table.add_row(field, str(value)[:60])
            
            console.print(table)
    
    # ===== Step 2: Get Place Details =====
    
    def auto_get_details(self):
        """Automatic place details retrieval"""
        console.print("\n[cyan]🚀 Auto-Get Place Details[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        # Select place IDs file
        place_ids_file = self.show_file_selector(PLACE_IDS_EXPORT_DIR, "*.json", "Place IDs JSON")
        if not place_ids_file:
            return
        
        # Load data
        console.print(f"\n[dim]Loading {place_ids_file.name}...[/dim]")
        place_ids_data = self.load_json_file(place_ids_file)
        
        if not place_ids_data:
            console.print("[red]No records found in file[/red]")
            return
        
        # Filter to only records with place_ids
        valid_records = [r for r in place_ids_data if r.get('place_id')]
        console.print(f"[green]Found {len(valid_records):,} records with place IDs[/green]")
        
        if not valid_records:
            console.print("[yellow]No valid place IDs to process[/yellow]")
            return
        
        # Get processing limit
        limit = self.get_processing_limit(len(valid_records))
        records_to_process = valid_records[:limit]
        
        self._get_details_from_results(records_to_process, place_ids_file.stem)
    
    def _get_details_from_results(self, place_ids_data: list, base_name: str = None):
        """Get details for place IDs results"""
        console.print(f"\n[green]Getting details for {len(place_ids_data):,} places...[/green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Getting place details...", total=len(place_ids_data))
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            results = self.scraper.get_details_with_cache(
                place_ids_data,
                progress_callback=update_progress
            )
        
        self.last_details = results
        
        # Show stats
        self._show_details_stats(results)
        
        # Export option
        if console.input("\nExport results? [y/n] (y): ").strip().lower() != 'n':
            self._export_details(results, base_name or 'place_details')
    
    def select_file_get_details(self):
        """Manual file selection for details retrieval"""
        console.print("\n[cyan]📁 Select Place IDs File[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        place_ids_file = self.show_file_selector(PLACE_IDS_EXPORT_DIR, "*.json", "Place IDs JSON")
        if place_ids_file:
            data = self.load_json_file(place_ids_file)
            valid_records = [r for r in data if r.get('place_id')]
            if valid_records:
                limit = self.get_processing_limit(len(valid_records))
                self._get_details_from_results(valid_records[:limit], place_ids_file.stem)
    
    def manual_get_details(self):
        """Manual place details lookup"""
        console.print("\n[cyan]🔍 Manual Place Details Lookup[/cyan]")
        
        if not google_places_config.has_api_key:
            console.print("[red]Error: Google Places API key not configured![/red]")
            return
        
        place_id = console.input("Enter Place ID: ").strip()
        if not place_id:
            console.print("[yellow]Place ID is required[/yellow]")
            return
        
        console.print("\n[dim]Fetching details...[/dim]")
        
        from src.api.google_places_client import GooglePlacesClient
        client = GooglePlacesClient()
        result = client.get_place_details(place_id)
        
        if result:
            self._display_place_details(result)
        else:
            console.print("[yellow]Error fetching place details[/yellow]")
    
    def preview_place_ids(self):
        """Preview place IDs from file"""
        console.print("\n[cyan]📊 Preview Place IDs[/cyan]")
        
        place_ids_file = self.show_file_selector(PLACE_IDS_EXPORT_DIR, "*.json", "Place IDs JSON")
        if not place_ids_file:
            return
        
        data = self.load_json_file(place_ids_file)
        if not data:
            return
        
        found = len([r for r in data if r.get('place_id')])
        not_found = len([r for r in data if r.get('match_status') == 'not_found'])
        
        console.print(f"\n[green]Total records: {len(data):,}[/green]")
        console.print(f"[green]  Found: {found:,}[/green]")
        console.print(f"[yellow]  Not found: {not_found:,}[/yellow]")
        
        console.print("\n[bold]Sample records (first 5):[/bold]")
        
        for i, record in enumerate(data[:5], 1):
            status_color = "green" if record.get('match_status') == 'found' else "yellow"
            console.print(f"\n[{status_color}]Record {i}: {record.get('match_status', 'unknown')}[/{status_color}]")
            console.print(f"  Taxpayer ID: {record.get('taxpayer_id', 'N/A')}")
            console.print(f"  Place ID: {record.get('place_id', 'N/A')}")
            console.print(f"  Search: {record.get('search_query', 'N/A')[:60]}")
    
    # ===== Utilities =====
    
    def configure_fields(self):
        """Configure fields to extract"""
        console.print("\n[cyan]🔧 Available Place Details Fields[/cyan]")
        
        table = Table(title="Available Fields", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Field", style="white")
        table.add_column("Description", style="dim")
        
        descriptions = {
            'name': 'Business name',
            'formatted_address': 'Full address',
            'formatted_phone_number': 'Local phone number',
            'international_phone_number': 'International phone',
            'website': 'Business website',
            'url': 'Google Maps URL',
            'rating': 'Average rating (1-5)',
            'user_ratings_total': 'Total number of ratings',
            'business_status': 'OPERATIONAL, CLOSED, etc.',
            'types': 'Business categories',
            'opening_hours': 'Business hours',
            'geometry': 'Lat/lng coordinates',
            'vicinity': 'Short address',
            'price_level': 'Price level (0-4)',
            'reviews': 'User reviews',
            'photos': 'Photo references'
        }
        
        for i, field in enumerate(DEFAULT_PLACE_DETAILS_FIELDS, 1):
            table.add_row(str(i), field, descriptions.get(field, ''))
        
        console.print(table)
        console.print("\n[dim]All fields are extracted by default.[/dim]")
    
    def show_stats(self):
        """Show processing statistics"""
        console.print("\n[cyan]📈 Processing Statistics[/cyan]")
        
        stats = self.scraper.get_scraper_stats()
        cache_stats = self.scraper.get_cache_stats()
        
        table = Table(title="Current Session Stats", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Records Processed", f"{stats.get('total_records', 0):,}")
        table.add_row("Places Found", f"{stats.get('places_found', 0):,}")
        table.add_row("Places Not Found", f"{stats.get('places_not_found', 0):,}")
        table.add_row("Details Fetched", f"{stats.get('details_fetched', 0):,}")
        table.add_row("Errors", f"{stats.get('errors', 0):,}")
        
        table.add_row("", "")
        table.add_row("[bold]Cache Stats[/bold]", "")
        table.add_row("Cached Place IDs", f"{cache_stats.get('place_ids_cached', 0):,}")
        table.add_row("Cached Details", f"{cache_stats.get('details_cached', 0):,}")
        
        console.print(table)
    
    def cache_management(self):
        """Cache management menu"""
        console.print("\n[cyan]💾 Cache Management[/cyan]")
        
        cache_stats = self.scraper.get_cache_stats()
        console.print(f"\nCache directory: {cache_stats['cache_directory']}")
        console.print(f"Place IDs cached: {cache_stats['place_ids_cached']:,}")
        console.print(f"Details cached: {cache_stats['details_cached']:,}")
        
        console.print("\nOptions:")
        console.print("  1. Clear place IDs cache")
        console.print("  2. Clear details cache")
        console.print("  3. Clear all cache")
        console.print("  0. Back")
        
        choice = console.input("\nSelect option: ").strip()
        
        if choice == '1':
            if console.input("Clear place IDs cache? [y/n]: ").strip().lower() == 'y':
                self.scraper.clear_cache('place_ids')
                console.print("[green]Place IDs cache cleared[/green]")
        elif choice == '2':
            if console.input("Clear details cache? [y/n]: ").strip().lower() == 'y':
                self.scraper.clear_cache('details')
                console.print("[green]Details cache cleared[/green]")
        elif choice == '3':
            if console.input("Clear ALL cache? [y/n]: ").strip().lower() == 'y':
                self.scraper.clear_cache('all')
                console.print("[green]All cache cleared[/green]")
    
    # ===== Helper Methods =====
    
    def _process_place_id_finding(self, records: list, base_name: str):
        """Process place ID finding for records"""
        console.print(f"\n[green]Processing {len(records):,} records...[/green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Finding place IDs...", total=len(records))
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            results = self.scraper.find_place_ids_with_cache(
                records,
                progress_callback=update_progress
            )
        
        self.last_place_ids = results
        self._show_place_id_stats(results)
        
        if console.input("\nExport results? [y/n] (y): ").strip().lower() != 'n':
            self._export_place_ids(results, base_name)
    
    def _show_place_id_stats(self, results: list):
        """Show place ID finding stats"""
        found = len([r for r in results if r.get('match_status') == 'found'])
        not_found = len([r for r in results if r.get('match_status') == 'not_found'])
        errors = len([r for r in results if r.get('match_status') == 'error'])
        
        console.print("\n")
        table = Table(title="Place ID Results", show_header=True)
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", justify="right")
        
        total = len(results)
        table.add_row("Found", f"{found:,}", f"{found/total*100:.1f}%" if total > 0 else "0%")
        table.add_row("Not Found", f"{not_found:,}", f"{not_found/total*100:.1f}%" if total > 0 else "0%")
        table.add_row("Errors", f"{errors:,}", f"{errors/total*100:.1f}%" if total > 0 else "0%")
        table.add_row("[bold]Total[/bold]", f"[bold]{total:,}[/bold]", "[bold]100%[/bold]")
        
        console.print(table)
    
    def _show_details_stats(self, results: list):
        """Show place details stats"""
        success = len([r for r in results if r.get('details_status') == 'success'])
        errors = len([r for r in results if r.get('details_status') in ['error', 'no_place_id']])
        
        console.print("\n")
        table = Table(title="Place Details Results", show_header=True)
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Success", f"{success:,}")
        table.add_row("Errors/No Place ID", f"{errors:,}")
        table.add_row("[bold]Total[/bold]", f"[bold]{len(results):,}[/bold]")
        
        console.print(table)
    
    def _display_place_id_result(self, result: dict):
        """Display single place ID result"""
        console.print("\n")
        table = Table(title="Place Found", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("Status", result.get('match_status', 'unknown'))
        table.add_row("Place ID", result.get('place_id', 'N/A'))
        table.add_row("Name", result.get('name', 'N/A'))
        table.add_row("Address", result.get('formatted_address', 'N/A'))
        table.add_row("Business Status", result.get('business_status', 'N/A'))
        
        console.print(table)
    
    def _display_place_details(self, details: dict):
        """Display place details"""
        console.print("\n")
        table = Table(title="Place Details", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("Name", details.get('name', 'N/A'))
        table.add_row("Address", details.get('formatted_address', 'N/A'))
        table.add_row("Phone", details.get('formatted_phone_number', 'N/A'))
        table.add_row("Website", details.get('website', 'N/A'))
        table.add_row("Rating", str(details.get('rating', 'N/A')))
        table.add_row("Total Ratings", str(details.get('user_ratings_total', 'N/A')))
        table.add_row("Status", details.get('business_status', 'N/A'))
        table.add_row("Types", ', '.join(details.get('types', [])))
        
        if details.get('opening_hours'):
            hours = details['opening_hours'].get('weekday_text', [])
            if hours:
                table.add_row("Hours", hours[0] + '...' if len(hours) > 1 else hours[0] if hours else 'N/A')
        
        console.print(table)
    
    def _export_place_ids(self, data: list, base_name: str):
        """Export place IDs"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"place_ids_{base_name}_{timestamp}"
        
        console.print(f"\n[cyan]Exporting to exports/place_ids/[/cyan]")
        
        try:
            json_path = self.place_ids_exporter.export_json(data, f"{export_name}.json")
            console.print(f"[green]✓ JSON: {json_path.name}[/green]")
            
            csv_path = self.place_ids_exporter.export_csv(data, f"{export_name}.csv")
            console.print(f"[green]✓ CSV: {csv_path.name}[/green]")
            
            excel_path = self.place_ids_exporter.export_excel(data, f"{export_name}.xlsx")
            console.print(f"[green]✓ Excel: {excel_path.name}[/green]")
            
            console.print(f"\n[bold green]✓ Exported {len(data):,} records[/bold green]")
            
        except Exception as e:
            console.print(f"[red]Export error: {e}[/red]")
            logger.error(f"Export failed: {e}")
    
    def _export_details(self, data: list, base_name: str):
        """Export place details"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"places_details_{base_name}_{timestamp}"
        
        console.print(f"\n[cyan]Exporting to exports/places_details/[/cyan]")
        
        try:
            json_path = self.details_exporter.export_json(data, f"{export_name}.json")
            console.print(f"[green]✓ JSON: {json_path.name}[/green]")
            
            csv_path = self.details_exporter.export_csv(data, f"{export_name}.csv")
            console.print(f"[green]✓ CSV: {csv_path.name}[/green]")
            
            excel_path = self.details_exporter.export_excel(data, f"{export_name}.xlsx")
            console.print(f"[green]✓ Excel: {excel_path.name}[/green]")
            
            console.print(f"\n[bold green]✓ Exported {len(data):,} records[/bold green]")
            
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
                
                # Step 1: Find Place IDs
                elif choice == '1':
                    self.auto_find_place_ids()
                elif choice == '2':
                    self.select_file_find_place_ids()
                elif choice == '3':
                    self.manual_find_place()
                elif choice == '4':
                    self.preview_polished_records()
                
                # Step 2: Get Place Details
                elif choice == '5':
                    self.auto_get_details()
                elif choice == '6':
                    self.select_file_get_details()
                elif choice == '7':
                    self.manual_get_details()
                elif choice == '8':
                    self.preview_place_ids()
                
                # Utilities
                elif choice == '9':
                    self.configure_fields()
                elif choice == '10':
                    self.show_stats()
                elif choice == '11':
                    self.cache_management()
                
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
    cli = GooglePlacesScraperCLI()
    cli.run()
