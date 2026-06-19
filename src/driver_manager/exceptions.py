"""Custom exceptions for the driver manager module."""

class DriverManagerError(Exception):
    """Base exception for all driver manager related errors."""
    pass

class DownloadError(DriverManagerError):
    """Raised when a download operation fails."""
    pass

class NetworkError(DownloadError):
    """Raised when there's a network-related error during download."""
    pass

class HTTPError(DownloadError):
    """Raised when an HTTP request fails."""
    def __init__(self, status_code: int, message: str = None):
        self.status_code = status_code
        self.message = message or f"HTTP request failed with status code {status_code}"
        super().__init__(self.message)

class TimeoutError(NetworkError):
    """Raised when a download times out."""
    pass

class FileSystemError(DownloadError):
    """Raised when there's an error writing to the filesystem."""
    pass

class InvalidURLError(DownloadError):
    """Raised when an invalid URL is provided."""
    pass
