# Email Module - Quick Start Guide

This guide shows you how to migrate from direct email provider usage to the SwapLayer email abstraction.

## Why Use the Abstraction?

**Before** (Direct provider usage - vendor lock-in):
```python
# Using SendGrid directly
import sendgrid
sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
message = Mail(from_email='no-reply@example.com', to_emails='user@example.com', ...)
response = sg.send(message)
```

**After** (Provider-agnostic - swap anytime):
```python
# Using abstraction - works with any provider
from swap_layer.email.factory import get_email_provider
email = get_email_provider()
email.send_email(to=['user@example.com'], subject='...', text_body='...')
```

✅ Change provider by changing ONE setting  
✅ Test with mocks instead of real API calls  
✅ No vendor lock-in

---

## Quick Migration Examples

### 1. Basic Email

**Before:**
```python
from django.core.mail import send_mail
send_mail('Subject', 'Message', 'from@example.com', ['to@example.com'])
```

**After:**
```python
from swap_layer.email.factory import get_email_provider
email = get_email_provider()
email.send_email(
    to=['to@example.com'],
    subject='Subject',
    text_body='Message'
)
```

### 2. HTML Email with Attachments

**Before:**
```python
from django.core.mail import EmailMultiAlternatives
msg = EmailMultiAlternatives('Subject', 'Text', 'from@example.com', ['to@example.com'])
msg.attach_alternative('<h1>HTML</h1>', 'text/html')
msg.attach_file('/path/to/file.pdf')
msg.send()
```

**After:**
```python
email = get_email_provider()
with open('/path/to/file.pdf', 'rb') as f:
    email.send_email(
        to=['to@example.com'],
        subject='Subject',
        text_body='Text',
        html_body='<h1>HTML</h1>',
        attachments=[{
            'filename': 'file.pdf',
            'content': f.read(),
            'mimetype': 'application/pdf'
        }]
    )
```

### 3. Template Email

**SMTP Provider (Django templates):**
```python
# Create template: templates/emails/welcome.html
email = get_email_provider()
email.send_template_email(
    to=['user@example.com'],
    template_id='emails/welcome',
    template_data={
        'name': 'John',
        'code': '123456',
        'subject': 'Welcome!'
    }
)
```

**SendGrid Provider (dynamic templates):**
```python
# Create template in SendGrid dashboard, get template ID
email = get_email_provider()
email.send_template_email(
    to=['user@example.com'],
    template_id='d-abc123def456',  # SendGrid template ID
    template_data={
        'name': 'John',
        'code': '123456',
        'subject': 'Welcome!'
    }
)
```

### 4. Bulk Email with Personalization

```python
email = get_email_provider()
recipients = [
    {'to': 'user1@example.com', 'substitutions': {'name': 'Alice', 'code': 'ABC123'}},
    {'to': 'user2@example.com', 'substitutions': {'name': 'Bob', 'code': 'XYZ789'}},
]

# SMTP uses $variable syntax
email.send_bulk_email(
    recipients=recipients,
    subject='Hello $name!',
    text_body='Your code: $code'
)

# SendGrid uses -variable- syntax
email.send_bulk_email(
    recipients=recipients,
    subject='Hello -name-!',
    text_body='Your code: -code-'
)
```

---

## Common Patterns

### User Registration Email
```python
from swap_layer.email.factory import get_email_provider

def send_welcome_email(user):
    email = get_email_provider()
    result = email.send_email(
        to=[user.email],
        subject=f'Welcome to {settings.SITE_NAME}!',
        text_body=f'Hi {user.first_name}, welcome aboard!',
        html_body=f'<h1>Hi {user.first_name}</h1><p>Welcome aboard!</p>'
    )
    return result['message_id']
```

### Password Reset
```python
def send_password_reset(user, reset_token):
    email = get_email_provider()
    reset_url = f'{settings.SITE_URL}/reset/{reset_token}'
    
    email.send_email(
        to=[user.email],
        subject='Reset Your Password',
        text_body=f'Click here to reset: {reset_url}',
        html_body=f'<a href="{reset_url}">Reset Password</a>',
        metadata={'type': 'password_reset', 'user_id': user.id}
    )
```

### Order Confirmation
```python
def send_order_confirmation(order):
    email = get_email_provider()
    email.send_template_email(
        to=[order.user.email],
        template_id='emails/order_confirmation',
        template_data={
            'order_number': order.number,
            'items': order.items.all(),
            'total': order.total_price,
            'subject': f'Order #{order.number} Confirmed'
        }
    )
```

---

## Testing Your Code

### Unit Test with Mock
```python
from unittest.mock import Mock, patch
from swap_layer.email.adapter import EmailProviderAdapter

def test_user_registration():
    mock_email = Mock(spec=EmailProviderAdapter)
    mock_email.send_email.return_value = {'message_id': 'test_123', 'status': 'sent'}
    
    with patch('myapp.views.get_email_provider', return_value=mock_email):
        # Your code that sends email
        register_user('user@example.com')
        
        # Verify email was sent
        mock_email.send_email.assert_called_once()
        call_args = mock_email.send_email.call_args
        assert call_args.kwargs['to'] == ['user@example.com']
```

---

## Provider Comparison

| Feature | SMTP (Django) | SendGrid | Mailgun | AWS SES |
|---------|---------------|----------|---------|---------|
| Send Email | ✅ | ✅ | 🚧 | 🚧 |
| Templates | ✅ Django | ✅ Dynamic | 🚧 | 🚧 |
| Bulk Send | ⚠️ Sequential | ✅ Optimized | 🚧 | 🚧 |
| Statistics | ❌ | ✅ | 🚧 | 🚧 |
| Webhooks | ❌ | ✅ | 🚧 | 🚧 |
| Cost | Free | Pay-per-send | Pay-per-send | Pay-per-send |

✅ Implemented | ⚠️ Limited | ❌ Not available | 🚧 Stub

---

## Configuration

### SMTP (Default)
```python
# settings.py
EMAIL_PROVIDER = 'django'  # or 'smtp' (deprecated)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@example.com'
```

### SendGrid
```python
# settings.py
EMAIL_PROVIDER = 'sendgrid'
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'noreply@example.com'
```

### Switching Providers
Just change `EMAIL_PROVIDER` - your code stays the same! 🎉

---

## Advanced: Provider-Specific Features

### Access Underlying SDK (Escape Hatch)
```python
email = get_email_provider()

# Get the raw provider client when you need provider-specific features
if hasattr(email, 'get_vendor_client'):
    client = email.get_vendor_client()
    # Now use provider-specific methods
```

### SendGrid Statistics
```python
email = get_email_provider()  # Must be SendGrid
stats = email.get_send_statistics(
    start_date='2026-01-01',
    end_date='2026-01-31'
)
print(f"Delivered: {stats['delivered']}, Opened: {stats['opened']}")
```

---

## Troubleshooting

**Error: "Unknown Email Provider"**
- Check `EMAIL_PROVIDER` setting matches available providers
- Options: `'django'`, `'smtp'`, `'sendgrid'`, `'mailgun'`, `'ses'`

**Email not sending (SMTP)**
- Verify `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- Check firewall/port access (587 for TLS, 465 for SSL)
- Test with Django shell: `python manage.py shell`

**Template not found**
- SMTP: Ensure template exists in `templates/` directory
- SendGrid: Verify template ID from SendGrid dashboard

---

## Next Steps

1. ✅ Replace direct email calls with `get_email_provider()`
2. ✅ Add email provider config to `settings.py`
3. ✅ Test with mock provider
4. ✅ Try switching providers to verify abstraction works

**See README.md for complete API reference.**
