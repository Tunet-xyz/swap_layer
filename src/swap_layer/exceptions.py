"""
SwapLayer Custom Exceptions

Provides rich, actionable error messages that guide developers to solutions.
"""

from collections.abc import Mapping, Sequence
from typing import Any

try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:  # pragma: no cover - exercised in environments without Django

    class ImproperlyConfigured(Exception):  # type: ignore[no-redef]
        """Fallback used when Django is not installed."""

        pass


# Documented vendor prefixes. A rejected value is described by these and by its
# length only; error messages never repeat any character the caller supplied.
_STRIPE_KEY_KINDS = (
    ("sk_", "a secret key"),
    ("rk_", "a restricted key"),
    ("pk_", "a publishable key"),
    ("whsec_", "a webhook signing secret"),
)
_TWILIO_SID_KINDS = (
    ("SK", "an API key SID"),
    ("MG", "a Messaging Service SID"),
    ("PN", "a phone number SID"),
)


def _describe_rejected_value(value: str, known_kinds: Sequence[tuple[str, str]]) -> str:
    """
    Describe a rejected credential without echoing any part of it.

    Examples:
        >>> _describe_rejected_value("pk_test_123", _STRIPE_KEY_KINDS)
        "The value looks like a publishable key ('pk_...', 11 characters)."
        >>> _describe_rejected_value("abc", _STRIPE_KEY_KINDS)
        'The value has 3 characters and no recognised prefix.'
    """
    if not value:
        return "The value is empty."
    for prefix, kind in known_kinds:
        if value.startswith(prefix):
            return f"The value looks like {kind} ('{prefix}...', {len(value)} characters)."
    return f"The value has {len(value)} characters and no recognised prefix."


class SwapLayerError(Exception):
    """Base exception for all SwapLayer errors."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        docs_url: str | None = None,
        examples: list[str] | None = None,
        related_settings: list[str] | None = None,
    ):
        """
        Create a rich error with helpful context.

        Args:
            message: Main error message
            hint: Helpful hint on how to fix the issue
            docs_url: URL to relevant documentation
            examples: List of example valid values
            related_settings: List of related settings to check
        """
        self.hint = hint
        self.docs_url = docs_url
        self.examples = examples or []
        self.related_settings = related_settings or []

        # Build comprehensive error message
        parts = [message]

        if hint:
            parts.append(f"\n💡 Hint: {hint}")

        if examples:
            parts.append("\n\n✅ Valid examples:")
            for example in examples:
                parts.append(f"   {example}")

        if related_settings:
            parts.append("\n\n🔍 Check these settings:")
            for setting in related_settings:
                parts.append(f"   - {setting}")

        if docs_url:
            parts.append(f"\n\n📚 Documentation: {docs_url}")

        super().__init__("\n".join(parts))


class ConfigurationError(SwapLayerError, ImproperlyConfigured):
    """Configuration is missing or invalid."""

    pass


class ValidationError(SwapLayerError):
    """Value failed validation."""

    pass


class ProviderError(SwapLayerError):
    """Error from external provider (Stripe, Twilio, etc.)."""

    pass


# ============================================================================
# Specific Configuration Errors
# ============================================================================


class StripeKeyError(ConfigurationError):
    """Stripe API key is invalid or incorrectly formatted."""

    def __init__(self, key_type: str, provided_value: str):
        super().__init__(
            f"❌ Invalid Stripe {key_type}",
            hint=f"Stripe {key_type}s have a specific format. "
            f"{_describe_rejected_value(provided_value, _STRIPE_KEY_KINDS)}",
            examples=[
                f"sk_test_51A... (test mode {key_type})",
                f"sk_live_51A... (live mode {key_type})",
            ]
            if key_type == "secret key"
            else [
                "pk_test_51A... (test mode publishable key)",
                "pk_live_51A... (live mode publishable key)",
            ],
            docs_url="https://stripe.com/docs/keys",
            related_settings=[
                "SWAPLAYER.billing.stripe.secret_key",
                "SWAPLAYER.billing.stripe.publishable_key",
            ],
        )


class TwilioConfigError(ConfigurationError):
    """Twilio configuration is invalid."""

    @classmethod
    def invalid_account_sid(cls, provided_value: str) -> "TwilioConfigError":
        return cls(
            "❌ Invalid Twilio Account SID",
            hint=f"Twilio Account SIDs always start with 'AC'. "
            f"{_describe_rejected_value(provided_value, _TWILIO_SID_KINDS)}",
            examples=[
                "AC1234567890abcdef1234567890abcd (34 characters)",
            ],
            docs_url="https://www.twilio.com/docs/iam/keys/api-key",
            related_settings=[
                "SWAPLAYER.sms.twilio.account_sid",
            ],
        )

    @classmethod
    def invalid_phone_number(cls, provided_value: str) -> "TwilioConfigError":
        # Describe the format problem without repeating the number
        starts_with_plus = provided_value.startswith("+") if provided_value else False

        return cls(
            "❌ Invalid phone number format",
            hint=f"Phone numbers must be in E.164 format (starts with '+' and country code). "
            f"The value has {len(provided_value)} characters (starts with '+': {starts_with_plus}).",
            examples=[
                "+15555551234 (US number)",
                "+442071838750 (UK number)",
                "+61212345678 (AU number)",
            ],
            docs_url="https://www.twilio.com/docs/glossary/what-e164",
            related_settings=[
                "SWAPLAYER.sms.twilio.from_number",
            ],
        )


class WorkOSConfigError(ConfigurationError):
    """WorkOS configuration is invalid."""

    @classmethod
    def short_cookie_password(cls, provided_length: int) -> "WorkOSConfigError":
        """Former name of :meth:`invalid_cookie_password`."""
        return cls.invalid_cookie_password(provided_length)

    @classmethod
    def invalid_cookie_password(cls, provided_length: int) -> "WorkOSConfigError":
        return cls(
            "❌ Invalid WorkOS cookie password",
            hint="WorkOS seals sessions with Fernet, so the cookie password must be a Fernet "
            "key: 32 random bytes, url-safe base64-encoded (44 characters). "
            f"You provided {provided_length} characters.",
            examples=[
                'Generate one: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"',
                "Or use: openssl rand -base64 32",
            ],
            docs_url="https://workos.com/docs/user-management/configuration",
            related_settings=[
                "SWAPLAYER.identity.workos_apps.<app_name>.cookie_password",
            ],
        )


class ProviderConfigMismatchError(ConfigurationError):
    """Provider is selected but configuration is missing."""

    def __init__(self, module: str, provider: str, missing_config: str):
        examples_map = {
            "stripe": [
                "billing={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...', 'publishable_key': 'pk_test_...'}}",
            ],
            "twilio": [
                "sms={'provider': 'twilio', 'twilio': {'account_sid': 'AC...', 'auth_token': '...', 'from_number': '+1555...'}}",
            ],
            "sns": [
                "sms={'provider': 'sns', 'sns': {'region_name': 'us-east-1', 'sender_id': 'MyApp'}}",
            ],
            "workos": [
                "identity={'provider': 'workos', 'workos_apps': {'default': {'api_key': '...', 'client_id': '...', 'cookie_password': '...'}}}",
            ],
            "auth0": [
                "identity={'provider': 'auth0', 'auth0_apps': {'default': {'client_id': '...', 'client_secret': '...'}}, 'auth0_domain': 'myapp.auth0.com'}",
            ],
        }

        super().__init__(
            f"❌ {module.title()} provider '{provider}' selected but {missing_config} not configured",
            hint=f"When you set provider='{provider}', you must also provide the {missing_config} configuration.",
            examples=examples_map.get(
                provider, [f"{module}={{'provider': '{provider}', '{provider}': {{...}}}}"]
            ),
            docs_url=f"https://github.com/Tunet-xyz/swap_layer/blob/main/src/swap_layer/{module}/README.md",
            related_settings=[
                f"SWAPLAYER.{module}.provider",
                f"SWAPLAYER.{module}.{provider}",
            ],
        )


class ModuleNotConfiguredError(ConfigurationError):
    """Attempted to use a module that isn't configured."""

    def __init__(self, module: str):
        module_examples = {
            "billing": "billing={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}}",
            "communications": "communications={'email': {'provider': 'django'}, 'sms': {'provider': 'twilio', 'twilio': {...}}}",
            "storage": "storage={'provider': 'local', 'media_root': '/path/to/media'}",
            "identity": "identity={'provider': 'workos', 'workos_apps': {...}}",
            "verification": "verification={'provider': 'stripe', 'stripe_secret_key': 'sk_test_...'}",
        }

        super().__init__(
            f"❌ SwapLayer '{module}' module is not configured",
            hint=f"You tried to use the {module} module, but it's not configured in your settings. "
            f"Add it to SWAPLAYER settings.",
            examples=[
                "# In settings.py",
                "SWAPLAYER = SwapLayerSettings(",
                f"    {module_examples.get(module, f'{module}={{...}}')}",
                ")",
            ],
            docs_url="https://github.com/Tunet-xyz/swap_layer/blob/main/docs/README.md",
            related_settings=[
                f"SWAPLAYER.{module}",
            ],
        )


class EnvironmentVariableError(ConfigurationError):
    """Required environment variable is missing or invalid."""

    def __init__(self, var_name: str, expected_format: str | None = None):
        hint_parts = [f"Set the environment variable: export {var_name}=<value>"]
        if expected_format:
            hint_parts.append(f"Expected format: {expected_format}")

        super().__init__(
            f"❌ Missing or invalid environment variable: {var_name}",
            hint=" ".join(hint_parts),
            examples=[
                f"export {var_name}=your_value_here",
                "# Or in .env file:",
                f"{var_name}=your_value_here",
            ],
            related_settings=[f"Environment variable: {var_name}"],
        )


class MultiTenantConfigError(ConfigurationError):
    """Multi-tenant app configuration error."""

    def __init__(self, app_name: str, provider: str, available_apps: list[str]):
        super().__init__(
            f"❌ App '{app_name}' not found in {provider} configuration",
            hint=f"You requested app '{app_name}', but it's not configured. "
            f"Available apps: {', '.join(available_apps) if available_apps else 'none'}",
            examples=[
                "# Configure the app in settings:",
                f"identity={{'provider': '{provider}', '{provider}_apps': {{",
                f"    '{app_name}': {{'api_key': '...', 'client_id': '...', ...}}",
                "}}",
            ],
            related_settings=[
                f"SWAPLAYER.identity.{provider}_apps",
            ],
        )


# ============================================================================
# Error Context Builder
# ============================================================================


class ErrorContext:
    """Build rich error context for debugging."""

    @staticmethod
    def build_config_error_context(
        error: Exception,
        config_dict: dict[str, Any] | None = None,
    ) -> str:
        """
        Build a detailed error context from a configuration error.

        Args:
            error: The exception that occurred
            config_dict: The configuration dictionary that caused the error

        Returns:
            Formatted error message with context
        """
        lines = [
            "=" * 80,
            "🚨 SWAPLAYER CONFIGURATION ERROR",
            "=" * 80,
            "",
            f"{type(error).__name__}: configuration validation failed",
            "",
        ]

        if config_dict:
            lines.extend(
                [
                    "📋 Your configuration:",
                    "---",
                    ErrorContext._format_config(config_dict, indent=0),
                    "",
                ]
            )

        lines.extend(
            [
                "=" * 80,
                "Need help? Check the documentation or file an issue:",
                "  📚 https://github.com/Tunet-xyz/swap_layer/blob/main/docs/README.md",
                "  🐛 https://github.com/Tunet-xyz/swap_layer/issues",
                "=" * 80,
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _format_config(config: Any, indent: int = 0) -> str:
        """Format configuration for display (mask secrets)."""
        if isinstance(config, dict):
            lines = []
            for key, value in config.items():
                prefix = "  " * indent
                if ErrorContext._is_sensitive_key(key):
                    lines.append(f"{prefix}{key}: {'*' * 8} (masked)")
                elif isinstance(value, (dict, list, tuple)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(ErrorContext._format_config(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
            return "\n".join(lines)
        if isinstance(config, (list, tuple)):
            return "\n".join(ErrorContext._format_config(item, indent) for item in config)
        return str(config)

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        """Check if a key contains sensitive data."""
        sensitive_keywords = [
            "key",
            "secret",
            "token",
            "password",
            "api_key",
            "auth_token",
            "client_secret",
            "cookie_password",
        ]
        return any(keyword in key.lower() for keyword in sensitive_keywords)


# ============================================================================
# Helper Functions
# ============================================================================


def enhance_validation_error(error: Exception, context: dict[str, Any]) -> Exception:
    """
    Enhance a Pydantic validation error with more helpful information.

    Args:
        error: Original validation error
        context: Context dictionary with config information

    Returns:
        Enhanced error with better messaging
    """
    error_str = str(error)

    # Detect common error patterns and provide better messages
    if "secret_key" in error_str and "must start with 'sk_'" in error_str:
        provided = context.get("secret_key", "")
        return StripeKeyError("secret key", provided)

    if "Account SID" in error_str and "must start with 'AC'" in error_str:
        provided = context.get("account_sid", "")
        return TwilioConfigError.invalid_account_sid(provided)

    if "E.164 format" in error_str:
        provided = context.get("from_number", "")
        return TwilioConfigError.invalid_phone_number(provided)

    if "cookie password" in error_str.lower() and (
        "32 characters" in error_str or "Fernet" in error_str
    ):
        provided_length = len(context.get("cookie_password", ""))
        return WorkOSConfigError.invalid_cookie_password(provided_length)

    # Default: wrap in SwapLayerError with context
    return SwapLayerError(
        str(error),
        hint="Check your configuration values and types",
        docs_url="https://github.com/Tunet-xyz/swap_layer/blob/main/docs/README.md",
    )


def format_startup_validation_errors(errors: Sequence[Mapping[str, Any]]) -> str:
    """
    Format Pydantic validation errors for display at startup.

    Args:
        errors: List of validation error dictionaries from Pydantic

    Returns:
        Formatted error message
    """
    lines = [
        "",
        "=" * 80,
        "🚨 SWAPLAYER CONFIGURATION VALIDATION FAILED",
        "=" * 80,
        "",
        "The following configuration errors were found:",
        "",
    ]

    for i, error in enumerate(errors, 1):
        loc = " → ".join(str(location) for location in error.get("loc", []))
        msg = error.get("msg", "Unknown error")
        error_type = error.get("type", "unknown")

        lines.extend(
            [
                f"{i}. ❌ {loc}",
                f"   Error: {msg}",
                f"   Type: {error_type}",
                "",
            ]
        )

    lines.extend(
        [
            "💡 Tips:",
            "  • Run: python manage.py swaplayer_check --verbose",
            "  • Check: docs/README.md for configuration guide",
            "  • See: docs/architecture.md for patterns and examples",
            "",
            "=" * 80,
        ]
    )

    return "\n".join(lines)
