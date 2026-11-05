# Security Policy

## Supported Versions

The active security line is 1.x. Pre-1.0 rows are retained as historical release information and no longer indicate active security support.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in SwapLayer, please report it responsibly.

### How to Report

**Please DO NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email security concerns to: **alex@tunet.xyz**

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

1. **Never commit secrets** — Use environment variables for API keys
2. **Use HTTPS** — Always use secure connections in production
3. **Keep dependencies updated** — Run `pip install --upgrade SwapLayer`
4. **Validate webhooks** — Always verify webhook signatures from providers
5. **Use strong cookie passwords** — WorkOS requires 32+ character passwords
6. **Scope storage paths** — Use `scope_format` on `StorageSecurityContext` for tenant isolation

### Known Security Considerations

- **Multi-tenant isolation**: When using multiple WorkOS/Auth0 apps, ensure proper tenant isolation
- **Scoped storage**: Use `ScopedStorageProvider` with `StorageSecurityContext` for RLS-style access control in the storage layer
- **Session management**: Store sealed sessions securely in Django sessions
- **API key rotation**: Implement regular rotation of provider API keys

## Security Features

SwapLayer includes several security features:

- ✅ Request timeouts to prevent hanging connections (30s default)
- Instance-owned provider clients; applications manage concurrency and lifetimes
- Nested credential redaction in MCP configuration and input-suppressed configuration diagnostics
- ✅ Input validation via Pydantic
- ✅ Type hints for static analysis
- ✅ Scoped storage with tenant-isolated path prefixing
- Lazy factory imports for optional providers

## Local tools and trust boundaries

MCP runs locally with caller-owned credentials; it does not expose maintainer agents, tokens, or accounts. Clients must approve test sends and writes. Public PRs/comments cannot authorize repository agents or workflows. Entry-point Actions are manual and owner-gated; PyPI publishing uses an owner-reviewed environment and short-lived OIDC identity.

Storage contexts require trusted, already-verified identity and an explicit organization scope. Local storage roots and their parents must not be writable by untrusted OS users; path checks do not replace a filesystem sandbox against concurrent replacement. Local URLs are unsigned and need application access control. Provider mocks and static scans do not constitute an independent security audit.
