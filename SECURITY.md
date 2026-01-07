# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in SwapLayer, please report it responsibly.

### How to Report

**Please DO NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email security concerns to: **alex@coded.uk**

Include the following in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability within 7 days
- **Resolution**: Critical issues will be patched within 14 days
- **Disclosure**: We will coordinate disclosure timing with you

### Security Best Practices for Users

When using SwapLayer:

1. **Never commit secrets** - Use environment variables for API keys
2. **Use HTTPS** - Always use secure connections in production
3. **Keep dependencies updated** - Run `pip install --upgrade swap-layer`
4. **Validate webhooks** - Always verify webhook signatures from providers
5. **Use strong cookie passwords** - WorkOS requires 32+ character passwords

### Known Security Considerations

- **Multi-tenant isolation**: When using multiple WorkOS/Auth0 apps, ensure proper tenant isolation
- **Session management**: Store sealed sessions securely in Django sessions
- **API key rotation**: Implement regular rotation of provider API keys

## Security Features

SwapLayer includes several security features:

- ✅ Request timeouts to prevent hanging connections
- ✅ Thread-safe provider clients
- ✅ Sensitive data masking in error messages
- ✅ Input validation via Pydantic
- ✅ Type hints for static analysis
