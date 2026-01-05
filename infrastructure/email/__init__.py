"""
Email Infrastructure

This module provides an abstraction layer for email providers, allowing the
application to switch between different email services (SMTP, SendGrid, Mailgun,
AWS SES, etc.) without modifying business logic.

Usage:
    from infrastructure.email.factory import get_email_provider
    
    provider = get_email_provider()
    result = provider.send_email(
        to=['user@example.com'],
        subject='Welcome!',
        text_body='Welcome to our platform.',
        html_body='<h1>Welcome to our platform.</h1>'
    )
"""

default_app_config = 'infrastructure.email.apps.EmailConfig'
