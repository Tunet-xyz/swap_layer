import unittest
from unittest.mock import MagicMock, patch, Mock
from django.conf import settings
from swap_layer.identity.platform.factory import get_identity_client
from swap_layer.identity.platform.adapter import AuthProviderAdapter
from swap_layer.identity.platform.providers.workos.client import WorkOSClient


class TestIdentityPlatformFactory(unittest.TestCase):
    def test_get_identity_client_returns_workos(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, 'IDENTITY_PROVIDER', 'workos'):
            provider = get_identity_client()
            self.assertIsInstance(provider, WorkOSClient)
            self.assertIsInstance(provider, AuthProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        with patch.object(settings, 'IDENTITY_PROVIDER', 'unknown'):
            with self.assertRaises(ValueError):
                get_identity_client()

    def test_factory_supports_app_name_parameter(self):
        """Test that factory accepts app_name parameter."""
        with patch.object(settings, 'IDENTITY_PROVIDER', 'workos'):
            provider = get_identity_client(app_name='custom_app')
            self.assertIsInstance(provider, WorkOSClient)


class TestWorkOSClient(unittest.TestCase):
    def setUp(self):
        with patch('swap_layer.identity.platform.providers.workos.client.workos') as mock_workos:
            self.mock_workos_module = mock_workos
            self.mock_workos_module.api_key = None
            self.mock_workos_module.client_id = None
            self.provider = WorkOSClient(app_name='default')
        
        self.mock_request = MagicMock()

    @patch('swap_layer.identity.platform.providers.workos.client.workos.client.sso.get_authorization_url')
    def test_get_authorization_url(self, mock_get_url):
        """Test generating authorization URL."""
        mock_get_url.return_value = "https://workos.com/sso/authorize?client_id=..."
        
        result = self.provider.get_authorization_url(
            request=self.mock_request,
            redirect_uri="https://example.com/callback",
            state="random_state"
        )
        
        self.assertIn("workos.com", result)
        mock_get_url.assert_called_once()

    @patch('swap_layer.identity.platform.providers.workos.client.workos.client.sso.get_profile_and_token')
    def test_exchange_code_for_user_success(self, mock_get_profile):
        """Test exchanging authorization code for user data."""
        mock_profile = MagicMock()
        mock_profile.id = "user_01ABC"
        mock_profile.email = "user@example.com"
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.raw_attributes = {
            'email_verified': True,
            'picture': 'https://example.com/photo.jpg'
        }
        
        mock_get_profile.return_value = {'profile': mock_profile}
        
        result = self.provider.exchange_code_for_user(
            request=self.mock_request,
            code="auth_code_123"
        )
        
        self.assertEqual(result['id'], "user_01ABC")
        self.assertEqual(result['email'], "user@example.com")
        self.assertEqual(result['first_name'], "John")
        self.assertEqual(result['last_name'], "Doe")
        self.assertIn('profile', result)

    def test_get_logout_url(self):
        """Test generating logout URL."""
        result = self.provider.get_logout_url(
            request=self.mock_request,
            return_to="https://example.com/"
        )
        
        # WorkOS may or may not have specific logout URL
        # This test verifies the method exists and returns a string
        self.assertIsInstance(result, str)


class TestAuth0Client(unittest.TestCase):
    def setUp(self):
        from swap_layer.identity.platform.providers.auth0.client import Auth0Client
        with patch('swap_layer.identity.platform.providers.auth0.client.OAuth2Session'):
            self.provider = Auth0Client(app_name='developer')
        
        self.mock_request = MagicMock()

    def test_get_authorization_url(self):
        """Test generating Auth0 authorization URL."""
        with patch.object(self.provider, 'oauth') as mock_oauth:
            mock_oauth.create_authorization_url.return_value = (
                "https://example.auth0.com/authorize?client_id=...",
                "state_value"
            )
            
            result = self.provider.get_authorization_url(
                request=self.mock_request,
                redirect_uri="https://example.com/callback",
                state="random_state"
            )
            
            self.assertIn("auth0.com", result)

    def test_exchange_code_for_user_success(self):
        """Test exchanging code for user with Auth0."""
        with patch.object(self.provider, 'oauth') as mock_oauth:
            mock_oauth.fetch_token.return_value = {
                'access_token': 'token_123'
            }
            mock_oauth.get.return_value.json.return_value = {
                'sub': 'auth0|123',
                'email': 'user@example.com',
                'email_verified': True,
                'given_name': 'Jane',
                'family_name': 'Smith',
                'picture': 'https://example.com/photo.jpg'
            }
            
            result = self.provider.exchange_code_for_user(
                request=self.mock_request,
                code="auth_code_123"
            )
            
            self.assertEqual(result['id'], 'auth0|123')
            self.assertEqual(result['email'], 'user@example.com')
            self.assertEqual(result['first_name'], 'Jane')
            self.assertEqual(result['last_name'], 'Smith')
            self.assertTrue(result['email_verified'])

    def test_get_logout_url(self):
        """Test generating Auth0 logout URL."""
        result = self.provider.get_logout_url(
            request=self.mock_request,
            return_to="https://example.com/"
        )
        
        self.assertIn("example.auth0.com", result)
        self.assertIn("logout", result)


if __name__ == '__main__':
    unittest.main()
