#!/usr/bin/env python3
"""
Helper script to automatically activate virtual environment and run commands.
This script can be used to run the scraper without manually activating the venv.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def find_venv_activate():
    """Find the virtual environment activation script."""
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate.bat"
    else:
        activate_script = venv_path / "bin" / "activate"
    
    return activate_script if activate_script.exists() else None

def run_in_venv(command_args):
    """Run a command in the virtual environment."""
    logger = logging.getLogger(__name__)
    activate_script = find_venv_activate()
    
    if not activate_script:
        logger.error("❌ Virtual environment not found!")
        logger.info("💡 Please run: flashscore-scraper --init")
        return 1
    
    if sys.platform == "win32":
        # Windows: Use cmd with activation
        cmd = ["cmd", "/c", str(activate_script), "&&", "python", "-m", "flashscore_scraper"] + command_args
        result = subprocess.run(cmd, shell=True)
    else:
        # Unix: Use bash with source
        cmd = ["bash", "-c", f"source {activate_script} && python -m flashscore_scraper {' '.join(command_args)}"]
        result = subprocess.run(cmd)
    
    return result.returncode

def main():
    """Main entry point."""
    logger = logging.getLogger(__name__)
    
    if len(sys.argv) < 2:
        logger.info("Usage: python activate_and_run.py [command] [args...]")
        logger.info("Commands:")
        logger.info("  init    - Initialize project")
        logger.info("  ui      - Launch GUI")
        logger.info("  cli     - Launch CLI")
        logger.info("  help    - Show help")
        return 1
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Map commands to arguments
    command_map = {
        "init": ["--init"],
        "ui": ["--ui"],
        "cli": ["--cli"],
        "help": ["--help"]
    }
    
    if command not in command_map:
        logger.error(f"❌ Unknown command: {command}")
        logger.info("Available commands: init, ui, cli, help")
        return 1
    
    return run_in_venv(command_map[command] + args)

if __name__ == "__main__":
    sys.exit(main()) 