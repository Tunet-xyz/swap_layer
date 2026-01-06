from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .operations import AuthenticationOperations
from django.conf import settings

class AuthenticationService(ABC):
    
    def __init__(self, operations: AuthenticationOperations = None):
        self.ops = operations or AuthenticationOperations()

    @abstractmethod
    def get_login_url(self, request: Any, redirect_uri: str, state: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def complete_login(self, request: Any, code: str) -> Any:
        """
        Exchanges code and returns user info.
        If persistence is enabled, it might return a User object or Identity object.
        """
        pass

    @abstractmethod
    def get_logout_url(self, request: Any, return_to: str) -> str:
        pass

class StandardAuthenticationService(AuthenticationService):
    """
    Standard service. Returns raw data or Pydantic models.
    """
    def get_login_url(self, request: Any, redirect_uri: str, state: Optional[str] = None) -> str:
        return self.ops.get_authorization_url(request, redirect_uri, state)

    def complete_login(self, request: Any, code: str) -> Dict[str, Any]:
        return self.ops.exchange_code(request, code)

    def get_logout_url(self, request: Any, return_to: str) -> str:
        return self.ops.get_logout_url(request, return_to)

def get_authentication_service():
    framework = getattr(settings, 'FRAMEWORK', None)
    
    if framework == 'django':
        try:
            from .frameworks.django import DjangoAuthenticationService
            return DjangoAuthenticationService()
        except ImportError as e:
            raise ImportError(f"Django framework requested but import failed: {e}")
            
    return StandardAuthenticationService()
