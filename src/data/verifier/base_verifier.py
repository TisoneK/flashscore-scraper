from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional, Callable

class BaseVerifier(ABC):
    """
    Abstract base class for all data verifiers.
    Provides a standard interface for verifying data.
    """
    @abstractmethod
    def verify(self, data: Any, status_callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Verify the given data.
        Args:
            data: The data to verify.
            status_callback: Optional callback function for status updates.
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        pass 