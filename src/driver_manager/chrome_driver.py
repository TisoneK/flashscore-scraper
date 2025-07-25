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
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ChromeDriverManager:
    """Manages Chrome WebDriver initialization and configuration."""
    
    def __init__(self, config: Dict[str, Any], chrome_log_path: Optional[str] = None):
        self.config = config
        self.chrome_log_path = chrome_log_path
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
            if not chrome_path or not chromedriver_path:
                chrome_base = base_dir / "chrome"
                if chrome_base.exists():
                    chrome_versions = [d for d in chrome_base.iterdir() if d.is_dir()]
                    if chrome_versions:
                        latest_chrome = max(chrome_versions, key=lambda x: x.name)
                        # Both binaries are in the same version directory
                        if not chrome_path:
                            chrome_path = latest_chrome / "chrome.exe" if platform_key.startswith('windows') else latest_chrome / "chrome"
                            if not chrome_path.exists():
                                chrome_path = None
                        if not chromedriver_path:
                            chromedriver_path = latest_chrome / "chromedriver.exe" if platform_key.startswith('windows') else latest_chrome / "chromedriver"
                            if not chromedriver_path.exists():
                                chromedriver_path = None
        
        return str(chrome_path) if chrome_path else None, str(chromedriver_path) if chromedriver_path else None
    
    def get_chrome_options(self) -> Options:
        """Get Chrome options from config, always including critical stability/sandbox flags."""
        options = Options()
        
        # Get browser config
        browser_config = self.config.get('browser', {})
        chrome_options = self.config.get('chrome_options', {})
        
        # Add binary location if specified
        chrome_path, _ = self.find_latest_driver_paths()
        if chrome_path:
            options.binary_location = chrome_path
        
        # Handle headless mode from browser config
        if browser_config.get('headless', False):
            options.add_argument('--headless=new')
        
        # Always add critical flags for stability/sandboxing and performance
        critical_flags = [
            # Core stability flags
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-gpu-sandbox',
            
            # Browser features
            '--disable-extensions',
            '--disable-infobars',
            '--disable-popup-blocking',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            
            # Performance optimizations
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            
            # Memory optimizations
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--js-flags=--max-old-space-size=4096',
            '--disable-javascript-harmony-shipping',
            '--disable-v8-idle-tasks',
            
            # Network optimizations
            '--disable-component-extensions-with-background-pages',
            '--no-first-run',
            '--no-default-browser-check',
            
            # Security and stability
            '--allow-running-insecure-content',
            '--disable-site-isolation-trials',
            '--disable-features=TranslateUI',
            '--disable-features=BlinkGenPropertyTrees',
            
            # Logging suppression
            '--log-level=3',
            '--silent',
            '--disable-logging',
        ]
        for flag in critical_flags:
            options.add_argument(flag)
        
        # Add window size from config if present
        window_size = chrome_options.get('window_size') or browser_config.get('window_size')
        if window_size:
            options.add_argument(f'--window-size={window_size}')
        
        # Add any extra arguments from config (user can add more, but not remove essentials)
        arguments = chrome_options.get('arguments', [])
        for arg in arguments:
            if arg not in critical_flags:
                options.add_argument(arg)
        
        # Add experimental options from config
        experimental_options = chrome_options.get('experimental_options', {})
        for key, value in experimental_options.items():
            options.add_experimental_option(key, value)
        
        # Add logging suppression experimental options
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('detach', True)
        
        # Add preferences from config
        preferences = chrome_options.get('preferences', {})
        for key, value in preferences.items():
            options.add_experimental_option(f"prefs.{key}", value)
        
        return options
    
    def create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver, redirecting all Chrome/ChromeDriver logs to the chrome log file."""
        try:
            # Get ChromeDriver path
            _, chromedriver_path = self.find_latest_driver_paths()
            if not chromedriver_path:
                raise WebDriverException("ChromeDriver not found. Run 'fss --init chrome' to install drivers.")

            # Use the chrome_log_path passed to the manager
            log_file_path = self.chrome_log_path
            if not log_file_path:
                raise Exception("chrome_log_path must be provided to ChromeDriverManager for dual logging.")

            # Create service, redirecting ChromeDriver logs to the chrome log file
            service_kwargs = {"executable_path": chromedriver_path}
            if log_file_path:
                service_kwargs["log_path"] = str(log_file_path)
            service = Service(**service_kwargs)

            # Monkey-patch Service.start to redirect ChromeDriver and Chrome browser stderr to chrome log file
            orig_start = service.start
            def patched_start(*args, **kwargs):
                import subprocess
                log_file = open(log_file_path, 'a', encoding='utf-8')
                orig_popen = subprocess.Popen
                def patched_popen(*popen_args, **popen_kwargs):
                    popen_kwargs['stderr'] = log_file
                    return orig_popen(*popen_args, **popen_kwargs)
                subprocess.Popen, orig_popen_bak = patched_popen, subprocess.Popen
                try:
                    return orig_start(*args, **kwargs)
                finally:
                    subprocess.Popen = orig_popen_bak
            service.start = patched_start

            # Get Chrome options
            options = self.get_chrome_options()

            # Create driver with timeout handling
            import time
            start_time = time.time()
            timeout = 60  # 60 seconds timeout
            
            logger.info("🔄 Creating Chrome WebDriver...")
            
            # Create driver with timeout
            driver = None
            try:
                driver = webdriver.Chrome(service=service, options=options)
                elapsed_time = time.time() - start_time
                logger.info(f"✅ Chrome WebDriver initialized successfully in {elapsed_time:.2f}s")
                logger.info(f"📁 ChromeDriver path: {chromedriver_path}")
            except Exception as driver_error:
                elapsed_time = time.time() - start_time
                logger.error(f"❌ Failed to create Chrome WebDriver after {elapsed_time:.2f}s: {driver_error}")
                raise

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