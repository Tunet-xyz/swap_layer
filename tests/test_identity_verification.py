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

        # Create mock settings with unknown provider
        mock_settings = SwapLayerSettings(
            verification={"provider": "stripe", "stripe_secret_key": "sk_test_123"}
        )
        # Override provider to invalid value after creation
        mock_settings.verification.provider = "unknown"

        with patch(
            "swap_layer.identity.verification.factory.get_swaplayer_settings",
            return_value=mock_settings,
        ):
            with self.assertRaises(ValueError):
                get_identity_verification_provider()


class TestStripeProvider(unittest.TestCase):
    def setUp(self):
        self.provider = StripeIdentityVerificationProvider()
        self.mock_user = MagicMock()
        self.mock_user.id = 123
        self.mock_user.username = "testuser"
        self.mock_user.email = "test@example.com"

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.create"
    )
    def test_create_verification_session_success(self, mock_create):
        """Test successful verification session creation."""
        # Mock the Stripe API response
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.client_secret = "vs_123_secret"
        mock_session.status = "requires_input"
        mock_session.type = "document"
        mock_session.url = "https://verify.stripe.com/123"
        mock_session.created = 1234567890
        mock_create.return_value = mock_session

        result = self.provider.create_verification_session(
            user=self.mock_user,
            verification_type="document",
            options={"return_url": "https://example.com/callback"},
        )

        self.assertEqual(result["provider_session_id"], "vs_123")
        self.assertEqual(result["client_secret"], "vs_123_secret")
        self.assertEqual(result["status"], "requires_input")
        mock_create.assert_called_once()

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.create"
    )
    def test_create_session_with_error_handling(self, mock_create):
        """Test that Stripe errors are converted to custom exceptions."""
        import stripe

        error = stripe.error.InvalidRequestError(
            message="Invalid type", param="type", code="parameter_invalid_value"
        )
        mock_create.side_effect = error

        with self.assertRaises(IdentityVerificationValidationError):
            self.provider.create_verification_session(
                user=self.mock_user, verification_type="invalid"
            )

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.retrieve"
    )
    def test_get_verification_session_success(self, mock_retrieve):
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
        mock_retrieve.return_value = mock_session

        result = self.provider.get_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        self.assertEqual(result["status"], "verified")
        self.assertIn("verified_outputs", result)
        mock_retrieve.assert_called_once()

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.retrieve"
    )
    def test_get_session_not_found(self, mock_retrieve):
        """Test that session not found raises appropriate exception."""
        import stripe

        error = stripe.error.InvalidRequestError(
            message="No such verification session: vs_123", param="id", code="resource_missing"
        )
        mock_retrieve.side_effect = error

        with self.assertRaises(IdentityVerificationSessionNotFoundError):
            self.provider.get_verification_session("vs_123")

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.cancel"
    )
    def test_cancel_verification_session(self, mock_cancel):
        """Test canceling a verification session."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.status = "canceled"
        mock_cancel.return_value = mock_session

        result = self.provider.cancel_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        self.assertEqual(result["status"], "canceled")
        mock_cancel.assert_called_once_with("vs_123")

    def test_escape_hatch(self):
        """Test that the escape hatch returns the raw stripe module."""
        client = self.provider.get_vendor_client()
        import stripe

        self.assertEqual(client, stripe)

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.list"
    )
    def test_list_verification_sessions(self, mock_list):
        """Test listing verification sessions."""
        mock_session1 = MagicMock()
        mock_session1.id = "vs_1"
        mock_session1.status = "verified"
        mock_session1.created = 1234567890

        mock_session2 = MagicMock()
        mock_session2.id = "vs_2"
        mock_session2.status = "requires_input"
        mock_session2.created = 1234567891

        mock_result = MagicMock()
        mock_result.data = [mock_session1, mock_session2]
        mock_result.has_more = False
        mock_list.return_value = mock_result

        result = self.provider.list_verification_sessions(limit=10, status="verified")

        # The method returns the Stripe object directly, not a dict
        self.assertIsNotNone(result)
        mock_list.assert_called_once()

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.redact"
    )
    def test_redact_verification_session(self, mock_redact):
        """Test redacting a verification session."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.status = "verified"
        mock_redact.return_value = mock_session

        result = self.provider.redact_verification_session("vs_123")

        self.assertEqual(result["id"], "vs_123")
        mock_redact.assert_called_once_with("vs_123")

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationReport.retrieve"
    )
    def test_get_verification_report(self, mock_retrieve):
        """Test retrieving a verification report."""
        mock_report = MagicMock()
        mock_report.id = "vr_123"
        mock_report.type = "document"
        mock_report.document = MagicMock()
        mock_report.document.status = "verified"
        mock_report.document.first_name = "John"
        mock_report.document.last_name = "Doe"
        mock_report.document.dob = MagicMock()
        mock_report.document.dob.day = 15
        mock_report.document.dob.month = 6
        mock_report.document.dob.year = 1990
        mock_report.created = 1234567890
        mock_report.id_number = None
        mock_report.selfie = None
        mock_report.verification_session = "vs_123"
        mock_report.options = {}
        mock_retrieve.return_value = mock_report

        result = self.provider.get_verification_report("vr_123")

        self.assertEqual(result["id"], "vr_123")
        self.assertEqual(result["type"], "document")
        self.assertIn("document", result)
        mock_retrieve.assert_called_once_with("vr_123")

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.create"
    )
    def test_create_session_with_email_option(self, mock_create):
        """Test creating session with email in options."""
        mock_session = MagicMock()
        mock_session.id = "vs_123"
        mock_session.client_secret = "secret"
        mock_session.status = "requires_input"
        mock_session.type = "document"
        mock_session.url = "https://verify.stripe.com/123"
        mock_session.created = 1234567890
        mock_create.return_value = mock_session

        result = self.provider.create_verification_session(
            user=self.mock_user,
            verification_type="document",
            options={"email": "user@example.com", "return_url": "https://example.com"},
        )

        self.assertEqual(result["provider_session_id"], "vs_123")
        # Verify the create call included provided_details
        call_args = mock_create.call_args
        self.assertIn("provided_details", call_args[1])
        self.assertEqual(call_args[1]["provided_details"]["email"], "user@example.com")

    @patch(
        "swap_layer.identity.verification.providers.stripe.stripe.identity.VerificationSession.create"
    )
    def test_create_session_connection_error(self, mock_create):
        """Test handling of connection errors."""
        import stripe

        error = stripe.error.APIConnectionError("Network error")
        mock_create.side_effect = error

        from swap_layer.identity.verification.adapter import IdentityVerificationConnectionError

        with self.assertRaises(IdentityVerificationConnectionError):
            self.provider.create_verification_session(
                user=self.mock_user, verification_type="document"
            )


if __name__ == "__main__":
    unittest.main()
