"""
Test that SwapLayer can be imported without Django being configured.

This is critical for developer experience - the package should not require
Django settings to be configured just to import it.
"""


def test_import_main_package():
    """Test that swap_layer can be imported without Django configured."""
    import swap_layer

    assert swap_layer.__version__ == "0.2.3"


def test_import_get_provider():
    """Test that get_provider can be imported."""
    from swap_layer import get_provider

    assert callable(get_provider)


def test_import_all_factories():
    """Test that all factory functions can be imported."""
    from swap_layer import (
        get_email_provider,
        get_identity_client,
        get_identity_verification_provider,
        get_payment_provider,
        get_sms_provider,
        get_storage_provider,
    )

    assert callable(get_email_provider)
    assert callable(get_identity_client)
    assert callable(get_identity_verification_provider)
    assert callable(get_payment_provider)
    assert callable(get_sms_provider)
    assert callable(get_storage_provider)


def test_import_settings_module():
    """Test that settings module can be imported."""
    from swap_layer.settings import SwapLayerSettings

    # Can create empty settings
    settings = SwapLayerSettings()
    assert settings.billing is None


def test_import_exceptions():
    """Test that exceptions can be imported."""
    from swap_layer import (
        ConfigurationError,
        ProviderError,
        SwapLayerError,
        ValidationError,
    )

    assert issubclass(ConfigurationError, SwapLayerError)
    assert issubclass(ValidationError, SwapLayerError)
    assert issubclass(ProviderError, SwapLayerError)


def test_cannot_import_django_models_from_module():
    """Test that Django models are NOT imported at module level."""
    # This should succeed - models shouldn't be in __all__
    from swap_layer.identity import platform

    # Models should NOT be available directly
    assert not hasattr(platform, "UserIdentity")
    assert not hasattr(platform, "OAuthIdentityMixin")


def test_can_import_django_models_directly():
    """Test that Django models CAN be imported directly when needed.

    Models can be imported, but will fail when instantiated without Django config.
    This is the expected behavior - lazy loading allows imports without Django,
    but actual usage still requires Django to be configured.
    """
    # Import should succeed
    from swap_layer.identity.platform.models import UserIdentity

    # But trying to use the model class will fail without Django configured
    # This is expected and acceptable - models are only used in Django projects
    assert UserIdentity is not None
