class FlashscoreScraperError(Exception):
    """Base exception for all Flashscore Scraper errors."""
    pass

# Data extraction hierarchy
class DataExtractionError(FlashscoreScraperError):
    """General data extraction error."""
    pass

class DataNotFoundError(DataExtractionError):
    """Raised when expected data is not found (e.g., selector returns nothing)."""
    pass

class DataParseError(DataExtractionError):
    """Raised when data is found but cannot be parsed (e.g., invalid format)."""
    pass

class DataValidationError(DataExtractionError):
    """Raised when data is found and parsed but fails validation (e.g., not enough H2H rows)."""
    pass

class DataUnavailableWarning(Warning):
    """Warning for expected missing data (not an error)."""
    pass

class NetworkError(FlashscoreScraperError):
    """Raised for network-related errors (timeouts, disconnections, etc)."""
    pass

class DriverError(FlashscoreScraperError):
    """Raised for browser/driver issues (installation, launch, crash, etc)."""
    pass

class ConfigError(FlashscoreScraperError):
    """Raised for configuration errors (invalid/missing config, etc)."""
    pass

class PredictionError(FlashscoreScraperError):
    """Raised for prediction module errors (model, calculation, etc)."""
    pass

class UIError(FlashscoreScraperError):
    """Raised for UI-related errors (CLI, GUI, display, etc)."""
    pass 
