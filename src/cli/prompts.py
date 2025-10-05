from InquirerPy import inquirer
from InquirerPy.validator import PathValidator

class ScraperPrompts:
    def ask_main_action(self):
        """Ask user for main action."""
        return inquirer.select(
            message="What would you like to do?",
            choices=[
                "Start Scraping",
                "Configure Settings", 
                "View Status",
                "Prediction",
                "Exit"
            ],
            default="Start Scraping"
        ).execute()

    def ask_scraping_day(self):
        """Ask user for which day to scrape."""
        return inquirer.select(
            message="Select day to scrape:",
            choices=[
                "Today",
                "Tomorrow",
                "Back"
            ],
            default="Today"
        ).execute()

    def ask_prediction_range(self):
        """Ask user for prediction date range."""
        return inquirer.select(
            message="Prediction - Select range:",
            choices=[
                "Yesterday",
                "Today",
                "Tomorrow",
                "All",
                "Back"
            ],
            default="Today"
        ).execute()

    def ask_settings(self):
        """Ask user for general settings."""
        settings = {}
        
        # Ask for settings category first
        category = inquirer.select(
            message="What would you like to configure?",
            choices=[
                "Browser Settings",
                "Driver Management", 
                "Output Settings",
                "Logging Settings",
                "Day Selection",
                "Terminal Clearing"
            ],
            default="Browser Settings"
        ).execute()
        
        if category == "Browser Settings":
            # Initialize browser settings if not exists
            if 'browser' not in settings:
                settings['browser'] = {}
                
            # Browser settings
            settings['browser']['headless'] = inquirer.confirm(
                message="Run browser in headless mode?",
                default=True
            ).execute()
            
            # Add more browser settings if needed
            settings['browser']['window_size'] = [1920, 1080]  # Default window size
            settings['browser']['disable_images'] = False  # Default image loading setting
            
        elif category == "Driver Management":
            # Driver management
            driver_action = inquirer.select(
                message="Driver Management:",
                choices=[
                    "Check Driver Status",
                    "List Installed Drivers",
                    "Set Default Driver",
                    "Install New Driver"
                ],
                default="Check Driver Status"
            ).execute()
            settings['driver_action'] = driver_action
            
        elif category == "Output Settings":
            # Output settings
            settings['output_format'] = inquirer.select(
                message="Default output format:",
                choices=["json", "csv"],
                default="json"
            ).execute()
            
        elif category == "Logging Settings":
            # Logging settings
            settings['log_level'] = inquirer.select(
                message="Log level:",
                choices=["INFO", "DEBUG", "WARNING", "ERROR"],
                default="INFO"
            ).execute()
            # Toggle detailed per-match logging
            settings['log_match_details'] = inquirer.confirm(
                message="Log detailed per-match blocks (verbose)?",
                default=False
            ).execute()
            
        elif category == "Day Selection":
            # Day selection settings
            settings['default_day'] = inquirer.select(
                message="Default day for scraping:",
                choices=["Today", "Tomorrow"],
                default="Today"
            ).execute()
        
        elif category == "Terminal Clearing":
            # Terminal clearing settings
            settings['clear_terminal'] = inquirer.confirm(
                message="Clear terminal before showing main menu?",
                default=True
            ).execute()
        
        return settings 

    def ask_league_filter(self, leagues):
        """Prompt user to filter by league or show all."""
        return inquirer.select(
            message="Filter by league:",
            choices=["All"] + sorted(leagues) + ["Back"],
            default="All"
        ).execute()

    def ask_team_filter(self, teams):
        """Prompt user to filter by team or show all."""
        return inquirer.select(
            message="Filter by team:",
            choices=["All"] + sorted(teams) + ["Back"],
            default="All"
        ).execute()

    def ask_post_summary_action(self, match_choices):
        """Prompt user for post-summary action: view details, export, or back."""
        return inquirer.select(
            message="What would you like to do next?",
            choices=[
                {"name": f"View details for a match", "value": "details"} if match_choices else None,
                {"name": "Export results", "value": "export"} if match_choices else None,
                {"name": "Back", "value": "back"}
            ],
            default="back",
            filter=lambda x: x  # Remove None
        ).execute()

    def ask_select_match(self, match_choices):
        """Prompt user to select a match for details."""
        return inquirer.select(
            message="Select a match for details:",
            choices=match_choices + ["Back"],
            default=match_choices[0] if match_choices else "Back"
        ).execute()

    def ask_export_format(self):
        """Prompt user to select export format."""
        return inquirer.select(
            message="Select export format:",
            choices=["CSV", "JSON", "Back"],
            default="CSV"
        ).execute()

    def ask_filter_choice(self):
        """Prompt user to choose between filtering or proceeding with actions."""
        return inquirer.select(
            message="What would you like to do?",
            choices=[
                "Filter Results",
                "Sort Results",
                "View Details/Export",
                "Back"
            ],
            default="View Details/Export"
        ).execute()

    def ask_prediction_sort(self):
        """Ask user how to sort prediction results."""
        return inquirer.select(
            message="Sort predictions by:",
            choices=[
                "Time (Earliest First)",
                "Time (Latest First)",
                "Date (Newest First)",
                "Date (Oldest First)",
                "Confidence (High to Low)",
                "Confidence (Low to High)",
                "Prediction (OVER/UNDER/NO_BET)",
                "Winner (HOME/AWAY/NO_BET)",
                "Average Rate (High to Low)",
                "Average Rate (Low to High)",
                "Line (High to Low)",
                "Line (Low to High)",
                "No Sorting"
            ],
            default="Time (Earliest First)"
        ).execute()

    def ask_prediction_filter(self):
        """Ask user to filter prediction results."""
        return inquirer.select(
            message="Filter predictions by:",
            choices=[
                "All Predictions",
                "OVER predictions only",
                "UNDER predictions only", 
                "NO_BET predictions only",
                "HIGH confidence only",
                "MEDIUM confidence only",
                "LOW confidence only",
                "HOME_TEAM winners only",
                "AWAY_TEAM winners only",
                "NO_BET winners only",
                "Custom filter"
            ],
            default="All Predictions"
        ).execute()

    def ask_custom_filter(self):
        """Ask user for custom filter criteria."""
        filter_type = inquirer.select(
            message="Custom filter by:",
            choices=[
                "League",
                "Team",
                "Date Range",
                "Rate Range",
                "Line Range"
            ],
            default="League"
        ).execute()
        
        if filter_type == "League":
            return {"type": "league", "value": inquirer.text(message="Enter league name:").execute()}
        elif filter_type == "Team":
            return {"type": "team", "value": inquirer.text(message="Enter team name:").execute()}
        elif filter_type == "Date Range":
            start_date = inquirer.text(message="Start date (dd.mm.yyyy):").execute()
            end_date = inquirer.text(message="End date (dd.mm.yyyy):").execute()
            return {"type": "date_range", "start": start_date, "end": end_date}
        elif filter_type == "Rate Range":
            min_rate = inquirer.text(message="Minimum rate:").execute()
            max_rate = inquirer.text(message="Maximum rate:").execute()
            return {"type": "rate_range", "min": min_rate, "max": max_rate}
        elif filter_type == "Line Range":
            min_line = inquirer.text(message="Minimum line:").execute()
            max_line = inquirer.text(message="Maximum line:").execute()
            return {"type": "line_range", "min": min_line, "max": max_line} 

    def ask_back(self):
        """Prompt user with a single Back option."""
        return inquirer.select(
            message="Navigation:",
            choices=["Back"],
            default="Back"
        ).execute() 

    def ask_scraping_mode(self):
        """Ask user for scraping mode: scheduled matches or results."""
        return inquirer.select(
            message="Select scraping mode:",
            choices=[
                "Scheduled Matches",
                "Results",
                "Back"
            ],
            default="Scheduled Matches"
        ).execute()

    def ask_results_date(self):
        """Ask user for results scraping date (Yesterday default, Custom Date, Back)."""
        return inquirer.select(
            message="Select results scraping date:",
            choices=[
                "Yesterday",
                "Custom Date",
                "Back"
            ],
            default="Yesterday"
        ).execute() 