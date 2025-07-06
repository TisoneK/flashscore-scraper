#!/usr/bin/env python3
"""
Flashscore Scraper - Main Entry Point

This script launches the UI by default, but can also run the CLI scraper.
"""

import sys
import argparse
from pathlib import Path

def run_cli_scraper():
    """Run the CLI version of the scraper using the new CLI manager."""
    from src.cli import CLIManager
    
    try:
        cli = CLIManager()
        cli.run()
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

def run_ui():
    """Run the UI version of the scraper."""
    try:
        import flet as ft
        from ui.main import main as ui_main
        ft.app(target=ui_main)
    except ImportError as e:
        print(f"Error importing UI modules: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching UI: {e}")
        sys.exit(1)

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Flashscore Basketball Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py          # Launch UI (default)
  python main.py --ui     # Launch UI explicitly
  python main.py --cli    # Run CLI scraper
  python main.py -c       # Run CLI scraper (short form)
        """
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run CLI scraper instead of UI'
    )
    
    parser.add_argument(
        '--ui', '-u',
        action='store_true',
        help='Launch UI (default behavior)'
    )
    
    args = parser.parse_args()
    
    # Determine which mode to run
    if args.cli:
        run_cli_scraper()
    else:
        print("Starting Flashscore Scraper UI...")
        run_ui()

if __name__ == "__main__":
    main()
