#!/usr/bin/env python3
"""
Automated Driver Installer for FlashScore Scraper
Downloads and installs Chrome and ChromeDriver for any platform using Chrome for Testing API.
Supports both latest version and specific version installation.
"""

import os
import sys
import platform
import urllib.request
import zipfile
import json
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import logging

from .downloader import DriverDownloader
from .exceptions import DownloadError, NetworkError, HTTPError, TimeoutError, FileSystemError

logger = logging.getLogger(__name__)

class DriverInstaller:
    """Manages automatic download and installation of Chrome and ChromeDriver."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.drivers_dir = self.project_root / "drivers"
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.downloader = DriverDownloader()
        
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
    
    def get_available_versions(self) -> list:
        """Get all available Chrome for Testing versions."""
        try:
            logger.info("[STATUS] Fetching available Chrome for Testing versions...")
            with urllib.request.urlopen(self.stable_endpoint) as response:
                data = json.load(response)
            
            return data.get('versions', [])
            
        except Exception as e:
            logger.error("[STATUS] Failed to fetch Chrome versions: %s", e)
            return []
    
    def find_version_by_major(self, major_version: str) -> Optional[Dict[str, Any]]:
        """Find a specific Chrome version by major version number (e.g., '138')."""
        versions = self.get_available_versions()
        
        # Look for exact major version match
        for version_info in versions:
            version = version_info['version']
            if version.startswith(f"{major_version}."):
                logger.info("[STATUS] Found Chrome version %s for major version %s", version, major_version)
                return version_info
        
        # If not found, return the latest version
        logger.warning("[STATUS] No Chrome version found for major version %s, using latest", major_version)
        return versions[0] if versions else None
    
    def get_latest_chrome_version(self) -> Dict[str, Any]:
        """Get the latest Chrome for Testing version and download URLs."""
        try:
            logger.info("[STATUS] Fetching latest Chrome for Testing version...")
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
            
            logger.info("[STATUS] Latest Chrome for Testing version: %s", version_info['version'])
            return version_info
            
        except Exception as e:
            logger.error("[STATUS] Failed to fetch Chrome version: %s", e)
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
        """
        Download and extract a file from URL using the new downloader with progress tracking.
        
        Args:
            url: The URL to download from
            target_path: The target path to save the downloaded file
            description: Description of the file being downloaded
            
        Returns:
            bool: True if download and extraction was successful, False otherwise
            
        Raises:
            DownloadError: If there's an error during download
            FileSystemError: If there's an error during file operations
        """
        try:
            version_dir = target_path.parent  # The version directory
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file using the new downloader
            temp_file = version_dir / (description.lower().replace(' ', '_') + '.zip')
            logger.info("[STATUS] Starting download of %s...", description)
            
            try:
                self.downloader.download(url, temp_file)
            except Exception as e:
                logger.error("[STATUS] ❌ Download failed: %s", e)
                if temp_file.exists():
                    temp_file.unlink()
                return False
            
            # Extract zip file
            logger.info("[STATUS] Extracting %s...", description)
            try:
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(version_dir)
                
                # Clean up zip file
                temp_file.unlink()
                
                # Handle platform-specific directory structures
                self._cleanup_extracted_files(version_dir, description)
                
                logger.info("[STATUS] ✅ %s installed successfully at: %s", description, version_dir)
                return True
                
            except zipfile.BadZipFile as e:
                logger.error("[STATUS] ❌ Invalid zip file: %s", e)
                return False
            except Exception as e:
                logger.error("[STATUS] ❌ Failed to extract %s: %s", description, e)
                return False
                
        except Exception as e:
            logger.error("[STATUS] ❌ Unexpected error during %s installation: %s", description, e)
            if 'temp_file' in locals() and temp_file.exists():
                temp_file.unlink()
            return False
    
    def _cleanup_extracted_files(self, version_dir: Path, description: str) -> None:
        """Clean up and organize extracted files."""
        # Handle Chrome browser files
        chrome_win64_dir = version_dir / "chrome-win64"
        if chrome_win64_dir.exists():
            logger.info("[STATUS] Organizing Chrome files in %s", version_dir)
            for item in chrome_win64_dir.iterdir():
                target = version_dir / item.name
                if target.exists():
                    if target.is_file():
                        target.unlink()
                    elif target.is_dir():
                        shutil.rmtree(target)
                shutil.move(str(item), str(version_dir))
            chrome_win64_dir.rmdir()
        
        # Handle ChromeDriver files
        chromedriver_dir = version_dir / "chromedriver-win64"
        if chromedriver_dir.exists():
            logger.info("[STATUS] Organizing ChromeDriver files in %s", version_dir)
            for item in chromedriver_dir.iterdir():
                target = version_dir / item.name
                if target.exists():
                    if target.is_file():
                        target.unlink()
                    elif target.is_dir():
                        shutil.rmtree(target)
                shutil.move(str(item), str(version_dir))
            chromedriver_dir.rmdir()
    
    def _get_clean_installation_paths(self, platform_key: str, version: str) -> Path:
        """Get clean installation path for the version directory."""
        if platform_key.startswith('windows'):
            base_dir = self.drivers_dir / "windows" / "chrome"
        elif platform_key.startswith('linux'):
            base_dir = self.drivers_dir / "linux" / "chrome"
        elif platform_key.startswith('macos'):
            base_dir = self.drivers_dir / "mac" / "chrome"
        else:
            raise ValueError(f"Unknown platform: {platform_key}")
        
        # Single version directory containing both Chrome and ChromeDriver
        version_dir = base_dir / version
        
        return version_dir
    
    def _cleanup_old_versions(self, platform_key: str, keep_versions: int = 2):
        """Clean up old driver versions, keeping only the specified number."""
        if platform_key.startswith('windows'):
            base_dir = self.drivers_dir / "windows"
        elif platform_key.startswith('linux'):
            base_dir = self.drivers_dir / "linux"
        elif platform_key.startswith('macos'):
            base_dir = self.drivers_dir / "mac"
        else:
            return
        
        # Clean up old Chrome versions (now contains both Chrome and ChromeDriver)
        chrome_base = base_dir / "chrome"
        if chrome_base.exists():
            versions = sorted([d for d in chrome_base.iterdir() if d.is_dir()], 
                           key=lambda x: x.name, reverse=True)
            for old_version in versions[keep_versions:]:
                logger.info("[STATUS] Removing old Chrome version: %s", old_version.name)
                shutil.rmtree(old_version, ignore_errors=True)
    
    def install_chrome(self, version_info: Dict[str, Any], platform_key: str) -> Optional[str]:
        """Install Chrome binary for the current platform."""
        chrome_url, _ = self.get_download_urls(version_info, platform_key)
        
        if not chrome_url:
            logger.warning("[STATUS] Chrome download URL not found, skipping Chrome installation")
            return None
        
        version = version_info['version']
        version_dir = self._get_clean_installation_paths(platform_key, version)
        
        # Install Chrome directory
        if self.download_and_extract(chrome_url, version_dir / "chrome.exe", "Chrome"):
            return str(version_dir)
        return None
    
    def install_chromedriver(self, version_info: Dict[str, Any], platform_key: str) -> Optional[str]:
        """Install ChromeDriver for the current platform."""
        _, chromedriver_url = self.get_download_urls(version_info, platform_key)
        
        if not chromedriver_url:
            logger.warning("[STATUS] ChromeDriver download URL not found, skipping ChromeDriver installation")
            return None
        
        version = version_info['version']
        version_dir = self._get_clean_installation_paths(platform_key, version)
        
        # Install ChromeDriver directory
        if self.download_and_extract(chromedriver_url, version_dir / "chromedriver.exe", "ChromeDriver"):
            return str(version_dir)
        return None
    
    def list_installed_versions(self) -> Dict[str, List[str]]:
        """List all installed driver versions."""
        platform_key = self.detect_platform()
        
        if platform_key.startswith('windows'):
            base_dir = self.drivers_dir / "windows"
        elif platform_key.startswith('linux'):
            base_dir = self.drivers_dir / "linux"
        elif platform_key.startswith('macos'):
            base_dir = self.drivers_dir / "mac"
        else:
            return {}
        
        installed = {'chrome': [], 'chromedriver': []}
        
        # Check Chrome versions (now contains both Chrome and ChromeDriver)
        chrome_base = base_dir / "chrome"
        if chrome_base.exists():
            versions = [d.name for d in chrome_base.iterdir() if d.is_dir()]
            installed['chrome'] = versions
            installed['chromedriver'] = versions  # Same versions for both
        
        return installed
    
    def update_config_with_paths(self, chrome_path: Optional[str], chromedriver_path: Optional[str], version: str) -> None:
        """Update config file with installed driver paths."""
        try:
            from src.utils.config_loader import CONFIG, save_config
            
            # Get the actual binary paths from the version directory
            platform_key = self.detect_platform()
            version_dir = self._get_clean_installation_paths(platform_key, version)
            
            if platform_key.startswith('windows'):
                chrome_binary = version_dir / "chrome.exe"
                chromedriver_binary = version_dir / "chromedriver.exe"
            else:
                chrome_binary = version_dir / "chrome"
                chromedriver_binary = version_dir / "chromedriver"
            
            # Update config with actual binary paths
            if chrome_binary.exists():
                CONFIG.setdefault('browser', {})['chrome_binary_path'] = str(chrome_binary)
            if chromedriver_binary.exists():
                CONFIG.setdefault('browser', {})['chromedriver_path'] = str(chromedriver_binary)
            
            # Save updated config
            save_config(CONFIG)
            logger.info("[STATUS] ✅ Updated config with driver paths")
            
        except Exception as e:
            logger.error("[STATUS] ❌ Failed to update config: %s", e)
    
    def install_all(self, version: Optional[str] = None, cleanup: bool = True) -> Dict[str, Optional[str]]:
        """Install both Chrome and ChromeDriver."""
        platform_key = self.detect_platform()
        logger.info("[STATUS] Installing drivers for platform: %s", platform_key)
        
        # Get version information
        if version:
            version_info = self.find_version_by_major(version)
            if not version_info:
                logger.error("[STATUS] Version %s not found", version)
                return {}
        else:
            version_info = self.get_latest_chrome_version()
        
        if not version_info:
            logger.error("[STATUS] Failed to get version information")
            return {}
        
        version_str = version_info['version']
        logger.info("[STATUS] Installing Chrome version: %s", version_str)
        
        # Clean up old versions if requested
        if cleanup:
            self._cleanup_old_versions(platform_key)
        
        # Check if version directory already exists before installing
        version_dir = self._get_clean_installation_paths(platform_key, version_str)
        if version_dir.exists():
            logger.warning("[STATUS] ⚠️ Chrome version %s already exists at %s", version_str, version_dir)
            resp = input("Do you want to [r]einstall (overwrite) or [c]ancel? [r/c]: ").strip().lower()
            if resp == 'c':
                logger.info("[STATUS] User cancelled installation")
                return {}
            elif resp == 'r':
                shutil.rmtree(version_dir, ignore_errors=True)
                logger.info("[STATUS] Overwriting Chrome version %s", version_str)
            else:
                logger.info("[STATUS] Invalid input, cancelling installation")
                return {}
        
        # Install Chrome and ChromeDriver
        chrome_path = self.install_chrome(version_info, platform_key)
        chromedriver_path = self.install_chromedriver(version_info, platform_key)
        
        results = {
            'chrome': chrome_path,
            'chromedriver': chromedriver_path,
            'version': version_str,
            'platform': platform_key
        }
        
        if chrome_path and chromedriver_path:
            logger.info("[STATUS] ✅ All drivers installed successfully")
            # Update config with installed paths
            self.update_config_with_paths(chrome_path, chromedriver_path, version_str)
        else:
            logger.warning("[STATUS] ⚠️ Some drivers failed to install")
        
        return results
    
    def list_available_versions(self) -> None:
        """List all available Chrome for Testing versions."""
        versions = self.get_available_versions()
        
        if not versions:
            logger.error("[STATUS] ❌ Failed to fetch available versions")
            return
        
        logger.info("[STATUS] 📋 Available Chrome for Testing versions (%d total):", len(versions))
        logger.info("-" * 80)
        
        for i, version_info in enumerate(versions[:20]):  # Show first 20 versions
            version = version_info['version']
            revision = version_info['revision']
            logger.info("%d. %s (revision: %s)", i+1, version, revision)
        
        if len(versions) > 20:
            logger.info("... and %d more versions", len(versions) - 20)
        
        logger.info("\n💡 Use: fss --init chrome <major_version> to install a specific version")
        logger.info("💡 Example: fss --init chrome 138")
    
    def check_installation(self) -> Dict[str, Any]:
        """Check the current driver installation status."""
        platform_key = self.detect_platform()
        installed_versions = self.list_installed_versions()
        
        # Get latest installed versions
        latest_chrome = max(installed_versions.get('chrome', []), default=None)
        latest_chromedriver = max(installed_versions.get('chromedriver', []), default=None)
        
        # Check if binaries exist
        chrome_path = None
        chromedriver_path = None
        
        if latest_chrome:
            if platform_key.startswith('windows'):
                chrome_path = self.drivers_dir / "windows" / "chrome" / latest_chrome / "chrome.exe"
                chromedriver_path = self.drivers_dir / "windows" / "chrome" / latest_chrome / "chromedriver.exe"
            elif platform_key.startswith('linux'):
                chrome_path = self.drivers_dir / "linux" / "chrome" / latest_chrome / "chrome"
                chromedriver_path = self.drivers_dir / "linux" / "chrome" / latest_chrome / "chromedriver"
            elif platform_key.startswith('macos'):
                chrome_path = self.drivers_dir / "mac" / "chrome" / latest_chrome / "chrome"
                chromedriver_path = self.drivers_dir / "mac" / "chrome" / latest_chrome / "chromedriver"
        
        chrome_installed = chrome_path.exists() if chrome_path else False
        chromedriver_installed = chromedriver_path.exists() if chromedriver_path else False
        
        return {
            'platform': platform_key,
            'chrome_installed': chrome_installed,
            'chrome_path': str(chrome_path) if chrome_path else None,
            'chrome_version': latest_chrome,
            'chromedriver_installed': chromedriver_installed,
            'chromedriver_path': str(chromedriver_path) if chromedriver_path else None,
            'chromedriver_version': latest_chromedriver,
            'all_installed': chrome_installed and chromedriver_installed,
            'installed_versions': installed_versions
        }
    
    def set_default_driver_version(self, version: str) -> bool:
        """Set the default driver version and update config."""
        try:
            platform_key = self.detect_platform()
            version_dir = self._get_clean_installation_paths(platform_key, version)
            
            if not version_dir.exists():
                logger.error("[STATUS] Version %s is not installed", version)
                return False
            
            # Get the binary paths for this version
            if platform_key.startswith('windows'):
                chrome_path = version_dir / "chrome.exe"
                chromedriver_path = version_dir / "chromedriver.exe"
            else:
                chrome_path = version_dir / "chrome"
                chromedriver_path = version_dir / "chromedriver"
            
            if not chrome_path.exists() or not chromedriver_path.exists():
                logger.error("[STATUS] Version %s is incomplete (missing binaries)", version)
                return False
            
            # Update config with the selected version paths
            self.update_config_with_paths(str(version_dir), str(version_dir), version)
            
            logger.info("[STATUS] ✅ Set version %s as default driver", version)
            return True
            
        except Exception as e:
            logger.error("[STATUS] ❌ Failed to set default driver version: %s", e)
            return False
    
    def select_default_driver(self) -> bool:
        """Interactive selection of default driver version."""
        try:
            installed_versions = self.list_installed_versions()
            chrome_versions = installed_versions.get('chrome', [])
            
            if not chrome_versions:
                logger.error("[STATUS] No Chrome versions installed")
                return False
            
            if len(chrome_versions) == 1:
                # Only one version, automatically set as default
                version = chrome_versions[0]
                logger.info("[STATUS] Only one version installed (%s), setting as default", version)
                return self.set_default_driver_version(version)
            
            # Multiple versions, let user choose
            logger.info("[STATUS] 📋 Installed Chrome versions:")
            for i, version in enumerate(chrome_versions, 1):
                logger.info("  %d. %s", i, version)
            
            while True:
                try:
                    choice = input(f"Select default version (1-{len(chrome_versions)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(chrome_versions):
                        selected_version = chrome_versions[choice_idx]
                        return self.set_default_driver_version(selected_version)
                    else:
                        logger.warning("[STATUS] Invalid choice. Please enter 1-%d", len(chrome_versions))
                except ValueError:
                    logger.warning("[STATUS] Invalid input. Please enter a number.")
                except KeyboardInterrupt:
                    logger.info("\n[STATUS] Cancelled")
                    return False
            
        except Exception as e:
            logger.error("[STATUS] ❌ Failed to select default driver: %s", e)
            return False


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Driver Installer for FlashScore Scraper')
    parser.add_argument('--check', action='store_true', help='Check driver installation status')
    parser.add_argument('--install', action='store_true', help='Install drivers')
    parser.add_argument('--list-versions', action='store_true', help='List available Chrome versions')
    parser.add_argument('--version', type=str, help='Specific Chrome version to install (e.g., 138)')
    
    args = parser.parse_args()
    
    installer = DriverInstaller()
    
    if args.check:
        status = installer.check_installation()
        logger.info("[STATUS] Platform: %s", status['platform'])
        logger.info("[STATUS] Chrome installed: %s", status['chrome_installed'])
        logger.info("[STATUS] ChromeDriver installed: %s", status['chromedriver_installed'])
        logger.info("[STATUS] All installed: %s", status['all_installed'])
        if status['chrome_path']:
            logger.info("[STATUS] Chrome path: %s", status['chrome_path'])
        if status['chromedriver_path']:
            logger.info("[STATUS] ChromeDriver path: %s", status['chromedriver_path'])
    
    elif args.list_versions:
        installer.list_available_versions()
    
    elif args.install:
        if args.version:
            logger.info("[STATUS] Installing Chrome version %s...", args.version)
            results = installer.install_all(version=args.version)
        else:
            logger.info("[STATUS] Installing latest Chrome version...")
            results = installer.install_all()
        
        if results:
            logger.info("[STATUS] Installation completed:")
            logger.info("  Chrome: %s", results.get('chrome', 'Not installed'))
            logger.info("  ChromeDriver: %s", results.get('chromedriver', 'Not installed'))
            logger.info("  Version: %s", results.get('version', 'Unknown'))
            logger.info("  Platform: %s", results.get('platform', 'Unknown'))
        else:
            logger.error("[STATUS] Installation failed")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()