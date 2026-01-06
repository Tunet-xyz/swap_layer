from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..schemas import VerificationSessionCreate
from .operations.core import IdentityOperations
from swap_layer.config import settings

class VerificationService(ABC):
    """
    Abstract Service Interface.
    Implementations handle the integration with the persistence layer (if any).
    """
    
    def __init__(self, operations: IdentityOperations = None):
        self.ops = operations or IdentityOperations()

    @abstractmethod
    def create_session(self, user_id: str, data: VerificationSessionCreate, user_email: Optional[str] = None) -> Any:
        pass

class StandardVerificationService(VerificationService):
    """
    Standard service for non-framework usage. 
    Returns Pydantic Models.
    """
    def create_session(self, user_id: str, data: VerificationSessionCreate, user_email: Optional[str] = None):
        return self.ops.create_session(user_id, data, user_email)

def get_verification_service():
    """
    Factory to get the correct Service implementation.
    """
    framework = getattr(settings, 'FRAMEWORK', None)
    
    if framework == 'django':
        try:
            from .frameworks.django import DjangoVerificationService
            return DjangoVerificationService()
        except ImportError as e:
            # Fallback or strict error?
            raise ImportError(f"Django framework requested but import failed. Ensure Django is installed: {e}")
            
    return StandardVerificationService()
