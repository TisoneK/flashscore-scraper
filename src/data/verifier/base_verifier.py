from abc import ABC, abstractmethod
from typing import Any, Tuple

class BaseVerifier(ABC):
    """
    Abstract base class for all data verifiers.
    Provides a standard interface for verifying data.
    """
    @abstractmethod
    def verify(self, data: Any) -> Tuple[bool, str]:
        """
        Verify the given data.
        Args:
            data: The data to verify.
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        pass 