from abc import ABC, abstractmethod
from typing import Optional, Any
from ..models import IdentityVerificationSession
from ..schemas import VerificationSessionCreate

class VerificationRepository(ABC):
    """
    Abstract interface for persisting Verification Sessions.
    """
    
    @abstractmethod
    def save(self, session: IdentityVerificationSession) -> Any:
        """
        Persist the session and return the persisted object (or the updated DTO).
        """
        pass

    @abstractmethod
    def get(self, session_id: str) -> Optional[IdentityVerificationSession]:
        """
        Retrieve a session by internal ID and return as DTO.
        """
        pass

    @abstractmethod
    def get_by_provider_id(self, provider_session_id: str) -> Optional[IdentityVerificationSession]:
        pass
