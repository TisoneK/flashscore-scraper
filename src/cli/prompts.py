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
                "Exit"
            ],
            default="Start Scraping"
        ).execute()

    def ask_main_action_dynamic(self, choices, default=None):
        """Ask user for main action with dynamic choices."""
        return inquirer.select(
            message="What would you like to do?",
            choices=choices,
            default=default or (choices[0] if choices else None)
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
                "Terminal Clearing",
                "Back"
            ],
            default="Browser Settings"
        ).execute()
        
        if category == "Back":
            return {"__back": True}

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

    def ask_scraping_mode_dynamic(self, choices, default=None):
        """Ask user for scraping mode with dynamic choices."""
        return inquirer.select(
            message="Select scraping mode:",
            choices=choices,
            default=default or (choices[0] if choices else None)
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

    # New: Frequency and scheduling prompts
    def ask_frequency_mode(self):
        """Ask user how often to run scraping."""
        return inquirer.select(
            message="Run scraping:",
            choices=[
                "Once",
                "Repetitive",
                "Back"
            ],
            default="Once"
        ).execute()

    def ask_repetitive_interval(self):
        """Ask for a predefined repetitive interval or custom."""
        return inquirer.select(
            message="Select frequency:",
            choices=[
                "Every 30 minutes",
                "Every 1 hour",
                "Every 2 hours",
                "Every 6 hours",
                "Every 12 hours",
                "Every 24 hours",
                "Set Custom Time",
                "Back"
            ],
            default="Every 1 hour"
        ).execute()

    def ask_custom_interval_text(self):
        """Ask for a custom interval (flexible formats)."""
        return inquirer.text(
            message="Enter custom interval (e.g., '45m', '45 minutes', 'Every 45 minutes'):"
        ).execute()

    def ask_start_time(self):
        """Ask when to start the schedule."""
        return inquirer.select(
            message="Start time:",
            choices=[
                "Now",
                "Midday",
                "Midnight",
                "Set Custom",
                "Back"
            ],
            default="Now"
        ).execute()

    def ask_custom_start_time(self):
        """Ask for a custom start time (HH:MM 24h)."""
        return inquirer.text(
            message="Enter start time (HH:MM, 24-hour):"
        ).execute()

    def ask_schedule_post_action(self):
        """Ask what to do with the active schedule after scraping finishes."""
        return inquirer.select(
            message="Schedule options:",
            choices=[
                "Keep schedule running (return to Main Menu)",
                "Cancel schedule",
                "Back"
            ],
            default="Keep schedule running (return to Main Menu)"
        ).execute()