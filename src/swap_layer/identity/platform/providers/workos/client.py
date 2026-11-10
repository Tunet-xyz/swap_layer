"""
WorkOS Authentication Client.

Thread-safe implementation using WorkOS SDK v6+/v7 client pattern.
Each instance maintains its own WorkOSClient with dedicated credentials.
"""

import secrets
import time
from typing import Any

from workos import WorkOSClient as WorkOSSDKClient
from workos.session import Session

from ...adapter import AuthProviderAdapter, OAuthStateError

# Pending sign-in states, kept in the Django session until their callback.
STATE_SESSION_KEY = "swaplayer_workos_oauth_states"
STATE_LIFETIME_SECONDS = 600
MAX_PENDING_STATES = 10


def _seal_auth_response(response: Any, user: Any, cookie_password: str) -> str:
    """Seal a WorkOS auth response across SDK versions."""
    sealed_session = getattr(response, "sealed_session", None)
    if sealed_session:
        return str(sealed_session)

    try:
        from workos.session import seal_session_from_auth_response
    except ImportError:
        seal_session_from_auth_response = None  # type: ignore[assignment]

    user_data = user.to_dict()
    impersonator = response.impersonator.to_dict() if response.impersonator else None

    if seal_session_from_auth_response is not None:
        return seal_session_from_auth_response(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            user=user_data,
            impersonator=impersonator,
            cookie_password=cookie_password,
        )

    return Session.seal_data(
        {
            "access_token": response.access_token,
            "refresh_token": response.refresh_token,
            "user": user_data,
            "impersonator": impersonator,
        },
        cookie_password,
    )


class WorkOSClient(AuthProviderAdapter):
    """
    WorkOS authentication client using SDK v6+/v7 pattern.

    Each instance creates its own WorkOSClient with dedicated credentials,
    making it thread-safe without requiring global state manipulation.
    """

    def __init__(self, app_name: str = "default"):
        """
        Initialize WorkOS client with app-specific configuration.

        Args:
            app_name: Key in SWAPLAYER.identity.workos_apps (or legacy settings.WORKOS_APPS)

        Raises:
            ValueError: If app_name is not configured
        """
        from swap_layer.identity.platform._config import workos_app_config

        self.app_name = app_name
        # Validated by WorkOSAppConfig whichever setting supplies it
        app = workos_app_config(app_name)
        self.config = app.model_dump()

        # Store credentials
        self._api_key = app.api_key
        self._client_id = app.client_id
        self._cookie_password = app.cookie_password

        # Create dedicated WorkOS client instance (v6+/v7 pattern)
        self._workos_client = WorkOSSDKClient(
            api_key=self._api_key,
            client_id=self._client_id,
        )

    @property
    def client(self):
        """Get the WorkOS SDK client instance."""
        return self._workos_client

    def get_authorization_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        """
        Generate OAuth authorization URL for WorkOS AuthKit.

        The state (a random one unless you pass your own) is stored in the
        Django session; exchange_code_for_user accepts only a callback that
        returns it, once, within 10 minutes.

        Args:
            request: Django HTTP request whose session records the state
            redirect_uri: URL to redirect after authentication
            state: Optional state value; one is generated when omitted

        Returns:
            Authorization URL to redirect the user to
        """
        state = state or secrets.token_urlsafe(32)
        now = time.time()
        pending = {
            key: expiry
            for key, expiry in dict(request.session.get(STATE_SESSION_KEY) or {}).items()
            if isinstance(expiry, (int, float)) and expiry > now
        }
        pending[state] = now + STATE_LIFETIME_SECONDS
        newest = sorted(pending.items(), key=lambda item: item[1])[-MAX_PENDING_STATES:]
        request.session[STATE_SESSION_KEY] = dict(newest)
        return self._workos_client.user_management.get_authorization_url(
            provider="authkit", redirect_uri=redirect_uri, state=state
        )

    @staticmethod
    def _consume_state(request) -> None:
        """Accept the callback only if it returns a pending, unexpired state."""
        params = request.GET if getattr(request, "method", "GET") == "GET" else request.POST
        state = params.get("state")
        pending = dict(request.session.get(STATE_SESSION_KEY) or {})
        expiry = pending.pop(state, None) if isinstance(state, str) and state else None
        request.session[STATE_SESSION_KEY] = pending
        if not isinstance(expiry, (int, float)) or expiry < time.time():
            raise OAuthStateError(
                "The sign-in state is missing, expired, or was not issued to this session."
            )

    def exchange_code_for_user(self, request, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for user data.

        In v6+/v7, authenticate_with_code no longer accepts session=.
        Sealed sessions are created explicitly after authentication.

        Args:
            request: Django HTTP callback request; its state must match the session
            code: Authorization code from OAuth callback

        Returns:
            Dict containing normalized user data and sealed session

        Raises:
            OAuthStateError: If the callback's state was not issued to this session
        """
        self._consume_state(request)
        response = self._workos_client.user_management.authenticate_with_code(code=code)

        user = response.user

        sealed_session = _seal_auth_response(response, user, self._cookie_password)

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email_verified": user.email_verified,
            "raw_user": user.to_dict(),
            "sealed_session": sealed_session,
        }

    def get_logout_url(self, request, return_to: str) -> str:
        """
        Generate logout URL for WorkOS session.

        Args:
            request: Django HTTP request containing session
            return_to: URL to redirect after logout

        Returns:
            Logout URL or return_to if session not found
        """
        sealed_session = request.session.get("workos_sealed_session")

        if sealed_session:
            try:
                session = self._workos_client.user_management.load_sealed_session(
                    session_data=sealed_session,
                    cookie_password=self._cookie_password,
                )
                return session.get_logout_url()
            except Exception:
                # If session loading fails, fallback to return_to url
                return return_to

        return return_to

    def clear_session(self, request) -> None:
        """
        Clear WorkOS-specific session data.

        Removes the sealed session from Django's session storage to ensure
        the user is fully logged out and won't be automatically re-authenticated.

        Args:
            request: Django HTTP request containing session to clear
        """
        # Remove WorkOS sealed session and pending sign-in states if they exist
        for key in ("workos_sealed_session", STATE_SESSION_KEY):
            if key in request.session:
                del request.session[key]
