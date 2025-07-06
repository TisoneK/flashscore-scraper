#!/usr/bin/env python3
"""
Automated Driver Manager for FlashScore Scraper
Downloads and installs Chrome and ChromeDriver for any platform using Chrome for Testing API.
"""

import os
import sys
import platform
import urllib.request
import zipfile
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class DriverManager:
    """Manages automatic download and installation of Chrome and ChromeDriver."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.drivers_dir = self.project_root / "drivers"
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        
        # Chrome for Testing API endpoints
        self.api_base = "https://googlechromelabs.github.io/chrome-for-testing"
        self.stable_endpoint = f"{self.api_base}/known-good-versions-with-downloads.json"
        
        # Platform mapping
        self.platform_map = {
            'windows-x64': 'win64',
            'windows-x86': 'win32', 
            'linux-x64': 'linux64',
            'linux-arm64': 'linux64',  # ChromeDriver doesn't have ARM64
            'macos-x64': 'mac-x64',
            'macos-arm64': 'mac-arm64'
        }
    
    def detect_platform(self) -> str:
        """Detect the current platform and architecture."""
        if self.system == 'windows':
            if '64' in self.machine or 'x86_64' in self.machine:
                return 'windows-x64'
            else:
                return 'windows-x86'
        elif self.system == 'linux':
            if 'x86_64' in self.machine or 'amd64' in self.machine:
                return 'linux-x64'
            elif 'aarch64' in self.machine or 'arm64' in self.machine:
                return 'linux-arm64'
            else:
                return 'linux-x64'  # Default fallback
        elif self.system == 'darwin':
            if 'arm64' in self.machine or 'aarch64' in self.machine:
                return 'macos-arm64'
            else:
                return 'macos-x64'
        else:
            raise ValueError(f"Unsupported platform: {self.system}")
    
    def get_latest_chrome_version(self) -> Dict[str, Any]:
        """Get the latest Chrome for Testing version and download URLs."""
        try:
            logger.info("Fetching latest Chrome for Testing version...")
            with urllib.request.urlopen(self.stable_endpoint) as response:
                data = json.load(response)
            
            # Get the latest stable version
            versions = data.get('versions', [])
            if not versions:
                raise ValueError("No versions found in API response")
            
            latest_version = versions[0]  # First version is the latest
            version_info = {
                'version': latest_version['version'],
                'revision': latest_version['revision'],
                'downloads': latest_version.get('downloads', {})
            }
            
            logger.info(f"Latest Chrome for Testing version: {version_info['version']}")
            return version_info
            
        except Exception as e:
            logger.error(f"Failed to fetch Chrome version: {e}")
            # Fallback to a known working version
            return {
                'version': '138.0.7204.92',
                'revision': 'r1465706',
                'downloads': {}
            }
    
    def get_download_urls(self, version_info: Dict[str, Any], platform_key: str) -> Tuple[Optional[str], Optional[str]]:
        """Get download URLs for Chrome and ChromeDriver for the current platform."""
        downloads = version_info.get('downloads', {})
        driver_platform = self.platform_map.get(platform_key, 'win64')
        
        chrome_url = None
        chromedriver_url = None
        
        # Find Chrome binary URL
        chrome_downloads = downloads.get('chrome', [])
        for download in chrome_downloads:
            if download.get('platform') == driver_platform:
                chrome_url = download.get('url')
                break
        
        # Find ChromeDriver URL
        chromedriver_downloads = downloads.get('chromedriver', [])
        for download in chromedriver_downloads:
            if download.get('platform') == driver_platform:
                chromedriver_url = download.get('url')
                break
        
        return chrome_url, chromedriver_url
    
    def download_and_extract(self, url: str, target_path: Path, description: str) -> bool:
        """Download and extract a file from URL."""
        try:
            logger.info(f"Downloading {description}...")
            logger.info(f"URL: {url}")
            
            # Create target directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            temp_file = target_path.with_suffix('.zip')
            urllib.request.urlretrieve(url, temp_file)
            
            # Extract zip file
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(target_path.parent)
            
            # Make executable on Unix systems
            if self.system != 'windows':
                os.chmod(target_path, 0o755)
            
            # Clean up zip file
            temp_file.unlink()
            
            logger.info(f"✅ {description} installed successfully at: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {description}: {e}")
            return False
    
    def install_chrome(self, version_info: Dict[str, Any], platform_key: str) -> Optional[str]:
        """Install Chrome binary for the current platform."""
        chrome_url, _ = self.get_download_urls(version_info, platform_key)
        
        if not chrome_url:
            logger.warning("Chrome download URL not found, skipping Chrome installation")
            return None
        
        # Determine Chrome installation path
        if platform_key.startswith('windows'):
            chrome_dir = self.drivers_dir / "windows" / "chrome-win64"
            chrome_binary = chrome_dir / "chrome.exe"
        elif platform_key.startswith('linux'):
            chrome_dir = self.drivers_dir / "linux"
            chrome_binary = chrome_dir / "chrome"
        elif platform_key.startswith('macos'):
            chrome_dir = self.drivers_dir / "mac"
            chrome_binary = chrome_dir / "chrome"
        else:
            logger.warning(f"Unknown platform: {platform_key}")
            return None
        
        # Check if already installed
        if chrome_binary.exists():
            logger.info(f"Chrome already installed at: {chrome_binary}")
            return str(chrome_binary)
        
        # Download and install Chrome
        if self.download_and_extract(chrome_url, chrome_binary, "Chrome binary"):
            return str(chrome_binary)
        
        return None
    
    def install_chromedriver(self, version_info: Dict[str, Any], platform_key: str) -> Optional[str]:
        """Install ChromeDriver for the current platform."""
        _, chromedriver_url = self.get_download_urls(version_info, platform_key)
        
        if not chromedriver_url:
            logger.warning("ChromeDriver download URL not found, skipping ChromeDriver installation")
            return None
        
        # Determine ChromeDriver installation path
        if platform_key.startswith('windows'):
            driver_dir = self.drivers_dir / "windows"
            driver_binary = driver_dir / "chromedriver.exe"
        elif platform_key.startswith('linux'):
            driver_dir = self.drivers_dir / "linux"
            driver_binary = driver_dir / "chromedriver"
        elif platform_key.startswith('macos'):
            driver_dir = self.drivers_dir / "mac"
            driver_binary = driver_dir / "chromedriver"
        else:
            logger.warning(f"Unknown platform: {platform_key}")
            return None
        
        # Check if already installed
        if driver_binary.exists():
            logger.info(f"ChromeDriver already installed at: {driver_binary}")
            return str(driver_binary)
        
        # Download and install ChromeDriver
        if self.download_and_extract(chromedriver_url, driver_binary, "ChromeDriver"):
            return str(driver_binary)
        
        return None
    
    def install_all(self) -> Dict[str, Optional[str]]:
        """Install both Chrome and ChromeDriver for the current platform."""
        logger.info("🚀 Starting automated driver installation...")
        
        # Detect platform
        platform_key = self.detect_platform()
        logger.info(f"Detected platform: {platform_key}")
        
        # Create drivers directory
        self.drivers_dir.mkdir(exist_ok=True)
        
        # Get latest version info
        version_info = self.get_latest_chrome_version()
        
        # Install Chrome and ChromeDriver
        chrome_path = self.install_chrome(version_info, platform_key)
        chromedriver_path = self.install_chromedriver(version_info, platform_key)
        
        results = {
            'chrome_path': chrome_path,
            'chromedriver_path': chromedriver_path,
            'version': version_info['version'],
            'platform': platform_key
        }
        
        logger.info("✅ Driver installation completed!")
        logger.info(f"   Chrome: {chrome_path or 'Not installed'}")
        logger.info(f"   ChromeDriver: {chromedriver_path or 'Not installed'}")
        logger.info(f"   Version: {version_info['version']}")
        
        return results
    
    def check_installation(self) -> Dict[str, bool]:
        """Check if Chrome and ChromeDriver are properly installed."""
        platform_key = self.detect_platform()
        
        # Check Chrome
        chrome_installed = False
        if platform_key.startswith('windows'):
            chrome_path = self.drivers_dir / "windows" / "chrome-win64" / "chrome.exe"
        elif platform_key.startswith('linux'):
            chrome_path = self.drivers_dir / "linux" / "chrome"
        elif platform_key.startswith('macos'):
            chrome_path = self.drivers_dir / "mac" / "chrome"
        else:
            chrome_path = None
        
        if chrome_path and chrome_path.exists():
            chrome_installed = True
        
        # Check ChromeDriver
        chromedriver_installed = False
        if platform_key.startswith('windows'):
            driver_path = self.drivers_dir / "windows" / "chromedriver.exe"
        elif platform_key.startswith('linux'):
            driver_path = self.drivers_dir / "linux" / "chromedriver"
        elif platform_key.startswith('macos'):
            driver_path = self.drivers_dir / "mac" / "chromedriver"
        else:
            driver_path = None
        
        if driver_path and driver_path.exists():
            chromedriver_installed = True
        
        return {
            'chrome_installed': chrome_installed,
            'chromedriver_installed': chromedriver_installed,
            'platform': platform_key
        }

def main():
    """Main entry point for driver installation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlashScore Scraper Driver Manager")
    parser.add_argument("--install", action="store_true", help="Install Chrome and ChromeDriver")
    parser.add_argument("--check", action="store_true", help="Check installation status")
    parser.add_argument("--version", action="version", version="1.0.0")
    
    args = parser.parse_args()
    
    driver_manager = DriverManager()
    
    if args.install:
        driver_manager.install_all()
    elif args.check:
        status = driver_manager.check_installation()
        print(f"Platform: {status['platform']}")
        print(f"Chrome installed: {status['chrome_installed']}")
        print(f"ChromeDriver installed: {status['chromedriver_installed']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 