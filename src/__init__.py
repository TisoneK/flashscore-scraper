"""Flashscore basketball scraper package."""

from .scraper import FlashscoreScraper
from .models import MatchModel
from .utils import save_matches_to_csv, format_matches_for_display

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("flashscore-scraper")
except PackageNotFoundError:
    __version__ = "1.0.0"
__all__ = [
    "FlashscoreScraper", 
    "MatchModel", 
    "save_matches_to_csv", 
    "format_matches_for_display"
]
 