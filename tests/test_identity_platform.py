import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

from swap_layer.identity.platform.adapter import AuthProviderAdapter
from swap_layer.identity.platform.factory import get_identity_client

# Import WorkOSClient conditionally - skip tests if workos not installed
try:
    from swap_layer.identity.platform.providers.workos.client import WorkOSClient

    WORKOS_AVAILABLE = True
except ImportError:
    WORKOS_AVAILABLE = False
    WorkOSClient = None


class TestIdentityPlatformFactory(unittest.TestCase):
    @pytest.mark.skipif(not WORKOS_AVAILABLE, reason="workos package not installed")
    def test_get_identity_client_returns_workos(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, "IDENTITY_PROVIDER", "workos"):
            provider = get_identity_client()
            self.assertIsInstance(provider, WorkOSClient)
            self.assertIsInstance(provider, AuthProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        from unittest.mock import MagicMock

        from swap_layer.settings import SwapLayerSettings

        # Create a mock settings object that returns 'unknown' provider
        mock_settings = MagicMock(spec=SwapLayerSettings)
        mock_identity = MagicMock()
        mock_identity.provider = "unknown"
        mock_settings.identity = mock_identity

        with patch(
            "swap_layer.identity.platform.factory.get_swaplayer_settings",
            return_value=mock_settings,
        ):
            with self.assertRaises(ValueError):
                get_identity_client()

    @pytest.mark.skipif(not WORKOS_AVAILABLE, reason="workos package not installed")
    def test_factory_supports_app_name_parameter(self):
        """Test that factory accepts app_name parameter."""
        with patch.object(settings, "IDENTITY_PROVIDER", "workos"):
            provider = get_identity_client(app_name="custom_app")
            if WORKOS_AVAILABLE:
                self.assertIsInstance(provider, WorkOSClient)


@pytest.mark.skipif(not WORKOS_AVAILABLE, reason="workos package not installed")
class TestWorkOSClient(unittest.TestCase):
    def setUp(self):
        with patch("swap_layer.identity.platform.providers.workos.client.workos") as mock_workos:
            self.mock_workos_module = mock_workos
            self.mock_workos_module.api_key = None
            self.mock_workos_module.client_id = None
            self.provider = WorkOSClient(app_name="default")

        self.mock_request = MagicMock()

    def test_get_authorization_url(self):
        """Test generating authorization URL."""
        with (
            patch("swap_layer.identity.platform.providers.workos.client.workos") as mock_workos,
            patch(
                "swap_layer.identity.platform.providers.workos.client.UserManagementProviderType"
            ),
        ):
            mock_workos.client.user_management.get_authorization_url.return_value = (
                "https://workos.com/sso/authorize?client_id=..."
            )
            result = self.provider.get_authorization_url(
                request=self.mock_request,
                redirect_uri="https://example.com/callback",
                state="random_state",
            )

            self.assertIn("workos.com", result)
            mock_workos.client.user_management.get_authorization_url.assert_called_once()

    def test_exchange_code_for_user_success(self):
        """Test exchanging authorization code for user data."""
        mock_user = MagicMock()
        mock_user.id = "user_01ABC"
        mock_user.email = "user@example.com"
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.email_verified = True
        mock_user.to_dict.return_value = {
            "id": "user_01ABC",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "email_verified": True,
        }

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.sealed_session = "sealed_session_value"

        with patch(
            "swap_layer.identity.platform.providers.workos.client.workos.client"
        ) as mock_client:
            mock_client.user_management.authenticate_with_code.return_value = mock_response
            result = self.provider.exchange_code_for_user(
                request=self.mock_request, code="auth_code_123"
            )

            self.assertEqual(result["id"], "user_01ABC")
            self.assertEqual(result["email"], "user@example.com")
            self.assertEqual(result["first_name"], "John")
            self.assertEqual(result["last_name"], "Doe")

    def test_get_logout_url(self):
        """Test generating logout URL."""
        # Test without sealed session - should return fallback URL
        self.mock_request.session = {}
        result = self.provider.get_logout_url(
            request=self.mock_request, return_to="https://example.com/"
        )

        # Should return fallback URL when no sealed session exists
        self.assertEqual(result, "https://example.com/")

    def test_get_logout_url_with_invalid_session(self):
        """Test logout URL with invalid sealed session falls back gracefully."""
        # Add invalid sealed session to mock request
        self.mock_request.session = {"workos_sealed_session": "invalid_sealed_value"}

        result = self.provider.get_logout_url(
            request=self.mock_request, return_to="https://example.com/fallback"
        )

        # Should fallback to return_to when session loading fails
        self.assertEqual(result, "https://example.com/fallback")


class TestAuth0Client(unittest.TestCase):
    def setUp(self):
        from swap_layer.identity.platform.providers.auth0.client import Auth0Client

        with patch("swap_layer.identity.platform.providers.auth0.client.OAuth"):
            self.provider = Auth0Client(app_name="developer")

        self.mock_request = MagicMock()

    def test_get_authorization_url(self):
        """Test generating Auth0 authorization URL."""
        with patch.object(self.provider, "client") as mock_client:
            mock_client.create_authorization_url.return_value = {
                "url": "https://example.auth0.com/authorize?client_id=...",
                "state": "state_value",
            }

            result = self.provider.get_authorization_url(
                request=self.mock_request,
                redirect_uri="https://example.com/callback",
                state="random_state",
            )

            self.assertIn("auth0.com", result)

    def test_exchange_code_for_user_success(self):
        """Test exchanging code for user with Auth0."""
        with patch.object(self.provider, "client") as mock_client:
            mock_client.authorize_access_token.return_value = {
                "access_token": "token_123",
                "userinfo": {
                    "sub": "auth0|123",
                    "email": "user@example.com",
                    "email_verified": True,
                    "given_name": "Jane",
                    "family_name": "Smith",
                    "picture": "https://example.com/photo.jpg",
                },
            }

            result = self.provider.exchange_code_for_user(
                request=self.mock_request, code="auth_code_123"
            )

            self.assertEqual(result["id"], "auth0|123")
            self.assertEqual(result["email"], "user@example.com")
            self.assertEqual(result["first_name"], "Jane")
            self.assertEqual(result["last_name"], "Smith")
            self.assertTrue(result["email_verified"])

    def test_get_logout_url(self):
        """Test generating Auth0 logout URL."""
        result = self.provider.get_logout_url(
            request=self.mock_request, return_to="https://example.com/"
        )

        # Check that result contains auth0 domain and return_to parameter
        self.assertIn("auth0.com", result)
        self.assertIn("returnTo", result)
        self.assertIn("logout", result)


if __name__ == "__main__":
    unittest.main()
