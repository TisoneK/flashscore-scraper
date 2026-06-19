import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the downloader after mocking tqdm
with patch('tqdm.tqdm'):
    from src.driver_manager.downloader import DriverDownloader
    from src.driver_manager.progress import DownloadProgress

class TestDownloaderIntegration(unittest.TestCase):
    """Integration tests for the downloader with progress tracking"""
    
    def setUp(self):
        # Create a temporary directory for downloads
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.test_file = self.test_dir / "test_download.bin"
        
        # Create a mock progress callback
        self.mock_progress = MagicMock(spec=DownloadProgress)
        
        # Initialize downloader with mock progress
        self.downloader = DriverDownloader(progress=self.mock_progress)
    
    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    @patch('requests.get')
    def test_download_file_with_progress(self, mock_get):
        """Test downloading a file with progress tracking"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Perform download
        test_url = "http://example.com/test.bin"
        self.downloader.download(test_url, self.test_file)
        
        # Verify requests was called correctly
        mock_get.assert_called_once_with(
            test_url, 
            stream=True, 
            timeout=30
        )
        
        # Verify progress methods were called
        self.mock_progress.init.assert_called_once_with(1024, f"Downloading {self.test_file.name}")
        self.assertEqual(self.mock_progress.update.call_count, 2)  # Two chunks
        self.mock_progress.close.assert_called_once()
    
    @patch('requests.get')
    def test_download_file_error_handling(self, mock_get):
        """Test error handling during download"""
        # Setup mock to raise an exception
        mock_get.side_effect = Exception("Network error")
        
        # Test that exception is properly propagated
        with self.assertRaises(Exception) as context:
            self.downloader.download("http://example.com/error.bin", self.test_file)
        
        self.assertIn("Network error", str(context.exception))
        
        # Verify progress was cleaned up even on error
        self.mock_progress.close.assert_called_once()
    
    def test_invalid_url_handling(self):
        """Test handling of invalid URLs"""
        from src.driver_manager.exceptions import DownloadError
        with self.assertRaises(DownloadError):
            self.downloader.download("not-a-url", self.test_file)
    
    @patch('requests.get')
    def test_atomic_download(self, mock_get):
        """Test that downloads are atomic: final file exists, no temp remains"""
        # Setup mock response
        content = b'chunk1'
        mock_response = MagicMock()
        mock_response.headers = {'content-length': str(len(content))}
        mock_response.iter_content.return_value = [content]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value.__enter__.return_value = mock_response

        # Perform download to real temp directory
        test_url = "http://example.com/atomic.bin"
        self.downloader.download(test_url, self.test_file)

        # Final file exists with expected content
        self.assertTrue(self.test_file.exists())
        with open(self.test_file, 'rb') as f:
            self.assertEqual(f.read(), content)

        # No temp .tmp files remain in directory
        tmp_files = list(self.test_dir.glob('*.tmp'))
        self.assertEqual(tmp_files, [])

if __name__ == "__main__":
    unittest.main()
