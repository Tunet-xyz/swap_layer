from swap_layer.settings import get_swaplayer_settings

from .adapter import EmailProviderAdapter


def get_email_provider() -> EmailProviderAdapter:
    """
    Factory function to return the configured Email Provider.
    This allows switching vendors by changing the provider in SwapLayerSettings.

    Returns:
        EmailProviderAdapter: The configured email provider instance

    Raises:
        ValueError: If the provider is not recognized

    Supported Providers:
        - 'django': Uses django-anymail (RECOMMENDED for production)
          Supports: SendGrid, Mailgun, SES, Postmark, SparkPost, etc.
          Configure via ANYMAIL setting in settings.py

        - 'smtp': Direct Django SMTP backend
          Good for development/simple use cases
    """
    # Get provider from SwapLayerSettings
    settings = get_swaplayer_settings()

    if settings.communications and settings.communications.email:
        provider = settings.communications.email.provider
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "EMAIL_PROVIDER", "django")

    if provider == "django":
        from .providers.django_email import DjangoEmailAdapter

        return DjangoEmailAdapter()
    elif provider == "smtp":
        from .providers.smtp import SMTPEmailProvider

        return SMTPEmailProvider()
    else:
        raise ValueError(
            f"Unknown Email Provider: '{provider}'. "
            f"Supported: 'django' (recommended), 'smtp'. "
            f"For SendGrid/Mailgun/SES, use EMAIL_PROVIDER='django' with django-anymail."
        )
