"""
Test that factory functions use SwapLayerSettings instead of legacy Django settings.

This validates that issue #2 (Factory Functions Don't Use SwapLayerSettings) is fixed.
"""

from unittest.mock import patch

from swap_layer.settings import SwapLayerSettings


def test_billing_factory_uses_swaplayer_settings():
    """Test that billing factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(
        billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}}
    )

    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=mock_settings):
        with patch("swap_layer.billing.providers.stripe.stripe"):
            from swap_layer.billing.factory import get_payment_provider
            from swap_layer.billing.providers.stripe import StripePaymentProvider

            provider = get_payment_provider()
            assert isinstance(provider, StripePaymentProvider)


def test_email_factory_uses_swaplayer_settings():
    """Test that email factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(communications={"email": {"provider": "django"}})

    with patch(
        "swap_layer.communications.email.factory.get_swaplayer_settings", return_value=mock_settings
    ):
        from swap_layer.communications.email.factory import get_email_provider
        from swap_layer.communications.email.providers.django_email import DjangoEmailAdapter

        provider = get_email_provider()
        assert isinstance(provider, DjangoEmailAdapter)


def test_sms_factory_uses_swaplayer_settings():
    """Test that SMS factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(
        communications={
            "sms": {
                "provider": "twilio",
                "twilio": {
                    "account_sid": "AC123",
                    "auth_token": "test",
                    "from_number": "+15555551234",
                },
            }
        }
    )

    with patch(
        "swap_layer.communications.sms.factory.get_swaplayer_settings", return_value=mock_settings
    ):
        with patch("twilio.rest.Client"):
            from swap_layer.communications.sms.factory import get_sms_provider
            from swap_layer.communications.sms.providers.twilio_sms import TwilioSMSProvider

            provider = get_sms_provider()
            assert isinstance(provider, TwilioSMSProvider)


def test_storage_factory_uses_swaplayer_settings():
    """Test that storage factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(storage={"provider": "local"})

    with patch("swap_layer.storage.factory.get_swaplayer_settings", return_value=mock_settings):
        from swap_layer.storage.factory import get_storage_provider
        from swap_layer.storage.providers.local import LocalFileStorageProvider

        provider = get_storage_provider()
        assert isinstance(provider, LocalFileStorageProvider)


def test_identity_platform_factory_uses_swaplayer_settings():
    """Test that identity platform factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(
        identity={
            "provider": "workos",
            "workos_apps": {
                "default": {
                    "api_key": "sk_test",
                    "client_id": "client_test",
                    "cookie_password": "a" * 32,
                }
            },
        }
    )

    with patch(
        "swap_layer.identity.platform.factory.get_swaplayer_settings", return_value=mock_settings
    ):
        with patch("swap_layer.identity.platform.providers.workos.client.workos"):
            from swap_layer.identity.platform.factory import get_identity_client
            from swap_layer.identity.platform.providers.workos.client import WorkOSClient

            provider = get_identity_client()
            assert isinstance(provider, WorkOSClient)


def test_identity_verification_factory_uses_swaplayer_settings():
    """Test that identity verification factory reads from SwapLayerSettings."""
    mock_settings = SwapLayerSettings(
        verification={"provider": "stripe", "stripe_secret_key": "sk_test_123"}
    )

    with patch(
        "swap_layer.identity.verification.factory.get_swaplayer_settings",
        return_value=mock_settings,
    ):
        with patch("swap_layer.identity.verification.providers.stripe.stripe"):
            from swap_layer.identity.verification.factory import get_identity_verification_provider
            from swap_layer.identity.verification.providers.stripe import (
                StripeIdentityVerificationProvider,
            )

            provider = get_identity_verification_provider()
            assert isinstance(provider, StripeIdentityVerificationProvider)


def test_factories_fallback_to_legacy_settings():
    """Test that factories fall back to legacy Django settings for backward compatibility."""
    # Empty SwapLayerSettings - no modules configured
    mock_settings = SwapLayerSettings()

    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=mock_settings):
        # Factory should fallback to Django settings
        from django.conf import settings as django_settings

        # Mock Django settings
        with patch.object(django_settings, "PAYMENT_PROVIDER", "stripe"):
            with patch("swap_layer.billing.providers.stripe.stripe"):
                from swap_layer.billing.factory import get_payment_provider
                from swap_layer.billing.providers.stripe import StripePaymentProvider

                provider = get_payment_provider()
                assert isinstance(provider, StripePaymentProvider)
