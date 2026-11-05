# SwapLayer 1.0 documentation

Start with the [tested installation and configuration examples](../README.md). Current guides:

| Guide | Contents |
| --- | --- |
| [Billing](billing.md) | Stripe, PayPal, Square and capability differences |
| [Email](email.md) | Django email, SMTP and Anymail backend configuration |
| [SMS](sms.md) | Twilio and AWS SNS |
| [Storage](storage.md) | Local, native GCS, Django backends and tenant boundaries |
| [Identity](identity-platform.md) | Django OAuth and management adapters |
| [Verification](identity-verification.md) | Stripe Identity |
| [MCP](mcp.md) | Local tools and credential boundaries |
| [Architecture](architecture.md) | Configuration, adapters and trust boundaries |
| [Release](RELEASE.md) | Verification, immutable versions and owner publishing |

Structured settings are `billing`, `communications`, `storage`, `identity`, and `verification`. Provider labels and method names in these current guides supersede 0.x design notes. Files under `development/` and older module notes record implementation history unless explicitly marked current. They do not promise additional providers or capabilities.

See [CONTRIBUTING.md](../CONTRIBUTING.md), [VERSIONING.md](../VERSIONING.md), and [SECURITY.md](../SECURITY.md) for repository and release rules shared by Claude and Codex.
