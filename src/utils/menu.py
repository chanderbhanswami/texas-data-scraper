"""
Interactive CLI Menu Utilities
"""
from typing import List, Dict, Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


class MenuItem:
    """Represents a single menu item"""
    
    def __init__(self, key: str, label: str, action: Optional[Callable] = None, 
                 description: str = ""):
        self.key = key
        self.label = label
        self.action = action
        self.description = description


class Menu:
    """Interactive CLI menu builder"""
    
    def __init__(self, title: str, subtitle: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.items: List[MenuItem] = []
        self.exit_key = "0"
        self.exit_label = "Exit"
        
    def add_item(self, key: str, label: str, action: Optional[Callable] = None,
                 description: str = ""):
        """Add menu item"""
        self.items.append(MenuItem(key, label, action, description))
        
    def add_separator(self):
        """Add visual separator"""
        self.items.append(MenuItem("", "", None, ""))
        
    def display(self) -> str:
        """Display menu and get user choice"""
        console.print("\n" + "="*60, style="bold")
        console.print(self.title.upper(), style="bold cyan")
        if self.subtitle:
            console.print(self.subtitle, style="dim")
        console.print("="*60, style="bold")
        
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan", width=4)
        table.add_column("Option", style="white")
        
        valid_keys = []
        for item in self.items:
            if item.key:
                table.add_row(item.key, item.label)
                valid_keys.append(item.key)
            else:
                table.add_row("", "")
        
        # Add exit option
        table.add_row(self.exit_key, self.exit_label)
        valid_keys.append(self.exit_key)
        
        console.print(table)
        
        choice = Prompt.ask("\nSelect an option", choices=valid_keys, default=self.exit_key)
        return choice
    
    def run(self):
        """Run menu loop"""
        while True:
            choice = self.display()
            
            if choice == self.exit_key:
                console.print(f"\nExiting {self.title}...", style="cyan")
                break
            
            # Find and execute action
            for item in self.items:
                if item.key == choice and item.action:
                    try:
                        item.action()
                    except KeyboardInterrupt:
                        console.print("\n\nOperation cancelled", style="yellow")
                        if Confirm.ask("Return to menu?", default=True):
                            continue
                        else:
                            return
                    except Exception as e:
                        console.print(f"\nError: {e}", style="red bold")
                        console.print("Returning to menu...", style="yellow")
                    break


class ProgressMenu:
    """Menu with progress tracking"""
    
    def __init__(self, title: str):
        self.title = title
        self.steps: List[Dict] = []
        self.current_step = 0
        
    def add_step(self, name: str, description: str, action: Callable):
        """Add a step to the workflow"""
        self.steps.append({
            'name': name,
            'description': description,
            'action': action,
            'completed': False
        })
    
    def display_progress(self):
        """Display progress"""
        console.print(f"\n[bold cyan]{self.title}[/bold cyan]")
        console.print(f"Progress: {self.current_step}/{len(self.steps)} steps completed\n")
        
        table = Table()
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Description", style="dim")
        
        for i, step in enumerate(self.steps, 1):
            status = "✓" if step['completed'] else "○"
            if i == self.current_step + 1 and not step['completed']:
                status = "→"
            
            style = "green" if step['completed'] else "white"
            table.add_row(
                f"{i}. {step['name']}",
                status,
                step['description'],
                style=style
            )
        
        console.print(table)
    
    def run(self):
        """Run workflow"""
        for i, step in enumerate(self.steps):
            self.current_step = i
            self.display_progress()
            
            console.print(f"\n[bold]Step {i+1}: {step['name']}[/bold]")
            
            if not Confirm.ask("Proceed with this step?", default=True):
                console.print("Workflow cancelled", style="yellow")
                return False
            
            try:
                step['action']()
                step['completed'] = True
                console.print(f"✓ {step['name']} completed!", style="green")
            except Exception as e:
                console.print(f"✗ Error: {e}", style="red")
                if not Confirm.ask("Continue with next step?", default=False):
                    return False
        
        self.current_step = len(self.steps)
        self.display_progress()
        console.print("\n[bold green]✓ All steps completed![/bold green]")
        return True


def show_banner(text: str, style: str = "bold cyan"):
    """Show a banner message"""
    width = max(len(line) for line in text.split('\n'))
    border = "═" * (width + 4)
    
    console.print(f"\n╔{border}╗", style=style)
    for line in text.split('\n'):
        padding = " " * (width - len(line))
        console.print(f"║  {line}{padding}  ║", style=style)
    console.print(f"╚{border}╝\n", style=style)


def show_success(message: str):
    """Show success message"""
    console.print(f"✓ {message}", style="green bold")


def show_error(message: str):
    """Show error message"""
    console.print(f"✗ {message}", style="red bold")


def show_warning(message: str):
    """Show warning message"""
    console.print(f"⚠ {message}", style="yellow bold")


def show_info(message: str):
    """Show info message"""
    console.print(f"ℹ {message}", style="cyan")


def confirm_action(message: str, default: bool = True) -> bool:
    """Ask for confirmation"""
    return Confirm.ask(message, default=default)


def select_from_list(items: List[str], title: str = "Select an option") -> Optional[str]:
    """Select item from list"""
    if not items:
        return None
    
    console.print(f"\n[bold]{title}:[/bold]")
    
    table = Table()
    table.add_column("#", style="cyan")
    table.add_column("Option", style="white")
    
    for i, item in enumerate(items, 1):
        table.add_row(str(i), item)
    
    console.print(table)
    
    choice = Prompt.ask(
        "Select number",
        choices=[str(i) for i in range(1, len(items) + 1)]
    )
    
    return items[int(choice) - 1]


def display_stats(stats: Dict, title: str = "Statistics"):
    """Display statistics table"""
    table = Table(title=title)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    for key, value in stats.items():
        # Format key (replace underscores with spaces, title case)
        formatted_key = key.replace('_', ' ').title()
        
        # Format value
        if isinstance(value, float):
            formatted_value = f"{value:.2f}"
        elif isinstance(value, int):
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        table.add_row(formatted_key, formatted_value)
    
    console.print("\n")
    console.print(table)
    console.print()


def create_panel(content: str, title: str, style: str = "cyan") -> Panel:
    """Create a panel with content"""
    return Panel(content, title=title, border_style=style)