"""Utility functions for the Flashscore scraper."""
import pandas as pd
import logging
from typing import List
from pathlib import Path
from datetime import datetime
import re

from ..models import MatchModel
from ..config import CONFIG, DEFAULT_OUTPUT_FILE

logger = logging.getLogger(__name__)

def setup_logging(log_file_path: str = None) -> str:
    """Configure logging for the application. Returns the log file path used."""
    logger.debug("setup_logging() called")
    
    # Create logs directory if it doesn't exist
    log_dir = Path(CONFIG.logging.log_directory)
    logger.debug(f"Log directory: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with date
    if log_file_path is None:
        log_filename = f"scraper_{datetime.now().strftime(CONFIG.logging.log_filename_date_format)}.log"
        log_file_path = log_dir / log_filename
    else:
        log_file_path = Path(log_file_path)
    logger.debug(f"Log file path: {log_file_path}")
    logger.debug(f"Log level: {CONFIG.logging.log_level}")
    logger.debug(f"Log format: {CONFIG.logging.log_format}")
    logger.debug(f"Log date format: {CONFIG.logging.log_date_format}")
    
    # Configure logging with separate levels for console and file
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # File shows DEBUG and above
    
    console_handler = logging.StreamHandler(stream=open(1, 'w', encoding='utf-8', closefd=False))
    console_handler.setLevel(logging.INFO)  # Console shows INFO and above
    
    # Set formatter for both handlers
    formatter = logging.Formatter(CONFIG.logging.log_format, datefmt=CONFIG.logging.log_date_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root logger accepts all levels
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Debug: Check if handlers were added
    logger.debug(f"Root logger handlers: {root_logger.handlers}")
    logger.debug(f"Root logger level: {root_logger.level}")
    
    # Test logging to file
    test_logger = logging.getLogger('test_setup')
    test_logger.info("=== TEST LOG MESSAGE FROM SETUP_LOGGING ===")
    logger.debug(f"Test log message sent. Check if it appears in: {log_file_path}")
    
    # Set specific log levels for noisy modules
    for module in CONFIG.logging.quiet_modules:
        logging.getLogger(module).setLevel(logging.WARNING)
    
    logger.debug("setup_logging() completed")
    return str(log_file_path)

def save_matches_to_csv(matches: List[MatchModel], filename: str = DEFAULT_OUTPUT_FILE) -> None:
    """Save a list of matches to a CSV file.
    
    Args:
        matches: List of MatchModel objects to save
        filename: Name of the output CSV file
    """
    if not matches:
        print("No matches to save")
        return
    
    df = pd.DataFrame([match.to_dict() for match in matches])
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def format_matches_for_display(matches: List[MatchModel]) -> str:
    """Format matches for console display.
    
    Args:
        matches: List of MatchModel objects to format
    
    Returns:
        Formatted string representation of matches
    """
    if not matches:
        return "No matches found"
    
    output = []
    for match in matches:
        output.append(
            f"\n{match.league}\n"
            f"{match.home_team} vs {match.away_team}\n"
            f"Score: {match.score}\n"
            f"Status: {match.status}\n"
            f"Time: {match.time}\n"
            f"{'='*50}"
        )
    
    return "\n".join(output)

def format_date(date_str):
    """
    Converts date strings like '19.06.2025' or '18.06.25' to '19/06/2025' or '18/06/2025'.
    """
    if not date_str:
        return None
    match = re.match(r"(\d{2})\.(\d{2})\.(\d{2,4})", date_str)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{day}/{month}/{year}"
    return date_str

def split_date_time(date_time_str):
    """
    Splits a string like '19.06.2025 20:30' into ('19.06.2025', '20:30').
    """
    if not date_time_str:
        return None, None
    parts = date_time_str.strip().split()
    if len(parts) == 2:
        return parts[0], parts[1]
    return date_time_str, None 
