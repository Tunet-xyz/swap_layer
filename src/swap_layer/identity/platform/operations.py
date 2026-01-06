from typing import Any, Dict, Optional
from .factory import get_identity_client
from .models import UserIdentity
from swap_layer.config import settings

class AuthenticationOperations:
    """
    Core Logic for Authentication.
    Stateless and Framework Agnostic.
    """
    
    def __init__(self, provider=None):
        self.provider = provider or get_identity_client()
        self.provider_name = getattr(settings, 'IDENTITY_PROVIDER', 'workos')

    def get_authorization_url(self, request: Any, redirect_uri: str, state: Optional[str] = None) -> str:
        return self.provider.get_authorization_url(request, redirect_uri, state)

    def exchange_code(self, request: Any, code: str) -> Dict[str, Any]:
        """
        Exchange code for user info. 
        Returns raw dict from provider, but normalized.
        """
        return self.provider.exchange_code_for_user(request, code)

    def create_identity_dto(self, user_id: str, provider_user_data: Dict[str, Any]) -> UserIdentity:
        """
        Helper to create a Pydantic DTO from provider data.
        """
        return UserIdentity(
            user_id=user_id,
            provider=self.provider_name,
            provider_user_id=provider_user_data.get('id') or provider_user_data.get('sub'),
            email=provider_user_data.get('email'),
            data=provider_user_data
        )

    def get_logout_url(self, request: Any, return_to: str) -> str:
        return self.provider.get_logout_url(request, return_to)
