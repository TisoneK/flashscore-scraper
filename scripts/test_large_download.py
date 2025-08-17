import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.driver_manager.downloader import DriverDownloader

def test_large_download(url: str, filename: str):
    """Test large file download with progress tracking"""
    print(f"Starting large file download test: {filename}")
    downloader = DriverDownloader()
    target = Path("downloads") / filename
    target.parent.mkdir(exist_ok=True)
    
    try:
        start_time = time.time()
        downloader.download(url, target)
        duration = time.time() - start_time
        
        if target.exists():
            size_mb = target.stat().st_size / (1024 * 1024)
            print(f"✅ Download successful! {size_mb:.2f}MB in {duration:.2f} seconds")
            print(f"Average speed: {size_mb/duration:.2f} MB/s")
        else:
            print("❌ Download failed - file not created")
    except Exception as e:
        print(f"❌ Download failed: {str(e)}")

if __name__ == "__main__":
    # Test with Chrome driver
    test_large_download(
        url="https://storage.googleapis.com/chrome-for-testing-public/140.0.7339.16/win64/chrome-win64.zip",
        filename="chrome-win64.zip"
    )
