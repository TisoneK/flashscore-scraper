#!/usr/bin/env python3
"""
Flashscore Scraper - CLI Version

This script runs the scraper in command-line mode using the new CLI utility.
"""

from src.cli import CLIManager

def main():
    cli = CLIManager()
    cli.run()

if __name__ == "__main__":
    main() 