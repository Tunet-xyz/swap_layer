from typing import Any
from urllib.parse import quote_plus, urlencode

from authlib.integrations.django_client import OAuth

from ..._config import auth0_app_config
from ...adapter import AuthProviderAdapter


class Auth0Client(AuthProviderAdapter):
    def __init__(self, app_name="developer"):
        self.app_name = app_name
        app, self.domain = auth0_app_config(app_name)
        self.config = app.model_dump()
        self.client_id = app.client_id

        self.oauth = OAuth()
        self.oauth.register(
            app_name,
            client_id=app.client_id,
            client_secret=app.client_secret,
            client_kwargs={
                "scope": "openid profile email",
            },
            server_metadata_url=f"https://{self.domain}/.well-known/openid-configuration",
        )
        self.client = getattr(self.oauth, app_name)

    def get_authorization_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        rv = self.client.create_authorization_url(redirect_uri, state=state)
        # Keep state, nonce and redirect URI in the session so the callback can verify them
        self.client.save_authorize_data(request, redirect_uri=redirect_uri, **rv)
        return str(rv["url"])

    def exchange_code_for_user(self, request, code: str) -> dict[str, Any]:
        # Authlib needs the request object to validate state
        token = self.client.authorize_access_token(request)
        user_info = token.get("userinfo")

        return {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "first_name": user_info.get("given_name", ""),
            "last_name": user_info.get("family_name", ""),
            "email_verified": user_info.get("email_verified", False),
            "raw_user": user_info,
            "sealed_session": None,  # Auth0 doesn't use sealed sessions in the same way
        }

    def get_logout_url(self, request, return_to: str) -> str:
        return f"https://{self.domain}/v2/logout?" + urlencode(
            {
                "returnTo": return_to,
                "client_id": self.client_id,
            },
            quote_via=quote_plus,
        )

    def clear_session(self, request) -> None:
        """
        Clear Auth0-specific session data.

        Auth0 uses Authlib's OAuth client which stores session data
        with specific keys. We clear those to prevent automatic re-authentication.

        Args:
            request: Django HTTP request containing session to clear
        """
        # Authlib stores OAuth state and token info in session
        # Clear any authlib-related session keys
        keys_to_remove = [
            key
            for key in request.session.keys()
            if key.startswith("_oauth_") or key.startswith("auth0_")
        ]
        for key in keys_to_remove:
            del request.session[key]
