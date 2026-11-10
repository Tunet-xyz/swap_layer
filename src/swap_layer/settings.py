"""
SwapLayer Settings Management

Provides a structured, validated, and developer-friendly way to manage
SwapLayer configuration across all modules.

Usage:
    # In any Python application
    from swap_layer.settings import SwapLayerSettings, configure

    configure(SwapLayerSettings(
        billing={
            'provider': 'stripe',
            'stripe': {
                'secret_key': os.environ['STRIPE_SECRET_KEY'],
            }
        },
    ))

    # Or, in your Django settings.py
    from swap_layer.settings import SwapLayerSettings

    SWAPLAYER = SwapLayerSettings(
        billing={
            'provider': 'stripe',
            'stripe': {
                'secret_key': os.environ['STRIPE_SECRET_KEY'],
                'publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY'),
            }
        },
        communications={
            'email': {'provider': 'django'},
        },
        # ... other modules
    )

    # Or use environment variables with SWAPLAYER_ prefix
    SWAPLAYER = SwapLayerSettings.from_env()
"""

import base64
import binascii
import os
import typing
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from .exceptions import (
    ConfigurationError,
    ErrorContext,
    ProviderConfigMismatchError,
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
    format_startup_validation_errors,
)

_settings_cache: "SwapLayerSettings | None" = None

# ============================================================================
# Module Configuration Classes
# ============================================================================


class _ConfigModel(BaseModel):
    """
    Base for every settings model.

    Unknown keys are rejected so a misspelt setting fails validation instead of
    being dropped, and input values (credentials) are kept out of error text.
    """

    model_config = {"hide_input_in_errors": True, "extra": "forbid"}


class StripeConfig(_ConfigModel):
    """Stripe payment provider configuration."""

    secret_key: str = Field(..., description="Stripe secret key (required)")
    publishable_key: str | None = Field(None, description="Stripe publishable key (optional)")
    webhook_secret: str | None = Field(None, description="Stripe webhook signing secret")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v.startswith("sk_"):
            raise StripeKeyError("secret key", v)
        return v


class PayPalConfig(_ConfigModel):
    """PayPal payment provider configuration."""

    client_id: str = Field(..., description="PayPal REST app client ID")
    client_secret: str = Field(..., description="PayPal REST app client secret")
    webhook_id: str | None = Field(None, description="PayPal webhook ID for signature verification")
    sandbox: bool = Field(True, description="Use the PayPal sandbox API")


class SquareConfig(_ConfigModel):
    """Square payment provider configuration."""

    access_token: str = Field(..., description="Square access token")
    location_id: str = Field(..., description="Square location ID")
    webhook_signature_key: str | None = Field(None, description="Square webhook signature key")
    webhook_notification_url: str | None = Field(
        None, description="Square webhook notification URL"
    )
    sandbox: bool = Field(True, description="Use the Square sandbox API")
    api_version: str = Field("2026-05-20", description="Square API version header")


class TwilioConfig(_ConfigModel):
    """Twilio SMS provider configuration."""

    account_sid: str = Field(..., description="Twilio Account SID")
    auth_token: str = Field(..., description="Twilio Auth Token")
    from_number: str = Field(..., description="Twilio phone number (E.164 format)")

    @field_validator("from_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v.startswith("+"):
            raise TwilioConfigError.invalid_phone_number(v)
        return v

    @field_validator("account_sid")
    @classmethod
    def validate_account_sid(cls, v: str) -> str:
        if not v.startswith("AC"):
            raise TwilioConfigError.invalid_account_sid(v)
        return v


class SNSConfig(_ConfigModel):
    """AWS SNS SMS provider configuration."""

    aws_access_key_id: str | None = Field(
        None, description="AWS Access Key ID (optional if using IAM)"
    )
    aws_secret_access_key: str | None = Field(None, description="AWS Secret Access Key")
    region_name: str = Field("us-east-1", description="AWS region")
    sender_id: str | None = Field(None, description="SMS Sender ID")


class BillingConfig(_ConfigModel):
    """Billing module configuration."""

    provider: Literal["stripe", "paypal", "square"] = Field(
        "stripe", description="Payment provider to use"
    )
    stripe: StripeConfig | None = Field(None, description="Stripe configuration")
    paypal: PayPalConfig | None = Field(None, description="PayPal configuration")
    square: SquareConfig | None = Field(None, description="Square configuration")

    @model_validator(mode="after")
    def validate_provider_config(self):
        if self.provider == "stripe" and not self.stripe:
            raise ProviderConfigMismatchError("billing", "stripe", "stripe")
        if self.provider == "paypal" and not self.paypal:
            raise ProviderConfigMismatchError("billing", "paypal", "paypal")
        if self.provider == "square" and not self.square:
            raise ProviderConfigMismatchError("billing", "square", "square")
        return self


class EmailProviderConfig(_ConfigModel):
    """Email provider configuration."""

    provider: Literal["django", "smtp"] = Field("django", description="Email provider to use")
    # Django/Anymail uses Django's EMAIL_BACKEND and ANYMAIL settings
    # SMTP uses Django's EMAIL_HOST, EMAIL_PORT, etc.


class SMSProviderConfig(_ConfigModel):
    """SMS provider configuration."""

    provider: Literal["twilio", "sns"] = Field("twilio", description="SMS provider to use")
    twilio: TwilioConfig | None = Field(None, description="Twilio configuration")
    sns: SNSConfig | None = Field(None, description="AWS SNS configuration")

    @model_validator(mode="after")
    def validate_provider_config(self):
        if self.provider == "twilio" and not self.twilio:
            raise ProviderConfigMismatchError("communications.sms", "twilio", "twilio")
        if self.provider == "sns" and not self.sns:
            raise ProviderConfigMismatchError("communications.sms", "sns", "sns")
        return self


class CommunicationsConfig(_ConfigModel):
    """Communications module configuration (email and SMS)."""

    email: EmailProviderConfig | None = Field(None, description="Email configuration")
    sms: SMSProviderConfig | None = Field(None, description="SMS configuration")


class StorageConfig(_ConfigModel):
    """Storage module configuration."""

    provider: Literal["local", "django", "gcs"] = Field("local", description="Storage provider to use")
    media_root: str | None = Field(None, description="Local storage root directory")
    media_url: str | None = Field("/media/", description="Media URL prefix")
    bucket_name: str | None = None
    credentials_path: str | None = None
    project_id: str | None = None
    location: str = "europe-west1"
    storage_class: str = "STANDARD"
    # Django-storages uses DEFAULT_FILE_STORAGE and storage backend settings

    @model_validator(mode="after")
    def validate_gcs_bucket(self):
        if self.provider == "gcs" and not self.bucket_name:
            raise ValueError("GCS storage requires bucket_name")
        return self


def _is_fernet_key(value: str) -> bool:
    """True when ``value`` is a Fernet key: 32 url-safe base64-encoded bytes."""
    try:
        return len(base64.urlsafe_b64decode(value.encode("ascii"))) == 32
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return False


class WorkOSAppConfig(_ConfigModel):
    """WorkOS application configuration."""

    api_key: str = Field(..., description="WorkOS API key")
    client_id: str = Field(..., description="WorkOS client ID")
    cookie_password: str = Field(
        ..., description="Fernet key that seals WorkOS sessions (32 url-safe base64-encoded bytes)"
    )

    @field_validator("cookie_password")
    @classmethod
    def validate_cookie_password(cls, v: str) -> str:
        # The WorkOS SDK seals sessions with Fernet, which accepts only such keys.
        if not _is_fernet_key(v):
            raise WorkOSConfigError.invalid_cookie_password(len(v))
        return v


class Auth0AppConfig(_ConfigModel):
    """Auth0 application configuration."""

    client_id: str = Field(..., description="Auth0 client ID")
    client_secret: str = Field(..., description="Auth0 client secret")
    management_client_id: str | None = Field(
        None, description="Machine-to-machine client ID for the Management API (optional)"
    )
    management_client_secret: str | None = Field(
        None, description="Machine-to-machine client secret for the Management API (optional)"
    )


class IdentityPlatformConfig(_ConfigModel):
    """Identity/OAuth module configuration."""

    provider: Literal["workos", "auth0"] = Field("workos", description="Identity provider to use")
    workos_apps: dict[str, WorkOSAppConfig] | None = Field(
        None, description="WorkOS app configurations"
    )
    auth0_apps: dict[str, Auth0AppConfig] | None = Field(
        None, description="Auth0 app configurations"
    )
    auth0_domain: str | None = Field(None, description="Auth0 domain (required for Auth0)")

    @model_validator(mode="after")
    def validate_provider_config(self):
        if self.provider == "workos" and not self.workos_apps:
            raise ProviderConfigMismatchError("identity", "workos", "workos_apps")
        if self.provider == "auth0":
            if not self.auth0_apps:
                raise ProviderConfigMismatchError("identity", "auth0", "auth0_apps")
            if not self.auth0_domain:
                raise ProviderConfigMismatchError("identity", "auth0", "auth0_domain")
        return self


class IdentityVerificationConfig(_ConfigModel):
    """Identity verification module configuration."""

    provider: Literal["stripe"] = Field("stripe", description="Verification provider to use")
    stripe_secret_key: str | None = Field(
        None, description="Stripe secret key for identity verification"
    )
    stripe_webhook_secret: str | None = Field(
        None, description="Stripe signing secret for Identity webhooks (whsec_...)"
    )

    @model_validator(mode="after")
    def validate_provider_config(self):
        if self.provider == "stripe" and not self.stripe_secret_key:
            raise ProviderConfigMismatchError("verification", "stripe", "stripe_secret_key")
        return self


def legacy_app_config(model: type[BaseModel], raw: Any) -> Any:
    """
    Keep only ``model``'s fields from a legacy Django app dict.

    WORKOS_APPS and AUTH0_APPS entries may hold the application's own keys
    too; SWAPLAYER settings, by contrast, reject unknown keys.
    """
    if isinstance(raw, dict):
        return {key: value for key, value in raw.items() if key in model.model_fields}
    return raw


def _legacy_apps(model: type[BaseModel], apps: Any) -> Any:
    if isinstance(apps, dict):
        return {name: legacy_app_config(model, app) for name, app in apps.items()}
    return apps


def _nested_model(annotation: Any) -> tuple[str | None, type[BaseModel] | None]:
    """Classify a field type as a nested model, a mapping of models, or a scalar."""
    for candidate in (annotation, *typing.get_args(annotation)):
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return "model", candidate
        if typing.get_origin(candidate) is dict:
            args = typing.get_args(candidate)
            if len(args) == 2 and isinstance(args[1], type) and issubclass(args[1], BaseModel):
                return "mapping", args[1]
    return None, None


def _env_path(model: type[BaseModel], parts: list[str]) -> list[str] | None:
    """
    Map lower-case, underscore-separated name parts onto a settings field path.

    Longer field names win, so ``raise_on_error`` is one field rather than three
    nested ones. Mapping fields (``workos_apps``, ``auth0_apps``) take the next
    part(s) as the app name. Returns None when the parts match no field.
    """
    fields = model.model_fields
    for length in range(len(parts), 0, -1):
        name = "_".join(parts[:length])
        if name not in fields:
            continue
        rest = parts[length:]
        if not rest:
            return [name]
        kind, nested = _nested_model(fields[name].annotation)
        if kind == "model" and nested is not None:
            tail = _env_path(nested, rest)
            if tail is not None:
                return [name, *tail]
        elif kind == "mapping" and nested is not None:
            for split in range(1, len(rest)):
                tail = _env_path(nested, rest[split:])
                if tail is not None:
                    return [name, "_".join(rest[:split]), *tail]
    return None


# ============================================================================
# Main Settings Class
# ============================================================================


class SwapLayerSettings(_ConfigModel):
    """
    SwapLayer unified settings configuration.

    Provides structured, validated configuration for all SwapLayer modules
    with helpful error messages and type safety.

    Example:
        # settings.py
        SWAPLAYER = SwapLayerSettings(
            billing={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}},
            communications={'email': {'provider': 'django'}, 'sms': {'provider': 'twilio', 'twilio': {...}}},
        )
    """

    # Module configurations
    billing: BillingConfig | None = Field(None, description="Billing module configuration")
    communications: CommunicationsConfig | None = Field(
        None, description="Communications module configuration (email and SMS)"
    )
    storage: StorageConfig | None = Field(None, description="Storage module configuration")
    identity: IdentityPlatformConfig | None = Field(
        None, description="Identity/OAuth configuration"
    )
    verification: IdentityVerificationConfig | None = Field(
        None, description="Identity verification configuration"
    )

    # Global settings
    debug: bool = Field(False, description="Enable debug mode for verbose logging")
    raise_on_error: bool = Field(True, description="Raise exceptions on provider errors")

    model_config = {
        "extra": "forbid",  # Prevent typos in configuration
        "validate_assignment": True,
    }

    @classmethod
    def from_env(cls, prefix: str = "SWAPLAYER_") -> "SwapLayerSettings":
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with SWAPLAYER_ (or custom prefix).

        Examples:
            SWAPLAYER_BILLING_PROVIDER=stripe
            SWAPLAYER_BILLING_STRIPE_SECRET_KEY=sk_test_...
            SWAPLAYER_COMMUNICATIONS_EMAIL_PROVIDER=django
            SWAPLAYER_COMMUNICATIONS_SMS_PROVIDER=twilio
            SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_ACCOUNT_SID=AC...
            SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_AUTH_TOKEN=...
            SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_FROM_NUMBER=+1555...
            SWAPLAYER_IDENTITY_WORKOS_APPS_DEFAULT_API_KEY=...
            SWAPLAYER_RAISE_ON_ERROR=false

        Args:
            prefix: Environment variable prefix (default: 'SWAPLAYER_')

        Returns:
            Configured SwapLayerSettings instance
        """
        config: dict[str, Any] = {}

        # Parse environment variables into nested config structure. Names are
        # matched against the settings schema, so compound field names
        # (raise_on_error, stripe_secret_key, workos_apps) and app names keep
        # their underscores. Unmatched names are kept as written and then
        # rejected by validation, so a misspelt variable is reported.
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            parts = key[len(prefix) :].lower().split("_")
            path = _env_path(cls, parts) or parts

            # Build nested dictionary
            current = config
            for depth, part in enumerate(path[:-1], start=1):
                current = current.setdefault(part, {})
                if not isinstance(current, dict):
                    parent = prefix + "_".join(path[:depth]).upper()
                    raise ConfigurationError(
                        f"Environment variables set both {parent} and fields below it"
                    )
            if isinstance(current.get(path[-1]), dict):
                raise ConfigurationError(
                    f"Environment variable {key} conflicts with nested {key}_* variables"
                )
            current[path[-1]] = value

        try:
            return cls(**config)
        except PydanticValidationError as e:
            # Enhance validation errors with rich context
            import logging

            logger = logging.getLogger(__name__)
            logger.error(format_startup_validation_errors(e.errors()))
            logger.error(ErrorContext.build_config_error_context(e, config))
            raise

    @classmethod
    def from_django(cls) -> "SwapLayerSettings":
        """
        Load configuration from Django settings.

        Looks for a SWAPLAYER dictionary in Django settings, or falls back
        to legacy individual settings for backward compatibility.

        Example Django settings:
            # New way (recommended)
            SWAPLAYER = {
                'billing': {'provider': 'stripe', 'stripe': {'secret_key': 'sk_...'}},
                'communications': {'email': {'provider': 'django'}},
            }

            # Old way (still supported for backward compatibility)
            PAYMENT_PROVIDER = 'stripe'
            STRIPE_SECRET_KEY = 'sk_...'
        """
        try:
            from django.conf import settings
        except ImportError as exc:
            raise ConfigurationError(
                "Django is not installed.",
                hint='Install SwapLayer with the Django extra: pip install "SwapLayer[django]"',
            ) from exc

        if not settings.configured:
            raise ConfigurationError(
                "Django settings are not configured.",
                hint=(
                    "Configure Django before using the Django adapter, or call "
                    "swap_layer.configure(...) with a SwapLayerSettings instance."
                ),
            )

        # Check for new SWAPLAYER config
        if hasattr(settings, "SWAPLAYER"):
            swaplayer_config = getattr(settings, "SWAPLAYER", None)
            if isinstance(swaplayer_config, dict):
                return cls(**swaplayer_config)
            elif isinstance(swaplayer_config, cls):
                return swaplayer_config

        # Fall back to legacy settings for backward compatibility
        return cls._from_legacy_django_settings(settings)

    @classmethod
    def _from_legacy_django_settings(cls, settings) -> "SwapLayerSettings":
        """Build config from legacy Django settings for backward compatibility."""
        config: dict[str, Any] = {}

        # Billing
        if hasattr(settings, "PAYMENT_PROVIDER"):
            billing_provider = getattr(settings, "PAYMENT_PROVIDER", "stripe")
            config["billing"] = {"provider": billing_provider}
            if billing_provider == "stripe" and hasattr(settings, "STRIPE_SECRET_KEY"):
                config["billing"]["stripe"] = {
                    "secret_key": settings.STRIPE_SECRET_KEY,
                    "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", None),
                    "webhook_secret": getattr(settings, "STRIPE_WEBHOOK_SECRET", None),
                }
            elif billing_provider == "paypal" and hasattr(settings, "PAYPAL_CLIENT_ID"):
                sandbox = getattr(settings, "PAYPAL_SANDBOX", True)
                if isinstance(sandbox, str):
                    sandbox = sandbox.lower() not in {"0", "false", "no", "off"}
                config["billing"]["paypal"] = {
                    "client_id": settings.PAYPAL_CLIENT_ID,
                    "client_secret": getattr(settings, "PAYPAL_CLIENT_SECRET", None)
                    or getattr(settings, "PAYPAL_SECRET", None),
                    "webhook_id": getattr(settings, "PAYPAL_WEBHOOK_ID", None),
                    "sandbox": sandbox,
                }
            elif billing_provider == "square" and hasattr(settings, "SQUARE_ACCESS_TOKEN"):
                sandbox = getattr(settings, "SQUARE_SANDBOX", True)
                if isinstance(sandbox, str):
                    sandbox = sandbox.lower() not in {"0", "false", "no", "off"}
                config["billing"]["square"] = {
                    "access_token": settings.SQUARE_ACCESS_TOKEN,
                    "location_id": getattr(settings, "SQUARE_LOCATION_ID", None),
                    "webhook_signature_key": getattr(
                        settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", None
                    ),
                    "webhook_notification_url": getattr(
                        settings, "SQUARE_WEBHOOK_NOTIFICATION_URL", None
                    ),
                    "sandbox": sandbox,
                    "api_version": getattr(settings, "SQUARE_API_VERSION", "2026-05-20"),
                }
        # Communications (Email + SMS)
        communications_config: dict[str, Any] = {}

        if hasattr(settings, "EMAIL_PROVIDER"):
            communications_config["email"] = {
                "provider": getattr(settings, "EMAIL_PROVIDER", "django"),
            }

        if hasattr(settings, "SMS_PROVIDER"):
            sms_provider = settings.SMS_PROVIDER
            communications_config["sms"] = {"provider": sms_provider}

            if sms_provider == "twilio" and hasattr(settings, "TWILIO_ACCOUNT_SID"):
                communications_config["sms"]["twilio"] = {
                    "account_sid": settings.TWILIO_ACCOUNT_SID,
                    "auth_token": settings.TWILIO_AUTH_TOKEN,
                    "from_number": settings.TWILIO_FROM_NUMBER,
                }

        if communications_config:
            config["communications"] = communications_config

        # Storage
        if hasattr(settings, "STORAGE_PROVIDER"):
            config["storage"] = {
                "provider": getattr(settings, "STORAGE_PROVIDER", "local"),
                "media_root": getattr(settings, "MEDIA_ROOT", None),
                "media_url": getattr(settings, "MEDIA_URL", "/media/"),
            }
            if config["storage"]["provider"] == "gcs":
                config["storage"].update(
                    bucket_name=getattr(settings, "GCS_BUCKET_NAME", None),
                    credentials_path=getattr(settings, "GCS_CREDENTIALS_PATH", None),
                    project_id=getattr(settings, "GCS_PROJECT_ID", None),
                    location=getattr(settings, "GCS_LOCATION", "europe-west1"),
                    storage_class=getattr(settings, "GCS_STORAGE_CLASS", "STANDARD"),
                )

        # Identity Platform
        if hasattr(settings, "IDENTITY_PROVIDER"):
            identity_provider = settings.IDENTITY_PROVIDER
            config["identity"] = {"provider": identity_provider}

            if identity_provider == "workos" and hasattr(settings, "WORKOS_APPS"):
                config["identity"]["workos_apps"] = _legacy_apps(WorkOSAppConfig, settings.WORKOS_APPS)
            elif identity_provider == "auth0" and hasattr(settings, "AUTH0_APPS"):
                config["identity"]["auth0_apps"] = _legacy_apps(Auth0AppConfig, settings.AUTH0_APPS)
                config["identity"]["auth0_domain"] = getattr(
                    settings, "AUTH0_DEVELOPER_DOMAIN", None
                )

        # Identity Verification
        if hasattr(settings, "IDENTITY_VERIFICATION_PROVIDER"):
            config["verification"] = {
                "provider": getattr(settings, "IDENTITY_VERIFICATION_PROVIDER", "stripe"),
                "stripe_secret_key": getattr(settings, "STRIPE_IDENTITY_SECRET_KEY", None)
                or getattr(settings, "STRIPE_SECRET_KEY", None),
                "stripe_webhook_secret": getattr(settings, "STRIPE_IDENTITY_WEBHOOK_SECRET", None),
            }

        try:
            return cls(**config) if config else cls()
        except PydanticValidationError as e:
            # Enhance validation errors with rich context
            import logging

            logger = logging.getLogger(__name__)
            logger.error(format_startup_validation_errors(e.errors()))
            logger.error(ErrorContext.build_config_error_context(e, config))
            raise

    def validate_module(self, module: str) -> None:
        """
        Validate that a specific module is properly configured.

        Args:
            module: Module name ('billing', 'communications', 'storage', 'identity', 'verification')

        Raises:
            ImproperlyConfigured: If module is not configured or invalid
        """
        from .exceptions import ModuleNotConfiguredError

        module_config = getattr(self, module, None)
        if module_config is None:
            raise ModuleNotConfiguredError(module)

    def get_status(self) -> dict[str, str]:
        """
        Get configuration status for all modules.

        Returns:
            Dictionary mapping module names to status ('configured', 'not configured', 'invalid')
        """
        status = {}
        for module in ["billing", "communications", "storage", "identity", "verification"]:
            config = getattr(self, module, None)
            if config is None:
                status[module] = "not configured"
            elif module == "communications":
                # Special handling for communications
                parts = []
                if config.email:
                    parts.append(f"email: {config.email.provider}")
                if config.sms:
                    parts.append(f"sms: {config.sms.provider}")
                status[module] = (
                    f"configured ({', '.join(parts) if parts else 'empty'})"
                    if parts
                    else "not configured"
                )
            else:
                try:
                    # Re-validate to catch any issues
                    config.model_validate(config)
                    status[module] = f"configured (provider: {config.provider})"
                except Exception as e:
                    status[module] = f"invalid: {str(e)}"
        return status

    def __repr__(self) -> str:
        """Pretty representation showing configured modules."""
        status = self.get_status()
        configured = [k for k, v in status.items() if v.startswith("configured")]
        return f"<SwapLayerSettings: {', '.join(configured) or 'no modules configured'}>"


# ============================================================================
# Helper Functions
# ============================================================================


def configure(
    settings: SwapLayerSettings | dict[str, Any] | None = None,
    **kwargs: Any,
) -> SwapLayerSettings:
    """
    Configure SwapLayer for plain Python or framework integrations.

    Args:
        settings: A SwapLayerSettings instance or dictionary.
        **kwargs: Settings fields used when ``settings`` is omitted.

    Returns:
        The configured SwapLayerSettings instance.
    """
    if settings is None:
        resolved = SwapLayerSettings(**kwargs)
    elif isinstance(settings, SwapLayerSettings):
        if kwargs:
            raise TypeError(
                "Pass either a SwapLayerSettings instance or keyword settings, not both."
            )
        resolved = settings
    elif isinstance(settings, dict):
        if kwargs:
            settings = {**settings, **kwargs}
        resolved = SwapLayerSettings(**settings)
    else:
        raise TypeError("settings must be a SwapLayerSettings instance, a dict, or None.")

    set_swaplayer_settings(resolved)
    return resolved


def set_swaplayer_settings(settings: SwapLayerSettings | dict[str, Any]) -> SwapLayerSettings:
    """Set the process-local SwapLayer settings instance."""
    global _settings_cache
    _settings_cache = (
        settings if isinstance(settings, SwapLayerSettings) else SwapLayerSettings(**settings)
    )
    return _settings_cache


def reset_swaplayer_settings() -> None:
    """Clear the process-local SwapLayer settings cache."""
    global _settings_cache
    _settings_cache = None


def get_swaplayer_settings() -> SwapLayerSettings:
    """
    Get the active SwapLayer settings instance.

    Returns:
        SwapLayerSettings instance

    If no explicit settings have been configured, this falls back to Django
    settings when Django is installed and configured, then to environment
    variables.
    """
    if _settings_cache is not None:
        return _settings_cache

    try:
        from django.conf import settings as django_settings
    except ImportError:
        return SwapLayerSettings.from_env()

    if not django_settings.configured:
        return SwapLayerSettings.from_env()

    if not hasattr(django_settings, "_swaplayer_settings_cache"):
        django_settings._swaplayer_settings_cache = SwapLayerSettings.from_django()

    cached = getattr(django_settings, "_swaplayer_settings_cache", None)
    if not isinstance(cached, SwapLayerSettings):
        raise ConfigurationError("Django SwapLayer settings cache has an invalid type")
    return cached


def validate_swaplayer_config() -> dict[str, Any]:
    """
    Validate SwapLayer configuration and return detailed status.

    Useful for Django management commands and health checks.

    Returns:
        Dictionary with validation results
    """
    try:
        settings = get_swaplayer_settings()
        status = settings.get_status()

        return {
            "valid": True,
            "modules": status,
            "settings": settings,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "modules": {},
        }
