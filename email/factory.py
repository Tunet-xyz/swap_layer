from django.conf import settings
from .adapter import EmailProviderAdapter


def get_email_provider() -> EmailProviderAdapter:
    """
    Factory function to return the configured Email Provider.
    This allows switching vendors by changing the EMAIL_PROVIDER setting.
    
    Returns:
        EmailProviderAdapter: The configured email provider instance
    
    Raises:
        ValueError: If the provider is not recognized
    """
    provider = getattr(settings, 'EMAIL_PROVIDER', 'smtp')
    
    if provider == 'django':
        from .providers.django_email import DjangoEmailAdapter
        return DjangoEmailAdapter()
    elif provider == 'smtp':
        # Deprecated: Use 'django' provider
        from .providers.smtp import SMTPEmailProvider
        return SMTPEmailProvider()
    elif provider == 'sendgrid':
        # Deprecated: Use 'django' provider with django-anymail
        from .providers.sendgrid import SendGridEmailProvider
        return SendGridEmailProvider()
    elif provider == 'mailgun':
        # Deprecated: Use 'django' provider with django-anymail
        from .providers.mailgun import MailgunEmailProvider
        return MailgunEmailProvider()
    elif provider == 'ses':
        # Deprecated: Use 'django' provider with django-anymail
        from .providers.ses import SESEmailProvider
        return SESEmailProvider()
    else:
        raise ValueError(f"Unknown Email Provider: {provider}")
