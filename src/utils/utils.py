"""Utility functions for the Flashscore scraper."""
import pandas as pd
import logging
from typing import List
from pathlib import Path
from datetime import datetime
import re

from ..models import MatchModel
from ..config import CONFIG, DEFAULT_OUTPUT_FILE

def setup_logging() -> None:
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path(CONFIG.logging.log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with date
    log_filename = f"scraper_{datetime.now().strftime(CONFIG.logging.log_filename_date_format)}.log"
    log_file_path = log_dir / log_filename
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, CONFIG.logging.log_level),
        format=CONFIG.logging.log_format,
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler(stream=open(1, 'w', encoding='utf-8', closefd=False))  # Use UTF-8 for console
        ]
    )
    
    # Set specific log levels for noisy modules
    for module in CONFIG.logging.quiet_modules:
        logging.getLogger(module).setLevel(logging.WARNING)

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
