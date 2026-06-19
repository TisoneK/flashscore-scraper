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
import logging
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
    logger = logging.getLogger(__name__)
    
    paths = get_driver_paths()
    existing = {}
    
    for browser, path in paths.items():
        existing[browser] = path.exists()
        if existing[browser]:
            logger.info(f"✓ {browser.capitalize()} driver found: {path}")
        else:
            logger.warning(f"✗ {browser.capitalize()} driver missing: {path}")
    
    return existing

def download_drivers():
    """Download drivers using webdriver-manager."""
    logger = logging.getLogger(__name__)
    
    logger.info("\nDownloading drivers...")
    
    try:
        # Download ChromeDriver
        logger.info("Downloading ChromeDriver...")
        chrome_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver downloaded to: {chrome_path}")
        
        # Download GeckoDriver
        logger.info("Downloading GeckoDriver...")
        firefox_path = GeckoDriverManager().install()
        logger.info(f"GeckoDriver downloaded to: {firefox_path}")
        
        return chrome_path, firefox_path
        
    except Exception as e:
        logger.error(f"Error downloading drivers: {e}")
        return None, None

def copy_drivers_to_project():
    """Copy downloaded drivers to the project's drivers directory."""
    import logging
    logger = logging.getLogger(__name__)
    
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
        logger.info(f"ChromeDriver copied to: {chrome_dest}")
        
        # Copy GeckoDriver
        firefox_dest = drivers_dir / ('geckodriver.exe' if system == 'windows' else 'geckodriver')
        shutil.copy2(firefox_path, firefox_dest)
        logger.info(f"GeckoDriver copied to: {firefox_dest}")
        
        # Make executable on Unix systems
        if system != 'windows':
            os.chmod(chrome_dest, 0o755)
            os.chmod(firefox_dest, 0o755)
            logger.info("Made drivers executable")
        
        return True
    
    return False

def verify_drivers():
    """Verify that drivers work correctly."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("\nVerifying drivers...")
    
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
                logger.info("✓ ChromeDriver verification successful")
            except Exception as e:
                logger.error(f"✗ ChromeDriver verification failed: {e}")
        
        # Test GeckoDriver
        if paths['firefox'].exists():
            try:
                service = FirefoxService(executable_path=str(paths['firefox']))
                driver = webdriver.Firefox(service=service)
                driver.quit()
                logger.info("✓ GeckoDriver verification successful")
            except Exception as e:
                logger.error(f"✗ GeckoDriver verification failed: {e}")
                
    except ImportError:
        logger.error("Selenium not installed. Install with: pip install selenium")
    except Exception as e:
        logger.error(f"Driver verification error: {e}")

def main():
    """Main setup function."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("FlashScore Scraper - Driver Setup")
    logger.info("=" * 40)
    
    system, architecture = get_system_info()
    logger.info(f"System: {system} ({architecture})")
    
    # Check existing drivers
    existing = check_drivers_exist()
    
    if all(existing.values()):
        logger.info("\n✓ All drivers are already installed!")
        verify_drivers()
        return
    
    # Ask user if they want to download drivers
    logger.info(f"\nMissing drivers detected.")
    response = input("Download and install drivers? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        if copy_drivers_to_project():
            logger.info("\n✓ Drivers installed successfully!")
            verify_drivers()
        else:
            logger.error("\n✗ Failed to install drivers.")
            logger.info("You can manually download drivers from:")
            logger.info("- ChromeDriver: https://chromedriver.chromium.org/")
            logger.info("- GeckoDriver: https://github.com/mozilla/geckodriver/releases")
    else:
        logger.info("\nDrivers not installed. The scraper will attempt to use system drivers.")
        logger.info("If you encounter issues, run this script again.")

if __name__ == "__main__":
    main() 