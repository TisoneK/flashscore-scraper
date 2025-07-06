#!/usr/bin/env python3
"""
Chrome WebDriver Manager for FlashScore Scraper
Handles Chrome driver initialization and configuration.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import logging

logger = logging.getLogger(__name__)

class ChromeDriverManager:
    """Manages Chrome WebDriver initialization and configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_root = Path(__file__).parent.parent.parent
        self.drivers_dir = self.project_root / "drivers"
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
    
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
    
    def find_latest_driver_paths(self) -> tuple[Optional[str], Optional[str]]:
        """Find the latest installed Chrome and ChromeDriver paths."""
        # Check config first for user-specified paths
        browser_config = self.config.get('browser', {})
        config_chrome_path = browser_config.get('chrome_binary_path')
        config_chromedriver_path = browser_config.get('chromedriver_path')
        
        # If config paths are set and exist, use them
        if config_chrome_path and Path(config_chrome_path).exists():
            chrome_path = config_chrome_path
        else:
            chrome_path = None
            
        if config_chromedriver_path and Path(config_chromedriver_path).exists():
            chromedriver_path = config_chromedriver_path
        else:
            chromedriver_path = None
        
        # If config paths not set or don't exist, auto-detect
        if not chrome_path or not chromedriver_path:
            platform_key = self.detect_platform()
            
            if platform_key.startswith('windows'):
                base_dir = self.drivers_dir / "windows"
            elif platform_key.startswith('linux'):
                base_dir = self.drivers_dir / "linux"
            elif platform_key.startswith('macos'):
                base_dir = self.drivers_dir / "mac"
            else:
                return chrome_path, chromedriver_path
            
            # Find latest Chrome version if not set in config
            if not chrome_path:
                chrome_base = base_dir / "chrome"
                if chrome_base.exists():
                    chrome_versions = [d for d in chrome_base.iterdir() if d.is_dir()]
                    if chrome_versions:
                        latest_chrome = max(chrome_versions, key=lambda x: x.name)
                        chrome_path = latest_chrome / "chrome.exe" if platform_key.startswith('windows') else latest_chrome / "chrome"
                        if not chrome_path.exists():
                            chrome_path = None
            
            # Find latest ChromeDriver version if not set in config
            if not chromedriver_path:
                chromedriver_base = base_dir / "chromedriver"
                if chromedriver_base.exists():
                    chromedriver_versions = [d for d in chromedriver_base.iterdir() if d.is_dir()]
                    if chromedriver_versions:
                        latest_chromedriver = max(chromedriver_versions, key=lambda x: x.name)
                        chromedriver_path = latest_chromedriver / "chromedriver.exe" if platform_key.startswith('windows') else latest_chromedriver / "chromedriver"
                        if not chromedriver_path.exists():
                            chromedriver_path = None
        
        return str(chrome_path) if chrome_path else None, str(chromedriver_path) if chromedriver_path else None
    
    def get_chrome_options(self) -> Options:
        """Get Chrome options from config."""
        options = Options()
        
        # Get options from config
        chrome_options = self.config.get('chrome_options', {})
        
        # Add binary location if specified
        chrome_path, _ = self.find_latest_driver_paths()
        if chrome_path:
            options.binary_location = chrome_path
        
        # Add arguments from config
        arguments = chrome_options.get('arguments', [])
        for arg in arguments:
            options.add_argument(arg)
        
        # Add experimental options from config
        experimental_options = chrome_options.get('experimental_options', {})
        for key, value in experimental_options.items():
            options.add_experimental_option(key, value)
        
        # Add preferences from config
        preferences = chrome_options.get('preferences', {})
        for key, value in preferences.items():
            options.add_experimental_option(f"prefs.{key}", value)
        
        return options
    
    def create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver."""
        try:
            # Get ChromeDriver path
            _, chromedriver_path = self.find_latest_driver_paths()
            
            if not chromedriver_path:
                raise WebDriverException("ChromeDriver not found. Run 'fss --init chrome' to install drivers.")
            
            # Create service
            service = Service(executable_path=chromedriver_path)
            
            # Get Chrome options
            options = self.get_chrome_options()
            
            # Create driver
            driver = webdriver.Chrome(service=service, options=options)
            
            logger.info(f"✅ Chrome WebDriver initialized successfully")
            logger.info(f"📁 ChromeDriver path: {chromedriver_path}")
            
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create Chrome WebDriver: {e}")
            raise
    
    def check_driver_installation(self) -> Dict[str, Any]:
        """Check if Chrome and ChromeDriver are properly installed."""
        chrome_path, chromedriver_path = self.find_latest_driver_paths()
        
        chrome_installed = chrome_path is not None and Path(chrome_path).exists()
        chromedriver_installed = chromedriver_path is not None and Path(chromedriver_path).exists()
        
        return {
            'chrome_installed': chrome_installed,
            'chrome_path': chrome_path,
            'chromedriver_installed': chromedriver_installed,
            'chromedriver_path': chromedriver_path,
            'all_installed': chrome_installed and chromedriver_installed
        } 