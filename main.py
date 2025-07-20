#!/usr/bin/env python3
"""
Flashscore Scraper - Main Entry Point

This script launches the CLI scraper.
"""

import warnings
import sys
import argparse
from pathlib import Path

# Suppress Python warnings about platform independent libraries
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

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

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Flashscore Basketball Scraper (CLI Only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py          # Run CLI scraper (default)
  python main.py --cli    # Run CLI scraper (explicit)
  python main.py -c       # Run CLI scraper (short form)
        """
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run CLI scraper'
    )
    
    args = parser.parse_args()
    
    # Always run CLI scraper
    run_cli_scraper()

if __name__ == "__main__":
    main()
