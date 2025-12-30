#!/usr/bin/env python3
"""
Texas Data Scraper - Master Script
Main entry point with unified interface
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def show_main_menu():
    """Show main menu"""
    console.clear()
    
    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           TEXAS GOVERNMENT DATA SCRAPER v1.4             ║
    ║                                                           ║
    ║              Comprehensive Data Extraction Tool          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    
    console.print(title, style="bold cyan")
    
    menu_text = """
    [bold cyan]DATA COLLECTION[/bold cyan]
    [cyan]1[/cyan]. Socrata Scraper          - Download TX open data
    [cyan]2[/cyan]. Comptroller Scraper      - Fetch taxpayer details
    [cyan]3[/cyan]. Batch Processor          - Large dataset processing
    
    [bold green]DATA PROCESSING[/bold green]
    [cyan]4[/cyan]. Data Combiner            - Merge multiple sources
    [cyan]5[/cyan]. Deduplicator             - Remove duplicates
    [cyan]6[/cyan]. Outlet Enricher          - Add outlet data to records
    
    [bold yellow]UTILITIES[/bold yellow]
    [cyan]7[/cyan]. API Tester               - Test API endpoints
    [cyan]8[/cyan]. Configuration             - View/edit settings
    
    [bold magenta]WORKFLOWS[/bold magenta]
    [cyan]9[/cyan]. Quick Start Workflow     - Guided setup
    [cyan]10[/cyan]. Full Pipeline            - Complete automation
    
    [bold red]0[/bold red]. Exit
    """
    
    console.print(Panel(menu_text, border_style="cyan"))


def run_socrata_scraper():
    """Run Socrata scraper"""
    console.print("\n[bold cyan]Launching Socrata Scraper...[/bold cyan]\n")
    
    from scripts.socrata_scraper import SocrataScraperCLI
    cli = SocrataScraperCLI()
    cli.run()


def run_comptroller_scraper():
    """Run Comptroller scraper"""
    console.print("\n[bold cyan]Launching Comptroller Scraper...[/bold cyan]\n")
    
    from scripts.comptroller_scraper import ComptrollerScraperCLI
    cli = ComptrollerScraperCLI()
    cli.run()


def run_batch_processor():
    """Run batch processor"""
    console.print("\n[bold cyan]Launching Batch Processor...[/bold cyan]\n")
    
    from scripts.batch_processor import BatchProcessor
    processor = BatchProcessor()
    processor.run()


def run_data_combiner():
    """Run data combiner"""
    console.print("\n[bold cyan]Launching Data Combiner...[/bold cyan]\n")
    
    from scripts.data_combiner import DataCombinerCLI
    cli = DataCombinerCLI()
    cli.run()


def run_deduplicator():
    """Run deduplicator"""
    console.print("\n[bold cyan]Launching Deduplicator...[/bold cyan]\n")
    
    from scripts.deduplicator import DeduplicatorCLI
    cli = DeduplicatorCLI()
    cli.run()


def run_outlet_enricher():
    """Run outlet enricher"""
    console.print("\n[bold cyan]Launching Outlet Enricher...[/bold cyan]\n")
    
    from scripts.outlet_enricher import OutletEnricherCLI
    cli = OutletEnricherCLI()
    cli.run()


def run_api_tester():
    """Run API tester"""
    console.print("\n[bold cyan]Running API Tests...[/bold cyan]\n")
    
    from scripts.api_tester import APITester
    tester = APITester()
    tester.run_all_tests()
    
    console.print("\nPress Enter to continue...")
    input()


def show_configuration():
    """Show configuration"""
    console.print("\n[bold cyan]Current Configuration[/bold cyan]\n")
    
    from config.settings import print_configuration
    print_configuration()
    
    console.print("\nPress Enter to continue...")
    input()


def run_quick_start():
    """Run quick start workflow"""
    console.print("\n[bold cyan]Quick Start Workflow[/bold cyan]\n")
    
    console.print("""
    This workflow will guide you through:
    1. Downloading a small sample dataset (1000 records)
    2. Enriching with Comptroller data
    3. Combining the results
    4. Removing duplicates
    
    Estimated time: 5-10 minutes
    """)
    
    from rich.prompt import Confirm
    
    if not Confirm.ask("\nProceed with Quick Start?", default=True):
        return
    
    try:
        # Step 1: Download sample
        console.print("\n[bold]Step 1/4: Downloading sample data...[/bold]")
        from src.api.socrata_client import SocrataClient
        from config.settings import socrata_config, SOCRATA_EXPORT_DIR
        from src.exporters.file_exporter import FileExporter
        from datetime import datetime
        
        client = SocrataClient()
        data = client.get_franchise_tax_holders(limit=1000)
        
        if data:
            exporter = FileExporter(SOCRATA_EXPORT_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            socrata_file = exporter.export_json(data, f"quickstart_{timestamp}.json")
            console.print(f"✓ Downloaded {len(data)} records", style="green")
        else:
            console.print("✗ Failed to download data", style="red")
            return
        
        # Step 2: Enrich
        console.print("\n[bold]Step 2/4: Enriching with Comptroller data...[/bold]")
        from src.api.comptroller_client import ComptrollerClient
        from config.settings import COMPTROLLER_EXPORT_DIR
        
        # Extract taxpayer IDs
        taxpayer_ids = []
        for record in data[:100]:  # Limit to 100 for quick start
            for field in ['taxpayer_id', 'taxpayer_number']:
                if field in record and record[field]:
                    taxpayer_ids.append(str(record[field]).strip())
                    break
        
        comptroller_client = ComptrollerClient()
        enriched = comptroller_client.batch_get_taxpayer_info(taxpayer_ids)
        
        exporter = FileExporter(COMPTROLLER_EXPORT_DIR)
        comptroller_file = exporter.export_json(enriched, f"quickstart_enriched_{timestamp}.json")
        console.print(f"✓ Enriched {len(enriched)} records", style="green")
        
        # Step 3: Combine
        console.print("\n[bold]Step 3/4: Combining data...[/bold]")
        from src.processors.data_combiner import SmartDataCombiner
        from config.settings import COMBINED_EXPORT_DIR
        
        combiner = SmartDataCombiner()
        combined = combiner.combine_by_taxpayer_id(data[:100], enriched)
        
        exporter = FileExporter(COMBINED_EXPORT_DIR)
        combined_file = exporter.export_json(combined, f"quickstart_combined_{timestamp}.json")
        console.print(f"✓ Combined {len(combined)} records", style="green")
        
        # Step 4: Deduplicate
        console.print("\n[bold]Step 4/4: Removing duplicates...[/bold]")
        from src.processors.deduplicator import AdvancedDeduplicator
        from config.settings import DEDUPLICATED_EXPORT_DIR
        
        deduplicator = AdvancedDeduplicator()
        unique, duplicates = deduplicator.deduplicate(combined)
        
        exporter = FileExporter(DEDUPLICATED_EXPORT_DIR)
        final_file = exporter.export_all_formats(unique, f"quickstart_final_{timestamp}")
        
        console.print(f"✓ Final dataset: {len(unique)} unique records", style="green bold")
        console.print(f"✓ Removed {len(duplicates)} duplicates", style="green")
        
        console.print("\n[bold green]✓ Quick Start Complete![/bold green]")
        console.print(f"\nFinal files saved to: {DEDUPLICATED_EXPORT_DIR}")
        
    except Exception as e:
        console.print(f"\n✗ Error: {e}", style="red bold")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
    
    console.print("\nPress Enter to continue...")
    input()


def run_full_pipeline():
    """Run full automated pipeline"""
    console.print("\n[bold cyan]Full Pipeline Automation[/bold cyan]\n")
    
    console.print("""
    This will run the complete pipeline:
    1. Download Socrata dataset (configurable size)
    2. Process all taxpayer IDs with Comptroller API
    3. Combine both datasets intelligently
    4. Remove duplicates
    5. Export final clean data
    
    ⚠ Warning: This may take significant time for large datasets
    """)
    
    from rich.prompt import Confirm, IntPrompt
    
    if not Confirm.ask("\nProceed with Full Pipeline?", default=False):
        return
    
    console.print("\n[bold]Starting Full Pipeline...[/bold]\n")
    
    try:
        from scripts.batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        processor.handle_full_pipeline()
        
        console.print("\n[bold green]✓ Full Pipeline Complete![/bold green]")
        
    except Exception as e:
        console.print(f"\n✗ Error: {e}", style="red bold")
    
    console.print("\nPress Enter to continue...")
    input()


def main():
    """Main entry point"""
    
    # Check configuration
    from config.settings import validate_configuration
    issues = validate_configuration()
    
    if issues:
        console.print("\n[yellow]Configuration Issues:[/yellow]")
        for issue in issues:
            console.print(f"  {issue}")
        console.print()
    
    while True:
        try:
            show_main_menu()
            
            choice = Prompt.ask(
                "\n[bold cyan]Select an option[/bold cyan]",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0"],
                default="0"
            )
            
            if choice == "0":
                console.print("\n[bold cyan]Thank you for using Texas Data Scraper![/bold cyan]")
                console.print("Goodbye! 👋\n")
                break
                
            elif choice == "1":
                run_socrata_scraper()
                
            elif choice == "2":
                run_comptroller_scraper()
                
            elif choice == "3":
                run_batch_processor()
                
            elif choice == "4":
                run_data_combiner()
                
            elif choice == "5":
                run_deduplicator()
                
            elif choice == "6":
                run_outlet_enricher()
                
            elif choice == "7":
                run_api_tester()
                
            elif choice == "8":
                show_configuration()
                
            elif choice == "9":
                run_quick_start()
                
            elif choice == "10":
                run_full_pipeline()
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
            from rich.prompt import Confirm
            if Confirm.ask("Exit program?", default=False):
                break
        except Exception as e:
            console.print(f"\n[red bold]Unexpected error: {e}[/red bold]")
            import traceback
            console.print(traceback.format_exc(), style="red dim")
            console.print("\nPress Enter to continue...")
            input()


if __name__ == "__main__":
    main()