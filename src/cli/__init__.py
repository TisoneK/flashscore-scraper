"""
CLI module for Flashscore Scraper.

This module provides comprehensive command-line interface utilities including:
- Interactive prompts using InquirerPy
- Rich console output using Rich
- Progress bars using tqdm
- Comprehensive logging
"""

from .cli_manager import CLIManager
from .prompts import ScraperPrompts
from .display import ConsoleDisplay
from .progress import ProgressManager

__all__ = [
    'CLIManager',
    'ScraperPrompts', 
    'ConsoleDisplay',
    'ProgressManager'
] 