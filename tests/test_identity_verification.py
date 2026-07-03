import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings

from swap_layer.identity.verification.adapter import (
    IdentityVerificationProviderAdapter,
    IdentityVerificationSessionNotFoundError,
    IdentityVerificationValidationError,
)
from swap_layer.identity.verification.factory import get_identity_verification_provider
from swap_layer.identity.verification.providers.stripe import StripeIdentityVerificationProvider


class TestIdentityVerificationFactory(unittest.TestCase):
    def test_get_provider_returns_stripe(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, "IDENTITY_VERIFICATION_PROVIDER", "stripe"):
            provider = get_identity_verification_provider()
            self.assertIsInstance(provider, StripeIdentityVerificationProvider)
            self.assertIsInstance(provider, IdentityVerificationProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        from swap_layer.settings import SwapLayerSettings

        mock_settings = SwapLayerSettings(
            verification={"provider": "stripe", "stripe_secret_key": "sk_test_123"}
        )
        mock_settings.verification.provider = "unknown"

        with patch(
            "swap_layer.identity.verification.factory.get_swaplayer_settings",
            return_value=mock_settings,
        ):
            with self.assertRaises(ValueError):
                get_identity_verification_provider()

    def test_factory_passes_swaplayer_stripe_secret_key(self):
        """Test that SwapLayerSettings identity Stripe key is used by the provider."""
        from swap_layer.settings import SwapLayerSettings

        mock_settings = SwapLayerSettings(
            verification={"provider": "stripe", "stripe_secret_key": "sk_test_identity"}
        )

        with patch(
            "swap_layer.identity.verification.factory.get_swaplayer_settings",
            return_value=mock_settings,
        ):
            provider = get_identity_verification_provider()

        self.assertEqual(provider.secret_key, "sk_test_identity")


class TestStripeProvider(unittest.TestCase):
    def setUp(self):
        self.provider = StripeIdentityVerificationProvider(secret_key="sk_test_identity")
        self.client = MagicMock()
        self.provider._client = self.client
        self.mock_user = MagicMock()
        self.mock_user.id = 123
        self.mock_user.username = "testuser"
        self.mock_user.email = "test@example.com"

    @property
    def verification_sessions(self):
        return self.client.v1.identity.verification_sessions

    @property
    def verification_reports(self):
        return self.client.v1.identity.verification_reports

    def _mock_session(self):
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.client_secret = "vs_123_secret"
        mock_session.status = "requires_input"
        mock_session.type = "document"
        mock_session.url = "https://verify.stripe.com/123"
        mock_session.created = 1234567890
        return mock_session

    def test_create_verification_session_success(self):
        """Test successful verification session creation."""
        self.verification_sessions.create.return_value = self._mock_session()

        result = self.provider.create_verification_session(
            user=self.mock_user,
            verification_type="document",
            options={"return_url": "https://example.com/callback"},
        )

        self.assertEqual(result["provider_session_id"], "vs_123")
        self.assertEqual(result["client_secret"], "vs_123_secret")
        self.assertEqual(result["status"], "requires_input")
        self.verification_sessions.create.assert_called_once()

    def test_create_session_with_error_handling(self):
        """Test that Stripe errors are converted to custom exceptions."""
        import stripe

        error = stripe.InvalidRequestError(
            message="Invalid type", param="type", code="parameter_invalid_value"
        )
        self.verification_sessions.create.side_effect = error

        with self.assertRaises(IdentityVerificationValidationError):
            self.provider.create_verification_session(
                user=self.mock_user, verification_type="invalid"
            )

    def test_get_verification_session_success(self):
        """Test successful retrieval of verification session."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.status = "verified"
        mock_session.type = "document"
        mock_session.created = 1234567890
        mock_session.metadata = {"user_id": "123"}
        mock_session.last_verification_report = "vr_123"
        mock_session.verified_outputs = {"first_name": "John", "last_name": "Doe"}
        mock_session.last_error = None
        self.verification_sessions.retrieve.return_value = mock_session

        result = self.provider.get_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        self.assertEqual(result["status"], "verified")
        self.assertIn("verified_outputs", result)
        self.verification_sessions.retrieve.assert_called_once_with(
            "vs_123", params={"expand": ["verified_outputs", "last_error"]}
        )

    def test_get_session_not_found(self):
        """Test that session not found raises appropriate exception."""
        import stripe

        error = stripe.InvalidRequestError(
            message="No such verification session: vs_123", param="id", code="resource_missing"
        )
        self.verification_sessions.retrieve.side_effect = error

        with self.assertRaises(IdentityVerificationSessionNotFoundError):
            self.provider.get_verification_session("vs_123")

    def test_cancel_verification_session(self):
        """Test canceling a verification session."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.status = "canceled"
        self.verification_sessions.cancel.return_value = mock_session

        result = self.provider.cancel_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        self.assertEqual(result["status"], "canceled")
        self.verification_sessions.cancel.assert_called_once_with("vs_123")

    def test_escape_hatch(self):
        """Test that the escape hatch returns the configured StripeClient."""
        self.assertIs(self.provider.get_vendor_client(), self.client)

    def test_list_verification_sessions(self):
        """Test listing verification sessions."""
        mock_result = MagicMock()
        mock_result.data = [MagicMock(id="vs_1"), MagicMock(id="vs_2")]
        mock_result.has_more = False
        self.verification_sessions.list.return_value = mock_result

        result = self.provider.list_verification_sessions(limit=10, status="verified")

        self.assertIsNotNone(result)
        self.verification_sessions.list.assert_called_once_with(
            params={"limit": 10, "status": "verified"}
        )

    def test_redact_verification_session(self):
        """Test redacting a verification session."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.status = "verified"
        self.verification_sessions.redact.return_value = mock_session

        result = self.provider.redact_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        self.verification_sessions.redact.assert_called_once_with("vs_123")

    def test_get_verification_report(self):
        """Test retrieving a verification report."""
        mock_report = MagicMock()
        mock_report.id = "vr_123"
        mock_report.type = "document"
        mock_report.document = MagicMock()
        mock_report.document.status = "verified"
        mock_report.created = 1234567890
        mock_report.id_number = None
        mock_report.selfie = None
        mock_report.verification_session = "vs_123"
        mock_report.options = {}
        self.verification_reports.retrieve.return_value = mock_report

        result = self.provider.get_verification_report("vr_123")

        self.assertEqual(result["id"], "vr_123")
        self.assertEqual(result["type"], "document")
        self.assertIn("document", result)
        self.verification_reports.retrieve.assert_called_once_with("vr_123")

    def test_create_session_with_email_option(self):
        """Test creating session with email in options."""
        self.verification_sessions.create.return_value = self._mock_session()

        result = self.provider.create_verification_session(
            user=self.mock_user,
            verification_type="document",
            options={"email": "user@example.com", "return_url": "https://example.com"},
        )

        self.assertEqual(result["provider_session_id"], "vs_123")
        call_kwargs = self.verification_sessions.create.call_args.kwargs
        self.assertIn("provided_details", call_kwargs["params"])
        self.assertEqual(call_kwargs["params"]["provided_details"]["email"], "user@example.com")

    def test_create_session_connection_error(self):
        """Test handling of connection errors."""
        import stripe

        self.verification_sessions.create.side_effect = stripe.APIConnectionError("Network error")

        from swap_layer.identity.verification.adapter import IdentityVerificationConnectionError

        with self.assertRaises(IdentityVerificationConnectionError):
            self.provider.create_verification_session(
                user=self.mock_user, verification_type="document"
            )


if __name__ == "__main__":
    unittest.main()
