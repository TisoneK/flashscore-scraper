"""
Color scheme for CLI interface.
Defines consistent colors for different UI elements.
"""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box

class ColorScheme:
    """Color scheme for CLI interface."""
    
    # Main colors
    PRIMARY = "cyan"
    SECONDARY = "blue"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "magenta"
    
    # UI element colors
    BUTTON = "cyan"
    BUTTON_SELECTED = "bright_cyan"
    BUTTON_BACK = "yellow"
    BUTTON_EXIT = "red"
    
    # Menu colors
    MENU_TITLE = "bold cyan"
    MENU_ITEM = "white"
    MENU_ITEM_SELECTED = "bright_cyan"
    MENU_BACK = "yellow"
    MENU_EXIT = "red"
    
    # Status colors
    STATUS_SUCCESS = "green"
    STATUS_WARNING = "yellow"
    STATUS_ERROR = "red"
    STATUS_INFO = "blue"
    
    # Table colors
    TABLE_HEADER = "bold cyan"
    TABLE_ROW_ALT = "dim"
    TABLE_BORDER = "cyan"
    
    # Progress colors
    PROGRESS_BAR = "cyan"
    PROGRESS_TEXT = "white"
    PROGRESS_SPINNER = "cyan"

class ColoredDisplay:
    """Enhanced display with consistent color scheme."""
    
    def __init__(self):
        self.console = Console()
        self.colors = ColorScheme()
    
    def create_menu_panel(self, title: str, content: str, color: str | None = None) -> Panel:
        """Create a colored menu panel."""
        if color is None:
            color = self.colors.PRIMARY
        return Panel(content, title=f"[{color}]{title}[/{color}]", box=box.ROUNDED, expand=False)
    
    def create_button_text(self, text: str, button_type: str = "primary") -> str:
        """Create colored button text."""
        if button_type == "back":
            return f"[{self.colors.BUTTON_BACK}]{text}[/{self.colors.BUTTON_BACK}]"
        elif button_type == "exit":
            return f"[{self.colors.BUTTON_EXIT}]{text}[/{self.colors.BUTTON_EXIT}]"
        elif button_type == "selected":
            return f"[{self.colors.BUTTON_SELECTED}]{text}[/{self.colors.BUTTON_SELECTED}]"
        else:
            return f"[{self.colors.BUTTON}]{text}[/{self.colors.BUTTON}]"
    
    def create_menu_item(self, text: str, is_selected: bool = False, item_type: str = "normal") -> str:
        """Create colored menu item text."""
        if item_type == "back":
            return f"[{self.colors.MENU_BACK}]{text}[/{self.colors.MENU_BACK}]"
        elif item_type == "exit":
            return f"[{self.colors.MENU_EXIT}]{text}[/{self.colors.MENU_EXIT}]"
        elif is_selected:
            return f"[{self.colors.MENU_ITEM_SELECTED}]{text}[/{self.colors.MENU_ITEM_SELECTED}]"
        else:
            return f"[{self.colors.MENU_ITEM}]{text}[/{self.colors.MENU_ITEM}]"
    
    def show_welcome(self):
        """Show enhanced welcome message with colors."""
        welcome_text = f"""
[bold {self.colors.PRIMARY}]Flashscore Basketball Scraper[/bold {self.colors.PRIMARY}]
[dim]Interactive CLI for scraping basketball match data[/dim]

[bold]Features:[/bold]
• One-click scraping with defaults
• Interactive configuration
• Real-time progress tracking  
• Rich console output
        """
        self.console.print(self.create_menu_panel("Welcome", welcome_text))
    
    def show_filter_header(self, filter_type: str):
        """Show filter section header."""
        header = f"[bold {self.colors.SECONDARY}]🔍 {filter_type} Filter[/bold {self.colors.SECONDARY}]"
        self.console.print(header)

    def show_sort_header(self):
        """Show sort section header."""
        header = f"[bold {self.colors.SECONDARY}]📊 Sort Results[/bold {self.colors.SECONDARY}]"
        self.console.print(header)
    
    def show_status_message(self, message: str, status_type: str = "info"):
        """Show colored status message."""
        color = getattr(self.colors, f"STATUS_{status_type.upper()}", self.colors.INFO)
        self.console.print(f"[{color}]{message}[/{color}]")
    
    def show_success_message(self, message: str):
        """Show success message."""
        self.console.print(f"[{self.colors.SUCCESS}]✅ {message}[/{self.colors.SUCCESS}]")
    
    def show_warning_message(self, message: str):
        """Show warning message."""
        self.console.print(f"[{self.colors.WARNING}]⚠️  {message}[/{self.colors.WARNING}]")
    
    def show_error_message(self, message: str):
        """Show error message."""
        self.console.print(f"[{self.colors.ERROR}]❌ {message}[/{self.colors.ERROR}]")
    
    def show_info_message(self, message: str):
        """Show info message."""
        self.console.print(f"[{self.colors.INFO}]ℹ️  {message}[/{self.colors.INFO}]")
    
    def show_goodbye(self):
        """Show enhanced goodbye message."""
        self.console.print(f"\n[bold {self.colors.SECONDARY}]👋 Goodbye![/bold {self.colors.SECONDARY}]")
