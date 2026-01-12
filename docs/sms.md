# SMS Abstraction Layer

A provider-agnostic SMS abstraction layer for sending text messages in Django applications. Switch between Twilio, AWS SNS, Vonage, and other providers without changing your application code.

## Overview

This abstraction layer follows the same architectural pattern as the authentication, payment, email, and storage abstractions in this project. It provides a consistent interface for SMS operations regardless of the underlying provider.

## Architecture

```
┌─────────────────────────────────────┐
│     Application / Business Logic    │
├─────────────────────────────────────┤
│         SMS Abstraction Layer       │
│    - SMSProviderAdapter (ABC)       │
│    - Factory Function               │
├─────────────────────────────────────┤
│         Provider Implementations     │
│    - TwilioSMSProvider              │
│    - SNSSMSProvider (stub)          │
│    - VonageSMSProvider (future)     │
└─────────────────────────────────────┘
```

## Features

The abstraction provides these operations:

- **send_sms** - Send individual SMS messages
- **send_bulk_sms** - Send messages to multiple recipients
- **get_message_status** - Check delivery status
- **validate_phone_number** - Validate and get phone number info
- **get_account_balance** - Check account credits/balance
- **list_messages** - List sent messages with filtering
- **opt_out_number** - Add to opt-out/unsubscribe list
- **opt_in_number** - Remove from opt-out list

## Installation

1. Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.sms.apps.SmsConfig',
    # ...
]
```

2. Install provider dependencies:

```bash
# For Twilio
pip install twilio

# For AWS SNS
pip install boto3
```

3. Configure your SMS provider in `settings.py`:

```python
# SMS Provider Selection
SMS_PROVIDER = 'twilio'  # 'twilio', 'sns'

# Twilio Configuration
TWILIO_ACCOUNT_SID = 'AC...'
TWILIO_AUTH_TOKEN = '...'
TWILIO_FROM_NUMBER = '+1234567890'  # E.164 format

# AWS SNS Configuration (if using SNS)
AWS_ACCESS_KEY_ID = 'AKIA...'
AWS_SECRET_ACCESS_KEY = '...'
AWS_REGION_NAME = 'us-east-1'
AWS_SNS_DEFAULT_SENDER_ID = 'MyApp'
```

**Security:** Use environment variables for credentials:

```python
import os
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
```

## Usage

### Basic Usage

```python
from swap_layer.sms.factory import get_sms_provider

# Get the configured provider
sms = get_sms_provider()

# Send an SMS
result = sms.send_sms(
    to='+14155552671',
    message='Hello! Your verification code is 123456.',
    from_number='+14155551234'  # Optional, uses default if not provided
)
print(f"Message ID: {result['message_id']}")
print(f"Status: {result['status']}")
```

### Send Verification Code

```python
from swap_layer.sms.factory import get_sms_provider
import random

def send_verification_code(phone_number):
    sms = get_sms_provider()
    
    # Generate code
    code = str(random.randint(100000, 999999))
    
    # Send SMS
    result = sms.send_sms(
        to=phone_number,
        message=f'Your verification code is {code}. Valid for 10 minutes.',
        metadata={'type': 'verification', 'code': code}
    )
    
    # Store code in cache/database for verification
    # cache.set(f'verification_{phone_number}', code, timeout=600)
    
    return result
```

### Send Bulk SMS

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# Prepare recipients with personalized messages
recipients = [
    {'to': '+14155551111', 'message': 'Hello Alice, your project was approved!'},
    {'to': '+14155552222', 'message': 'Hello Bob, your project was approved!'},
    {'to': '+14155553333'},  # Will use default message
]

# Send bulk SMS
result = sms.send_bulk_sms(
    recipients=recipients,
    message='Your project status has been updated.',  # Default message
)

print(f"Sent: {result['total_sent']}")
print(f"Failed: {result['total_failed']}")
for failure in result['failed_recipients']:
    print(f"Failed to send to {failure['to']}: {failure['error']}")
```

### Check Message Status

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# Get message status
status = sms.get_message_status('SM1234567890abcdef')
print(f"Status: {status['status']}")  # sent, delivered, failed, etc.
if status['error']:
    print(f"Error: {status['error']}")
```

### Validate Phone Number

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# Validate phone number
info = sms.validate_phone_number('+14155552671')
if info['is_valid']:
    print(f"Valid number: {info['phone_number']}")
    print(f"Country: {info['country_code']}")
    print(f"Carrier: {info['carrier']}")
    print(f"Type: {info['line_type']}")  # mobile, landline, voip
else:
    print("Invalid phone number")
```

### Check Account Balance

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# Get account balance
balance = sms.get_account_balance()
print(f"Balance: {balance['balance']} {balance['currency']}")
print(f"Status: {balance['account_status']}")
```

### List Sent Messages

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# List messages from the last 7 days
from datetime import datetime, timedelta

start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
messages = sms.list_messages(
    start_date=start_date,
    status='delivered',
    limit=100
)

for msg in messages:
    print(f"{msg['message_id']}: {msg['to']} - {msg['status']}")
```

### Handle Opt-Outs

```python
from swap_layer.sms.factory import get_sms_provider

sms = get_sms_provider()

# Add to opt-out list (when user texts STOP)
sms.opt_out_number('+14155552671')

# Remove from opt-out list (when user texts START)
sms.opt_in_number('+14155552671')

# Before sending, check if opted out (implement in your database)
# if not is_opted_out(phone_number):
#     sms.send_sms(...)
```

## Django Integration

### SMS View

```python
from django.views import View
from django.http import JsonResponse
from swap_layer.sms.factory import get_sms_provider
from swap_layer.sms.adapter import SMSSendError

class SendSMSView(View):
    def post(self, request):
        phone_number = request.POST.get('phone_number')
        message = request.POST.get('message')
        
        if not phone_number or not message:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        try:
            sms = get_sms_provider()
            result = sms.send_sms(
                to=phone_number,
                message=message,
                metadata={'user_id': str(request.user.id)}
            )
            
            return JsonResponse({
                'success': True,
                'message_id': result['message_id'],
                'status': result['status'],
            })
        except SMSSendError as e:
            return JsonResponse({'error': str(e)}, status=500)
```

### Two-Factor Authentication

```python
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from swap_layer.sms.factory import get_sms_provider
import random

@login_required
def send_2fa_code(request):
    # Generate 6-digit code
    code = str(random.randint(100000, 999999))
    
    # Store in session
    request.session['2fa_code'] = code
    request.session['2fa_phone'] = request.user.phone_number
    
    # Send SMS
    sms = get_sms_provider()
    try:
        sms.send_sms(
            to=request.user.phone_number,
            message=f'Your 2FA code is {code}. Do not share this code.'
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': 'Failed to send SMS'}, status=500)

@login_required
def verify_2fa_code(request):
    code = request.POST.get('code')
    if code == request.session.get('2fa_code'):
        request.session['2fa_verified'] = True
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid code'}, status=400)
```

## Providers

### Twilio (Fully Implemented)

Twilio is a leading SMS provider with excellent reliability and features.

**Pros:**
- Reliable delivery
- Global coverage
- Rich API features
- Excellent documentation
- Delivery receipts
- Phone number validation

**Cons:**
- Cost per message
- Requires account setup

**Setup:**
1. Sign up at https://twilio.com
2. Get Account SID and Auth Token
3. Purchase a phone number
4. Configure in settings

### AWS SNS (Stub - Needs Implementation)

AWS Simple Notification Service can send SMS messages.

**Pros:**
- Integrated with AWS ecosystem
- Pay-per-message
- No monthly fees
- Global reach

**Cons:**
- Limited features vs Twilio
- No delivery receipts by default
- Requires AWS account

**To implement:**
1. Install: `pip install boto3`
2. Complete the stub in `providers/sns.py`
3. Configure AWS credentials

## Testing

### Unit Tests with Mocks

```python
from unittest.mock import Mock, patch
from swap_layer.sms.adapter import SMSProviderAdapter

# Mock the SMS provider
mock_sms = Mock(spec=SMSProviderAdapter)
mock_sms.send_sms.return_value = {
    'message_id': 'SM123',
    'status': 'sent',
    'to': '+14155552671',
    'from_number': '+14155551234',
    'segments': 1,
}

# Use in tests
with patch('swap_layer.sms.factory.get_sms_provider', return_value=mock_sms):
    # Your test code
    pass
```

### Integration Tests

```python
from django.test import TestCase
from swap_layer.sms.factory import get_sms_provider

class SMSIntegrationTest(TestCase):
    def test_send_sms(self):
        sms = get_sms_provider()
        result = sms.send_sms(
            to='+14155552671',  # Twilio test number
            message='Test message'
        )
        self.assertIn('message_id', result)
        self.assertIn('status', result)
```

## Best Practices

1. **Use E.164 Format**: Always format phone numbers as +[country code][number] (e.g., +14155552671)

2. **Validate Before Sending**: Use `validate_phone_number()` to check numbers before sending

3. **Handle Opt-Outs**: Respect user preferences and legal requirements (TCPA in US, GDPR in EU)

4. **Rate Limiting**: Implement rate limits to prevent abuse and control costs

5. **Message Length**: Keep messages under 160 characters to avoid multi-segment fees

6. **Error Handling**: Always wrap SMS operations in try-except blocks

7. **Delivery Receipts**: Track message status for important messages

8. **Cost Monitoring**: Monitor SMS costs and set up alerts

9. **Testing**: Use provider test numbers during development

10. **Compliance**: Follow regulations like TCPA, GDPR, and local laws

## Error Handling

```python
from swap_layer.sms.adapter import (
    SMSError,                    # Base exception
    SMSSendError,               # Send failures
    SMSMessageNotFoundError,    # Message not found
    SMSInvalidPhoneNumberError, # Invalid phone number
)

try:
    sms.send_sms('+14155552671', 'Hello!')
except SMSInvalidPhoneNumberError:
    print("Invalid phone number format")
except SMSSendError as e:
    print(f"Failed to send SMS: {e}")
except SMSError as e:
    print(f"SMS error: {e}")
```

## Adding a New Provider

To add Vonage (formerly Nexmo):

1. Create `providers/vonage.py`:

```python
from swap_layer.sms.adapter import SMSProviderAdapter

class VonageSMSProvider(SMSProviderAdapter):
    def __init__(self):
        # Initialize Vonage client
        pass
    
    def send_sms(self, to, message, from_number=None, metadata=None):
        # Implement using Vonage API
        pass
    
    # Implement other methods...
```

2. Update `factory.py`:

```python
elif provider == 'vonage':
    from swap_layer.sms.providers.vonage import VonageSMSProvider
    return VonageSMSProvider()
```

3. Add configuration to `settings.py`:

```python
VONAGE_API_KEY = os.environ.get('VONAGE_API_KEY')
VONAGE_API_SECRET = os.environ.get('VONAGE_API_SECRET')
VONAGE_FROM_NUMBER = os.environ.get('VONAGE_FROM_NUMBER')
```

## Comparison with Other Abstractions

| Aspect | Authentication | Payments | Email | Storage | **SMS** |
|--------|---------------|----------|-------|---------|---------|
| **Location** | `swap_layer/identity/platform/` | `swap_layer/payments/` | `swap_layer/email/` | `swap_layer/storage/` | `swap_layer/sms/` |
| **Base Class** | `AuthProviderAdapter` | `PaymentProviderAdapter` | `EmailProviderAdapter` | `StorageProviderAdapter` | `SMSProviderAdapter` |
| **Factory** | `get_identity_client()` | `get_payment_provider()` | `get_email_provider()` | `get_storage_provider()` | `get_sms_provider()` |
| **Methods** | 3 | 21 | 8 | 12 | 8 |
| **Providers** | Auth0, WorkOS | Stripe | SMTP, SendGrid | Local, S3, Azure | Twilio, SNS (stub) |
| **Config Key** | `IDENTITY_PROVIDER` | `PAYMENT_PROVIDER` | `EMAIL_PROVIDER` | `STORAGE_PROVIDER` | `SMS_PROVIDER` |
| **Pattern** | Provider Adapter | Provider Adapter | Provider Adapter | Provider Adapter | Provider Adapter |

## Benefits

1. **Provider Independence** - Switch SMS providers by changing one setting
2. **Consistent Interface** - Same API regardless of provider
3. **Cost Optimization** - Compare providers and switch to cheaper options
4. **Easy Testing** - Mock the adapter interface for unit tests
5. **Multi-Provider Support** - Use different providers for different regions
6. **Future-Proof** - Add new providers without changing application code

## Compliance and Legal

### TCPA (US)

- Obtain prior express consent before sending messages
- Include opt-out instructions in messages
- Honor opt-out requests immediately
- Keep records of consent

### GDPR (EU)

- Obtain explicit consent for marketing messages
- Provide clear privacy information
- Allow users to withdraw consent easily
- Maintain consent records

### Best Practices

- Include opt-out instructions: "Reply STOP to unsubscribe"
- Identify your organization
- Don't send messages between 9 PM and 8 AM local time
- Keep messages relevant and valuable

## Security Considerations

1. **Credentials**: Store API keys in environment variables
2. **Rate Limiting**: Prevent abuse with rate limits
3. **Validation**: Validate phone numbers before sending
4. **Logging**: Log SMS operations for audit trails (but not message content)
5. **Privacy**: Don't log sensitive information in SMS content
6. **2FA**: Use SMS for 2FA but consider it less secure than app-based 2FA

## Cost Optimization

1. **Message Length**: Keep under 160 characters to avoid multi-segment fees
2. **Consolidate**: Send one comprehensive message instead of multiple short ones
3. **Timing**: Some providers charge different rates at different times
4. **International**: Be aware of higher costs for international SMS
5. **Alternatives**: Consider push notifications for less critical messages

## License

This module is part of SwapLayer and follows the MIT License.
