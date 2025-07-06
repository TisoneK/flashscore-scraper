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
        
        # Browser settings
        settings['headless'] = inquirer.confirm(
            message="Run browser in headless mode?",
            default=True
        ).execute()
        
        # Output settings
        settings['output_format'] = inquirer.select(
            message="Default output format:",
            choices=["json", "csv"],
            default="json"
        ).execute()
        
        # Logging settings
        settings['log_level'] = inquirer.select(
            message="Log level:",
            choices=["INFO", "DEBUG", "WARNING", "ERROR"],
            default="INFO"
        ).execute()
        
        return settings 