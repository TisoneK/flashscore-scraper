#!/usr/bin/env python3
"""
Chrome WebDriver Manager for FlashScore Scraper
Handles Chrome driver initialization and configuration.
"""

import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Module-level cache for the chromedriver path — avoids race conditions when
# multiple threads call webdriver-manager simultaneously (which corrupts the
# download cache directory). After the first successful find, all subsequent
# calls return the cached path without touching webdriver-manager.
_chromedriver_cache: Optional[str] = None
_chromedriver_cache_lock = threading.Lock()

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
    
    def get_chrome_options(self, chrome_path: Optional[str] = None) -> Options:
        """Get Chrome options from config, always including critical stability/sandbox flags.
        
        Args:
            chrome_path: Optional explicit Chrome binary path. If not provided,
                        will try to find it via find_latest_driver_paths() or system PATH.
        """
        options = Options()
        
        # Get browser config
        browser_config = self.config.get('browser', {})
        chrome_options = self.config.get('chrome_options', {})
        
        # Add binary location: use explicit path if given, otherwise look in local drivers/
        if chrome_path:
            options.binary_location = chrome_path
        else:
            local_chrome_path, _ = self.find_latest_driver_paths()
            if local_chrome_path:
                options.binary_location = local_chrome_path
        
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
            '--disable-features=IsolateOrigins,site-per-process,VizDisplayCompositor,TranslateUI,BlinkGenPropertyTrees',
            
            # Performance optimizations
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
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
            
            # Security and stability (safer options)
            '--disable-site-isolation-trials',
            
            # Comprehensive logging suppression
            '--log-level=3',  # Only fatal errors
            '--silent',
            '--disable-logging',
            '--disable-dev-shm-usage',
            '--disable-gpu-logging',
            '--disable-background-logging',
            '--disable-component-logging',
            '--disable-extensions-logging',
            '--disable-features=VizDisplayCompositor',
            '--disable-ipc-logging',
            '--disable-logging',
            '--disable-perf-logging',
            '--disable-renderer-logging',
            '--disable-service-logging',
            '--disable-web-security-logging',
            '--log-file=/dev/null',  # Redirect logs to null
            '--enable-logging=false',
            '--v=0',  # Verbose level 0
            '--vmodule=*=0',  # Disable all verbose modules
        ]
        
        # Add risky flags only if explicitly enabled in config
        risky_flags = [
            '--disable-web-security',
            '--allow-running-insecure-content',
        ]
        
        if chrome_options.get('enable_risky_flags', False):
            critical_flags.extend(risky_flags)
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
    
    def _find_chromedriver_system_path(self) -> Optional[str]:
        """Try to find ChromeDriver on the system PATH."""
        chromedriver_name = 'chromedriver.exe' if platform.system().lower() == 'windows' else 'chromedriver'
        path = shutil.which(chromedriver_name)
        if path:
            logger.info(f"Found ChromeDriver on system PATH: {path}")
        return path

    def _find_chromedriver_via_webdriver_manager(self) -> Optional[str]:
        """Find ChromeDriver using webdriver-manager, with thread-safe caching.

        Caches the result after the first successful find so concurrent
        threads don't race on webdriver-manager's download cache.
        """
        global _chromedriver_cache

        # Fast path — return cached path if valid
        if _chromedriver_cache is not None and Path(_chromedriver_cache).exists():
            return _chromedriver_cache

        with _chromedriver_cache_lock:
            # Double-check after acquiring lock
            if _chromedriver_cache is not None and Path(_chromedriver_cache).exists():
                return _chromedriver_cache

            try:
                from webdriver_manager.chrome import ChromeDriverManager as WDMChromeDriverManager
                chromedriver_path = WDMChromeDriverManager().install()
                if not chromedriver_path or not Path(chromedriver_path).exists():
                    return None

                def _is_binary(path):
                    try:
                        with open(path, "rb") as f:
                            magic = f.read(4)
                        return (
                            magic == b"\x7fELF" or
                            magic[:2] == b"MZ" or
                            magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe",
                                      b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce") or
                            magic[:2] == b"#!"
                        )
                    except Exception:
                        return False

                # If webdriver-manager returned the real binary, use it
                if _is_binary(chromedriver_path):
                    logger.info(f"Found ChromeDriver via webdriver-manager: {chromedriver_path}")
                    _chromedriver_cache = chromedriver_path
                    return chromedriver_path

                # webdriver-manager returned THIRD_PARTY_NOTICES.chromedriver (text file)
                # Search the same directory for the real binary
                parent = Path(chromedriver_path).parent
                logger.warning(f"webdriver-manager returned non-binary: {chromedriver_path}. Searching {parent}...")

                for candidate in sorted(parent.iterdir(), key=lambda p: len(p.name)):
                    name = candidate.name.lower()
                    if name in ("chromedriver", "chromedriver.exe") and _is_binary(str(candidate)):
                        try:
                            st = os.stat(str(candidate))
                            os.chmod(str(candidate), st.st_mode | 0o111)
                        except Exception:
                            logger.debug("Non-critical error (swallowed)")
                        logger.info(f"Found real ChromeDriver binary: {candidate}")
                        _chromedriver_cache = str(candidate)
                        return str(candidate)

                for candidate in parent.iterdir():
                    name = candidate.name.lower()
                    if "chromedriver" in name and "notices" not in name and "license" not in name:
                        if _is_binary(str(candidate)):
                            logger.info(f"Found ChromeDriver (fallback): {candidate}")
                            _chromedriver_cache = str(candidate)
                            return str(candidate)

                logger.error(f"Could not find real chromedriver in {parent}")
                return None
            except ImportError:
                logger.debug("webdriver-manager not available")
                return None
            except Exception as e:
                logger.debug(f"webdriver-manager lookup failed: {e}")
                return None

    def _find_chrome_binary_system_path(self) -> Optional[str]:
        """Try to find Chrome binary on the system PATH."""
        chrome_names = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium',
                        'chrome.exe', 'Google Chrome.app/Contents/MacOS/Google Chrome']
        for name in chrome_names:
            path = shutil.which(name)
            if path:
                logger.info(f"Found Chrome binary on system PATH: {path}")
                return path
        return None

    def create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver.
        
        Uses a multi-strategy approach to find ChromeDriver:
        1. Local drivers/ directory (find_latest_driver_paths)
        2. webdriver-manager package (auto-downloads matching version)
        3. System PATH (works with chromedriver_autoinstaller on CI)
        """
        try:
            # Get Chrome options first (we need them regardless)
            options = self.get_chrome_options()
            
            # Strategy 1: Find ChromeDriver in local drivers/ directory
            chrome_path, chromedriver_path = self.find_latest_driver_paths()
            
            # Strategy 2: Try webdriver-manager if local lookup failed
            if not chromedriver_path:
                logger.info("ChromeDriver not found in local drivers/, trying webdriver-manager...")
                chromedriver_path = self._find_chromedriver_via_webdriver_manager()
            
            # Strategy 3: Try system PATH as last resort (works with chromedriver_autoinstaller)
            if not chromedriver_path:
                logger.info("ChromeDriver not found via webdriver-manager, trying system PATH...")
                chromedriver_path = self._find_chromedriver_system_path()
            
            # If Chrome binary not found locally, try system PATH
            if not chrome_path:
                chrome_path = self._find_chrome_binary_system_path()
                if chrome_path:
                    options.binary_location = chrome_path

            # Create the driver
            logger.info("🔄 Creating Chrome WebDriver...")
            
            if chromedriver_path:
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
                logger.info(f"✅ Chrome WebDriver initialized successfully")
                logger.info(f"📁 ChromeDriver path: {chromedriver_path}")
            else:
                # Last resort: let Selenium find ChromeDriver on its own
                logger.warning("No explicit ChromeDriver path found, relying on Selenium auto-discovery...")
                driver = webdriver.Chrome(options=options)
                logger.info(f"✅ Chrome WebDriver initialized via auto-discovery")
            
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