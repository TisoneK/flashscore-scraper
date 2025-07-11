import warnings
import logging
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import io
import contextlib
import threading
import queue
import time
import re
import os
import datetime
import glob
import json
from datetime import datetime, timedelta
import csv
import json as pyjson

# Suppress Python warnings about platform independent libraries
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

from src.config import CONFIG
from src.utils import setup_logging
from src.scraper import FlashscoreScraper
from .prompts import ScraperPrompts
from .display import ConsoleDisplay
from .colors import ColoredDisplay
from .progress import ProgressManager
from src.prediction import PredictionService
from src.models import MatchModel, OddsModel, H2HMatchModel
from src.prediction.prediction_data_loader import load_matches

class CLIManager:
    def __init__(self):
        self.prompts = ScraperPrompts()
        self.display = ConsoleDisplay()
        self.colored_display = ColoredDisplay()
        self.progress = ProgressManager()
        self.logger = logging.getLogger("cli")
        self.scraper: Optional[FlashscoreScraper] = None
        self.user_settings = self._load_user_settings()
        self.scraping_results = {}
        self.log_queue = queue.Queue()
        self.critical_messages = []
        self.browser_noise_patterns = [
            r'DevTools listening on ws://',
            r'ERROR:gpu\\command_buffer\\service\\gles2_cmd_decoder_passthrough\.cc',
            r'Automatic fallback to software WebGL has been deprecated',
            r'GroupMarkerNotSet\(crbug\.com/242999\)',
            r'\[.*\] \[.*\] \[.*\]',
            r'Created TensorFlow Lite XNNPACK delegate',
            r'Attempting to use a delegate that only supports static-sized tensors',
            r'WARNING: All log messages before absl::InitializeLog',
            r'Registering VoiceTranscriptionCapability',
            r'Registration response error message: PHONE_REGISTRATION_ERROR',
            r'google_apis\\gcm\\engine\\registration_request\.cc',
            r'DevTools listening on ws://.*',
            r'\[.*:.*:.*\] \[.*\] \[.*\]',
            r'ERROR:gpu.*',
            r'Automatic fallback to software WebGL.*',
            r'GroupMarkerNotSet.*',
            r'Created TensorFlow Lite.*',
            r'Attempting to use a delegate.*',
            r'WARNING: All log messages before.*',
            r'Registering VoiceTranscriptionCapability.*',
            r'Registration response error message.*',
            r'google_apis.*registration_request.*'
        ]
        self.debug = False
        
    def run(self, args=None):
        """Main CLI entry point."""
        # Parse command line arguments
        if args is None:
            args = sys.argv[1:]
        
        parser = argparse.ArgumentParser(
            description="FlashScore Scraper - Basketball match data extraction tool",
            prog="flashscore-scraper"
        )
        parser.add_argument("--init", nargs='*', metavar='BROWSER [VERSION]',
                          help="Initialize project (venv, install, drivers). Browser: chrome (default) or firefox. Version: major version (e.g., 138)")
        parser.add_argument("--ui", "-u", action="store_true", 
                          help="Launch GUI interface")
        parser.add_argument("--cli", "-c", action="store_true", 
                          help="Launch CLI interface")
        parser.add_argument("--install-drivers", nargs='*', metavar='BROWSER [VERSION]',
                          help="Install drivers only. Browser: chrome (default) or firefox. Version: major version (e.g., 138)")
        parser.add_argument("--list-versions", action="store_true",
                          help="List available Chrome versions")
        parser.add_argument("--version", "-v", action="version", version="1.0.0")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        
        parsed_args = parser.parse_args(args)
        self.debug = parsed_args.debug
        
        # Handle version listing
        if parsed_args.list_versions:
            self.list_available_versions()
            return
        
        # Handle driver installation
        if parsed_args.install_drivers:
            args = parsed_args.install_drivers
            browser = args[0].lower() if args else 'chrome'
            version = args[1] if len(args) > 1 else None
            self.install_drivers_automated(browser, version)
            return
        
        # Handle initialization
        if parsed_args.init is not None:
            args = parsed_args.init
            browser = args[0].lower() if args else 'chrome'
            version = args[1] if len(args) > 1 else None
            self.initialize_project(browser, version)
            return
        
        # Handle UI mode
        if parsed_args.ui:
            self.launch_ui()
            return
        
        # Handle CLI mode
        if parsed_args.cli:
            self.run_interactive_cli()
            return
        
        # Default: show help
        parser.print_help()
    
    def initialize_project(self, browser='chrome', version=None):
        """Initialize the project and install drivers."""
        print(f"🚀 Initializing FlashScore Scraper with {browser}...")
        
        # Validate browser choice
        if browser not in ['chrome', 'firefox']:
            print(f"❌ Unsupported browser: {browser}")
            print("   Supported browsers: chrome, firefox")
            return
        
        # Check if virtual environment exists
        venv_path = Path(__file__).parent.parent.parent / ".venv"
        if not venv_path.exists():
            print("📦 Creating virtual environment...")
            try:
                import subprocess
                result = subprocess.run([sys.executable, "-m", "venv", ".venv"], 
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Virtual environment created successfully!")
                    print("💡 To activate it, run:")
                    print("   • Windows: .venv\\Scripts\\activate")
                    print("   • Linux/Mac: source .venv/bin/activate")
                else:
                    print("⚠️  Virtual environment creation failed. You may need to install it manually.")
            except Exception as e:
                print(f"❌ Error creating virtual environment: {e}")
        else:
            print("✅ Virtual environment already exists!")
        
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        if not in_venv:
            print("⚠️  You're not in a virtual environment.")
            print("💡 Please activate it first:")
            print("   • Windows: .venv\\Scripts\\activate")
            print("   • Linux/Mac: source .venv/bin/activate")
            print("   Then run: pip install -e .")
            return
        
        # Install the project if not already installed
        try:
            import subprocess
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Project installed successfully!")
            else:
                print("⚠️  Project installation had issues. Try running: pip install -e .")
        except Exception as e:
            print(f"❌ Error installing project: {e}")
        
        # Install drivers using the new automated driver manager
        print(f"📥 Installing {browser} drivers...")
        try:
            if browser == 'chrome':
                from src.driver_manager import DriverInstaller
                
                driver_manager = DriverInstaller()
                if version:
                    print(f"🎯 Installing Chrome version {version}.*")
                else:
                    print("🎯 Installing latest Chrome version")
                
                results = driver_manager.install_all(version)
                
                if results['chrome'] and results['chromedriver']:
                    print("✅ Chrome drivers installed successfully!")
                    print(f"   Chrome: {results['chrome']}")
                    print(f"   ChromeDriver: {results['chromedriver']}")
                    print(f"   Version: {results['version']}")
                else:
                    print("⚠️  Some Chrome drivers failed to install.")
                    print("   You can try: fss --install-drivers chrome")
            elif browser == 'firefox':
                print("📥 Installing Firefox drivers...")
                # For Firefox, we'll use webdriver-manager or manual installation
                try:
                    from webdriver_manager.firefox import GeckoDriverManager
                    driver_path = GeckoDriverManager().install()
                    print(f"✅ Firefox driver installed at: {driver_path}")
                except Exception as e:
                    print(f"❌ Firefox driver installation failed: {e}")
                    print("   You can try: fss --install-drivers firefox")
        except ImportError as e:
            print(f"❌ Error importing driver manager: {e}")
            print("💡 Make sure all dependencies are installed.")
        except Exception as e:
            print(f"❌ Error installing drivers: {e}")
            print("💡 Check your internet connection and try again.")
        
        # Create necessary directories
        output_dirs = ["output", "output/json", "output/logs", "output/database"]
        for dir_path in output_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("✅ Project initialized successfully!")
        print(f"\n📋 Next steps:")
        print("  • Run: flashscore-scraper --ui    (for GUI)")
        print("  • Run: flashscore-scraper --cli   (for command line)")
        print("  • Run: fss -u                     (short form for GUI)")
        print("  • Run: fss -c                     (short form for CLI)")
    
    def list_available_versions(self):
        """List available Chrome versions."""
        try:
            from src.driver_manager import DriverInstaller
            driver_manager = DriverInstaller()
            driver_manager.list_available_versions()
        except Exception as e:
            print(f"❌ Error listing versions: {e}")
    
    def install_drivers_automated(self, browser='chrome', version=None):
        """Install drivers for the specified browser."""
        print(f"🚀 Installing {browser} drivers automatically...")
        
        # Validate browser choice
        if browser not in ['chrome', 'firefox']:
            print(f"❌ Unsupported browser: {browser}")
            print("   Supported browsers: chrome, firefox")
            return
        
        try:
            if browser == 'chrome':
                print("📡 Using Chrome for Testing API...")
                from src.driver_manager import DriverInstaller
                
                driver_manager = DriverInstaller()
                if version:
                    print(f"🎯 Installing Chrome version {version}.*")
                else:
                    print("🎯 Installing latest Chrome version")
                
                results = driver_manager.install_all(version)
                
                print("\n✅ Chrome driver installation completed!")
                print(f"   Chrome: {results['chrome'] or 'Not installed'}")
                print(f"   ChromeDriver: {results['chromedriver'] or 'Not installed'}")
                print(f"   Version: {results['version']}")
                print(f"   Platform: {results['platform']}")
                
                if results['chrome'] and results['chromedriver']:
                    print("\n🎉 Chrome drivers installed successfully!")
                    print("   You can now run the scraper with:")
                    print("   • fss --cli")
                    print("   • fss --ui")
                else:
                    print("\n⚠️  Some Chrome drivers failed to install.")
                    print("   You may need to install them manually or use system drivers.")
                    
            elif browser == 'firefox':
                print("📡 Using webdriver-manager for Firefox...")
                from webdriver_manager.firefox import GeckoDriverManager
                
                driver_path = GeckoDriverManager().install()
                print(f"\n✅ Firefox driver installed successfully!")
                print(f"   GeckoDriver: {driver_path}")
                print("\n🎉 Firefox driver installed successfully!")
                print("   You can now run the scraper with:")
                print("   • fss --cli")
                print("   • fss --ui")
                
        except ImportError as e:
            print(f"❌ Error importing driver manager: {e}")
            print("💡 Make sure all dependencies are installed.")
        except Exception as e:
            print(f"❌ Error installing {browser} drivers: {e}")
            print("💡 Check your internet connection and try again.")
    
    def launch_ui(self):
        """Launch the GUI interface."""
        try:
            import flet as ft
            from src.ui.main import main as ui_main
            ft.app(target=ui_main)
        except ImportError as e:
            print(f"❌ Error launching UI: {e}")
            print("💡 Make sure you're in the project directory and all dependencies are installed.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error launching UI: {e}")
            sys.exit(1)

    def run_interactive_cli(self):
        """Run the interactive CLI interface."""
        try:
            self.show_main_menu()
        except KeyboardInterrupt:
            self.display.show_interrupted()
            sys.exit(130)
        except Exception as e:
            self.display.show_error(str(e))
            sys.exit(1)

    def show_main_menu(self):
        while True:
            self._clear_and_header('main')
            action = self.prompts.ask_main_action()
            
            if action == "Start Scraping":
                self.handle_scraping_selection()
            elif action == "Configure Settings":
                self.configure_settings()
            elif action == "View Status":
                self.view_status()
            elif action == "Prediction":
                self.run_prediction_menu()
            elif action == "Exit":
                self.colored_display.show_goodbye()
                break

    def _clear_and_header(self, context):
        if self.user_settings.get('clear_terminal', True):
            self.clear_terminal()
        if context == 'main':
            self.display.show_main_menu_header()
        elif context == 'scraping':
            self.display.show_scraping_header()
        elif context == 'settings':
            self.display.show_settings_header()
        elif context == 'prediction':
            self.display.show_prediction_header()
        elif context == 'status':
            self.display.show_status_header()

    def handle_scraping_selection(self):
        self._clear_and_header('scraping')
        default_day = self.user_settings.get('default_day', 'Today')
        selected_day = self.prompts.ask_scraping_day()
        if selected_day != default_day:
            self.user_settings['default_day'] = selected_day
            self._save_user_settings(self.user_settings)
        self.start_scraping_with_day(selected_day)
        self.prompts.ask_back()
        # Do NOT clear after scraping; let user see results
        # Return to main menu on next loop

    def run_prediction_menu(self):
        while True:
            self._clear_and_header('prediction')
            range_choice = self.prompts.ask_prediction_range()
            if range_choice == "Back":
                # Return to main menu (will clear and show header in next loop)
                break
            self.handle_prediction_range(range_choice)

    def handle_prediction_range(self, range_choice):
        from datetime import datetime, timedelta
        from src.prediction import PredictionService
        from src.prediction.prediction_data_loader import load_matches

        today = datetime.now().strftime('%d.%m.%Y')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
        date_filter = None
        if range_choice == "Today":
            date_filter = today
        elif range_choice == "Yesterday":
            date_filter = yesterday
        # else: All (no filter)

        # Load all matches with debug flag
        match_models = load_matches(date_filter=date_filter, status="complete", debug=self.debug)
        if not match_models:
            self.colored_display.show_warning_message("No completed matches found for the selected range.")
            return

        # Run predictions first
        prediction_service = PredictionService()
        results = []
        match_id_map = {}
        for match in match_models:
            result = prediction_service.generate_prediction(match)
            if result.success and result.prediction:
                pred = result.prediction
                
                # Calculate AVG (average H2H total)
                h2h_totals = pred.h2h_totals
                avg_h2h = sum(h2h_totals) / len(h2h_totals) if h2h_totals else 0
                
                # Calculate RATIO (how many times went over/under)
                matches_above = pred.matches_above_line
                total_matches = pred.total_matches
                ratio = f"{matches_above}/{total_matches}"
                
                # Format date properly
                date_str = match.date if match.date else "N/A"
                time_str = match.time if match.time else ""
                date_time = f"{date_str} ({time_str})" if time_str else date_str
                
                # Format country and league
                country = match.country if match.country else "N/A"
                league = match.league if match.league else "N/A"
                
                summary = {
                    "date": date_time,
                    "country": country,
                    "league": league,
                    "home": match.home_team,
                    "away": match.away_team,
                    "line": match.odds.match_total if match.odds else 0,
                    "avg": round(avg_h2h, 1),
                    "ratio": ratio,
                    "prediction": pred.recommendation.value,
                    "winner": pred.team_winner.value,
                    "confidence": pred.confidence.value,
                    "avg_rate": f"{pred.average_rate:.2f}",
                    "match_id": match.match_id
                }
                results.append(summary)
                match_id_map[match.match_id] = (match, pred)

        # Display initial results
        if not results:
            self.colored_display.show_warning_message("No valid predictions for the selected range.")
            return
        
        # Sort results by time by default
        results = self.sort_results_by_time(results)
        
        # Separate actionable predictions (OVER/UNDER) from NO_BET predictions
        actionable_results = [r for r in results if r['prediction'] in ['OVER', 'UNDER']]
        no_bet_results = [r for r in results if r['prediction'] == 'NO_BET']
        
        # Clear console and show prediction header
        self._clear_and_header('prediction')
        
        # Display dual tables - actionable predictions first, then NO_BET predictions
        self.colored_display.show_dual_prediction_tables(actionable_results, no_bet_results)
        print()

        # Ask if user wants to filter, sort, or proceed
        filter_choice = self.prompts.ask_filter_choice()
        if filter_choice == "Back":
            # Return to prediction menu (will clear and show header in next loop)
            return
        elif filter_choice == "Filter Results":
            # Apply filters
            filtered_results = self.apply_prediction_filters(results, match_id_map)
            if filtered_results:
                # Re-separate filtered results
                filtered_actionable = [r for r in filtered_results if r['prediction'] in ['OVER', 'UNDER']]
                filtered_no_bet = [r for r in filtered_results if r['prediction'] == 'NO_BET']
                
                # Clear console and show prediction header
                self._clear_and_header('prediction')
                
                # Re-display filtered results
                self.colored_display.show_dual_prediction_tables(filtered_actionable, filtered_no_bet)
                print()
                results = filtered_results  # Update results for post-actions
        elif filter_choice == "Sort Results":
            # Sort results
            sorted_results = self.sort_prediction_results(results)
            if sorted_results:
                # Re-separate sorted results
                sorted_actionable = [r for r in sorted_results if r['prediction'] in ['OVER', 'UNDER']]
                sorted_no_bet = [r for r in sorted_results if r['prediction'] == 'NO_BET']
                
                # Clear console and show prediction header
                self._clear_and_header('prediction')
                
                # Re-display sorted results
                self.colored_display.show_dual_prediction_tables(sorted_actionable, sorted_no_bet)
                print()
                results = sorted_results  # Update results for post-actions

        # Post-summary actions
        match_choices = [f"{r['date']} | {r['home']} vs {r['away']} | {r['match_id']}" for r in results]
        while True:
            action = self.prompts.ask_post_summary_action(match_choices)
            if action == "back":
                return
            elif action == "details":
                selected = self.prompts.ask_select_match(match_choices)
                if selected == "Back":
                    continue
                # Extract match_id from choice
                match_id = selected.split("|")[-1].strip()
                match, pred = match_id_map[match_id]
                self.display_prediction_details(match, pred)
            elif action == "export":
                fmt = self.prompts.ask_export_format()
                if fmt == "Back":
                    continue
                filename = f"output/predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt.lower()}"
                try:
                    if fmt == "CSV":
                        with open(filename, "w", newline='', encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=["date", "home", "away", "line", "prediction", "confidence", "avg_rate", "match_id"])
                            writer.writeheader()
                            writer.writerows(results)
                    elif fmt == "JSON":
                        with open(filename, "w", encoding="utf-8") as f:
                            pyjson.dump(results, f, ensure_ascii=False, indent=2)
                    print(f"Exported predictions to {filename}")
                except Exception as e:
                    print(f"Error exporting predictions: {e}")

    def apply_filters(self, results, match_id_map):
        """Apply league and team filters to results."""
        # Get all unique leagues from results
        leagues = sorted(set(match_id_map[r['match_id']].league for r in results))
        
        # Prompt for league filter
        self.colored_display.show_filter_header("League")
        league_choice = self.prompts.ask_league_filter(leagues) if leagues else "All"
        if league_choice == "Back":
            return results
        if league_choice != "All":
            # Filter by league
            filtered_results = []
            for r in results:
                match = match_id_map[r['match_id']]
                if match.league == league_choice:
                    filtered_results.append(r)
            results = filtered_results
            if not results:
                self.colored_display.show_warning_message(f"No matches found for league: {league_choice}")
                return []

        # Prompt for team filter
        self.colored_display.show_filter_header("Team")
        teams = sorted(set([r['home'] for r in results] + [r['away'] for r in results]))
        team_choice = self.prompts.ask_team_filter(teams) if teams else "All"
        if team_choice == "Back":
            return results
        if team_choice != "All":
            # Filter by team
            filtered_results = []
            for r in results:
                if r['home'] == team_choice or r['away'] == team_choice:
                    filtered_results.append(r)
            results = filtered_results
            if not results:
                self.colored_display.show_warning_message(f"No matches found for team: {team_choice}")
                return []

        return results

    def apply_prediction_filters(self, results, match_id_map):
        """Apply comprehensive prediction filters."""
        filter_choice = self.prompts.ask_prediction_filter()
        
        if filter_choice == "Back":
            return results
            
        filtered_results = []
        
        for r in results:
            include = True
            
            if filter_choice == "OVER predictions only":
                include = r['prediction'] == 'OVER'
            elif filter_choice == "UNDER predictions only":
                include = r['prediction'] == 'UNDER'
            elif filter_choice == "NO_BET predictions only":
                include = r['prediction'] == 'NO_BET'
            elif filter_choice == "HIGH confidence only":
                include = r['confidence'] == 'HIGH'
            elif filter_choice == "MEDIUM confidence only":
                include = r['confidence'] == 'MEDIUM'
            elif filter_choice == "LOW confidence only":
                include = r['confidence'] == 'LOW'
            elif filter_choice == "HOME_TEAM winners only":
                include = r['winner'] == 'HOME_TEAM'
            elif filter_choice == "AWAY_TEAM winners only":
                include = r['winner'] == 'AWAY_TEAM'
            elif filter_choice == "NO_BET winners only":
                include = r['winner'] == 'NO_BET'
            elif filter_choice == "Custom filter":
                custom_filter = self.prompts.ask_custom_filter()
                include = self._apply_custom_filter(r, custom_filter, match_id_map)
            
            if include:
                filtered_results.append(r)
        
        if not filtered_results:
            self.colored_display.show_warning_message(f"No matches found for filter: {filter_choice}")
            return []
            
        return filtered_results

    def _apply_custom_filter(self, result, custom_filter, match_id_map):
        """Apply custom filter to a single result."""
        if custom_filter['type'] == 'league':
            match = match_id_map[result['match_id']]
            return custom_filter['value'].lower() in match.league.lower()
        elif custom_filter['type'] == 'team':
            return (custom_filter['value'].lower() in result['home'].lower() or 
                   custom_filter['value'].lower() in result['away'].lower())
        elif custom_filter['type'] == 'date_range':
            # Parse date from result['date'] format "12.07.2025 (12:00)"
            try:
                date_str = result['date'].split(' (')[0]  # Extract "12.07.2025"
                from datetime import datetime
                result_date = datetime.strptime(date_str, '%d.%m.%Y')
                start_date = datetime.strptime(custom_filter['start'], '%d.%m.%Y')
                end_date = datetime.strptime(custom_filter['end'], '%d.%m.%Y')
                return start_date <= result_date <= end_date
            except:
                return False
        elif custom_filter['type'] == 'rate_range':
            try:
                avg_rate = float(result['avg_rate'])
                min_rate = float(custom_filter['min'])
                max_rate = float(custom_filter['max'])
                return min_rate <= avg_rate <= max_rate
            except:
                return False
        elif custom_filter['type'] == 'line_range':
            try:
                line = float(result['line'])
                min_line = float(custom_filter['min'])
                max_line = float(custom_filter['max'])
                return min_line <= line <= max_line
            except:
                return False
        return True

    def sort_prediction_results(self, results):
        """Sort prediction results based on user choice."""
        sort_choice = self.prompts.ask_prediction_sort()
        
        if sort_choice == "No Sorting":
            return results
            
        # Create a copy to avoid modifying original
        sorted_results = results.copy()
        
        if sort_choice == "Time (Earliest First)":
            sorted_results = self.sort_results_by_time(sorted_results)
        elif sort_choice == "Time (Latest First)":
            sorted_results = self.sort_results_by_time(sorted_results)
            sorted_results.reverse()  # Reverse to get latest first
        elif sort_choice == "Date (Newest First)":
            sorted_results.sort(key=lambda x: x['date'], reverse=True)
        elif sort_choice == "Date (Oldest First)":
            sorted_results.sort(key=lambda x: x['date'])
        elif sort_choice == "Confidence (High to Low)":
            confidence_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            sorted_results.sort(key=lambda x: confidence_order.get(x['confidence'], 0), reverse=True)
        elif sort_choice == "Confidence (Low to High)":
            confidence_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            sorted_results.sort(key=lambda x: confidence_order.get(x['confidence'], 0))
        elif sort_choice == "Prediction (OVER/UNDER/NO_BET)":
            prediction_order = {'OVER': 3, 'UNDER': 2, 'NO_BET': 1}
            sorted_results.sort(key=lambda x: prediction_order.get(x['prediction'], 0), reverse=True)
        elif sort_choice == "Winner (HOME/AWAY/NO_BET)":
            winner_order = {'HOME_TEAM': 3, 'AWAY_TEAM': 2, 'NO_BET': 1}
            sorted_results.sort(key=lambda x: winner_order.get(x['winner'], 0), reverse=True)
        elif sort_choice == "Average Rate (High to Low)":
            sorted_results.sort(key=lambda x: float(x['avg_rate']), reverse=True)
        elif sort_choice == "Average Rate (Low to High)":
            sorted_results.sort(key=lambda x: float(x['avg_rate']))
        elif sort_choice == "Line (High to Low)":
            sorted_results.sort(key=lambda x: float(x['line']), reverse=True)
        elif sort_choice == "Line (Low to High)":
            sorted_results.sort(key=lambda x: float(x['line']))
            
        return sorted_results

    def sort_results_by_time(self, results):
        """Sort results by time (earliest first)."""
        def extract_time(result):
            """Extract time from date string like '12.07.2025 (12:00)'."""
            try:
                # Extract time part from "12.07.2025 (12:00)" -> "12:00"
                time_part = result['date'].split(' (')[1].rstrip(')')
                # Convert "12:00" to minutes for sorting
                hours, minutes = map(int, time_part.split(':'))
                return hours * 60 + minutes
            except (IndexError, ValueError):
                # If time parsing fails, return 0 (will sort to beginning)
                return 0
        
        # Create a copy to avoid modifying original
        sorted_results = results.copy()
        sorted_results.sort(key=extract_time)
        return sorted_results

    def display_prediction_details(self, match, pred):
        """Display detailed prediction information with colors."""
        self.colored_display.console.print(f"\n[bold {self.colored_display.colors.PRIMARY}]Prediction Details[/bold {self.colored_display.colors.PRIMARY}]")
        
        # Match info
        self.colored_display.console.print(f"[bold]Match:[/bold] {match.home_team} vs {match.away_team}")
        self.colored_display.console.print(f"[bold]Date:[/bold] {match.date}  [bold]Time:[/bold] {match.time}")
        self.colored_display.console.print(f"[bold]League:[/bold] {match.league}  [bold]Country:[/bold] {match.country}")
        self.colored_display.console.print(f"[bold]Bookmaker Line:[/bold] {match.odds.match_total}")
        
        # Prediction info with colors
        pred_color = self.colored_display.colors.PREDICTION_NO_BET
        if pred.recommendation.value == 'OVER':
            pred_color = self.colored_display.colors.PREDICTION_OVER
        elif pred.recommendation.value == 'UNDER':
            pred_color = self.colored_display.colors.PREDICTION_UNDER
            
        conf_color = self.colored_display.colors.PREDICTION_LOW_CONFIDENCE
        if pred.confidence.value == 'HIGH':
            conf_color = self.colored_display.colors.PREDICTION_HIGH_CONFIDENCE
        elif pred.confidence.value == 'MEDIUM':
            conf_color = self.colored_display.colors.PREDICTION_MEDIUM_CONFIDENCE
            
        self.colored_display.console.print(f"[bold]Prediction:[/bold] [{pred_color}]{pred.recommendation.value}[/{pred_color}]  [bold]Confidence:[/bold] [{conf_color}]{pred.confidence.value}[/{conf_color}]")
        self.colored_display.console.print(f"[bold]Average Rate:[/bold] {pred.average_rate:.2f}")
        
        # Statistics
        self.colored_display.console.print(f"[bold]Matches Above Line:[/bold] {pred.matches_above_line}")
        self.colored_display.console.print(f"[bold]Matches Below Line:[/bold] {pred.matches_below_line}")
        self.colored_display.console.print(f"[bold]Decrement Test:[/bold] {pred.decrement_test}")
        self.colored_display.console.print(f"[bold]Increment Test:[/bold] {pred.increment_test}")
        self.colored_display.console.print(f"[bold]H2H Totals:[/bold] {pred.h2h_totals}")
        self.colored_display.console.print(f"[bold]Rate Values:[/bold] {[f'{r:.2f}' for r in pred.rate_values]}")
        
        # H2H Matches
        self.colored_display.console.print(f"\n[bold {self.colored_display.colors.SECONDARY}]H2H Matches:[/bold {self.colored_display.colors.SECONDARY}]")
        for h2h in match.h2h_matches:
            self.colored_display.console.print(f"  {h2h.date}: {h2h.home_team} {h2h.home_score} - {h2h.away_score} {h2h.away_team} ({h2h.competition})")
        
        # Calculation Details
        self.colored_display.console.print(f"\n[bold {self.colored_display.colors.SECONDARY}]Calculation Details:[/bold {self.colored_display.colors.SECONDARY}]")
        for k, v in pred.calculation_details.items():
            self.colored_display.console.print(f"  [bold]{k}:[/bold] {v}")
        print()

    def start_scraping_with_day(self, day="Today"):
        """Start scraping with the specified day."""
        try:
            # Reset results
            self.scraping_results = {}
            self.critical_messages = []
            
            # Show scraping start message with day info
            self.display.show_scraping_start_with_day(day)
            
            # Setup logging with capture and noise filtering
            CONFIG.logging.log_to_console = False
            log_dir = CONFIG.logging.log_directory
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime(CONFIG.logging.log_filename_date_format)
            scraper_log_path = os.path.join(log_dir, f"scraper_{timestamp}.log")
            setup_logging(scraper_log_path)
            
            # Initialize scraper
            self.scraper = FlashscoreScraper()
            
            # Start scraping with enhanced progress tracking
            with self.progress.scraping_progress() as progress:
                task = progress.add_task("Initializing...", total=1)
                
                # Start log monitoring in background with noise filtering
                log_thread = threading.Thread(target=self._monitor_logs, daemon=True)
                log_thread.start()
                
                def progress_callback(current, total):
                    if current == 1:
                        # First call - switch from "Initializing..." to "Processing match 1 of X"
                        progress.update(task, description=f"Processing match {current} of {total}", total=total)
                    else:
                        # Update progress
                        progress.update(task, description=f"Processing match {current} of {total}", completed=current)
                
                # Run scraper and capture results with complete output suppression
                try:
                    with self._suppress_all_output():
                        self.scraper.scrape(progress_callback=progress_callback, day=day)
                    progress.update(task, description="Scraping completed!", completed=progress.tasks[0].total)
                except Exception as e:
                    progress.update(task, description="Scraping failed!", completed=progress.tasks[0].total)
                    raise e
                
                # Wait a moment for any final logs
                time.sleep(0.5)
            
            # Show detailed results
            self.display.show_scraping_results(self.scraping_results, self.critical_messages)
            
        except Exception as e:
            self.display.show_error(f"Scraping failed: {str(e)}")
            self.logger.error(f"Scraping error: {e}")

    def start_scraping_immediate(self):
        """Start scraping immediately with current settings."""
        try:
            # Reset results
            self.scraping_results = {}
            self.critical_messages = []
            
            # Use current settings (defaults or user-configured)
            self.display.show_scraping_start_immediate()
            
            # Setup logging with capture and noise filtering
            CONFIG.logging.log_to_console = False
            log_dir = CONFIG.logging.log_directory
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime(CONFIG.logging.log_filename_date_format)
            scraper_log_path = os.path.join(log_dir, f"scraper_{timestamp}.log")
            setup_logging(scraper_log_path)
            
            # Initialize scraper
            self.scraper = FlashscoreScraper()
            
            # Start scraping with enhanced progress tracking
            with self.progress.scraping_progress() as progress:
                task = progress.add_task("Initializing...", total=1)
                
                # Start log monitoring in background with noise filtering
                log_thread = threading.Thread(target=self._monitor_logs, daemon=True)
                log_thread.start()
                
                def progress_callback(current, total):
                    if current == 1:
                        # First call - switch from "Initializing..." to "Processing match 1 of X"
                        progress.update(task, description=f"Processing match {current} of {total}", total=total)
                    else:
                        # Update progress
                        progress.update(task, description=f"Processing match {current} of {total}", completed=current)
                
                # Run scraper and capture results with complete output suppression
                try:
                    with self._suppress_all_output():
                        self.scraper.scrape(progress_callback=progress_callback)
                    progress.update(task, description="Scraping completed!", completed=progress.tasks[0].total)
                except Exception as e:
                    progress.update(task, description="Scraping failed!", completed=progress.tasks[0].total)
                    raise e
                
                # Wait a moment for any final logs
                time.sleep(0.5)
            
            # Show detailed results
            self.display.show_scraping_results(self.scraping_results, self.critical_messages)
            
        except Exception as e:
            self.display.show_error(f"Scraping failed: {str(e)}")
            self.logger.error(f"Scraping error: {e}")

    def _is_browser_noise(self, message):
        """Check if a message is browser noise that should be filtered out."""
        for pattern in self.browser_noise_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _monitor_logs(self):
        """Monitor logs in background thread to capture all errors/warnings for summary display."""
        try:
            # Capture logs from the scraper
            log_capture = io.StringIO()
            log_handler = logging.StreamHandler(log_capture)
            log_handler.setLevel(logging.INFO)
            
            # Add handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)
            
            # Also capture stderr to catch browser/system messages
            original_stderr = sys.stderr
            stderr_capture = io.StringIO()
            sys.stderr = stderr_capture
            
            try:
                # Monitor for important messages
                while True:
                    time.sleep(0.1)
                    
                    # Check log content
                    log_content = log_capture.getvalue()
                    if log_content:
                        self._parse_log_content(log_content)
                        log_capture.truncate(0)
                        log_capture.seek(0)
                    
                    # Check stderr content for browser/system errors
                    stderr_content = stderr_capture.getvalue()
                    if stderr_content:
                        self._parse_log_content(stderr_content)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
            finally:
                # Restore original stderr
                sys.stderr = original_stderr
        except Exception as e:
            self.logger.error(f"Log monitoring error: {e}")

    def _parse_log_content(self, log_content):
        """Parse log content to extract important information."""
        lines = log_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Capture all errors/warnings and browser messages for summary
            if any(keyword in line.lower() for keyword in [
                'error:', 'warning:', 'devtools listening', 'gpu', 'webgl', 
                'driver', 'chrome', 'chromedriver', 'groupmarkernotset',
                'automatic fallback', 'tensorflow', 'voice', 'registration'
            ]):
                self.critical_messages.append(line)
            # Capture scraping statistics
            if 'Found' in line and 'matches' in line:
                if 'scheduled' in line:
                    self.scraping_results['scheduled_matches'] = self._extract_number(line)
                elif 'previously processed' in line:
                    self.scraping_results['processed_matches'] = self._extract_number(line)
            # Capture processing results
            if 'Processing match' in line:
                if 'Skipping already processed match' in line:
                    self.scraping_results['skipped_matches'] = self.scraping_results.get('skipped_matches', 0) + 1
                else:
                    self.scraping_results['new_matches'] = self.scraping_results.get('new_matches', 0) + 1
            # Capture final summary
            if '--- Summary:' in line:
                self.scraping_results['total_collected'] = self._extract_number(line)
            # Capture match info for detailed statistics
            if 'Match Info:' in line:
                self.scraping_results['total_matches_processed'] = self.scraping_results.get('total_matches_processed', 0) + 1
            # Capture match status for complete/incomplete breakdown
            if 'Status: complete' in line:
                self.scraping_results['complete_matches'] = self.scraping_results.get('complete_matches', 0) + 1
            elif 'Status: incomplete' in line:
                self.scraping_results['incomplete_matches'] = self.scraping_results.get('incomplete_matches', 0) + 1
            # Capture today's date for daily statistics
            if 'Created At:' in line:
                today = datetime.now().strftime('%Y-%m-%d')
                if today in line:
                    self.scraping_results['matches_collected_today'] = self.scraping_results.get('matches_collected_today', 0) + 1
            # Capture skipped match reasons for better statistics
            if 'Skipping already processed match:' in line:
                self.scraping_results['skipped_matches'] = self.scraping_results.get('skipped_matches', 0) + 1
                # Extract skip reason if available
                if '(reason:' in line:
                    reason_start = line.find('(reason:') + 8
                    reason_end = line.find(')', reason_start)
                    if reason_end > reason_start:
                        reason = line[reason_start:reason_end].strip()
                        if reason and reason != 'already processed':
                            if 'skip_reasons' not in self.scraping_results:
                                self.scraping_results['skip_reasons'] = {}
                            # Clean up the reason text
                            clean_reason = reason.strip()
                            if clean_reason:
                                self.scraping_results['skip_reasons'][clean_reason] = self.scraping_results['skip_reasons'].get(clean_reason, 0) + 1

    def _extract_number(self, text):
        """Extract number from text."""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0

    def configure_settings(self):
        self._clear_and_header('settings')
        settings = self.prompts.ask_settings()
        try:
            # Handle driver management actions
            if 'driver_action' in settings:
                driver_action = settings['driver_action']
                if driver_action == "Check Driver Status":
                    self.check_drivers("chrome")
                elif driver_action == "List Installed Drivers":
                    self.list_installed_drivers("chrome")
                elif driver_action == "Set Default Driver":
                    self.set_default_driver("chrome")
                elif driver_action == "Install New Driver":
                    version = input("Enter Chrome version to install (e.g., 138) or press Enter for latest: ").strip()
                    if version:
                        self.init_drivers("chrome", version)
                    else:
                        self.init_drivers("chrome")
                self.prompts.ask_back()
                return
            
            # Handle day selection
            if 'default_day' in settings:
                self.user_settings['default_day'] = settings['default_day']
                self._save_user_settings(self.user_settings)
                self.display.show_settings_saved()
                self.prompts.ask_back()
                return
            
            # Handle terminal clearing setting
            if 'clear_terminal' in settings:
                self.user_settings['clear_terminal'] = settings['clear_terminal']
                self._save_user_settings(self.user_settings)
                self.display.show_settings_saved()
                self.prompts.ask_back()
                return
            
            # Update configuration based on user input
            if settings.get('headless') is not None:
                CONFIG.browser.headless = settings['headless']
                
            if settings.get('output_format'):
                CONFIG.output.default_file = f"matches.{settings['output_format']}"
            
            if settings.get('log_level'):
                CONFIG.logging.log_level = settings['log_level']
            
            # Save configuration
            CONFIG.save()
            self.display.show_settings_saved()
            self.prompts.ask_back()
            
        except Exception as e:
            self.display.show_error(f"Configuration failed: {str(e)}")
            self.logger.error(f"Configuration error: {e}")
            self.prompts.ask_back()
        # Do NOT clear after settings; let user see confirmation
        # Return to main menu on next loop

    def _load_user_settings(self):
        """Load user settings from file."""
        settings_file = Path(__file__).parent / "cli_settings.json"
        if settings_file.exists():
            try:
                import json
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_user_settings(self, settings):
        """Save user settings to file."""
        try:
            import json
            settings_file = Path(__file__).parent / "cli_settings.json"
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save user settings: {e}")

    @contextlib.contextmanager
    def _suppress_logging(self):
        """Context manager to suppress logging output during interactive mode."""
        # Store original handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()
        
        # Remove console handlers to suppress output
        root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]
        
        try:
            yield
        finally:
            # Restore original handlers
            root_logger.handlers = original_handlers

    @contextlib.contextmanager
    def _suppress_all_output(self):
        """Context manager to suppress ALL output during scraping."""
        # Store original streams
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # Redirect to null
        null_fd = os.open(os.devnull, os.O_RDWR)
        null_stream = os.fdopen(null_fd, 'w')
        
        try:
            sys.stdout = null_stream
            sys.stderr = null_stream
            yield
        finally:
            # Restore original streams
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            null_stream.close()

    def view_status(self):
        self._clear_and_header('status')
        try:
            # Check output directory
            output_dir = Path(CONFIG.output.directory)
            if output_dir.exists():
                files = list(output_dir.glob("*.json"))
                self.display.show_status(len(files))
            else:
                self.display.show_status(0)
                
        except Exception as e:
            self.display.show_error(f"Failed to get status: {str(e)}")
        self.prompts.ask_back()
        # Do NOT clear after status; let user see output
        # Return to main menu on next loop

    def init_drivers(self, driver_type: str = "chrome", version: Optional[str] = None) -> bool:
        """Initialize drivers for the scraper."""
        try:
            if driver_type.lower() == "chrome":
                from ..driver_manager.driver_installer import DriverInstaller
                
                installer = DriverInstaller()
                results = installer.install_all(version=version)
                
                if results.get('chrome') and results.get('chromedriver'):
                    print(f"✅ Chrome installed: {results['chrome']}")
                    print(f"✅ ChromeDriver installed: {results['chromedriver']}")
                    print(f"✅ Version: {results['version']}")
                    print(f"✅ Platform: {results['platform']}")
                    return True
                else:
                    print("❌ Failed to install drivers")
                    return False
            else:
                print(f"❌ Unsupported driver type: {driver_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error initializing drivers: {e}")
            return False

    def list_drivers(self, driver_type: str = "chrome") -> bool:
        """List available driver versions."""
        try:
            if driver_type.lower() == "chrome":
                from ..driver_manager.driver_installer import DriverInstaller
                
                installer = DriverInstaller()
                installer.list_available_versions()
                return True
            else:
                print(f"❌ Unsupported driver type: {driver_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error listing drivers: {e}")
            return False

    def check_drivers(self, driver_type: str = "chrome") -> bool:
        """Check driver installation status."""
        try:
            if driver_type.lower() == "chrome":
                from ..driver_manager.driver_installer import DriverInstaller
                from ..config import CONFIG
                
                installer = DriverInstaller()
                status = installer.check_installation()
                
                print(f"📋 Driver Status for {status['platform']}:")
                print("-" * 50)
                
                # Show config paths if set
                if CONFIG.browser.chrome_binary_path:
                    print(f"📁 Config Chrome path: {CONFIG.browser.chrome_binary_path}")
                if CONFIG.browser.chromedriver_path:
                    print(f"📁 Config ChromeDriver path: {CONFIG.browser.chromedriver_path}")
                
                if status['chrome_installed']:
                    print(f"✅ Chrome: {status['chrome_version']} at {status['chrome_path']}")
                else:
                    print("❌ Chrome: Not installed")
                
                if status['chromedriver_installed']:
                    print(f"✅ ChromeDriver: {status['chromedriver_version']} at {status['chromedriver_path']}")
                else:
                    print("❌ ChromeDriver: Not installed")
                
                if status['all_installed']:
                    print("✅ All drivers ready for use")
                else:
                    print("⚠️ Some drivers missing - run 'fss --init chrome' to install")
                
                return status['all_installed']
            else:
                print(f"❌ Unsupported driver type: {driver_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking drivers: {e}")
            return False

    def set_default_driver(self, driver_type: str = "chrome") -> bool:
        """Set the default driver version."""
        try:
            if driver_type.lower() == "chrome":
                from ..driver_manager.driver_installer import DriverInstaller
                
                installer = DriverInstaller()
                return installer.select_default_driver()
            else:
                print(f"❌ Unsupported driver type: {driver_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting default driver: {e}")
            return False
    
    def list_installed_drivers(self, driver_type: str = "chrome") -> bool:
        """List installed driver versions."""
        try:
            if driver_type.lower() == "chrome":
                from ..driver_manager.driver_installer import DriverInstaller
                
                installer = DriverInstaller()
                installed = installer.list_installed_versions()
                
                chrome_versions = installed.get('chrome', [])
                if not chrome_versions:
                    print("❌ No Chrome versions installed")
                    return False
                
                print(f"📋 Installed Chrome versions ({len(chrome_versions)} total):")
                print("-" * 50)
                
                for i, version in enumerate(chrome_versions, 1):
                    print(f"{i:2d}. {version}")
                
                print(f"\n💡 Use: fss --set-default chrome to set default version")
                return True
            else:
                print(f"❌ Unsupported driver type: {driver_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error listing installed drivers: {e}")
            return False

    def clear_terminal(self):
        """Clear the terminal screen for a clean CLI display."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main entry point for the CLI application."""
    cli_manager = CLIManager()
    cli_manager.run()


if __name__ == "__main__":
    main() 