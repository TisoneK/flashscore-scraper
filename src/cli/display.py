from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

class ConsoleDisplay:
    def __init__(self):
        self.console = Console()

    def show_welcome(self):
        """Show welcome message."""
        welcome_text = """
[bold green]Flashscore Basketball Scraper[/bold green]
[dim]Interactive CLI for scraping basketball match data[/dim]

[bold]Features:[/bold]
• One-click scraping with defaults
• Interactive configuration
• Real-time progress tracking  
• Rich console output
        """
        self.console.print(Panel(welcome_text, box=box.ROUNDED, expand=False))

    def show_main_menu_header(self):
        """Show main menu header."""
        self.show_welcome()

    def show_settings_header(self):
        """Show settings menu header."""
        settings_text = """
[bold blue]⚙️  Settings Configuration[/bold blue]
[dim]Configure your scraper settings and preferences[/dim]
        """
        self.console.print(Panel(settings_text, box=box.ROUNDED, expand=False))

    def show_prediction_header(self):
        """Show prediction menu header."""
        prediction_text = """
[bold purple]🔮 Match Predictions[/bold purple]
[dim]Analyze match data and generate predictions[/dim]
        """
        self.console.print(Panel(prediction_text, box=box.ROUNDED, expand=False))

    def show_status_header(self):
        """Show status page header."""
        status_text = """
[bold yellow]📊 Scraper Status[/bold yellow]
[dim]View current scraper status and statistics[/dim]
        """
        self.console.print(Panel(status_text, box=box.ROUNDED, expand=False))

    def show_scraping_header(self):
        """Show scraping page header."""
        scraping_text = """
[bold green]🚀 Scraping Mode[/bold green]
[dim]Extract basketball match data from Flashscore[/dim]
        """
        self.console.print(Panel(scraping_text, box=box.ROUNDED, expand=False))

    def show_scraping_start_immediate(self):
        """Show immediate scraping start message."""
        self.console.print("\n[bold yellow]🚀 Starting scraper with current settings...[/bold yellow]")

    def show_scraping_start_with_day(self, day):
        """Show scraping start message with day information."""
        self.console.print(f"\n[bold yellow]🚀 Starting scraping for {day.lower()}...[/bold yellow]")

    def show_scraping_start(self):
        """Show scraping start message."""
        self.console.print("\n[bold yellow]🚀 Starting scraping process...[/bold yellow]")

    def show_scraping_complete(self):
        """Show scraping completion message."""
        self.console.print("\n[bold green]✅ Scraping completed successfully![/bold green]")

    def show_scraping_results(self, results, critical_messages):
        """Show detailed scraping results."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]📊 SCRAPING RESULTS[/bold green]")
        self.console.print("="*60)
        
        # Show basic statistics
        if results:
            table = Table(title="Scraping Statistics", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")
            
            if 'scheduled_matches' in results:
                table.add_row("Scheduled Matches", str(results['scheduled_matches']))
            if 'processed_matches' in results:
                table.add_row("Previously Processed", str(results['processed_matches']))
            if 'skipped_matches' in results:
                table.add_row("Skipped Matches", str(results['skipped_matches']))
            if 'new_matches' in results:
                table.add_row("New Matches Processed", str(results['new_matches']))
            if 'total_collected' in results:
                table.add_row("Total Collected", str(results['total_collected']))
            
            self.console.print(table)
            
            # Show detailed statistics if available
            detailed_stats = []
            if 'complete_matches' in results or 'incomplete_matches' in results:
                complete = results.get('complete_matches', 0)
                incomplete = results.get('incomplete_matches', 0)
                total_processed = complete + incomplete
                if total_processed > 0:
                    success_rate = (complete / total_processed) * 100
                    detailed_stats.append(f"Complete Matches: {complete}")
                    detailed_stats.append(f"Incomplete Matches: {incomplete}")
                    detailed_stats.append(f"Success Rate: {success_rate:.1f}%")
            
            if 'matches_collected_today' in results and results['matches_collected_today'] > 0:
                detailed_stats.append(f"Matches Collected Today: {results['matches_collected_today']}")
            
            if detailed_stats:
                self.console.print("\n[bold cyan]📈 DETAILED STATISTICS[/bold cyan]")
                for stat in detailed_stats:
                    self.console.print(f"[dim]• {stat}[/dim]")
            
            # Show skip reasons if available
            if 'skip_reasons' in results and results['skip_reasons']:
                self.console.print("\n[bold yellow]⏭️  SKIP REASONS[/bold yellow]")
                for reason, count in results['skip_reasons'].items():
                    # Clean up the reason text to ensure proper formatting
                    clean_reason = reason.strip()
                    if clean_reason and not clean_reason.endswith(')'):
                        clean_reason += ')'
                    self.console.print(f"[dim]• {clean_reason}: {count} matches[/dim]")
        
        # Show critical messages if any
        if critical_messages:
            self.console.print("\n[bold yellow]⚠️  BROWSER/DRIVER MESSAGES[/bold yellow]")
            for msg in critical_messages:
                if 'error:' in msg.lower():
                    self.console.print(f"[red]{msg}[/red]")
                elif 'warning:' in msg.lower():
                    self.console.print(f"[yellow]{msg}[/yellow]")
                elif 'devtools' in msg.lower():
                    self.console.print(f"[blue]{msg}[/blue]")
                else:
                    self.console.print(f"[dim]{msg}[/dim]")
        
        # Show summary
        if results.get('total_collected', 0) > 0:
            self.console.print(f"\n[bold green]✅ Successfully collected {results['total_collected']} matches![/bold green]")
        elif results.get('skipped_matches', 0) > 0:
            self.console.print(f"\n[bold yellow]ℹ️  Skipped {results['skipped_matches']} matches (already processed).[/bold yellow]")
            if 'skip_reasons' in results and results['skip_reasons']:
                reasons = list(results['skip_reasons'].keys())
                if reasons:
                    self.console.print(f"[dim]Main reasons: {', '.join(reasons[:3])}[/dim]")
        else:
            self.console.print(f"\n[bold blue]ℹ️  No new matches found to process.[/bold blue]")
        
        self.console.print("="*60)

    def show_initializing(self):
        """Show initialization message."""
        self.console.print("[cyan]🔧 Initializing scraper...[/cyan]")

    def show_configuration_start(self):
        """Show configuration start message."""
        self.console.print("\n[cyan]⚙️  Configuration Mode[/cyan]")
        self.console.print("[dim]Configure your scraper settings below:[/dim]\n")

    def show_scraping_config(self, options):
        """Show scraping configuration."""
        table = Table(title="Scraping Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Browser Mode", "Headless" if options.get('headless') else "Visible")
        table.add_row("Logging", "Verbose" if options.get('verbose_logging') else "Standard")
        table.add_row("Output Format", options.get('output_format', 'json').upper())
        
        self.console.print(table)

    def show_settings_saved(self):
        """Show settings saved message."""
        self.console.print("[green]✅ Settings saved successfully![/green]")

    def show_cancelled(self):
        """Show cancellation message."""
        self.console.print("[yellow]⚠️  Scraping cancelled by user[/yellow]")

    def show_interrupted(self):
        """Show interruption message."""
        self.console.print("\n[yellow]⚠️  Scraping interrupted by user[/yellow]")

    def show_error(self, error_msg):
        """Show error message."""
        self.console.print(f"[bold red]❌ Error: {error_msg}[/bold red]")

    def show_status(self, file_count):
        """Show current status."""
        status_text = f"""
[bold]Current Status:[/bold]
• Output files: {file_count}
• Output directory: output/
        """
        self.console.print(Panel(status_text, title="Status", box=box.ROUNDED))

    def show_settings(self):
        self.console.print(Panel("[cyan]Settings page (not implemented yet)[/cyan]", expand=False))

    def show_goodbye(self):
        """Show goodbye message."""
        self.console.print("\n[bold blue]👋 Goodbye![/bold blue]") 