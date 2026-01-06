import os
import workos
from workos.user_management import UserManagementProviderType
from swap_layer.config import settings
from ...adapter import AuthProviderAdapter
from typing import Dict, Any, Optional

class WorkOSClient(AuthProviderAdapter):
    def __init__(self, app_name='default'):
        self.app_name = app_name
        self.config = settings.WORKOS_APPS.get(app_name)
        if not self.config:
            raise ValueError(f"WorkOS configuration for '{app_name}' not found in settings.WORKOS_APPS")
            
        # Configure the global WorkOS SDK
        # Note: This SDK relies on global state, so switching apps in the same process 
        # requires resetting these values. This is not thread-safe for concurrent multi-tenant usage.
        workos.api_key = self.config['api_key']
        workos.client_id = self.config['client_id']
        
        # The client is accessed via the global module instance
        self.client = workos.client

    def get_authorization_url(self, request, redirect_uri: str, state: Optional[str] = None) -> str:
        return self.client.user_management.get_authorization_url(
            provider=UserManagementProviderType.AuthKit,
            redirect_uri=redirect_uri,
            state=state
        )

    def exchange_code_for_user(self, request, code: str) -> Dict[str, Any]:
        # We use the 'authenticate_with_code' method which returns a user and a sealed session
        # We need to capture the sealed session if we want to support logout later
        
        response = self.client.user_management.authenticate_with_code(
            code=code,
            client_id=self.config['client_id'],
            session={
                "seal_session": True,
                "cookie_password": self.config['cookie_password']
            }
        )
        
        user = response.user
        
        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email_verified': user.email_verified,
            'raw_user': user.to_dict(),
            'sealed_session': response.sealed_session # Return this so we can store it
        }

    def get_logout_url(self, request, return_to: str) -> str:
        # Try to retrieve the sealed session from the Django session
        sealed_session = request.session.get('workos_sealed_session')
        
        if sealed_session:
            try:
                session = self.client.user_management.load_sealed_session(
                    sealed_session=sealed_session,
                    cookie_password=self.config['cookie_password'],
                )
                return session.get_logout_url()
            except Exception:
                # If session loading fails, fallback to just the return_to url
                pass
        
        return return_to
