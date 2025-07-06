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
                "Logging Settings"
            ],
            default="Browser Settings"
        ).execute()
        
        if category == "Browser Settings":
            # Browser settings
            settings['headless'] = inquirer.confirm(
                message="Run browser in headless mode?",
                default=True
            ).execute()
            
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
        
        return settings 