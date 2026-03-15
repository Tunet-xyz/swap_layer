# SwapLayer Documentation

All documentation in one place. Pick your module:

## 📦 Core Modules

- **[email.md](email.md)** - Send emails through any provider
- **[billing.md](billing.md)** - Accept payments without vendor lock-in
- **[sms.md](sms.md)** - Send SMS messages
- **[storage.md](storage.md)** - Store files anywhere
- **[identity-platform.md](identity-platform.md)** - OAuth/SSO authentication
- **[identity-verification.md](identity-verification.md)** - KYC verification

## 🤖 AI Integration

- **[mcp.md](mcp.md)** - MCP server for AI assistant integration
- **[llm-agents.md](llm-agents.md)** - LLM agent use cases for solo development

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
