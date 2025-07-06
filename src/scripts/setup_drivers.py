#!/usr/bin/env python3
"""
Driver Setup Script for FlashScore Scraper

This script helps manage browser drivers for the FlashScore scraper.
It can download and set up the appropriate drivers for your operating system.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

def get_system_info():
    """Get system information for driver selection."""
    system = platform.system().lower()
    architecture = platform.machine()
    return system, architecture

def get_driver_paths():
    """Get the expected driver paths for the current system."""
    system, _ = get_system_info()
    project_root = Path(__file__).parent
    
    if system == 'windows':
        return {
            'chrome': project_root / 'drivers' / 'windows' / 'chromedriver.exe',
            'firefox': project_root / 'drivers' / 'windows' / 'geckodriver.exe'
        }
    elif system == 'linux':
        return {
            'chrome': project_root / 'drivers' / 'linux' / 'chromedriver',
            'firefox': project_root / 'drivers' / 'linux' / 'geckodriver'
        }
    elif system == 'darwin':  # macOS
        return {
            'chrome': project_root / 'drivers' / 'mac' / 'chromedriver',
            'firefox': project_root / 'drivers' / 'mac' / 'geckodriver'
        }
    else:
        raise ValueError(f"Unsupported operating system: {system}")

def check_drivers_exist():
    """Check if drivers already exist."""
    paths = get_driver_paths()
    existing = {}
    
    for browser, path in paths.items():
        existing[browser] = path.exists()
        if existing[browser]:
            print(f"✓ {browser.capitalize()} driver found: {path}")
        else:
            print(f"✗ {browser.capitalize()} driver missing: {path}")
    
    return existing

def download_drivers():
    """Download drivers using webdriver-manager."""
    print("\nDownloading drivers...")
    
    try:
        # Download ChromeDriver
        print("Downloading ChromeDriver...")
        chrome_path = ChromeDriverManager().install()
        print(f"ChromeDriver downloaded to: {chrome_path}")
        
        # Download GeckoDriver
        print("Downloading GeckoDriver...")
        firefox_path = GeckoDriverManager().install()
        print(f"GeckoDriver downloaded to: {firefox_path}")
        
        return chrome_path, firefox_path
        
    except Exception as e:
        print(f"Error downloading drivers: {e}")
        return None, None

def copy_drivers_to_project():
    """Copy downloaded drivers to the project's drivers directory."""
    system, _ = get_system_info()
    project_root = Path(__file__).parent
    
    # Create drivers directory structure
    if system == 'windows':
        drivers_dir = project_root / 'drivers' / 'windows'
    elif system == 'linux':
        drivers_dir = project_root / 'drivers' / 'linux'
    elif system == 'darwin':
        drivers_dir = project_root / 'drivers' / 'mac'
    
    drivers_dir.mkdir(parents=True, exist_ok=True)
    
    # Download drivers
    chrome_path, firefox_path = download_drivers()
    
    if chrome_path and firefox_path:
        # Copy ChromeDriver
        chrome_dest = drivers_dir / ('chromedriver.exe' if system == 'windows' else 'chromedriver')
        shutil.copy2(chrome_path, chrome_dest)
        print(f"ChromeDriver copied to: {chrome_dest}")
        
        # Copy GeckoDriver
        firefox_dest = drivers_dir / ('geckodriver.exe' if system == 'windows' else 'geckodriver')
        shutil.copy2(firefox_path, firefox_dest)
        print(f"GeckoDriver copied to: {firefox_dest}")
        
        # Make executable on Unix systems
        if system != 'windows':
            os.chmod(chrome_dest, 0o755)
            os.chmod(firefox_dest, 0o755)
            print("Made drivers executable")
        
        return True
    
    return False

def verify_drivers():
    """Verify that drivers work correctly."""
    print("\nVerifying drivers...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.firefox.service import Service as FirefoxService
        
        paths = get_driver_paths()
        
        # Test ChromeDriver
        if paths['chrome'].exists():
            try:
                service = ChromeService(executable_path=str(paths['chrome']))
                driver = webdriver.Chrome(service=service)
                driver.quit()
                print("✓ ChromeDriver verification successful")
            except Exception as e:
                print(f"✗ ChromeDriver verification failed: {e}")
        
        # Test GeckoDriver
        if paths['firefox'].exists():
            try:
                service = FirefoxService(executable_path=str(paths['firefox']))
                driver = webdriver.Firefox(service=service)
                driver.quit()
                print("✓ GeckoDriver verification successful")
            except Exception as e:
                print(f"✗ GeckoDriver verification failed: {e}")
                
    except ImportError:
        print("Selenium not installed. Install with: pip install selenium")
    except Exception as e:
        print(f"Driver verification error: {e}")

def main():
    """Main setup function."""
    print("FlashScore Scraper - Driver Setup")
    print("=" * 40)
    
    system, architecture = get_system_info()
    print(f"System: {system} ({architecture})")
    
    # Check existing drivers
    existing = check_drivers_exist()
    
    if all(existing.values()):
        print("\n✓ All drivers are already installed!")
        verify_drivers()
        return
    
    # Ask user if they want to download drivers
    print(f"\nMissing drivers detected.")
    response = input("Download and install drivers? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        if copy_drivers_to_project():
            print("\n✓ Drivers installed successfully!")
            verify_drivers()
        else:
            print("\n✗ Failed to install drivers.")
            print("You can manually download drivers from:")
            print("- ChromeDriver: https://chromedriver.chromium.org/")
            print("- GeckoDriver: https://github.com/mozilla/geckodriver/releases")
    else:
        print("\nDrivers not installed. The scraper will attempt to use system drivers.")
        print("If you encounter issues, run this script again.")

if __name__ == "__main__":
    main() 