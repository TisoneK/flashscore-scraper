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
import psutil

# Suppress Python warnings about platform independent libraries
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

from src.utils.config_loader import CONFIG
from src.utils import setup_logging, ensure_logging_configured, get_logging_status, get_scraping_date
from src.scraper import FlashscoreScraper
from .prompts import ScraperPrompts
from .display import ConsoleDisplay
from .colors import ColoredDisplay
from .progress import ProgressManager
from src.prediction import PredictionService
from src.models import MatchModel, OddsModel, H2HMatchModel
from src.prediction.prediction_data_loader import load_matches
from .performance_display import PerformanceDisplay
from src.core.performance_monitor import PerformanceMonitor

class CLIManager:
    def clear_terminal(self):
        """Clear the terminal screen in a cross-platform way."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')

    def __init__(self):
        """Initialize the CLI manager."""
        self.logger = logging.getLogger(__name__)
        self.user_settings = self._load_user_settings()
        self.display = ConsoleDisplay()
        self.prompts = ScraperPrompts()
        # No toolbar: use window title for live countdown overlay
        self.colored_display = ColoredDisplay()
        self._is_running = False
        self._should_stop_scraper = False
        self._is_closing = False
        self.scraper = None
        self._scraper_thread = None
        # Initialize runtime state and performance components
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
        self.performance_display = PerformanceDisplay()
        self.performance_display.set_stop_callback(self._stop_scraper)
        self.performance_monitor = PerformanceMonitor()
        # Schedule tracking for main menu snapshot
        self._schedule_label = ""
        self._schedule_next_run = None
        # Batch UI state
        self._batch_no = None
        self._batch_start_ts = None
        # Initial status in alerts panel
        try:
            self.performance_display.show_status("Scraping not started!")
        except Exception:
            pass
        
    def __del__(self):
        """Ensure cleanup when the object is garbage collected."""
        if hasattr(self, '_is_running') and self._is_running:
            self.close()
        self.scraper: Optional[FlashscoreScraper] = None
        self._scraper_thread = None
        self._should_stop_scraper = False
        self._is_running = False
        # Avoid calling _load_user_settings() or creating new Queues during teardown
        try:
            self.user_settings = None
        except Exception:
            self.user_settings = None
        self.scraping_results = {}
        self.log_queue = None
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
        self._should_stop_scraper = False
        self._scraper_thread = None
        # Avoid creating new UI/monitor instances during object destruction; they may start threads
        try:
            if hasattr(self, 'performance_display') and self.performance_display is not None:
                try:
                    self.performance_display.set_stop_callback(self._stop_scraper)
                except Exception:
                    pass
        except Exception:
            pass
        # Do NOT instantiate PerformanceMonitor here (it may start threads during interpreter shutdown)

    def _stop_scraper(self):
        """Stop the currently running scraper. Idempotent - safe to call multiple times."""
        from urllib3.exceptions import MaxRetryError, NewConnectionError
        
        # Only proceed if we have an active scraper session
        if not (self.scraper and hasattr(self.scraper, 'has_active_driver') and self.scraper.has_active_driver()):
            if self._is_closing:
                self.logger.debug("No active scraper session to stop during shutdown")
            return
        
        self.logger.info("🛑 Stopping scraper...")
        self._should_stop_scraper = True
        
        try:
            # Stop any running performance monitoring
            if hasattr(self, 'performance_display'):
                self.performance_display.stop()
            
            # Clean up the scraper if it exists and has active driver
            if self.scraper and self.scraper.has_active_driver():
                try:
                    self.logger.debug("Closing WebDriver...")
                    # Use the scraper's close method which handles driver cleanup properly
                    self.scraper.close()
                except (MaxRetryError, NewConnectionError):
                    pass  # Expected during shutdown
                except Exception as e:
                    self.logger.debug(f"Error during scraper cleanup: {e}")
            
            # Stop the scraper thread if it's running
            if hasattr(self, '_scraper_thread') and self._scraper_thread is not None:
                if hasattr(self._scraper_thread, 'is_alive') and callable(self._scraper_thread.is_alive) and self._scraper_thread.is_alive():
                    self.logger.debug("Waiting for scraper thread to finish...")
                    self._scraper_thread.join(timeout=2)
                    if hasattr(self._scraper_thread, 'is_alive') and callable(self._scraper_thread.is_alive) and self._scraper_thread.is_alive():
                        self.logger.warning("Scraper thread did not stop gracefully")
        
        except Exception as e:
            if not self._is_closing:
                self.logger.error(f"Error during scraper stop: {e}", exc_info=True)
            else:
                self.logger.debug(f"Error during scraper stop (shutdown): {e}")
        finally:
            # Ensure thread reference is cleared
            if hasattr(self, '_scraper_thread'):
                self._scraper_thread = None
            # Reset state
            self._should_stop_scraper = False
            if not self._is_closing:
                self.logger.info("✅ Scraper stopped")

    def close(self):
        """Clean up resources and ensure clean exit."""
        import logging
        import threading
        from urllib3.exceptions import MaxRetryError, NewConnectionError
        
        self._is_running = False
        self._is_closing = True
        
        try:
            # Mark current thread as shutting down to suppress retry warnings
            threading.current_thread()._is_shutting_down = True
            
            # Stop the scraper first (idempotent)
            self._stop_scraper()
            
            # Clean up the scraper instance if it exists
            if hasattr(self, 'scraper') and self.scraper:
                try:
                    # Only close if it hasn't been closed already by _stop_scraper
                    if hasattr(self.scraper, 'has_active_driver') and self.scraper.has_active_driver():
                        self.logger.debug("Starting scraper cleanup...")
                        self.scraper.close()
                except (MaxRetryError, NewConnectionError) as e:
                    # These are expected during shutdown
                    pass
                except Exception as e:
                    # Don't log errors during shutdown
                    pass
                finally:
                    self.scraper = None
            
            # Clean up the scraper thread
            if hasattr(self, '_scraper_thread') and self._scraper_thread is not None:
                if hasattr(self._scraper_thread, 'join') and callable(self._scraper_thread.join):
                    self._scraper_thread.join(timeout=1)
                self._scraper_thread = None
                
        finally:
            # Clean up logging
            logging.shutdown()
            
            # Remove all handlers from the root logger
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                try:
                    handler.flush()
                    handler.close()
                    root_logger.removeHandler(handler)
                except Exception:
                    pass
                    
            # Clear any existing handlers
            root_logger.handlers.clear()
            
            # Disable propagation to prevent any further logging
            root_logger.propagate = False
            logging.captureWarnings(False)
        
    def run(self, args=None):
        """
        Main CLI entry point.
        
        Returns:
            int: Exit code (0 for success, non-zero for errors)
        """
        exit_code = 0
        self._is_running = True
        
        try:
            # Parse command line arguments
            if args is None:
                args = sys.argv[1:]
            
            parser = argparse.ArgumentParser(
                description="FlashScore Scraper - Basketball match data extraction tool",
                prog="flashscore-scraper"
            )
            parser.add_argument("--init", nargs='*', metavar='BROWSER [VERSION]',
                            help="Initialize project (venv, install, drivers). Browser: chrome (default) or firefox. Version: major version (e.g., 138)")
            parser.add_argument("--cli", "-c", action="store_true", 
                            help="Launch CLI interface")
            parser.add_argument("--install-drivers", nargs='*', metavar='BROWSER [VERSION]',
                            help="Install drivers only. Browser: chrome (default) or firefox. Version: major version (e.g., 138)")
            parser.add_argument("--list-versions", action="store_true",
                            help="List available Chrome versions")
            parser.add_argument("--results-update", metavar="JSON_FILE",
                            help="Update match results from JSON file")
            parser.add_argument("--output", "-o", metavar="OUTPUT_FILE",
                            help="Output file for results update")
            parser.add_argument("--version", "-v", action="version", version="1.0.0")
            parser.add_argument("--debug", action="store_true", help="Enable debug output")
            
            parsed_args = parser.parse_args(args)
            self.debug = parsed_args.debug
            
            # Handle version listing
            if parsed_args.list_versions:
                self.list_available_versions()
                return 0
            
            # Handle driver installation
            if parsed_args.install_drivers:
                args = parsed_args.install_drivers
                browser = args[0].lower() if args else 'chrome'
                version = args[1] if len(args) > 1 else None
                # Default to Chrome 138 if no version specified
                if browser == 'chrome' and version is None:
                    version = '138'
                self.install_drivers_automated(browser, version)
                return 0
            
            # Handle initialization
            if parsed_args.init is not None:
                args = parsed_args.init
                browser = args[0].lower() if args else 'chrome'
                version = args[1] if len(args) > 1 else None
                self.initialize_project(browser, version)
                return 0
            
            # Handle results update
            if parsed_args.results_update:
                self.handle_results_update(parsed_args.results_update, parsed_args.output)
                return 0
            
            # Handle CLI mode
            if parsed_args.cli:
                return self.run_interactive_cli()
            
            # Default: launch CLI (no arguments needed)
            return self.run_interactive_cli()
            
        except KeyboardInterrupt:
            print('\nOperation cancelled by user')
            return 130
            
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}", exc_info=self.debug)
            return 1
            
        finally:
            self.close()
    
    def initialize_project(self, browser='chrome', version=None):
        """Initialize the project and install drivers."""
        # Default to Chrome 138 if no version specified
        if browser == 'chrome' and version is None:
            version = '138'
        
        print(f"🚀 Initializing FlashScore Scraper with {browser} {version or 'latest'}...")
        
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
        print("  • Run: flashscore-scraper --cli   (for command line)")
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
                else:
                    print("\n⚠️  Some Chrome drivers failed to install.")
                    print("   You may need to install them manually or use system drivers.")
                    
            elif browser == 'firefox':
                print("\U0001F4E1 Using webdriver-manager for Firefox...")
                from webdriver_manager.firefox import GeckoDriverManager
                
                driver_path = GeckoDriverManager().install()
                print(f"\n✅ Firefox driver installed successfully!")
                print(f"   GeckoDriver: {driver_path}")
                print("\n🎉 Firefox driver installed successfully!")
                print("   You can now run the scraper with:")
                print("   • fss --cli")
                
        except ImportError as e:
            print(f"❌ Error importing driver manager: {e}")
            print("💡 Make sure all dependencies are installed.")
        except Exception as e:
            print(f"❌ Error installing {browser} drivers: {e}")
            print("💡 Check your internet connection and try again.")
    
    def run_interactive_cli(self):
        """Run the interactive CLI interface."""
        try:
            while self._is_running:
                try:
                    self.show_main_menu()
                except KeyboardInterrupt:
                    print('\nReturning to previous menu...')
                    # This will cause the menu to be redrawn
                    continue
        except Exception as e:
            self.display.show_error(str(e))
            return 1
        return 0

    def show_main_menu(self):
        while True:
            self._clear_and_header('main')
            # If a schedule is running, show a snapshot of countdown in the main menu
            try:
                self._print_schedule_snapshot_in_main_menu()
            except Exception:
                pass
            try:
                # Build dynamic main menu choices
                choices = []
                if hasattr(self, '_schedule_thread') and self._schedule_thread and self._schedule_thread.is_alive():
                    choices.append("Stop Running Schedule")
                choices.extend([
                    "Start Scraping",
                    "Configure Settings",
                    "View Status",
                    "Prediction",
                    "Exit"
                ])
                action = self.prompts.ask_main_action_dynamic(choices, default=choices[0])
            except RuntimeError as e:
                # Recover from PromptToolkit executor shutdown by recreating prompt loop
                try:
                    self.logger.warning(f"Prompt recovered after executor shutdown: {e}")
                except Exception:
                    pass
                continue
            
            if action == "Start Scraping":
                self.handle_scraping_selection()
            elif action == "Stop Running Schedule":
                # Gracefully stop background schedule
                self._stop_background_schedule()
                try:
                    self.performance_display.update_schedule_info("", "")
                except Exception:
                    pass
                self._schedule_label = ""
                self._schedule_next_run = None
                print("\n[Schedule] Background schedule canceled.\n")
            elif action == "Configure Settings":
                self.configure_settings()
            elif action == "View Status":
                self.view_status()
            elif action == "Prediction":
                self.run_prediction_menu()
            elif action == "Exit":
                # Stop background schedule if running and notify
                try:
                    was_running = hasattr(self, '_schedule_thread') and self._schedule_thread and self._schedule_thread.is_alive()
                except Exception:
                    was_running = False
                try:
                    self._stop_background_schedule()
                except Exception:
                    pass
                # Clear schedule info in UI and snapshot
                try:
                    self.performance_display.update_schedule_info("", "")
                except Exception:
                    pass
                self._schedule_label = ""
                self._schedule_next_run = None
                if was_running:
                    try:
                        print("\n[Schedule] Background schedule canceled.\n")
                    except Exception:
                        pass
                # Now show goodbye and proceed to shutdown
                self.colored_display.show_goodbye()
                self._is_running = False
                self._is_closing = True
                # Stop UI threads first
                if hasattr(self, 'performance_display'):
                    self.performance_display.stop()
                # Then stop scraper if active
                self._stop_scraper()
                # Finally null out scraper
                self.scraper = None
                # Exit the process explicitly to avoid lingering threads
                try:
                    import sys
                    sys.exit(0)
                except SystemExit:
                    return

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
        elif context == 'results_scraping':
            self.display.show_results_scraping_header()

    def handle_scraping_selection(self):
        self._clear_and_header('scraping')
        # New: Ask for scraping mode
        # Build dynamic scraping choices
        choices = []
        if hasattr(self, '_schedule_thread') and self._schedule_thread and self._schedule_thread.is_alive():
            # Scheduling actions first when active
            choices.append("Start on schedule")
            choices.append("Run scheduled scraper now")
        choices.extend([
            "Scheduled Matches",
            "Results",
            "Back"
        ])
        scraping_mode = self.prompts.ask_scraping_mode_dynamic(choices, default=choices[0])
        # Some test harnesses set prompts to a MagicMock which returns a non-str;
        # default to the normal interactive choice in that case so tests proceed.
        if not isinstance(scraping_mode, str):
            scraping_mode = "Scheduled Matches"
        if scraping_mode == "Back":
            return  # Go back to main menu
        if scraping_mode == "Start on schedule":
            # Do nothing; background scheduler will run at the planned time
            return
        if scraping_mode == "Run scheduled scraper now":
            # Start scraping immediately; keep the background schedule intact
            self.start_scraping_with_day(self.user_settings.get('default_day', 'Today'))
            return
        if scraping_mode == "Scheduled Matches":
            # Existing scheduled matches flow
            default_day = self.user_settings.get('default_day', 'Today')
            selected_day = self.prompts.ask_scraping_day()
            if selected_day == "Back":
                return  # Go back to main menu
            if selected_day != default_day:
                self.user_settings['default_day'] = selected_day
                self._save_user_settings(self.user_settings)
            # New: frequency and start-time flow
            freq_mode = self.prompts.ask_frequency_mode()
            # Tests may use MagicMock; default to a single-run schedule when non-string
            if not isinstance(freq_mode, str):
                freq_mode = "Once"
            if freq_mode == "Back":
                return
            if freq_mode == "Once":
                try:
                    self.performance_display.update_schedule_info("Once", "Now")
                except Exception:
                    pass
                self.start_scraping_with_day(selected_day)
            else:
                # Repetitive
                interval_choice = self.prompts.ask_repetitive_interval()
                if interval_choice == "Back":
                    return
                if interval_choice == "Set Custom Time":
                    custom_text = self.prompts.ask_custom_interval_text()
                    interval_seconds = self._parse_interval_to_seconds(custom_text)
                else:
                    interval_seconds = self._map_interval_choice(interval_choice)
                if not interval_seconds or interval_seconds <= 0:
                    self.display.show_error("Invalid interval. Please try again.")
                    return

                start_choice = self.prompts.ask_start_time()
                if start_choice == "Back":
                    return
                start_dt = self._resolve_start_time(start_choice)
                if start_dt is None:
                    custom_time = self.prompts.ask_custom_start_time()
                    start_dt = self._parse_custom_start_time(custom_time)
                    if start_dt is None:
                        self.display.show_error("Invalid start time format. Use HH:MM (24-hour).")
                        return

                # Determine frequency label once
                try:
                    label = f"Every {interval_choice.split('Every ')[1]}" if interval_choice != "Set Custom Time" else f"Every {custom_text}"
                except Exception:
                    label = "Repetitive"
                # If start time is now/past: run first cycle interactively, then background schedule
                from datetime import datetime, timedelta
                now_dt = datetime.now()
                if start_dt <= now_dt:
                    # Compute and show the true next run BEFORE starting immediate scraping
                    next_dt = now_dt + timedelta(seconds=interval_seconds)
                    try:
                        self.performance_display.update_schedule_info(label, next_dt.strftime('%Y-%m-%d %H:%M'))
                        self._schedule_label = label
                        self._schedule_next_run = next_dt
                    except Exception:
                        pass
                    self.start_scraping_with_day(selected_day)
                    self._start_background_schedule(selected_day, interval_seconds, next_dt)
                else:
                    # First run is in the future: start scheduler immediately
                    try:
                        self.performance_display.update_schedule_info(label, start_dt.strftime('%Y-%m-%d %H:%M'))
                        self._schedule_label = label
                        self._schedule_next_run = start_dt
                    except Exception:
                        pass
                    self._start_background_schedule(selected_day, interval_seconds, start_dt)

                # Prompt user what to do with schedule
                choice = self.prompts.ask_schedule_post_action()
                if choice == "Cancel schedule":
                    self._stop_background_schedule()
                    self.performance_display.update_schedule_info("", "")
                # If keep running or back, return to main menu; countdown continues
            # Do NOT clear after scraping; let user see results
            # Return to main menu on next loop
        elif scraping_mode == "Results":
            # New results scraping flow
            self._clear_and_header('results_scraping')
            while True:
                results_date_choice = self.prompts.ask_results_date()
                if results_date_choice == "Back":
                    return
                elif results_date_choice == "Yesterday":
                    from datetime import datetime, timedelta
                    results_date = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
                elif results_date_choice == "Custom Date":
                    # Prompt for custom date input
                    from InquirerPy import inquirer
                    results_date = inquirer.text(message="Enter results date (DD.MM.YYYY):").execute()
                else:
                    continue
                # Call results scraping logic (stub for now)
                self.scrape_results_for_date(results_date)
                self.prompts.ask_back()
                break

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
        from src.utils import get_scraping_date

        today = datetime.now().strftime('%d.%m.%Y')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
        date_filter = None
        if range_choice == "Today":
            date_filter = today
            day_for_file = "Today"
        elif range_choice == "Yesterday":
            date_filter = yesterday
            day_for_file = "Yesterday"
        elif range_choice == "Tomorrow":
            date_filter = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
            day_for_file = "Tomorrow"
        else:
            day_for_file = "Today"
        # else: All (no filter)

        # Load all matches with debug flag
        match_models = load_matches(date_filter=date_filter, status="complete", debug=self.debug)
        if not match_models:
            if range_choice == "Tomorrow":
                self.colored_display.show_warning_message("No completed matches found for tomorrow. Try scraping tomorrow's matches first, then run predictions.")
            elif range_choice == "Today":
                self.colored_display.show_warning_message("No completed matches found for today. Try scraping today's matches first, then run predictions.")
            elif range_choice == "Yesterday":
                self.colored_display.show_warning_message("No completed matches found for yesterday. Try scraping yesterday's matches first, then run predictions.")
            else:
                self.colored_display.show_warning_message("No completed matches found for the selected range.")
            # Wait for user to read the message
            input("\nPress Enter to continue...")
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
                matches_below = pred.matches_below_line
                total_matches = pred.total_matches
                
                # Show appropriate ratio based on prediction type
                if pred.recommendation.value == 'OVER':
                    ratio = f"{matches_above}/{total_matches}"
                elif pred.recommendation.value == 'UNDER':
                    ratio = f"{matches_below}/{total_matches}"
                else:  # NO_BET
                    ratio = f"{matches_above}/{total_matches}"  # Default to matches_above
                
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
                    "match_id": match.match_id,
                    "winning_streak_data": pred.winning_streak_data.__dict__ if hasattr(pred, 'winning_streak_data') else {},
                    "home_odds": match.odds.home_odds if match.odds and match.odds.home_odds is not None else 'N/A',
                    "away_odds": match.odds.away_odds if match.odds and match.odds.away_odds is not None else 'N/A',
                    "over_odds": match.odds.over_odds if match.odds and match.odds.over_odds is not None else 'N/A',
                    "under_odds": match.odds.under_odds if match.odds and match.odds.under_odds is not None else 'N/A',
                }
                results.append(summary)
                match_id_map[match.match_id] = (match, pred)

        # Display initial results
        if not results:
            self.colored_display.show_warning_message("No valid predictions for the selected range.")
            return
        
        # Sort results by time by default
        results = self.sort_results_by_time(results)
        
        # Strictly separate actionable tables
        actionable_over_under = []
        actionable_home_away = []
        for r in results:
            # Table 1: OVER/UNDER
            if r['prediction'] in ['OVER', 'UNDER']:
                actionable_over_under.append(r)
            # Table 2: Home/Away
            if r['prediction'] == 'NO_BET':
                actionable_home_away.append(r)
        # Only show matches that qualify for at least one table
        # Clear console and show prediction header
        self._clear_and_header('prediction')
        self.colored_display.show_dual_prediction_tables(actionable_over_under, actionable_home_away)
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
                file_date = get_scraping_date(day_for_file)
                filename = f"output/predictions_{file_date}.{fmt.lower()}"
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

    def display_show_scraping_results(self, results, critical_messages):
        """Delegate to ConsoleDisplay to show scraping results summary."""
        try:
            if hasattr(self, 'display') and hasattr(self.display, 'show_scraping_results'):
                self.display.show_scraping_results(results, critical_messages)
        except Exception as e:
            self.logger.error(f"Failed to display scraping results: {e}")

    def _show_log_file_info(self, log_path):
        """Display information about where logs are being written."""
        print(f"[blue]📝 Logs are being written to: {log_path}[/blue]")
        print(f"[blue]📊 Status updates will appear below:[/blue]")
        print("-" * 60)

    def start_scraping_with_day(self, day="Today"):
        try:
            self.scraping_results = {}
            self.critical_messages = []
            self.display.show_scraping_start_with_day(day)
            
            # Get logging config with defaults
            logging_config = CONFIG.get('logging', {})
            logging_config['log_to_console'] = False
            
            log_dir = logging_config.get('log_directory', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            file_date = get_scraping_date(day)
            scraper_log_path = os.path.join(log_dir, f"scraper_{file_date}.log")
            self.output_filename = f"matches_{file_date}.json"
            ensure_logging_configured(scraper_log_path)
            self._show_log_file_info(scraper_log_path)
            logging_status = get_logging_status()
            if logging_status['configured']:
                self.logger.info(f"✅ Logging configured: {logging_status['log_file']}")
            else:
                self.logger.warning("⚠️ Logging not properly configured")
            
            # Define progress_callback before creating scraper
            def progress_callback(current, total, task_description=None):
                try:
                    if total > 0:
                        progress_percent = (current / total) * 100
                        # Overall progress from single source of truth
                        self.performance_display.update_progress(current, total, f"Overall ({current}/{total})")
                        self._last_progress_current = current
                except Exception as e:
                    self.logger.debug(f"Progress callback error: {e}")
            
            # Provide match_finalized callback to align timing with data persistence
            def match_finalized_callback(match_id: str):
                try:
                    now_ts = time.time()
                    # If we were timing a current match, close it on finalize
                    idx = getattr(self, "_last_progress_current", 0)
                    start_ts = getattr(self, "_current_match_start_ts", None)
                    if start_ts is not None and idx > 0:
                        duration = max(0.0, now_ts - start_ts)
                        # Avoid double-counting: remove any provisional index-based record before recording by match_id
                        try:
                            if hasattr(self.performance_monitor, 'metrics') and hasattr(self.performance_monitor.metrics, 'match_processing_times'):
                                self.performance_monitor.metrics.match_processing_times.pop(f"match-{idx}", None)
                        except Exception:
                            pass
                        # Record using the actual match_id for authoritative timing
                        self.performance_monitor.record_match_time(str(match_id), duration)
                        self.performance_monitor.metrics.successful_matches = max(self.performance_monitor.metrics.successful_matches, idx)
                        self._avg_count += 1
                        self._avg_processing_time += (duration - self._avg_processing_time) / max(1, self._avg_count)
                        # Optional debug logging guarded by config
                        try:
                            if CONFIG.get('logging', {}).get('perf_debug', False):
                                self.logger.debug(f"[Perf] finalize match_id={match_id} idx={idx} duration={duration:.3f}s avg={self._avg_processing_time:.3f}s count={self._avg_count}")
                        except Exception:
                            pass
                        # Reset start marker to avoid double-closing; next boundary will re-start timing
                        self._current_match_start_ts = None
                        # Force an immediate UI update with the new average to avoid 0.00s between ticks
                        try:
                            avg_time_display = self._avg_processing_time
                            if avg_time_display > 0 and avg_time_display < 0.01:
                                avg_time_display = 0.01
                            stats = self.performance_monitor.get_stats()
                            cpu_display = stats.get('system_cpu_percent', stats.get('cpu_usage', 0))
                            mem_display = stats.get('memory_usage', 0)
                            metrics = {
                                'memory_usage': mem_display,
                                'memory_system_total_mb': stats.get('system_memory_total_mb', 0),
                                'memory_system_used_mb': stats.get('system_memory_used_mb', 0),
                                'memory_system_percent': stats.get('system_memory_percent', 0),
                                'memory_peak_mb': stats.get('peak_memory_usage', 0),
                                'cpu_usage': cpu_display,
                                'active_workers': 1,
                                'tasks_processed': stats.get('successful_matches', 0) + stats.get('failed_matches', 0),
                                'success_rate': stats.get('success_rate', 0),
                                'average_processing_time': avg_time_display,
                            }
                            self.performance_display.update_metrics(metrics)
                        except Exception:
                            pass
                except Exception:
                    pass

            from src.reporting import CallbackReporter
            self.scraper = FlashscoreScraper(
                status_callback=self._status_update,
                progress_callback=progress_callback,
                reporter=CallbackReporter(status_callback=self._status_update, progress_callback=progress_callback, match_finalized_callback=match_finalized_callback)
            )
            self._should_stop_scraper = False
            self.performance_display.set_stop_callback(self._stop_scraper)
            # Reset per-match UI trackers
            self._last_progress_current = 0
            # Ensure network monitoring is on to avoid false red indicator at startup
            try:
                from src.core.network_monitor import NetworkMonitor
                _nm_boot = NetworkMonitor()
                if not getattr(_nm_boot, 'monitoring', False):
                    _nm_boot.start_monitoring(status_callback=self._status_update)
            except Exception:
                pass

            def update_performance_metrics():
                import time as _time
                try:
                    while not self._should_stop_scraper and getattr(self.performance_display, "_is_running", False):
                        # Get latest performance metrics
                        stats = self.performance_monitor.get_stats()
                        
                        # Update the performance display (prefer system-wide metrics when available)
                        cpu_display = stats.get('system_cpu_percent', stats.get('cpu_usage', 0))
                        # Show process memory (RSS) to reflect scraper consumption
                        mem_display = stats.get('memory_usage', 0)
                        # Clamp tiny average values to ensure non-zero visibility once timings exist
                        avg_time_display = (self._avg_processing_time if getattr(self, '_avg_processing_time', 0) else stats.get('average_match_time', 0))
                        try:
                            if avg_time_display and avg_time_display > 0 and avg_time_display < 0.01:
                                avg_time_display = 0.01
                        except Exception:
                            pass

                        metrics = {
                            'memory_usage': mem_display,
                            'memory_system_total_mb': stats.get('system_memory_total_mb', 0),
                            'memory_system_used_mb': stats.get('system_memory_used_mb', 0),
                            'memory_system_percent': stats.get('system_memory_percent', 0),
                            'memory_peak_mb': stats.get('peak_memory_usage', 0),
                            'cpu_usage': cpu_display,
                            'active_workers': 1,  # Default to 1 worker for now
                            'tasks_processed': stats.get('successful_matches', 0) + stats.get('failed_matches', 0),
                            'success_rate': stats.get('success_rate', 0),
                            'average_processing_time': avg_time_display
                        }
                        self.performance_display.update_metrics(metrics)

                        # Build status indicators: Driver, Network, Scraper
                        try:
                            driver_state = "red"
                            if hasattr(self, 'scraper') and getattr(self.scraper, '_driver_manager', None):
                                dm = self.scraper._driver_manager
                                # Red (off) if closing/failed; red while not initialized
                                if getattr(dm, '_is_closing', False):
                                    driver_state = "red"
                                else:
                                    drv = getattr(dm, 'driver', None)
                                    if drv is None:
                                        driver_state = "red"  # not started/off
                                    else:
                                        # Prefer manager's validity check if available
                                        try:
                                            is_valid = False
                                            if hasattr(dm, '_is_valid_session') and callable(getattr(dm, '_is_valid_session')):
                                                is_valid = dm._is_valid_session()
                                            else:
                                                _ = drv.current_url
                                                is_valid = True
                                        except Exception:
                                            is_valid = False
                                        driver_state = "green" if is_valid else "yellow"  # yellow = down (session error)
                            # Network
                            from src.core.network_monitor import NetworkMonitor
                            nm = NetworkMonitor()
                            # Not monitoring yet → try a quick connectivity probe; show red only if unknown
                            if not getattr(nm, 'monitoring', False):
                                try:
                                    quick_ok = nm.is_connected()
                                    net_state = "green" if quick_ok else "yellow"
                                except Exception:
                                    net_state = "red"
                            else:
                                if not getattr(nm, 'connection_status', True):
                                    net_state = "yellow"  # down
                                else:
                                    try:
                                        net_state = "yellow" if nm.is_connection_degraded() else "green"
                                    except Exception:
                                        # Fallback to green if degradation check fails but connected
                                        net_state = "green"
                            # Scraper paused/stopping
                            scraper_state = "green"
                            if getattr(self, '_should_stop_scraper', False):
                                scraper_state = "red"  # off
                            elif getattr(self.performance_display, '_paused', False):
                                scraper_state = "yellow"  # down/paused

                            self.performance_display.update_status_indicators({
                                'Driver': driver_state,
                                'Network': net_state,
                                'Scraper': scraper_state,
                            })
                        except Exception:
                            pass
                        _time.sleep(1)  # Update every second
                except Exception as e:
                    self.logger.error(f"Error updating performance metrics: {e}")
                    # Surface errors to alert panel
                    try:
                        self.performance_display.show_alert(f"Performance monitor error: {e}", "error", persist=False, duration=5)
                    except Exception:
                        pass
            
            # Initialize per-match timing tracker and rolling average (in seconds)
            self._last_match_ts = None
            self._avg_processing_time = 0.0
            self._avg_count = 0

            # Update the existing progress_callback to include performance monitoring
            original_progress_callback = progress_callback
            def progress_callback(current, total, task_description=None):
                # Call the original progress callback
                original_progress_callback(current, total, task_description)
                
                # Update performance monitor counters and timings
                try:
                    pm = self.performance_monitor
                    # Set total matches if not yet set or if higher value provided
                    if not pm.metrics.total_matches or total > pm.metrics.total_matches:
                        pm.metrics.total_matches = total
                except Exception:
                    pass

                # Batch progress with actual batch size for final/incomplete batch
                batch_size = 10  # logical batch window
                import math
                total_batches = math.ceil(total / batch_size)
                batch_number = math.ceil(current / batch_size)
                # Determine actual size of the current batch
                if batch_number < total_batches:
                    batch_total = batch_size
                else:
                    batch_total = total - batch_size * (total_batches - 1)
                    if batch_total <= 0:
                        batch_total = batch_size
                # Processed within this batch
                processed_in_batch = current - batch_size * (batch_number - 1)
                if processed_in_batch < 0:
                    processed_in_batch = 0
                if processed_in_batch > batch_total:
                    processed_in_batch = batch_total

                # If new batch started, reset batch timer and counters
                if batch_number != getattr(self, "_last_batch_number", None):
                    self.performance_display.reset_batch_progress(batch_total, f"Batch {batch_number}   (0/{batch_total})")
                    self._last_batch_number = batch_number
                # Update within-batch progress
                batch_desc = f"Batch {batch_number}   ({processed_in_batch}/{batch_total})"
                self.performance_display.update_batch_progress(processed_in_batch, batch_total, batch_desc)
                
                # Match boundary: only when index increases
                if current != getattr(self, "_last_progress_current", 0):
                    try:
                        pm = self.performance_monitor
                        now_ts = time.time()
                        # Finalize previous match timing if any
                        if getattr(self, "_current_match_start_ts", None) is not None and getattr(self, "_last_progress_current", 0) > 0:
                            prev_idx = getattr(self, "_last_progress_current", 0)
                            duration = max(0.0, now_ts - self._current_match_start_ts)
                            pm.record_match_time(f"match-{prev_idx}", duration)
                            # Count processed matches accurately by index
                            pm.metrics.successful_matches = max(pm.metrics.successful_matches, prev_idx)
                            # Update rolling average immediately after first duration recorded
                            self._avg_count += 1
                            self._avg_processing_time += (duration - self._avg_processing_time) / max(1, self._avg_count)
                        # Start timer for the new match index
                        self._current_match_start_ts = now_ts
                    except Exception:
                        pass
                    self.performance_display.clear_subtasks()
                    self.performance_display.update_current_match(f"Processing match {current}/{total}")
                    self._last_progress_current = current

                # Enhanced task display and subtasks
                if task_description:
                    desc = f"{task_description}"
                    self.performance_display.update_current_task(f"{desc} ({current}/{total})")
                    # Also record as a subtask step
                    self.performance_display.add_subtask(desc + "...")
                else:
                    self.performance_display.update_current_task(f"Processing match {current} of {total}")
                
                # Log progress periodically
                if current % 5 == 0 or current == total:
                    progress_percent = (current / total) * 100 if total > 0 else 0
                    self.logger.info(f"Progress: {current}/{total} ({progress_percent:.1f}%)")

                # If we are at the final match, record its duration as well
                try:
                    if total > 0 and current == total and hasattr(self, "_current_match_start_ts") and self._current_match_start_ts is not None:
                        end_ts = time.time()
                        duration = max(0.0, end_ts - self._current_match_start_ts)
                        self.performance_monitor.record_match_time(f"match-{current}", duration)
                        # Ensure counts reflect completion
                        try:
                            pm = self.performance_monitor
                            pm.metrics.successful_matches = max(pm.metrics.successful_matches, total)
                            # Update rolling average fallback too
                            self._avg_count += 1
                            self._avg_processing_time += (duration - self._avg_processing_time) / max(1, self._avg_count)
                        except Exception:
                            pass
                except Exception:
                    pass
                

            # Start the performance metrics update thread
            metrics_thread = threading.Thread(target=update_performance_metrics, daemon=True)
            metrics_thread.start()

            log_thread = threading.Thread(target=self._monitor_logs, daemon=True)
            log_thread.start()

            scraping_result = []
            scraping_exception = []
            def run_scraper():
                try:
                    with self._allow_status_messages():
                        # Pass both progress_callback and status_callback to the scraper
                        results = self.scraper.scrape(progress_callback=progress_callback, day=day, status_callback=self._status_update, stop_callback=lambda: self._should_stop_scraper)
                        
                        # Store the results
                        if results:
                            self.scraping_results = results
                        
                        # If we get here, scraping completed successfully
                        scraping_result.append(True)
                except Exception as e:
                    self.logger.error(f"Error in scraper thread: {str(e)}")
                    if self._status_update:
                        self._status_update(f"Error: {str(e)}", level="error")
                    scraping_exception.append(e)
            self._scraper_thread = threading.Thread(target=run_scraper)
            self._scraper_thread.daemon = True
            self._scraper_thread.start()
            # Give the scraper thread a short moment to start and invoke scrape
            try:
                if hasattr(self, '_scraper_thread') and self._scraper_thread is not None and hasattr(self._scraper_thread, 'join'):
                    self._scraper_thread.join(timeout=0.1)
            except Exception:
                pass

            try:
                # Update status and start live display
                # Startup phase messaging
                self.performance_display.update_current_task("Initializing...")
                self.performance_display.clear_subtasks()
                self.performance_display.add_subtask("Initializing driver...")
                self.performance_display.add_subtask("Checking network...")
                self.performance_display.show_status("Scraping in progress...")
                # Auto-stop the display when the scraper thread finishes
                def _auto_stop_display():
                    try:
                        import time as _t
                        while True:
                            if (hasattr(self, '_scraper_thread') and self._scraper_thread is not None and
                                hasattr(self._scraper_thread, 'is_alive') and callable(self._scraper_thread.is_alive)):
                                if not self._scraper_thread.is_alive():
                                    try:
                                        # Mark display to stop; alert will be updated in main flow
                                        self.performance_display.stop()
                                    except Exception:
                                        pass
                                    break
                            else:
                                break
                            _t.sleep(0.2)
                    except Exception:
                        pass
                threading.Thread(target=_auto_stop_display, daemon=True).start()
                self.performance_display.start()  # This now runs in the main thread and handles controls
            except KeyboardInterrupt:
                print("\nExiting on Ctrl+C")
                self._should_stop_scraper = True
                if hasattr(self, '_scraper_thread') and self._scraper_thread is not None and self._scraper_thread.is_alive():
                    self._scraper_thread.join(timeout=2)
                sys.exit(0)
            # After performance_display exits, join scraper thread if still running
            if hasattr(self, '_scraper_thread') and self._scraper_thread is not None and self._scraper_thread.is_alive():
                self._should_stop_scraper = True
                self._scraper_thread.join(timeout=2)
            if scraping_exception:
                self.performance_display.show_alert("Scraping failed!", alert_type="error", persist=True)
                raise scraping_exception[0]
            elif scraping_result:
                # Show summary completion with elapsed time if available
                try:
                    total_time = self.performance_monitor.get_stats().get('total_time', 0.0)
                except Exception:
                    total_time = 0.0
                def _fmt_secs(s):
                    s = int(s)
                    h = s // 3600
                    m = (s % 3600) // 60
                    s = s % 60
                    return f"{h}h {m}m {s}s"
                self.performance_display.show_alert(f"Scraping completed in {_fmt_secs(total_time)}", alert_type="success", persist=True)
                # Automatically stop the display after completion
                self.performance_display.stop()
            
            # Show summary and stay on results until user chooses to go back
            import time
            time.sleep(3)
            self.clear_terminal()

            total_matches = self.scraping_results.get('total_collected', 0)
            new_matches = self.scraping_results.get('new_matches', 0)
            skipped_matches = self.scraping_results.get('skipped_matches', 0)
            # Build specific reasons if nothing was processed
            reasons = []
            try:
                from .prompts import ScraperPrompts
            except Exception:
                pass
            try:
                # If there were scheduled but all were already processed
                scheduled = self.scraping_results.get('scheduled_matches')
                processed_prev = self.scraping_results.get('processed_matches')
                if scheduled is not None and processed_prev is not None and scheduled > 0 and new_matches == 0:
                    reasons.append("All matches were already processed for the selected day.")
                # If scheduling found zero
                if scheduled == 0:
                    reasons.append("No matches are scheduled for the selected day.")
            except Exception:
                pass

            if total_matches > 0:
                try:
                    stats = self.performance_monitor.get_stats()
                    success = int(stats.get('successful_matches', 0) or 0)
                    failed = int(stats.get('failed_matches', 0) or 0)
                    total_pf = success + failed
                    if total_pf > 0:
                        self.scraping_results['complete_matches'] = success
                        self.scraping_results['incomplete_matches'] = failed
                        self.scraping_results['success_rate'] = float(stats.get('success_rate', 0.0) or 0.0)
                except Exception:
                    pass
                self.display_show_scraping_results(self.scraping_results, self.critical_messages)
                self.prompts.ask_back()
            elif new_matches == 0 and skipped_matches == 0:
                self.display.show_no_matches_found(reasons if reasons else None)
                self.prompts.ask_back()
            else:
                try:
                    stats = self.performance_monitor.get_stats()
                    success = int(stats.get('successful_matches', 0) or 0)
                    failed = int(stats.get('failed_matches', 0) or 0)
                    total_pf = success + failed
                    if total_pf > 0:
                        self.scraping_results['complete_matches'] = success
                        self.scraping_results['incomplete_matches'] = failed
                        self.scraping_results['success_rate'] = float(stats.get('success_rate', 0.0) or 0.0)
                except Exception:
                    pass
                self.display_show_scraping_results(self.scraping_results, self.critical_messages)
                self.prompts.ask_back()
        except Exception as e:
            self.display.show_error(f"Scraping failed: {str(e)}")
            self.logger.error(f"Scraping error: {e}")

    def start_scraping_immediate(self):
        try:
            self.scraping_results = {}
            self.critical_messages = []
            self.display.show_scraping_start_immediate()
            
            # Get logging config with defaults
            logging_config = CONFIG.get('logging', {})
            logging_config['log_to_console'] = False
            
            log_dir = logging_config.get('log_directory', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Get log filename date format with fallback
            log_date_format = logging_config.get('log_filename_date_format', '%Y%m%d_%H%M%S')
            timestamp = datetime.now().strftime(log_date_format)
            scraper_log_path = os.path.join(log_dir, f"scraper_{timestamp}.log")
            ensure_logging_configured(scraper_log_path)
            self._show_log_file_info(scraper_log_path)
            logging_status = get_logging_status()
            if logging_status['configured']:
                self.logger.info(f"✅ Logging configured: {logging_status['log_file']}")
            else:
                self.logger.warning("⚠️ Logging not properly configured")
            
            # Define progress_callback for results scraping
            def progress_callback(current, total, task_description=None):
                try:
                    if total > 0:
                        progress_percent = (current / total) * 100
                        self.performance_display.update_progress(current, total, "Results")
                except Exception as e:
                    self.logger.debug(f"Progress callback error: {e}")
            
            from src.reporting import CallbackReporter
            self.scraper = FlashscoreScraper(
                status_callback=self._status_update,
                progress_callback=progress_callback,
                reporter=CallbackReporter(status_callback=self._status_update, progress_callback=progress_callback, match_finalized_callback=None)
            )
            self._should_stop_scraper = False
            self.performance_display.set_stop_callback(self._stop_scraper)
            
            def update_performance_metrics():
                try:
                    while not self._should_stop_scraper:
                        # Get latest performance metrics
                        stats = self.performance_monitor.get_stats()
                        
                        # Update the performance display (prefer system-wide metrics when available)
                        cpu_display = stats.get('system_cpu_percent', stats.get('cpu_usage', 0))
                        # Show process memory (RSS) to reflect scraper consumption
                        mem_display = stats.get('memory_usage', 0)
                        metrics = {
                            'memory_usage': mem_display,
                            'memory_system_total_mb': stats.get('system_memory_total_mb', 0),
                            'memory_system_used_mb': stats.get('system_memory_used_mb', 0),
                            'memory_system_percent': stats.get('system_memory_percent', 0),
                            'memory_peak_mb': stats.get('peak_memory_usage', 0),
                            'cpu_usage': cpu_display,
                            'active_workers': 1,  # Default to 1 worker for now
                            'tasks_processed': stats.get('successful_matches', 0) + stats.get('failed_matches', 0),
                            'success_rate': stats.get('success_rate', 0),
                            'average_processing_time': self._avg_processing_time or stats.get('average_match_time', 0)
                        }
                        self.performance_display.update_metrics(metrics)
                        time.sleep(1)  # Update every second
                except Exception as e:
                    self.logger.error(f"Error updating performance metrics: {e}")
            
            # Start the performance metrics update thread
            metrics_thread = threading.Thread(target=update_performance_metrics, daemon=True)
            metrics_thread.start()

            log_thread = threading.Thread(target=self._monitor_logs, daemon=True)
            log_thread.start()

            scraping_result = []
            scraping_exception = []
            
            def run_scraper():
                try:
                    with self._allow_status_messages():
                        # Pass both progress_callback and status_callback to the scraper
                        self.scraper.scrape(
                            progress_callback=progress_callback,
                            day=day,
                            status_callback=self._status_update,
                            stop_callback=lambda: self._should_stop_scraper
                        )
                        scraping_result.append(True)
                except Exception as e:
                    self.logger.error(f"Error in scraper thread: {e}")
                    scraping_exception.append(e)
            
            # Start the scraper in a separate thread
            self._scraper_thread = threading.Thread(target=run_scraper, daemon=True)
            self._scraper_thread.start()
            
            try:
                # Start the performance display in the main thread
                self.performance_display.start()
                
                # Wait for the scraper to finish, but allow keyboard interrupt
                while (hasattr(self, '_scraper_thread') and 
                       self._scraper_thread is not None and 
                       hasattr(self._scraper_thread, 'is_alive') and 
                       callable(self._scraper_thread.is_alive) and 
                       self._scraper_thread.is_alive()):
                    if hasattr(self._scraper_thread, 'join') and callable(self._scraper_thread.join):
                        self._scraper_thread.join(timeout=0.5)
                
                # Check scraping results after completion
                if scraping_exception:
                    self.performance_display.show_alert("Scraping failed!", alert_type="error")
                    raise scraping_exception[0]
                elif scraping_result:
                    self.performance_display.show_alert("Scraping completed!", alert_type="success")
                    
                return scraping_result, scraping_exception
                    
            except KeyboardInterrupt:
                self.logger.info("\nReceived keyboard interrupt, stopping scraper...")
                self._should_stop_scraper = True
                
                # Wait for the scraper thread to finish
                if (hasattr(self, '_scraper_thread') and 
                    self._scraper_thread is not None and 
                    hasattr(self._scraper_thread, 'is_alive') and 
                    callable(self._scraper_thread.is_alive) and 
                    self._scraper_thread.is_alive()):
                    if hasattr(self._scraper_thread, 'join') and callable(self._scraper_thread.join):
                        self._scraper_thread.join(timeout=5)
                
                # Re-raise the KeyboardInterrupt to allow proper cleanup
                raise
                
            finally:
                try:
                    # Clean up resources
                    self._should_stop_scraper = True
                    
                    # Stop and clean up threads
                    if (hasattr(metrics_thread, 'is_alive') and 
                        callable(metrics_thread.is_alive) and 
                        metrics_thread.is_alive() and 
                        hasattr(metrics_thread, 'join') and 
                        callable(metrics_thread.join)):
                        metrics_thread.join(timeout=1)
                    
                    if (hasattr(log_thread, 'is_alive') and 
                        callable(log_thread.is_alive) and 
                        log_thread.is_alive() and 
                        hasattr(log_thread, 'join') and 
                        callable(log_thread.join)):
                        log_thread.join(timeout=1)
                    
                    # Ensure performance display is properly closed
                    self.performance_display.stop()
                    
                    # Wait 5 seconds, then clear screen and show summary
                    import time
                    time.sleep(5)
                    self.clear_terminal()
                    
                    # Check if any matches were found and processed
                    total_matches = self.scraping_results.get('total_collected', 0)
                    new_matches = self.scraping_results.get('new_matches', 0)
                    skipped_matches = self.scraping_results.get('skipped_matches', 0)
                    
                    if total_matches > 0:
                        self.display_show_scraping_results(self.scraping_results, self.critical_messages)
                    elif new_matches == 0 and skipped_matches == 0:
                        # No matches found to process
                        self.display.show_no_matches_found()
                    else:
                        # Show summary even if no new matches but some were skipped
                        self.display_show_scraping_results(self.scraping_results, self.critical_messages)
                except Exception as e:
                    self.logger.error(f"Error during cleanup: {e}")
                    raise
            
            self.logger.info("Returning to main menu...")
            time.sleep(1.2)
        except Exception as e:
            self.display.show_error(f"Scraping failed: {str(e)}")
            self.logger.error(f"Scraping error: {e}")

    def _status_update(self, message, level="info"):
        """Handle status updates during scraping.
        
        Args:
            message (str): The status message to display (can include Rich markup)
                          Messages starting with [STATUS] are considered progress updates
            level (str): Log level ('info', 'warning', 'error')
        """
        is_status_message = message.startswith('[STATUS]')
        
        # For file logging: strip Rich markup and [STATUS] prefix
        clean_message = message.replace('[', '').replace(']', '')
        if is_status_message:
            clean_message = clean_message.replace('STATUS', '').strip()
        
        # Log to file with standard logging (all messages)
        if level == "info":
            self.logger.info(clean_message)
        elif level == "warning":
            self.logger.warning(clean_message)
        elif level == "error":
            self.logger.error(clean_message)
            self.critical_messages.append(clean_message)
        
        # For console: only show status and error messages
        if hasattr(self, 'display') and hasattr(self.display, 'console'):
            if is_status_message or level in ("error", "warning"):
                # Remove [STATUS] prefix for display
                display_message = message.replace('[STATUS]', '').strip()
                if level == "error":
                    self.display.console.print(f"[red]❌ {display_message}[/red]")
                elif level == "warning":
                    self.display.console.print(f"[yellow]⚠️  {display_message}[/yellow]")
                else:
                    self.display.console.print(display_message)
                # Also reflect latest status as current task in the performance display
                try:
                    self.performance_display.update_current_task(display_message)
                except Exception:
                    pass

        # Heuristic: treat certain info lines as subtasks for the current match (but do not store messages)
        try:
            display_msg = message.replace('[STATUS]', '').strip()
            lower = display_msg.lower()
            if any(v in lower for v in ["loading", "extracting", "verifying", "saving", "parsing", "retrying"]):
                short = display_msg if len(display_msg) <= 100 else (display_msg[:97] + "...")
                self.performance_display.add_subtask(short)
                # Also promote a concise version to the main Current Task header
                try:
                    concise = display_msg
                    # Trim URLs to avoid clutter in header
                    if "http" in concise:
                        concise = concise.split("http")[0].strip()
                    # Remove trailing punctuation/ellipsis
                    concise = concise.rstrip('.').rstrip('…').rstrip(':').strip()
                    if concise:
                        self.performance_display.update_current_task(concise)
                except Exception:
                    pass
        except Exception:
            pass

        # Surface warnings/errors to the Alerts panel
        try:
            if level == "error":
                self.performance_display.show_alert(clean_message, alert_type="error", persist=False, duration=6)
            elif level == "warning":
                self.performance_display.show_alert(clean_message, alert_type="warning", persist=False, duration=5)
        except Exception:
            pass

    def _is_browser_noise(self, message):
        """Check if a message is browser noise that should be filtered out."""
        for pattern in self.browser_noise_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _display_log_update(self, message):
        """Display log updates in the UI."""
        # Filter out browser noise
        if any(re.search(pattern, message, re.IGNORECASE) for pattern in self.browser_noise_patterns):
            return
            
        # Display the message in the UI
        self.logger.info(message)
        
        # Check for critical messages
        if any(keyword in message.lower() for keyword in [
            'error', 'warning', 'exception', 'failed', 'critical',
            'timeout', 'not found', 'missing', 'invalid'
        ]):
            self.critical_messages.append(message)

            # Heuristics: update performance monitor on failure lines for real-time stats
            try:
                pm = self.performance_monitor
                msg = message.lower()
                if 'failed to process match' in msg or 'worker timeout processing match' in msg or 'error processing match' in msg:
                    pm.metrics.failed_matches += 1
                # Keep total as sum of success + failed when non-zero
                total_calc = pm.metrics.successful_matches + pm.metrics.failed_matches
                if total_calc > 0 and total_calc >= pm.metrics.total_matches:
                    pm.metrics.total_matches = total_calc
            except Exception:
                pass

    def _monitor_logs(self):
        """Monitor logs in background thread to capture all errors/warnings for summary display."""
        try:
            # Create a custom log handler that captures to memory without console output
            log_capture = io.StringIO()
            
            class CaptureHandler(logging.Handler):
                def __init__(self, capture_stream, display_callback=None):
                    super().__init__()
                    self.capture_stream = capture_stream
                    self.display_callback = display_callback
                
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        self.capture_stream.write(msg + '\n')
                        # Display important messages in real-time
                        if self.display_callback:
                            self.display_callback(msg)
                    except Exception:
                        pass
            
            log_handler = CaptureHandler(log_capture, self._display_log_update)
            log_handler.setLevel(logging.INFO)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            
            # Add handler to root logger (don't clear existing handlers)
            root_logger = logging.getLogger()
            # Only add if we don't already have this type of handler
            existing_capture_handlers = [h for h in root_logger.handlers if isinstance(h, CaptureHandler)]
            if not existing_capture_handlers:
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
                # Remove our custom handler
                root_logger.removeHandler(log_handler)
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

    # =====================
    # Scheduling utilities
    # =====================
    def _map_interval_choice(self, choice: str) -> int:
        """Map predefined interval choice to seconds."""
        mapping = {
            "Every 30 minutes": 30 * 60,
            "Every 1 hour": 60 * 60,
            "Every 2 hours": 2 * 60 * 60,
            "Every 6 hours": 6 * 60 * 60,
            "Every 12 hours": 12 * 60 * 60,
            "Every 24 hours": 24 * 60 * 60,
        }
        return mapping.get(choice, 0)

    def _parse_interval_to_seconds(self, text: str) -> int:
        """Parse flexible interval strings into seconds.
        Accepts: 'Every 45 minutes', '45 minutes', '45 mins', '45 min', '45 m', '45m', '2h', '2 hours'.
        """
        try:
            if not text:
                return 0
            s = text.strip().lower()
            if s.startswith("every "):
                s = s[6:].strip()
            import re as _re
            m = _re.match(r"^(\d+)\s*([a-z]+)?$", s) or _re.match(r"^(\d+)([a-z]+)$", s)
            if not m:
                return 0
            value = int(m.group(1))
            unit = (m.group(2) or "m").lower()
            if unit in ("m", "min", "mins", "minute", "minutes"):
                return value * 60
            if unit in ("h", "hr", "hrs", "hour", "hours"):
                return value * 60 * 60
            return 0
        except Exception:
            return 0

    def _resolve_start_time(self, start_choice):
        """Return datetime for Now/Midday/Midnight; None for custom."""
        from datetime import datetime, timedelta
        now = datetime.now()
        if start_choice == "Now":
            return now
        if start_choice == "Midday":
            dt = now.replace(hour=12, minute=0, second=0, microsecond=0)
            return dt if dt > now else dt + timedelta(days=1)
        if start_choice == "Midnight":
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return dt if dt > now else dt + timedelta(days=1)
        if start_choice == "Set Custom":
            return None
        return now

    def _parse_custom_start_time(self, time_text: str):
        """Parse HH:MM 24-hour to next occurrence datetime."""
        from datetime import datetime, timedelta
        try:
            if not time_text:
                return None
            t = time_text.strip()
            hh, mm = t.split(":")
            hh = int(hh)
            mm = int(mm)
            now = datetime.now()
            dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if dt <= now:
                dt = dt + timedelta(days=1)
            return dt
        except Exception:
            return None

    def _run_repetitive_schedule(self, day: str, interval_seconds: int, start_dt):
        """Run scraping on a repetitive schedule until user stops (blocking)."""
        import time as _time
        from datetime import datetime, timedelta
        next_run = start_dt if start_dt else datetime.now()
        self._clear_and_header('scraping')
        # Simple banner
        freq_label = f"{interval_seconds//60} min" if interval_seconds < 3600 else f"{interval_seconds//3600} hr"
        print(f"Scheduling: every {freq_label} starting at {next_run.strftime('%Y-%m-%d %H:%M')}")
        try:
            while True:
                now = datetime.now()
                if now < next_run:
                    remaining = int((next_run - now).total_seconds())
                    mins, secs = divmod(remaining, 60)
                    print(f"Next run in {mins:02d}:{secs:02d} (at {next_run.strftime('%H:%M')})\r", end="")
                    # Keep schedule info fresh in UI
                    try:
                        freq_label = f"{interval_seconds//60} min" if interval_seconds < 3600 else f"{interval_seconds//3600} hr"
                        # Feed absolute time for precise countdown in Schedule panel
                        next_text = next_run.strftime('%Y-%m-%d %H:%M')
                        self.performance_display.update_schedule_info(f"Every {freq_label}", next_text)
                        # Keep snapshot state for main menu
                        self._schedule_label = f"Every {freq_label}"
                        self._schedule_next_run = next_run
                    except Exception:
                        pass
                    _time.sleep(1)
                    if getattr(self, '_is_closing', False):
                        break
                    continue
                print("\nStarting scheduled scraping...")
                self.start_scraping_with_day(day)
                next_run = next_run + timedelta(seconds=interval_seconds)
                while next_run <= datetime.now():
                    next_run = next_run + timedelta(seconds=interval_seconds)
                # Update next run in UI after completion
                try:
                    freq_label = f"{interval_seconds//60} min" if interval_seconds < 3600 else f"{interval_seconds//3600} hr"
                    next_text = next_run.strftime('%Y-%m-%d %H:%M')
                    self.performance_display.update_schedule_info(f"Every {freq_label}", next_text)
                    self._schedule_label = f"Every {freq_label}"
                    self._schedule_next_run = next_run
                except Exception:
                    pass
                if getattr(self, '_is_closing', False):
                    break
        except KeyboardInterrupt:
            print("\nSchedule stopped by user.")

    def _start_background_schedule(self, day: str, interval_seconds: int, start_dt):
        """Start the scheduler in a background thread and keep countdown visible in UI."""
        import threading
        self._schedule_stop_flag = False
        # Start or refresh a window-title countdown updater
        try:
            self._start_window_title_countdown()
        except Exception:
            pass

        def _runner():
            import time as _time
            from datetime import datetime, timedelta
            next_run = start_dt if start_dt else datetime.now()
            try:
                while not getattr(self, '_schedule_stop_flag', False):
                    now = datetime.now()
                    if now < next_run:
                        # Update schedule info frequently
                        try:
                            freq_label = f"{interval_seconds//60} min" if interval_seconds < 3600 else f"{interval_seconds//3600} hr"
                            next_text = next_run.strftime('%Y-%m-%d %H:%M')
                            self.performance_display.update_schedule_info(f"Every {freq_label}", next_text)
                            self._schedule_label = f"Every {freq_label}"
                            self._schedule_next_run = next_run
                        except Exception:
                            pass
                        _time.sleep(1)
                        continue
                    # Run scraping once (silent, no prompts/UI)
                    try:
                        self._run_scrape_silent(day)
                    except Exception:
                        pass
                    # Compute next
                    next_run = next_run + timedelta(seconds=interval_seconds)
                    while next_run <= datetime.now():
                        next_run = next_run + timedelta(seconds=interval_seconds)
                    # Reflect new next_run in snapshot right away
                    try:
                        freq_label = f"{interval_seconds//60} min" if interval_seconds < 3600 else f"{interval_seconds//3600} hr"
                        self.performance_display.update_schedule_info(f"Every {freq_label}", next_run.strftime('%Y-%m-%d %H:%M'))
                        self._schedule_label = f"Every {freq_label}"
                        self._schedule_next_run = next_run
                    except Exception:
                        pass
            except Exception:
                pass

        self._schedule_thread = threading.Thread(target=_runner, daemon=True)
        self._schedule_thread.start()

    def _print_schedule_snapshot_in_main_menu(self):
        """Render a single-line countdown snapshot in the main menu if a schedule exists."""
        try:
            label = self._schedule_label or getattr(self.performance_display, 'schedule_label', '')
            next_dt = self._schedule_next_run
            # Best-effort parse from display if local state missing
            if next_dt is None:
                next_text = getattr(self.performance_display, 'schedule_next_text', '')
                try:
                    if next_text and next_text.lower() != 'now':
                        next_dt = datetime.strptime(next_text, '%Y-%m-%d %H:%M')
                    else:
                        next_dt = datetime.now()
                except Exception:
                    next_dt = None
            if label and next_dt:
                remaining = int((next_dt - datetime.now()).total_seconds())
                if remaining < 0:
                    remaining = 0
                mins, secs = divmod(remaining, 60)
                hours, mins = divmod(mins, 60)
                countdown = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
                print(f"[Schedule] {label}  |  Next run in {countdown} (at {next_dt.strftime('%H:%M')})\n")
        except Exception:
            pass

    # Removed intrusive menu countdown updater; now using Inquirer bottom_toolbar.

    def _stop_background_schedule(self):
        """Signal the background scheduler to stop and join thread."""
        try:
            self._schedule_stop_flag = True
            if hasattr(self, '_schedule_thread') and self._schedule_thread and self._schedule_thread.is_alive():
                self._schedule_thread.join(timeout=2)
            # Stop window title updater
            self._stop_window_title_countdown()
        except Exception:
            pass

    def _start_window_title_countdown(self):
        """Update the terminal window title with countdown every second (non-intrusive)."""
        try:
            if getattr(self, '_title_updater_thread', None) and self._title_updater_thread.is_alive():
                return
            self._title_updater_stop = False
            import threading
            def _tick():
                import time as _t
                while not getattr(self, '_title_updater_stop', False):
                    try:
                        label = self._schedule_label or getattr(self.performance_display, 'schedule_label', '')
                        next_dt = self._schedule_next_run
                        if next_dt is None:
                            next_text = getattr(self.performance_display, 'schedule_next_text', '')
                            if next_text and next_text.lower() != 'now':
                                next_dt = datetime.strptime(next_text, '%Y-%m-%d %H:%M')
                        if label and next_dt:
                            remaining = int((next_dt - datetime.now()).total_seconds())
                            if remaining < 0:
                                remaining = 0
                            mins, secs = divmod(remaining, 60)
                            hours, mins = divmod(mins, 60)
                            countdown = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
                            title = f"Flashscore Scraper - Next in {countdown} (at {next_dt.strftime('%H:%M')})"
                            # Windows Powershell compatible title set
                            sys.stdout.write(f"\33]0;{title}\7")
                            try:
                                sys.stdout.flush()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    _t.sleep(1)
            self._title_updater_thread = threading.Thread(target=_tick, daemon=True)
            self._title_updater_thread.start()
        except Exception:
            pass

    def _stop_window_title_countdown(self):
        try:
            self._title_updater_stop = True
            t = getattr(self, '_title_updater_thread', None)
            if t and t.is_alive():
                t.join(timeout=0.5)
            # Clear title suffix
            try:
                sys.stdout.write("\33]0;Flashscore Scraper\7")
                sys.stdout.flush()
            except Exception:
                pass
        except Exception:
            pass

    def _run_scrape_silent(self, day: str):
        """Run a single scrape cycle without interactive UI or prompts (for background scheduling)."""
        try:
            # Minimal logging setup
            logging_config = CONFIG.get('logging', {})
            logging_config['log_to_console'] = False
            log_dir = logging_config.get('log_directory', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            file_date = get_scraping_date(day)
            scraper_log_path = os.path.join(log_dir, f"scraper_{file_date}.log")
            ensure_logging_configured(scraper_log_path)

            # Create scraper and run
            def progress_callback(current, total, task_description=None):
                # Simple progress callback for background scraping
                pass
            
            from src.reporting import CallbackReporter
            scraper = FlashscoreScraper(status_callback=self._status_update, progress_callback=progress_callback, reporter=CallbackReporter(status_callback=self._status_update, progress_callback=progress_callback, match_finalized_callback=None))
            scraper.scrape(progress_callback=None, day=day, status_callback=self._status_update, stop_callback=lambda: getattr(self, '_schedule_stop_flag', False))
        except Exception as e:
            try:
                self.logger.error(f"Background schedule scrape error: {e}")
            except Exception:
                pass

    def configure_settings(self):
        self._clear_and_header('settings')
        settings = self.prompts.ask_settings()
        try:
            # If user chose Back, just return
            if isinstance(settings, dict) and settings.get('__back'):
                return
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
            if 'browser' in settings:
                if 'headless' in settings['browser']:
                    CONFIG.setdefault('browser', {})['headless'] = settings['browser']['headless']
                
            if settings.get('output_format'):
                CONFIG.setdefault('output', {})['default_file'] = f"matches.{settings['output_format']}"
            
            if settings.get('log_level'):
                CONFIG.setdefault('logging', {})['log_level'] = settings['log_level']
            if 'log_match_details' in settings:
                CONFIG.setdefault('logging', {})['log_match_details'] = settings['log_match_details']
            
            # Save configuration
            from src.utils.config_loader import save_config
            save_config(CONFIG)
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
        """Context manager to suppress logging output during scraping."""
        # Store original handlers and level
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()
        original_level = root_logger.level
        
        # Remove console handlers to suppress output
        root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]
        
        # Create a null handler to prevent "No handlers could be found" warnings
        null_handler = logging.NullHandler()
        root_logger.addHandler(null_handler)
        
        try:
            yield
        finally:
            # Remove our null handler
            root_logger.removeHandler(null_handler)
            
            # Restore original handlers and level
            root_logger.handlers = original_handlers
            root_logger.setLevel(original_level)
            
            # Force flush any remaining log messages
            for handler in root_logger.handlers:
                handler.flush()

    @contextlib.contextmanager
    def _allow_status_messages(self):
        """Context manager that allows status messages while suppressing verbose logging."""
        # Store original handlers and level
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()
        original_level = root_logger.level
        
        # Remove console handlers to suppress verbose logging
        root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, logging.StreamHandler)]
        
        # Create a null handler to prevent "No handlers could be found" warnings
        null_handler = logging.NullHandler()
        root_logger.addHandler(null_handler)
        
        # Store original stdout to restore later
        original_stdout = sys.stdout
        
        try:
            # Allow status messages to go through
            yield
        finally:
            # Remove our null handler
            root_logger.removeHandler(null_handler)
            
            # Restore original handlers and level
            root_logger.handlers = original_handlers
            root_logger.setLevel(original_level)
            sys.stdout = original_stdout
            
            # Force flush any remaining log messages
            for handler in root_logger.handlers:
                handler.flush()

    def view_status(self):
        self._clear_and_header('status')
        try:
            # Check output directory
            output_dir = Path(CONFIG.get('output', {}).get('directory', 'output'))
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
                from ..utils.config_loader import CONFIG
                
                installer = DriverInstaller()
                status = installer.check_installation()
                
                print(f"📋 Driver Status for {status['platform']}:")
                print("-" * 50)
                
                # Show config paths if set
                browser_config = CONFIG.get('browser', {})
                if browser_config.get('chrome_binary_path'):
                    print(f"📁 Config Chrome path: {browser_config['chrome_binary_path']}")
                if browser_config.get('chromedriver_path'):
                    print(f"📁 Config ChromeDriver path: {browser_config['chromedriver_path']}")
                
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

def main():
    """Main entry point for the CLI application."""
    cli_manager = CLIManager()
    cli_manager.run()


if __name__ == "__main__":
    main() 