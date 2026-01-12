from typing import Any
from urllib.parse import quote_plus, urlencode

from authlib.integrations.django_client import OAuth
from django.conf import settings

from ...adapter import AuthProviderAdapter


class Auth0Client(AuthProviderAdapter):
    def __init__(self, app_name="developer"):
        self.app_name = app_name
        self.config = settings.AUTH0_APPS.get(app_name)
        if not self.config:
            raise ValueError(
                f"Auth0 configuration for '{app_name}' not found in settings.AUTH0_APPS"
            )

        self.oauth = OAuth()
        self.oauth.register(
            app_name,
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            client_kwargs={
                "scope": "openid profile email",
            },
            server_metadata_url=f"https://{settings.AUTH0_DEVELOPER_DOMAIN}/.well-known/openid-configuration",
        )
        self.client = getattr(self.oauth, app_name)

    def get_authorization_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        rv = self.client.create_authorization_url(redirect_uri, state=state)
        return rv["url"]

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
        return f"https://{settings.AUTH0_DEVELOPER_DOMAIN}/v2/logout?" + urlencode(
            {
                "returnTo": return_to,
                "client_id": self.config["client_id"],
            },
            quote_via=quote_plus,
        )
