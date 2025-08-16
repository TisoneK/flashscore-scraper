#!/usr/bin/env python3
"""
Flashscore Scraper Cleanup Utility

This utility cleans up corrupted package installations and reinstalls the package.
Use this when the 'fss' command is not working due to corrupted installations.

Usage:
    python cleanup.py           # Clean and reinstall
    python cleanup.py --clean   # Clean only (no reinstall)
    python cleanup.py --help    # Show help
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
import glob


def find_corrupted_packages(site_packages_dir):
    """Find corrupted package directories."""
    corrupted = []
    
    # Look for directories starting with ~ (corrupted prefix)
    pattern = os.path.join(site_packages_dir, "~*flashscore*")
    corrupted.extend(glob.glob(pattern))
    
    # Look for directories with mangled names
    pattern = os.path.join(site_packages_dir, "*lashscore*")  # Missing 'f'
    corrupted.extend(glob.glob(pattern))
    
    return corrupted


def clean_corrupted_packages():
    """Clean up corrupted package installations."""
    print("🧹 Flashscore Scraper Cleanup Utility")
    print("=====================================")
    
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
    corrupted = find_corrupted_packages(site_packages)
    
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
    
    # Also try to uninstall the package properly
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
    
    if success:
        print("\n🎉 Cleanup completed successfully!")
    else:
        print("\n⚠️  Cleanup completed with some errors.")
    
    return success


def reinstall_package():
    """Reinstall the package in development mode."""
    print("\n📦 Reinstalling flashscore-scraper...")
    
    try:
        # Change to the project root directory
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Package reinstalled successfully!")
            print("\n🎯 You can now run:")
            print("   • fss --help")
            print("   • fss --cli")
            return True
        else:
            print("❌ Package reinstallation failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during reinstallation: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Flashscore Scraper Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup.py           # Clean corrupted packages and reinstall
  python cleanup.py --clean   # Clean corrupted packages only
  
This utility is useful when the 'fss' command is not working due to
corrupted package installations.
        """
    )
    
    parser.add_argument(
        '--clean', '-c',
        action='store_true',
        help='Clean corrupted packages only (do not reinstall)'
    )
    
    args = parser.parse_args()
    
    # Clean corrupted packages
    cleanup_success = clean_corrupted_packages()
    
    if not cleanup_success:
        sys.exit(1)
    
    # Reinstall if requested (default behavior)
    if not args.clean:
        reinstall_success = reinstall_package()
        if not reinstall_success:
            sys.exit(1)
    else:
        print("\n💡 To reinstall the package, run:")
        print("   pip install -e .")
    
    print("\n🎉 All done!")


if __name__ == "__main__":
    main()
