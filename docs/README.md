# SwapLayer Documentation

All documentation in one place. Pick your module:

## Current Capability Status

| Module | Current provider surface |
|--------|--------------------------|
| Email | Direct SMTP plus Django-anymail for SendGrid, Mailgun, SES, Postmark, and similar providers |
| Billing | Stripe, PayPal, and Square adapters; Stripe has the broadest billing feature coverage |
| SMS | Twilio and AWS SNS adapters |
| Storage | Local files, direct GCS, and Django-storage backends for S3/Azure/GCS |
| Identity | WorkOS/Auth0 OAuth and management helpers |
| Verification | Stripe Identity |
| MCP | Runtime `swaplayer-mcp` plus public-agent contract in `../mcp/` |

Older architecture notes may mention planned providers or adapter stubs. Treat this table and the package tests as the current source of truth for share-ready capability claims.

## 📦 Core Modules

- **[email.md](email.md)** - Send emails through any provider
- **[billing.md](billing.md)** - Accept payments without vendor lock-in
- **[sms.md](sms.md)** - Send SMS messages
- **[storage.md](storage.md)** - Store files anywhere
- **[identity-platform.md](identity-platform.md)** - OAuth/SSO authentication
- **[identity-verification.md](identity-verification.md)** - KYC verification

## 🤖 AI Integration

- **[mcp.md](mcp.md)** - MCP server for AI assistant integration

## 🏗️ Architecture

- **[architecture.md](architecture.md)** - Core patterns and design philosophy

## 👩‍💻 Contributing

- **[development/contributing.md](development/contributing.md)** - How to contribute

---

## Quick Start

```python
from swap_layer import get_provider

# Use any module
email = get_provider('email')
payments = get_provider('payments')
sms = get_provider('sms')
```

See module docs above for complete details.
