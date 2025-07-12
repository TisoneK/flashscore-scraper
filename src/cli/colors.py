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
    
    # Prediction colors
    PREDICTION_OVER = "green"
    PREDICTION_UNDER = "red"
    PREDICTION_NO_BET = "yellow"
    PREDICTION_HIGH_CONFIDENCE = "bright_green"
    PREDICTION_MEDIUM_CONFIDENCE = "yellow"
    PREDICTION_LOW_CONFIDENCE = "red"
    
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
    
    def create_menu_panel(self, title: str, content: str, color: str = None) -> Panel:
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
    
    def create_prediction_table(self, results: list) -> Table:
        """Create a colored prediction results table."""
        table = Table(
            title="[bold cyan]Prediction Results[/bold cyan]",
            box=box.ROUNDED,
            border_style=self.colors.TABLE_BORDER
        )
        
        # Add columns with colors
        table.add_column("Date/Time", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("Home", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("Away", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("Line", style="yellow", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVG", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("RATIO", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("Prediction", style="magenta", header_style=self.colors.TABLE_HEADER)
        table.add_column("Winner", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("Conf.", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("AvgRate", style="green", header_style=self.colors.TABLE_HEADER)
        
        # Add rows with prediction-specific colors
        for i, result in enumerate(results):
            # Determine prediction color
            pred_color = self.colors.PREDICTION_NO_BET
            if result['prediction'] == 'OVER':
                pred_color = self.colors.PREDICTION_OVER
            elif result['prediction'] == 'UNDER':
                pred_color = self.colors.PREDICTION_UNDER
            
            # Determine winner color
            winner_color = self.colors.PREDICTION_NO_BET
            winner_value = result.get('winner', 'NO_BET')
            if winner_value == 'HOME_TEAM':
                winner_color = self.colors.PREDICTION_OVER
            elif winner_value == 'AWAY_TEAM':
                winner_color = self.colors.PREDICTION_UNDER
            
            # Determine confidence color
            conf_color = self.colors.PREDICTION_LOW_CONFIDENCE
            if result['confidence'] == 'HIGH':
                conf_color = self.colors.PREDICTION_HIGH_CONFIDENCE
            elif result['confidence'] == 'MEDIUM':
                conf_color = self.colors.PREDICTION_MEDIUM_CONFIDENCE
            
            # Alternate row colors
            row_style = self.colors.TABLE_ROW_ALT if i % 2 == 1 else None
            
            table.add_row(
                result['date'],
                result['home'],
                result['away'],
                str(result['line']),
                str(result.get('avg', 'N/A')),
                str(result.get('ratio', 'N/A')),
                f"[{pred_color}]{result['prediction']}[/{pred_color}]",
                f"[{winner_color}]{winner_value}[/{winner_color}]",
                f"[{conf_color}]{result['confidence']}[/{conf_color}]",
                result['avg_rate'],
                style=row_style
            )
        
        return table
    
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
• [bold {self.colors.SUCCESS}]AI-powered predictions[/bold {self.colors.SUCCESS}]
        """
        self.console.print(self.create_menu_panel("Welcome", welcome_text))
    
    def show_prediction_header(self):
        """Show prediction section header."""
        header = f"""
[bold {self.colors.PRIMARY}]🎯 Prediction System[/bold {self.colors.PRIMARY}]
[dim]Analyze match data using ScoreWise algorithm[/dim]
        """
        self.console.print(Panel(header, box=box.ROUNDED, expand=False))
    
    def show_filter_header(self, filter_type: str):
        """Show filter section header."""
        header = f"[bold {self.colors.SECONDARY}]🔍 {filter_type} Filter[/bold {self.colors.SECONDARY}]"
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