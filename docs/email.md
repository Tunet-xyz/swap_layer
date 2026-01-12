# Email Infrastructure

This module provides an abstraction layer for email service providers, allowing the application to switch between different email services (SMTP, SendGrid, Mailgun, AWS SES, etc.) without modifying business logic.

## Architecture

The email infrastructure follows the same pattern as the authentication and payment abstractions:

```
swap_layer/email/
├── __init__.py
├── apps.py                    # Django AppConfig
├── adapter.py                 # Abstract base class (EmailProviderAdapter)
├── factory.py                 # Provider selection factory
└── providers/                 # Provider implementations
    ├── __init__.py
    ├── smtp.py                # Django SMTP backend (default)
    ├── sendgrid.py            # SendGrid implementation
    ├── mailgun.py             # Mailgun (stub)
    └── ses.py                 # AWS SES (stub)
```

## Design Pattern

### 1. Abstract Base Class (`adapter.py`)

The `EmailProviderAdapter` defines the interface that all email providers must implement:

- **Email Sending**: Send single emails with text/HTML bodies, attachments, CC/BCC
- **Template Emails**: Send emails using provider templates
- **Bulk Sending**: Send personalized bulk emails
- **Email Verification**: Verify email addresses (provider-dependent)
- **Statistics**: Get sending statistics (delivered, bounced, opened, clicked)
- **Suppression Lists**: Manage bounce/complaint suppression lists
- **Webhooks**: Validate webhook signatures from providers

### 2. Provider Implementations (`providers/`)

Each provider (e.g., SMTP, SendGrid) implements the `EmailProviderAdapter` interface:

```python
class SMTPEmailProvider(EmailProviderAdapter):
    def send_email(self, to, subject, text_body=None, html_body=None, ...):
        # Django SMTP-specific implementation
        msg = EmailMultiAlternatives(...)
        return normalized_data
```

### 3. Factory Function (`factory.py`)

The factory function returns the appropriate provider based on Django settings:

```python
from swap_layer.email.factory import get_email_provider

# Get the configured provider (defaults to SMTP)
provider = get_email_provider()

# Use the provider
result = provider.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    text_body='Welcome to our platform.',
    html_body='<h1>Welcome to our platform.</h1>'
)
```

## Configuration

Add to your Django `settings.py`:

```python
# Email Provider Selection
EMAIL_PROVIDER = 'django'  # Recommended: uses django-anymail
# Or: 'smtp', 'sendgrid', 'mailgun', 'ses' (legacy)

# Django-Anymail Configuration (RECOMMENDED)
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
ANYMAIL = {
    'SENDGRID_API_KEY': 'SG...',
}

# OR: SMTP Configuration (Django default)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
```

**Security:** Use environment variables:

```python
import os
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.email.apps.EmailConfig',
    # ...
]
```

## Usage Examples

### Basic Email Sending

```python
from swap_layer.email.factory import get_email_provider

provider = get_email_provider()

# Send a simple email
result = provider.send_email(
    to=['user@example.com'],
    subject='Welcome to SwapLayer',
    text_body='Thank you for joining our platform.',
    html_body='<h1>Welcome!</h1><p>Thank you for joining our platform.</p>',
)

print(f"Message ID: {result['message_id']}")
print(f"Status: {result['status']}")
```

### Email with Attachments

```python
result = provider.send_email(
    to=['user@example.com'],
    subject='Your Report',
    text_body='Please find your report attached.',
    attachments=[
        {
            'filename': 'report.pdf',
            'content': pdf_bytes,
            'mimetype': 'application/pdf'
        }
    ]
)
```

### CC, BCC, and Reply-To

```python
result = provider.send_email(
    to=['user@example.com'],
    subject='Team Update',
    text_body='Here is the latest team update.',
    cc=['manager@example.com'],
    bcc=['archive@example.com'],
    reply_to=['support@example.com'],
)
```

### Template Emails (SendGrid)

```python
# With SendGrid, use dynamic templates
result = provider.send_template_email(
    to=['user@example.com'],
    template_id='d-1234567890abcdef',
    template_data={
        'name': 'John Doe',
        'verification_code': '123456',
        'subject': 'Verify Your Email'
    }
)
```

### Template Emails (SMTP/Django)

```python
# With SMTP, use Django templates
# Create templates: emails/welcome.html and emails/welcome.txt
result = provider.send_template_email(
    to=['user@example.com'],
    template_id='emails/welcome',
    template_data={
        'name': 'John Doe',
        'subject': 'Welcome to SwapLayer'
    }
)
```

### Bulk Email with Personalization

```python
# SMTP provider uses $variable format (Python string.Template)
recipients = [
    {
        'to': 'user1@example.com',
        'substitutions': {'name': 'Alice', 'code': 'ABC123'}
    },
    {
        'to': 'user2@example.com',
        'substitutions': {'name': 'Bob', 'code': 'XYZ789'}
    }
]

result = provider.send_bulk_email(
    recipients=recipients,
    subject='Hello $name!',
    text_body='Your verification code is: $code',
    html_body='<h1>Hello $name!</h1><p>Your code: <strong>$code</strong></p>'
)

# SendGrid provider uses -variable- format
result = provider.send_bulk_email(
    recipients=recipients,
    subject='Hello -name-!',
    text_body='Your verification code is: -code-',
    html_body='<h1>Hello -name-!</h1><p>Your code: <strong>-code-</strong></p>'
)

print(f"Sent: {result['total_sent']}, Failed: {result['total_failed']}")
```

### Email Verification

```python
result = provider.verify_email('user@example.com')
print(f"Valid: {result['is_valid']}, Reason: {result['reason']}")
```

### Get Statistics

```python
# Get statistics for a date range
stats = provider.get_send_statistics(
    start_date='2024-01-01',
    end_date='2024-01-31'
)

print(f"Sent: {stats['sent']}")
print(f"Delivered: {stats['delivered']}")
print(f"Bounced: {stats['bounced']}")
print(f"Opened: {stats['opened']}")
print(f"Clicked: {stats['clicked']}")
```

### Suppression List Management

```python
# Add to suppression list
result = provider.add_to_suppression_list(
    email='bounced@example.com',
    reason='bounce'
)

# Remove from suppression list
result = provider.remove_from_suppression_list('bounced@example.com')
```

### Webhook Validation

```python
# In your webhook view
def sendgrid_webhook(request):
    payload = request.body
    signature = request.headers.get('X-Twilio-Email-Event-Webhook-Signature')
    timestamp = request.headers.get('X-Twilio-Email-Event-Webhook-Timestamp')
    
    provider = get_email_provider()
    if provider.validate_webhook_signature(payload, signature, timestamp):
        # Process webhook
        import json
        events = json.loads(payload)
        for event in events:
            handle_email_event(event)
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
```

## Provider Comparison

| Feature | SMTP | SendGrid | Mailgun | AWS SES |
|---------|------|----------|---------|---------|
| **Basic Sending** | ✅ | ✅ | 🚧 | 🚧 |
| **Templates** | ✅ (Django) | ✅ (Dynamic) | 🚧 | 🚧 |
| **Bulk Sending** | ⚠️ (Sequential) | ✅ (Optimized) | 🚧 | 🚧 |
| **Email Verification** | ⚠️ (Format only) | ⚠️ (Paid add-on) | 🚧 | 🚧 |
| **Statistics** | ❌ | ✅ | 🚧 | 🚧 |
| **Suppression Lists** | ❌ | ✅ | 🚧 | 🚧 |
| **Webhooks** | ❌ | ✅ | 🚧 | 🚧 |
| **Attachments** | ✅ | ✅ | 🚧 | 🚧 |
| **Cost** | Free (self-hosted) | Pay-as-you-go | Pay-as-you-go | Pay-as-you-go |

✅ = Fully implemented | ⚠️ = Limited support | ❌ = Not supported | 🚧 = Stub (to be implemented)

## Benefits

1. **Provider Independence**: Switch email providers by changing one setting
2. **Consistent Interface**: Same API regardless of provider
3. **Easy Testing**: Mock the adapter interface for unit tests
4. **Type Safety**: Type hints throughout for better IDE support
5. **Feature Detection**: Gracefully handle unsupported features
6. **Extensibility**: Easy to add new providers
7. **No Vendor Lock-in**: Avoid being tied to a single email service

## Adding a New Provider

To add a new email provider (e.g., Postmark):

1. Create `swap_layer/email/providers/postmark.py`:

```python
from ..adapter import EmailProviderAdapter

class PostmarkEmailProvider(EmailProviderAdapter):
    def __init__(self):
        self.api_key = settings.POSTMARK_API_KEY
        # Initialize Postmark client
    
    def send_email(self, to, subject, text_body=None, html_body=None, ...):
        # Implement using Postmark API
        pass
    
    # Implement other abstract methods...
```

2. Update `factory.py`:

```python
def get_email_provider():
    provider = getattr(settings, 'EMAIL_PROVIDER', 'smtp')
    
    if provider == 'postmark':
        from .providers.postmark import PostmarkEmailProvider
        return PostmarkEmailProvider()
    # ... existing providers
```

3. Add configuration to `settings.py`:

```python
EMAIL_PROVIDER = 'postmark'
POSTMARK_API_KEY = os.environ.get('POSTMARK_API_KEY')
```

## Testing

### Unit Testing with Mocks

```python
from unittest.mock import Mock
from swap_layer.email.adapter import EmailProviderAdapter

# Create a mock provider
mock_provider = Mock(spec=EmailProviderAdapter)
mock_provider.send_email.return_value = {
    'message_id': 'test_123',
    'status': 'sent',
    'provider_response': {}
}

# Use in tests
def test_user_registration():
    # Mock the factory
    with patch('swap_layer.email.factory.get_email_provider', return_value=mock_provider):
        # Test your code
        register_user('user@example.com')
        
        # Verify email was sent
        mock_provider.send_email.assert_called_once()
```

### Integration Testing

```python
from swap_layer.email.factory import get_email_provider

def test_smtp_integration():
    provider = get_email_provider()
    result = provider.send_email(
        to=['test@example.com'],
        subject='Test Email',
        text_body='This is a test email.'
    )
    assert result['status'] == 'sent'
    assert 'message_id' in result
```

## Error Handling

```python
from swap_layer.email.adapter import EmailSendError, TemplateNotFoundError

try:
    provider.send_email(
        to=['user@example.com'],
        subject='Test',
        text_body='Hello'
    )
except EmailSendError as e:
    logger.error(f"Failed to send email: {e}")
    # Handle error (retry, notify admin, etc.)

try:
    provider.send_template_email(
        to=['user@example.com'],
        template_id='nonexistent',
        template_data={}
    )
except TemplateNotFoundError as e:
    logger.error(f"Template not found: {e}")
```

## Migration from Direct Email Usage

### Before (Direct Django email):

```python
from django.core.mail import send_mail

send_mail(
    'Welcome',
    'Welcome to our platform.',
    'noreply@example.com',
    ['user@example.com'],
)
```

### After (Using abstraction):

```python
from swap_layer.email.factory import get_email_provider

provider = get_email_provider()
provider.send_email(
    to=['user@example.com'],
    subject='Welcome',
    text_body='Welcome to our platform.',
)
```

## Best Practices

1. **Always use the factory**: Don't instantiate providers directly
2. **Handle errors gracefully**: Catch `EmailSendError` and `TemplateNotFoundError`
3. **Use environment variables**: Store API keys in environment, not in code
4. **Test with mocks**: Use mock providers for unit tests
5. **Monitor statistics**: Track email performance using `get_send_statistics()`
6. **Respect suppression lists**: Check before sending to known bounced emails
7. **Validate webhooks**: Always validate webhook signatures

## Related Infrastructure

- **Authentication**: `swap_layer/identity/platform/`
- **Payments**: `swap_layer/payments/`
- **Localization**: `swap_layer/localization/`

All follow the same provider adapter pattern for consistency.

## License

This module is part of SwapLayer.
