#!/usr/bin/env python3
"""
Launcher script for the Flashscore Scraper UI
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Launch the UI application"""
    try:
        # Import and run the UI
        from ui.main import main as ui_main
        ui_main()
    except ImportError as e:
        print(f"Error importing UI modules: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 