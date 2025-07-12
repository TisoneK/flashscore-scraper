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
    
    def create_prediction_table(self, results: list) -> Table:
        """Create a colored prediction results table."""
        table = Table(
            title="[bold cyan]Prediction Results[/bold cyan]",
            box=box.ROUNDED,
            border_style=self.colors.TABLE_BORDER,
            row_styles=["", "dim"],  # Alternate row styling
            show_lines=True  # Show lines between rows
        )
        
        # Add columns with colors in new order
        table.add_column("NO.", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("MATCH_ID", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("DATE/TIME", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("COUNTRY/LEAGUE", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("HOME", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("AWAY", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("LINE", style="yellow", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVG", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("RATIO", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("PRED.", style="magenta", header_style=self.colors.TABLE_HEADER)
        table.add_column("WINNER", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("CONF.", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVGRATE", style="green", header_style=self.colors.TABLE_HEADER)
        
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
            winner_value = result.get('winner') or 'NO_BET'
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
            row_style = self.colors.TABLE_ROW_ALT if i % 2 == 1 else ""
            
            table.add_row(
                str(i + 1),
                str(result.get('match_id', 'N/A')),
                str(result.get('date', 'N/A')),
                f"{str(result.get('country', 'N/A'))}\n{str(result.get('league', 'N/A'))}",
                str(result.get('home', 'N/A')),
                str(result.get('away', 'N/A')),
                str(result.get('line', 'N/A')),
                str(result.get('avg', 'N/A')),
                str(result.get('ratio', 'N/A')),
                f"[{pred_color}]{result.get('prediction', 'N/A')}[/{pred_color}]",
                f"[{winner_color}]{winner_value}[/{winner_color}]",
                f"[{conf_color}]{result.get('confidence', 'N/A')}[/{conf_color}]",
                str(result.get('avg_rate', 'N/A')),
                style=row_style
            )
        
        return table

    def create_actionable_predictions_table(self, results: list) -> Table:
        """Create a table for actionable predictions (OVER/UNDER only)."""
        table = Table(
            title="[bold green]🎯 ACTIONABLE PREDICTIONS (OVER/UNDER)[/bold green]",
            box=box.ROUNDED,
            border_style=self.colors.TABLE_BORDER,
            row_styles=["", "dim"],  # Alternate row styling
            show_lines=True  # Show lines between rows
        )
        
        # Add columns with colors in new order
        table.add_column("NO.", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("MATCH_ID", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("DATE/TIME", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("COUNTRY/LEAGUE", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("HOME", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("AWAY", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("LINE", style="yellow", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVG", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("RATIO", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("PRED.", style="magenta", header_style=self.colors.TABLE_HEADER)
        table.add_column("WINNER", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("CONF.", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVGRATE", style="green", header_style=self.colors.TABLE_HEADER)
        
        # Add rows with prediction-specific colors
        for i, result in enumerate(results):
            # Determine prediction color
            pred_color = self.colors.PREDICTION_OVER if result['prediction'] == 'OVER' else self.colors.PREDICTION_UNDER
            
            # Determine winner color
            winner_color = self.colors.PREDICTION_NO_BET
            winner_value = result.get('winner') or 'NO_BET'
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
            row_style = self.colors.TABLE_ROW_ALT if i % 2 == 1 else ""
            
            table.add_row(
                str(i + 1),
                str(result.get('match_id', 'N/A')),
                str(result.get('date', 'N/A')),
                f"{str(result.get('country', 'N/A'))}\n{str(result.get('league', 'N/A'))}",
                str(result.get('home', 'N/A')),
                str(result.get('away', 'N/A')),
                str(result.get('line', 'N/A')),
                str(result.get('avg', 'N/A')),
                str(result.get('ratio', 'N/A')),
                f"[{pred_color}]{result.get('prediction', 'N/A')}[/{pred_color}]",
                f"[{winner_color}]{winner_value}[/{winner_color}]",
                f"[{conf_color}]{result.get('confidence', 'N/A')}[/{conf_color}]",
                str(result.get('avg_rate', 'N/A')),
                style=row_style
            )
        
        return table

    def create_no_bet_predictions_table(self, results: list) -> Table:
        """Create a table for NO_BET predictions only."""
        table = Table(
            title="[bold yellow]⏸️  NO_BET PREDICTIONS (For Team Winner Analysis)[/bold yellow]",
            box=box.ROUNDED,
            border_style=self.colors.TABLE_BORDER,
            row_styles=["", "dim"],  # Alternate row styling
            show_lines=True  # Show lines between rows
        )
        
        # Add columns with colors in new order
        table.add_column("NO.", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("MATCH_ID", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("DATE/TIME", style="cyan", header_style=self.colors.TABLE_HEADER)
        table.add_column("COUNTRY/LEAGUE", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("HOME", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("AWAY", style="white", header_style=self.colors.TABLE_HEADER)
        table.add_column("LINE", style="yellow", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVG", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("RATIO", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("PRED.", style="magenta", header_style=self.colors.TABLE_HEADER)
        table.add_column("WINNER", style="green", header_style=self.colors.TABLE_HEADER)
        table.add_column("CONF.", style="blue", header_style=self.colors.TABLE_HEADER)
        table.add_column("AVGRATE", style="green", header_style=self.colors.TABLE_HEADER)
        
        # Add rows with prediction-specific colors
        for i, result in enumerate(results):
            # Determine prediction color (all NO_BET)
            pred_color = self.colors.PREDICTION_NO_BET
            
            # Determine winner color
            winner_color = self.colors.PREDICTION_NO_BET
            winner_value = result.get('winner') or 'NO_BET'
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
            row_style = self.colors.TABLE_ROW_ALT if i % 2 == 1 else ""
            
            table.add_row(
                str(i + 1),
                str(result.get('match_id', 'N/A')),
                str(result.get('date', 'N/A')),
                f"{str(result.get('country', 'N/A'))}\n{str(result.get('league', 'N/A'))}",
                str(result.get('home', 'N/A')),
                str(result.get('away', 'N/A')),
                str(result.get('line', 'N/A')),
                str(result.get('avg', 'N/A')),
                str(result.get('ratio', 'N/A')),
                f"[{pred_color}]{result.get('prediction', 'N/A')}[/{pred_color}]",
                f"[{winner_color}]{winner_value}[/{winner_color}]",
                f"[{conf_color}]{result.get('confidence', 'N/A')}[/{conf_color}]",
                str(result.get('avg_rate', 'N/A')),
                style=row_style
            )
        
        return table

    def show_dual_prediction_tables(self, actionable_results: list, no_bet_results: list):
        """Display dual prediction tables - actionable and NO_BET separately."""
        # Show actionable predictions first (most important)
        if actionable_results:
            self.console.print("\n")
            actionable_table = self.create_actionable_predictions_table(actionable_results)
            self.console.print(actionable_table)
            self.console.print(f"\n[bold green]📊 Found {len(actionable_results)} actionable predictions[/bold green]")
        else:
            self.console.print("\n[bold yellow]⚠️  No actionable predictions found[/bold yellow]")
        
        # Show NO_BET predictions second (for team winner analysis)
        if no_bet_results:
            self.console.print("\n")
            no_bet_table = self.create_no_bet_predictions_table(no_bet_results)
            self.console.print(no_bet_table)
            self.console.print(f"\n[bold yellow]📊 Found {len(no_bet_results)} NO_BET predictions (check team winners)[/bold yellow]")
        else:
            self.console.print("\n[bold yellow]⚠️  No NO_BET predictions found[/bold yellow]")
        
        # Show summary
        total_predictions = len(actionable_results) + len(no_bet_results)
        if total_predictions > 0:
            actionable_percentage = (len(actionable_results) / total_predictions) * 100
            self.console.print(f"\n[bold cyan]📈 SUMMARY: {len(actionable_results)}/{total_predictions} predictions are actionable ({actionable_percentage:.1f}%)[/bold cyan]")
    
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

    def show_sort_header(self):
        """Show sort section header."""
        header = f"[bold {self.colors.SECONDARY}]📊 Sort Results[/bold {self.colors.SECONDARY}]"
        self.console.print(header)

    def show_prediction_menu_header(self):
        """Show prediction menu header."""
        header = f"""
[bold {self.colors.PRIMARY}]🎯 Prediction Menu[/bold {self.colors.PRIMARY}]
[dim]Filter, sort, and analyze your predictions[/dim]
        """
        self.console.print(Panel(header, box=box.ROUNDED, expand=False))
    
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