# Email

Email adapters require configured Django settings. Install `SwapLayer[email]` for Django and Anymail, or `SwapLayer[django]` for Django's built-in backends.

The selectable values are `django` and `smtp`. SendGrid, Mailgun, SES and other Anymail services are Django backend choices, not SwapLayer provider values.

```python
# Django settings.py
import os
SWAPLAYER = {"communications": {"email": {"provider": "django"}}}
EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
ANYMAIL = {"SENDGRID_API_KEY": os.environ["SENDGRID_API_KEY"]}
DEFAULT_FROM_EMAIL = "sender@example.com"
```

```python
from swap_layer import get_provider
email = get_provider("email")
result = email.send_email(
    to=["recipient@example.com"], subject="Hello", text_body="Example message",
    reply_to=["support@example.com"],
)
```

For local testing use `EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'`. The `smtp` provider (`communications.email.provider='smtp'`) sends through Django's configured `EMAIL_BACKEND`; with Django's default SMTP backend, Django reads `EMAIL_HOST`, `EMAIL_PORT`, TLS and account settings. When neither `EMAIL_TIMEOUT` nor the mailer's `timeout` option is set, SwapLayer gives the SMTP connection a 30-second timeout.

Use `send_email`, `send_template_email`, and `send_bulk_email` as implemented by your adapter. Django adapter templates are Django template paths rendered by the application. `metadata` passed to a send goes to Anymail's message `metadata` and `tags` (a `tags` string is one tag), never into message headers. The `django` provider returns Anymail's message ID, a sorted list when the service returns one per recipient, or `sent-via-django` when the backend reports none. `validate_webhook_signature` returns `False` for the `django` and `smtp` providers, which have no signed webhooks of their own. Rich provider analytics, suppression management, verification and webhook support are not portable guarantees; inspect the selected adapter and use vendor-specific facilities where needed. The library does not implement consent, deliverability, queueing, or account authorization policies.

Abstract models/admin helpers are under `swap_layer.communications.email.models` and `.admin`. Applications own their concrete models and migrations. Sending uses the caller's account and may incur charges; MCP test sends require explicit client approval.
