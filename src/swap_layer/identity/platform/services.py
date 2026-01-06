"""
Django service layer for authentication operations.
"""

from typing import Any, Dict, Optional
from .operations import AuthenticationOperations
from .repository import PlatformRepository


class AuthenticationService:
    """
    High-level Django service for authentication operations.
    Handles OAuth/OIDC flows and persists identity mappings to Django models.
    """
    
    def __init__(self, operations: AuthenticationOperations = None):
        self.ops = operations or AuthenticationOperations()
        self.repository = PlatformRepository()

    def get_login_url(self, request: Any, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL."""
        return self.ops.get_authorization_url(request, redirect_uri, state)

    def complete_login(self, request: Any, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for user data.
        Returns normalized user data dict from the provider.
        
        Note: This method returns provider data but does not automatically
        create/login Django users. Handle user creation in your view:
        
            service = AuthenticationService()
            user_data = service.complete_login(request, code)
            user, created = User.objects.get_or_create(email=user_data['email'])
            service.link_identity(user.id, user_data)
            login(request, user)
        """
        return self.ops.exchange_code(request, code)

    def get_logout_url(self, request: Any, return_to: str) -> str:
        """Generate provider logout URL."""
        return self.ops.get_logout_url(request, return_to)

    def link_identity(self, user_id: str, provider_data: Dict[str, Any]) -> Any:
        """
        Link an authenticated provider user to a local Django user.
        Saves the identity mapping to the database.
        
        Args:
            user_id: Local Django user ID
            provider_data: User data from provider (from complete_login())
            
        Returns:
            Saved Django model instance
        """
        dto = self.ops.create_identity_dto(user_id, provider_data)
        return self.repository.save(dto)
