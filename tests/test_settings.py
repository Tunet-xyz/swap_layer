"""
Tests for SwapLayer settings management system.
"""

import pytest
from pydantic import ValidationError

from swap_layer.exceptions import (
    ModuleNotConfiguredError,
    ProviderConfigMismatchError,
    StripeKeyError,
    TwilioConfigError,
)
from swap_layer.settings import (
    BillingConfig,
    CommunicationsConfig,
    SMSProviderConfig,
    StripeConfig,
    SwapLayerSettings,
    TwilioConfig,
    validate_swaplayer_config,
)


class TestStripeConfig:
    def test_valid_stripe_config(self):
        """Test valid Stripe configuration."""
        config = StripeConfig(
            secret_key="sk_test_123",
            publishable_key="pk_test_123",
        )
        assert config.secret_key == "sk_test_123"
        assert config.publishable_key == "pk_test_123"

    def test_stripe_secret_key_validation(self):
        """Test that secret key must start with sk_."""
        with pytest.raises(StripeKeyError):
            StripeConfig(secret_key="pk_test_123")


class TestTwilioConfig:
    def test_valid_twilio_config(self):
        """Test valid Twilio configuration."""
        config = TwilioConfig(
            account_sid="AC123",
            auth_token="test_token",
            from_number="+15555551234",
        )
        assert config.account_sid == "AC123"

    def test_phone_number_validation(self):
        """Test that phone number must be E.164 format."""
        with pytest.raises(TwilioConfigError):
            TwilioConfig(
                account_sid="AC123",
                auth_token="token",
                from_number="5555551234",  # Missing +
            )

    def test_account_sid_validation(self):
        """Test that Account SID must start with AC."""
        with pytest.raises(TwilioConfigError):
            TwilioConfig(
                account_sid="XX123",
                auth_token="token",
                from_number="+15555551234",
            )


class TestBillingConfig:
    def test_stripe_config_required_when_provider_is_stripe(self):
        """Test that Stripe config is required when using Stripe provider."""
        with pytest.raises(ProviderConfigMismatchError):
            BillingConfig(provider="stripe")

    def test_valid_billing_config(self):
        """Test valid billing configuration."""
        config = BillingConfig(provider="stripe", stripe=StripeConfig(secret_key="sk_test_123"))
        assert config.provider == "stripe"
        assert config.stripe.secret_key == "sk_test_123"


class TestCommunicationsConfig:
    def test_twilio_config_required_when_provider_is_twilio(self):
        """Test that Twilio config is required."""
        with pytest.raises(ProviderConfigMismatchError):
            SMSProviderConfig(provider="twilio")

    def test_valid_sms_config(self):
        """Test valid SMS configuration."""
        config = SMSProviderConfig(
            provider="twilio",
            twilio=TwilioConfig(
                account_sid="AC123",
                auth_token="token",
                from_number="+15555551234",
            ),
        )
        assert config.provider == "twilio"

    def test_valid_communications_config(self):
        """Test valid communications configuration with email and SMS."""
        config = CommunicationsConfig(
            email={"provider": "django"},
            sms={
                "provider": "twilio",
                "twilio": {
                    "account_sid": "AC123",
                    "auth_token": "token",
                    "from_number": "+15555551234",
                },
            },
        )
        assert config.email.provider == "django"
        assert config.sms.provider == "twilio"


class TestSwapLayerSettings:
    def test_minimal_config(self):
        """Test minimal configuration."""
        settings = SwapLayerSettings()
        assert settings.billing is None
        assert settings.communications is None
        assert settings.debug is False

    def test_full_config(self):
        """Test full configuration."""
        settings = SwapLayerSettings(
            billing=BillingConfig(provider="stripe", stripe=StripeConfig(secret_key="sk_test_123")),
            communications=CommunicationsConfig(
                email={"provider": "django"},
                sms={
                    "provider": "twilio",
                    "twilio": {
                        "account_sid": "AC123",
                        "auth_token": "token",
                        "from_number": "+15555551234",
                    },
                },
            ),
            debug=True,
        )
        assert settings.billing.provider == "stripe"
        assert settings.communications.email.provider == "django"
        assert settings.communications.sms.provider == "twilio"
        assert settings.debug is True

    def test_from_dict(self):
        """Test creating settings from dictionary."""
        settings = SwapLayerSettings(
            billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}}
        )
        assert settings.billing.provider == "stripe"
        assert settings.billing.stripe.secret_key == "sk_test_123"

    def test_get_status(self):
        """Test getting configuration status."""
        settings = SwapLayerSettings(
            billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}},
            communications={"email": {"provider": "django"}},
        )
        status = settings.get_status()
        assert "billing" in status
        assert status["billing"].startswith("configured")
        assert "communications" in status
        assert status["communications"].startswith("configured")

    def test_validate_module(self):
        """Test module validation."""
        settings = SwapLayerSettings(
            billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}}
        )

        # Should not raise for configured module
        settings.validate_module("billing")

        # Should raise for unconfigured module
        with pytest.raises(ModuleNotConfiguredError):
            settings.validate_module("communications")

    def test_repr(self):
        """Test string representation."""
        settings = SwapLayerSettings(
            billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}}
        )
        repr_str = repr(settings)
        assert "SwapLayerSettings" in repr_str
        assert "billing" in repr_str

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed (prevents typos)."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SwapLayerSettings(
                payment={"provider": "stripe"}  # Typo: should be 'billing'
            )


class TestEnvironmentVariables:
    def test_from_env_billing(self, monkeypatch):
        """Test loading billing config from environment."""
        monkeypatch.setenv("SWAPLAYER_BILLING_PROVIDER", "stripe")
        monkeypatch.setenv("SWAPLAYER_BILLING_STRIPE_SECRET_KEY", "sk_test_123")

        settings = SwapLayerSettings.from_env()
        assert settings.billing.provider == "stripe"
        assert settings.billing.stripe.secret_key == "sk_test_123"

    def test_from_env_communications_sms(self, monkeypatch):
        """Test loading SMS config from environment."""
        monkeypatch.setenv("SWAPLAYER_COMMUNICATIONS_SMS_PROVIDER", "twilio")
        monkeypatch.setenv("SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_AUTH_TOKEN", "token")
        monkeypatch.setenv("SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_FROM_NUMBER", "+15555551234")

        settings = SwapLayerSettings.from_env()
        assert settings.communications.sms.provider == "twilio"
        assert settings.communications.sms.twilio.account_sid == "AC123"

    def test_from_env_custom_prefix(self, monkeypatch):
        """Test loading with custom prefix."""
        monkeypatch.setenv("MYAPP_BILLING_PROVIDER", "stripe")
        monkeypatch.setenv("MYAPP_BILLING_STRIPE_SECRET_KEY", "sk_test_123")

        settings = SwapLayerSettings.from_env(prefix="MYAPP_")
        assert settings.billing.provider == "stripe"


class TestLegacyCompatibility:
    def test_from_legacy_django_settings(self):
        """Test loading from legacy Django settings."""

        # The conftest.py already sets up legacy settings
        # Just verify that from_django can read them
        swaplayer_settings = SwapLayerSettings.from_django()

        # Verify we got valid settings (exact values depend on conftest.py)
        assert swaplayer_settings.billing is not None
        assert swaplayer_settings.billing.provider == "stripe"
        assert swaplayer_settings.communications is not None
        assert swaplayer_settings.communications.email is not None


class TestValidation:
    def test_validate_swaplayer_config_valid(self, monkeypatch):
        """Test validation with valid config."""
        from django.conf import settings as django_settings

        # Set up a valid SWAPLAYER config
        test_config = SwapLayerSettings(
            billing={"provider": "stripe", "stripe": {"secret_key": "sk_test_123"}}
        )
        monkeypatch.setattr(django_settings, "SWAPLAYER", test_config, raising=False)

        result = validate_swaplayer_config()
        assert result["valid"] is True
        assert "modules" in result

    def test_validate_swaplayer_config_without_swaplayer_setting(self, monkeypatch):
        """Test validation without SWAPLAYER setting falls back to legacy settings."""
        from django.conf import settings as django_settings

        # Ensure SWAPLAYER doesn't exist (use legacy settings from conftest)
        if hasattr(django_settings, "SWAPLAYER"):
            monkeypatch.delattr(django_settings, "SWAPLAYER", raising=False)

        result = validate_swaplayer_config()
        # Should still be valid (uses legacy settings from conftest)
        assert result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
