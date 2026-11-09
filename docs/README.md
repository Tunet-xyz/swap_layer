# SwapLayer documentation

Start with the [README](../README.md) for installation and configuration
examples. These guides cover each service.

## Guides

| Guide | Contents |
| --- | --- |
| [Billing](billing.md) | Stripe, PayPal, and Square, and how their capabilities differ |
| [Email](email.md) | Django email, SMTP, and Anymail backend configuration |
| [SMS](sms.md) | Twilio and AWS SNS |
| [Storage](storage.md) | Local, native GCS, and Django backends, and tenant boundaries |
| [Identity](identity-platform.md) | Django OAuth and management adapters |
| [Auth0 and WorkOS](auth0-vs-workos-comparison.md) | How the two identity providers differ in SwapLayer |
| [Verification](identity-verification.md) | Stripe Identity |
| [Architecture](architecture.md) | Configuration, adapters, and trust boundaries |
| [MCP tools](mcp.md) | The local `swaplayer-mcp` tools and their credential boundaries |
| [MCP contract server](../mcp/README.md) | The dependency-free public contract server |

Structured settings are `billing`, `communications`, `storage`, `identity`, and
`verification`. Provider labels and method names in these guides supersede 0.x
design notes. Files under `development/` record implementation history; they do
not promise additional providers or capabilities.

## Security

| Document | Contents |
| --- | --- |
| [Security policy](../SECURITY.md) | Supported versions, private vulnerability reporting, and response targets |
| [Threat model](THREAT_MODEL.md) | Assets, trust boundaries, threats, controls, and residual risks |
| [Security assurance](SECURITY_ASSURANCE.md) | The evidence behind each security claim, and what it does not establish |
| [Audit scope](AUDIT_SCOPE.md) | What a package security review covers and where to start |
| [Secure development](SECURE_DEVELOPMENT.md) | How changes are designed, tested, reviewed, and released |

## Releases and contributing

| Document | Contents |
| --- | --- |
| [Changelog](../CHANGELOG.md) | Changes in each version, and which versions reached PyPI |
| [Versioning policy](../VERSIONING.md) | SemVer and release rules shared by the Tunet libraries |
| [Release procedure](RELEASE.md) | Verification, build, and owner-approved publication |
| [Contributing](../CONTRIBUTING.md) | How to report issues and propose changes |
| [Code of conduct](../CODE_OF_CONDUCT.md) | Expected behavior in project spaces |

## Links

- [PyPI](https://pypi.org/project/SwapLayer/)
- [GitHub](https://github.com/Tunet-xyz/swap_layer)
- [Product page](https://www.tunet.xyz/engineering/swap-layer/)
- [Tunet open-source libraries](https://www.tunet.xyz/engineering/)
