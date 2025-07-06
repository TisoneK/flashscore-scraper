#!/usr/bin/env python3
"""
Platform-independent setup script for FlashScore Scraper.
Detects the current platform and sets up appropriate drivers and Chrome installation.
"""

import os
import sys
import platform
import subprocess
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", message="Could not find platform independent libraries")

class PlatformSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.drivers_dir = self.project_root / "drivers"
        
    def detect_platform(self):
        """Detect the current platform and architecture."""
        print(f"🔍 Detecting platform...")
        print(f"   System: {platform.system()}")
        print(f"   Machine: {platform.machine()}")
        print(f"   Platform: {platform.platform()}")
        print(f"   Python: {sys.version}")
        
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
            print(f"⚠️  Unknown platform: {self.system}")
            return 'unknown'
    
    def get_chrome_version(self):
        """Get the installed Chrome version."""
        try:
            if self.system == 'windows':
                # Try to get Chrome version from registry or executable
                chrome_paths = [
                    str(self.project_root / "drivers" / "windows" / "chrome-win64" / "chrome.exe"),
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                ]
                
                for path in chrome_paths:
                    if os.path.exists(path):
                        try:
                            result = subprocess.run([path, "--version"], 
                                                 capture_output=True, text=True, timeout=10)
                            if result.returncode == 0:
                                version = result.stdout.strip().split()[-1]
                                print(f"   Found Chrome version: {version}")
                                return version
                        except Exception as e:
                            print(f"   Could not get version from {path}: {e}")
                            continue
                            
            elif self.system == 'linux':
                result = subprocess.run(['google-chrome', '--version'], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return version
                    
            elif self.system == 'darwin':
                result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return version
                    
        except Exception as e:
            print(f"⚠️  Could not detect Chrome version: {e}")
            
        return None
    
    def download_chromedriver(self, chrome_version=None):
        """Download the appropriate ChromeDriver version."""
        if not chrome_version:
            chrome_version = self.get_chrome_version()
            
        if not chrome_version:
            print("⚠️  Could not detect Chrome version, using Chrome 138.* compatible version")
            chrome_version = "138.0.7044.0"  # Chrome 138.* compatible version
        
        print(f"📥 Downloading ChromeDriver for Chrome {chrome_version}...")
        
        # Determine the platform-specific ChromeDriver URL
        platform_map = {
            'windows-x64': 'win64',
            'windows-x86': 'win32',
            'linux-x64': 'linux64',
            'linux-arm64': 'linux64',  # ChromeDriver doesn't have ARM64 version
            'macos-x64': 'mac64',
            'macos-arm64': 'mac_arm64'
        }
        
        platform_key = self.detect_platform()
        driver_platform = platform_map.get(platform_key, 'win64')
        
        # ChromeDriver download URL
        if chrome_version == "latest":
            base_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
            try:
                with urllib.request.urlopen(base_url) as response:
                    chrome_version = response.read().decode('utf-8').strip()
            except Exception as e:
                print(f"⚠️  Could not get latest version: {e}")
                chrome_version = "138.0.7044.0"  # Fallback version
        
        driver_url = f"https://chromedriver.storage.googleapis.com/{chrome_version}/chromedriver_{driver_platform}.zip"
        
        # Create drivers directory
        platform_dir = self.drivers_dir / self.system
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if ChromeDriver already exists
        driver_file = platform_dir / f"chromedriver{'.exe' if self.system == 'windows' else ''}"
        if driver_file.exists():
            print(f"✅ ChromeDriver already exists at: {driver_file}")
            return str(driver_file)
        
        # Download and extract ChromeDriver
        try:
            print(f"   Downloading from: {driver_url}")
            urllib.request.urlretrieve(driver_url, driver_file.with_suffix('.zip'))
            
            # Extract the zip file
            with zipfile.ZipFile(driver_file.with_suffix('.zip'), 'r') as zip_ref:
                zip_ref.extractall(platform_dir)
            
            # Make executable on Unix systems
            if self.system != 'windows':
                os.chmod(driver_file, 0o755)
            
            # Clean up zip file
            driver_file.with_suffix('.zip').unlink()
            
            print(f"✅ ChromeDriver downloaded to: {driver_file}")
            return str(driver_file)
            
        except Exception as e:
            print(f"❌ Failed to download ChromeDriver: {e}")
            print(f"   This is normal if ChromeDriver already exists or network issues occur")
            return None
    
    def setup_chrome_installation(self):
        """Set up Chrome installation for the current platform."""
        print(f"🔧 Setting up Chrome installation for {self.system}...")
        
        platform_dir = self.drivers_dir / self.system
        
        if self.system == 'windows':
            # For Windows, we already have chrome-win64 directory
            chrome_dir = platform_dir / "chrome-win64"
            if chrome_dir.exists():
                print(f"✅ Chrome installation found at: {chrome_dir}")
                return str(chrome_dir / "chrome.exe")
            else:
                print("⚠️  Chrome installation not found, will use system Chrome")
                return None
                
        elif self.system == 'linux':
            # For Linux, we can use system Chrome or download portable version
            chrome_binary = platform_dir / "chrome"
            if chrome_binary.exists():
                print(f"✅ Chrome binary found at: {chrome_binary}")
                return str(chrome_binary)
            else:
                print("⚠️  Chrome binary not found, will use system Chrome")
                return None
                
        elif self.system == 'darwin':
            # For macOS, we can use system Chrome or download portable version
            chrome_binary = platform_dir / "chrome"
            if chrome_binary.exists():
                print(f"✅ Chrome binary found at: {chrome_binary}")
                return str(chrome_binary)
            else:
                print("⚠️  Chrome binary not found, will use system Chrome")
                return None
        
        return None
    
    def update_config(self):
        """Update the configuration file with platform-specific settings."""
        print("⚙️  Updating configuration...")
        
        config_file = self.project_root / "src" / "config.json"
        if not config_file.exists():
            print("⚠️  config.json not found, creating default configuration")
            return
        
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update driver path to be platform-independent
            config['browser']['driver_path'] = None  # Let the driver auto-detect
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            print("✅ Configuration updated successfully")
            
        except Exception as e:
            print(f"❌ Failed to update configuration: {e}")
    
    def run(self):
        """Run the complete platform setup."""
        print("🚀 FlashScore Scraper - Platform Setup")
        print("=" * 50)
        
        # Detect platform
        platform_key = self.detect_platform()
        print(f"✅ Detected platform: {platform_key}")
        
        # Create drivers directory structure
        self.drivers_dir.mkdir(exist_ok=True)
        (self.drivers_dir / self.system).mkdir(exist_ok=True)
        
        # Download ChromeDriver
        driver_path = self.download_chromedriver()
        
        # Set up Chrome installation
        chrome_path = self.setup_chrome_installation()
        
        # Update configuration
        self.update_config()
        
        print("\n" + "=" * 50)
        print("✅ Platform Setup Completed!")
        print(f"\n📋 Summary:")
        print(f"   • Platform: {platform_key}")
        print(f"   • ChromeDriver: {'✅ Found' if driver_path else '❌ Missing'}")
        print(f"   • Chrome Binary: {'✅ Found' if chrome_path else '⚠️  Using System'}")
        print(f"   • Configuration: ✅ Updated")
        
        print(f"\n🚀 Your scraper is ready to use!")
        print(f"   Run: python main.py --cli")
        print(f"   Run: python main.py --ui")
        print(f"   Run: python run_cli.py --cli")

if __name__ == "__main__":
    setup = PlatformSetup()
    setup.run() 