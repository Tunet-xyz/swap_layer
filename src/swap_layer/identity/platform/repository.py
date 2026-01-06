from abc import ABC, abstractmethod
from typing import Optional, Any
from ..models import UserIdentity

class PlatformRepository(ABC):
    """
    Abstract interface for persisting User Identity mappings.
    """
    
    @abstractmethod
    def save(self, identity: UserIdentity) -> Any:
        pass

    @abstractmethod
    def get(self, provider: str, provider_user_id: str) -> Optional[UserIdentity]:
        pass

    @abstractmethod
    def get_by_user(self, user_id: str) -> Optional[UserIdentity]:
        pass
