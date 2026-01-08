from django.conf import settings

from .adapter import EmailProviderAdapter


def get_email_provider() -> EmailProviderAdapter:
    """
    Factory function to return the configured Email Provider.
    This allows switching vendors by changing the EMAIL_PROVIDER Django setting.

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
    provider = getattr(settings, "EMAIL_PROVIDER", "django")

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
