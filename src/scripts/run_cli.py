#!/usr/bin/env python3
"""
FlashScore Scraper CLI Entry Point
"""

import warnings
import os
import sys

# Suppress Python warnings about platform independent libraries
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.cli.cli_manager import main

if __name__ == "__main__":
    main() 