#!/usr/bin/env python3
"""
Flashscore Scraper - Main Entry Point

This script launches the CLI scraper and provides cleanup functionality.
"""

import warnings
import sys
import signal
import os
import shutil
import subprocess
import glob
import atexit
import argparse
from pathlib import Path

# Suppress Python warnings about platform independent libraries
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

# Global variable to hold reference to the scraper for cleanup
_scraper_instance = None

def cleanup():
    """Cleanup function to be called on exit."""
    global _scraper_instance
    if _scraper_instance is not None:
        try:
            _scraper_instance.close()
        except Exception as e:
            print(f"Error during cleanup: {e}", file=sys.stderr)
    # Ensure we flush all output
    sys.stdout.flush()
    sys.stderr.flush()

def signal_handler(sig, frame):
    """Handle termination signals."""
    print('\nExiting gracefully...')
    cleanup()
    # Exit with status code 130 (128 + SIGINT)
    sys.exit(130)

# Register the cleanup function to run on normal program termination
atexit.register(cleanup)

# Set up signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

def run_cleanup():
    """Run cleanup utility for corrupted installations."""
    print("🧹 Flashscore Scraper Emergency Cleanup")
    print("======================================")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        print("⚠️  Warning: You're not in a virtual environment!")
        print("💡 It's recommended to activate your .venv first:")
        print("   • Windows: .venv\\Scripts\\activate")
        print("   • Linux/Mac: source .venv/bin/activate")
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Cleanup cancelled.")
            return False
    
    # Find site-packages directory
    site_packages = None
    for path in sys.path:
        if 'site-packages' in path:
            site_packages = path
            break
    
    if not site_packages or not os.path.exists(site_packages):
        print("❌ Could not find site-packages directory!")
        return False
    
    print(f"📂 Checking site-packages: {site_packages}")
    
    # Find corrupted packages
    corrupted = []
    pattern = os.path.join(site_packages, "~*flashscore*")
    corrupted.extend(glob.glob(pattern))
    pattern = os.path.join(site_packages, "*lashscore*")  # Missing 'f'
    corrupted.extend(glob.glob(pattern))
    
    if not corrupted:
        print("✅ No corrupted packages found!")
        return True
    
    print(f"🔍 Found {len(corrupted)} corrupted package(s):")
    for pkg in corrupted:
        print(f"   • {os.path.basename(pkg)}")
    
    # Confirm cleanup
    response = input("\n🗑️  Remove these corrupted packages? (Y/n): ").strip().lower()
    if response == 'n':
        print("❌ Cleanup cancelled.")
        return False
    
    # Remove corrupted packages
    success = True
    for pkg in corrupted:
        try:
            if os.path.isdir(pkg):
                print(f"🗑️  Removing directory: {os.path.basename(pkg)}")
                shutil.rmtree(pkg)
            elif os.path.isfile(pkg):
                print(f"🗑️  Removing file: {os.path.basename(pkg)}")
                os.remove(pkg)
            print(f"   ✅ Removed successfully")
        except Exception as e:
            print(f"   ❌ Failed to remove: {e}")
            success = False
    
    # Try to uninstall the package properly
    print("\n📦 Attempting to uninstall flashscore-scraper...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "uninstall", "flashscore-scraper", "-y"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Package uninstalled successfully")
        else:
            print("⚠️  Package uninstall had issues (this is often normal)")
    except Exception as e:
        print(f"⚠️  Error during uninstall: {e}")
    
    # Reinstall the package
    print("\n📦 Reinstalling flashscore-scraper...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Package reinstalled successfully!")
            print("\n🎯 You can now run:")
            print("   • fss --help")
            print("   • fss --cli")
        else:
            print("❌ Package reinstallation failed!")
            print(f"Error: {result.stderr}")
            success = False
    except Exception as e:
        print(f"❌ Error during reinstallation: {e}")
        success = False
    
    if success:
        print("\n🎉 Emergency cleanup completed successfully!")
    else:
        print("\n⚠️  Emergency cleanup completed with some errors.")
    
    return success

def run_cli_scraper():
    """Run the CLI version of the scraper using the new CLI manager."""
    global _scraper_instance
    from src.cli import CLIManager
    
    try:
        cli = CLIManager()
        _scraper_instance = cli  # Store reference for cleanup
        cli.run()
    except KeyboardInterrupt:
        # Signal handler will take care of this
        pass
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        _scraper_instance = None

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
  python main.py --cleanup # Emergency cleanup for corrupted installations
        """
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run CLI scraper'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Emergency cleanup for corrupted package installations'
    )
    
    args = parser.parse_args()
    
    # Handle cleanup mode
    if args.cleanup:
        success = run_cleanup()
        sys.exit(0 if success else 1)
    
    # Always run CLI scraper (default)
    run_cli_scraper()

if __name__ == "__main__":
    main()
