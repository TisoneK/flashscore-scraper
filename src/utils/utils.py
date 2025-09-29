"""Utility functions for the Flashscore scraper."""
import pandas as pd
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import re

from src.models import MatchModel
from src.utils.config_loader import CONFIG, DEFAULT_OUTPUT_FILE

logger = logging.getLogger(__name__)

def setup_logging(log_file_path: Optional[str] = None, force: bool = False) -> str:
    """Configure logging for the application. Returns the log file path used.
    
    Args:
        log_file_path: Optional path for the log file. If None, generates a timestamped filename.
        force: If True, forces reconfiguration even if logging is already set up.
    """
    logger.debug("setup_logging() called")
    
    # Get logging config with defaults
    logging_config = CONFIG.get('logging', {})
    
    # Create logs directory if it doesn't exist
    log_dir = Path(logging_config.get('log_directory', 'logs'))
    logger.debug(f"Log directory: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with date
    if log_file_path is None:
        log_filename = f"scraper_{datetime.now().strftime(logging_config.get('log_filename_date_format', '%Y%m%d'))}.log"
        final_log_path = log_dir / log_filename
    else:
        final_log_path = Path(log_file_path)
        
    logger.debug(f"Log file path: {final_log_path}")
    logger.debug(f"Log level: {logging_config.get('log_level', 'INFO')}")
    logger.debug(f"Log format: {logging_config.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')}")
    logger.debug(f"Log date format: {logging_config.get('log_date_format', '%Y-%m-%d %H:%M:%S')}")
    
    # Configure root logger
    root_logger = logging.getLogger()
    
    # Check if we already have a file handler for this log file
    existing_file_handler = None
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(final_log_path):
            existing_file_handler = handler
            break
    
    # If we already have a handler for this file and force=False, don't reconfigure
    if existing_file_handler and not force:
        logger.debug(f"Logging already configured for {final_log_path}, skipping reconfiguration")
        return str(final_log_path)
    
    # Clear existing handlers if force=True or if we don't have the right handler
    if force or not existing_file_handler:
        root_logger.handlers.clear()
        logger.debug("Cleared existing log handlers")
    
    # Set log level
    log_level = getattr(logging, logging_config.get('log_level', 'INFO').upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatters
    file_formatter = logging.Formatter(
        fmt=logging_config.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        datefmt=logging_config.get('log_date_format', '%Y-%m-%d %H:%M:%S')
    )
    
    # Create console handler with Rich formatting - only show INFO and above
    from rich.logging import RichHandler
    console = RichHandler(rich_tracebacks=True, markup=True, show_time=False, show_path=False)
    console.setFormatter(logging.Formatter(fmt='%(message)s'))
    console.setLevel(logging.INFO)  # Only show INFO and above in console
    
    # Create file handler - capture all levels including DEBUG
    file_handler = logging.FileHandler(str(final_log_path), encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
    
    # Add handlers to root logger
    root_logger.addHandler(console)
    root_logger.addHandler(file_handler)
    
    # Set root logger level to accept all messages
    root_logger.setLevel(logging.DEBUG)
    
    # Set specific log levels for noisy modules
    for module in logging_config.get('quiet_modules', []):
        logging.getLogger(module).setLevel(logging.WARNING)
    
    # Test logging (removed permanent test message)
    logger.debug(f"Logging setup completed. Log file: {final_log_path}")
    
    logger.debug("setup_logging() completed")
    return str(final_log_path)

def ensure_logging_configured(log_file_path: Optional[str] = None) -> str:
    """Ensure logging is properly configured for the application.
    
    This function checks if logging is already configured and sets it up if needed.
    It's safe to call multiple times and prevents duplicate handlers.
    
    Args:
        log_file_path: Optional path for the log file. If None, generates a timestamped filename.
    
    Returns:
        The log file path being used.
    """
    root_logger = logging.getLogger()
    
    # If we already have handlers, assume logging is configured
    if root_logger.handlers:
        # Find the file handler to get the current log path
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                return handler.baseFilename
        
        # If no file handler found, reconfigure
        return setup_logging(log_file_path, force=True)
    
    # No handlers found, configure logging
    return setup_logging(log_file_path, force=False)

def get_logging_status() -> dict:
    """Get the current logging configuration status.
    
    Returns:
        Dictionary with logging status information.
    """
    root_logger = logging.getLogger()
    
    status = {
        'configured': bool(root_logger.handlers),
        'level': root_logger.level,
        'handlers': [],
        'log_file': None
    }
    
    for handler in root_logger.handlers:
        handler_info = {
            'type': type(handler).__name__,
            'level': handler.level
        }
        
        if isinstance(handler, logging.FileHandler):
            handler_info['filename'] = handler.baseFilename
            status['log_file'] = handler.baseFilename
        
        status['handlers'].append(handler_info)
    
    return status

def save_matches_to_csv(matches: List[MatchModel], filename: str = DEFAULT_OUTPUT_FILE) -> None:
    """Save a list of matches to a CSV file.
    
    Args:
        matches: List of MatchModel objects to save
        filename: Name of the output CSV file
    """
    if not matches:
        return
    
    df = pd.DataFrame([match.to_dict() for match in matches])
    df.to_csv(filename, index=False)

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
            f"Status: {match.status}\n"
            f"Date: {match.date}\n"
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

def get_scraping_date(day: str) -> str:
    """Return date string in YYYYMMDD format for 'Today' or 'Tomorrow'."""
    if day == "Tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    else:
        return datetime.now().strftime("%Y%m%d") 
