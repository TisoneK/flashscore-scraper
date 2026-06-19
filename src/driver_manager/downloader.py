import os
import requests
import socket
import ssl
import time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from tqdm import tqdm
from .progress import DownloadProgress
from .exceptions import (
    DownloadError, NetworkError, HTTPError, TimeoutError,
    FileSystemError, InvalidURLError
)

class DriverDownloader:
    """Handles chunked downloads with progress tracking"""
    
    def __init__(self, progress: Optional[DownloadProgress] = None, chunk_size: int = 8192):
        """Initialize the downloader with an optional progress tracker.
        
        Args:
            progress: Optional DownloadProgress instance for tracking download progress.
                     If None, a new DownloadProgress will be created.
            chunk_size: The size of each chunk in bytes. Defaults to 8192 (8KB).
        """
        self.chunk_size = chunk_size
        self.progress = progress if progress is not None else DownloadProgress()
        
    def _validate_url(self, url: str) -> None:
        """Validate the download URL.
        
        Args:
            url: The URL to validate
            
        Raises:
            InvalidURLError: If the URL is invalid
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
            if result.scheme not in ('http', 'https'):
                raise ValueError(f"Unsupported protocol: {result.scheme}")
        except ValueError as e:
            raise InvalidURLError(f"Invalid URL: {e}")

    def _handle_download_error(self, error: Exception, url: str) -> None:
        """Handle download errors and raise appropriate exceptions.
        
        Args:
            error: The exception that was caught
            url: The URL being downloaded from
            
        Raises:
            Appropriate exception based on the error type
        """
        error_mapping: Dict[Any, Any] = {
            KeyboardInterrupt: lambda _: DownloadError(
                "Download was cancelled by user"
            ),
            requests.exceptions.HTTPError: lambda e: HTTPError(
                status_code=e.response.status_code if hasattr(e, 'response') else 0,
                message=f"HTTP error occurred: {str(e)}"
            ),
            requests.exceptions.ConnectionError: lambda _: NetworkError(
                f"Failed to connect to {url}. Please check your internet connection."
            ),
            requests.exceptions.Timeout: lambda _: TimeoutError(
                f"Request to {url} timed out. The server took too long to respond."
            ),
            requests.exceptions.RequestException: lambda e: NetworkError(
                f"Network error occurred: {str(e)}"
            ),
            (FileNotFoundError, PermissionError, OSError): lambda e: FileSystemError(
                f"Filesystem error: {str(e)}"
            ),
            (socket.gaierror, ssl.SSLError): lambda e: NetworkError(
                f"Network resolution error: {str(e)}"
            )
        }
        
        # Find the appropriate exception type or use DownloadError as default
        for error_type, exception_factory in error_mapping.items():
            if isinstance(error, error_type):
                raise exception_factory(error)
        
        # For any other exception, wrap it in a DownloadError
        raise DownloadError(f"Download failed: {str(error)}")

    def _cleanup_temp_file(self, temp_target: Path):
        """Safely remove temporary file"""
        if temp_target and temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass

    def download(self, url: str, target: Path) -> None:
        """
        Download file from URL to target path with progress tracking
        
        Args:
            url: Download source URL
            target: Local destination path
            
        Raises:
            DownloadError: Base class for all download errors
            NetworkError: For network-related issues
            HTTPError: For HTTP errors (status codes 4xx, 5xx)
            TimeoutError: When the request times out
            FileSystemError: For file system related errors
            InvalidURLError: When the provided URL is invalid
        """
        temp_target = None
        try:
            # Validate URL before proceeding
            self._validate_url(url)
            
            # Ensure target directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            tqdm.write(f"[STATUS] Connecting to {url}")
            
            # Revert SSL verification for production use
            temp_target = target.with_suffix(f".{os.getpid()}.tmp")
            
            # Remove existing temp file
            if temp_target.exists():
                temp_target.unlink()
                
            with requests.get(url, stream=True, timeout=30, verify=True) as response:
                response.raise_for_status()
                
                # Check content length
                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0:
                    raise DownloadError("Server returned empty content")
                
                tqdm.write(f"[STATUS] Download started | Size: {total_size/1024/1024:.2f}MB")
                self.progress.init(total_size, f"Downloading {target.name}")
                
                # Write to temp file
                with open(temp_target, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:  # filter out keep-alive chunks
                            f.write(chunk)
                            self.progress.update(len(chunk))
            
            # Move to final location
            if temp_target.exists():
                if target.exists():
                    target.unlink()
                temp_target.rename(target)
                tqdm.write(f"\n[STATUS] Download completed: {target}")
        
        except KeyboardInterrupt:
            self._cleanup_temp_file(temp_target)
            tqdm.write("\n[STATUS] Download cancelled by user")
            raise
        except Exception as e:
            self._cleanup_temp_file(temp_target)
            tqdm.write(f"[ERROR] Failed to download {url}: {str(e)}")
            self._handle_download_error(e, url)
            
        finally:
            self.progress.close()
