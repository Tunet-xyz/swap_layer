from abc import ABC, abstractmethod
from typing import Any


class AuthProviderAdapter(ABC):
    """
    Abstract base class for Authentication Providers (WorkOS, Auth0, Supabase, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """

    @abstractmethod
    def get_authorization_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        """
        Generate the URL to redirect the user to for login.
        """
        pass

    @abstractmethod
    def exchange_code_for_user(self, request, code: str) -> dict[str, Any]:
        """
        Exchange the authorization code for user details.
        Returns a dictionary with normalized user data.
        """
        pass

    @abstractmethod
    def get_logout_url(self, request, return_to: str) -> str:
        """
        Generate the URL to redirect the user to for logout.
        """
        pass
