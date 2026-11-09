# SwapLayer audit scope

An assessment must name an immutable Git commit and the exact wheel and sdist
SHA-256 digests. Findings against a moving branch or an unverified local build
are not release evidence.

## In scope

- All code under `src/swap_layer`: settings and factories, the provider
  adapters, storage security and key validation, webhook verification, the
  Django and FastAPI integrations, the Django admin helpers, and the
  `swaplayer-mcp` tools.
- The contract server and agent contract in `mcp/`.
- Build, dependency, and release configuration.

## Out of scope unless separately commissioned

- Provider services and SDKs, Django, and other dependencies.
- The host application's identity verification, authorization, provider
  account and webhook configuration, secret management, and storage
  infrastructure.
- Live behavior of provider accounts.

## Review entry points

Start with the [threat model](THREAT_MODEL.md), the
[architecture](architecture.md) and [storage](storage.md) guides, and the
[security assurance case](SECURITY_ASSURANCE.md). Then trace credentials from
settings to each provider, storage scoping and key validation, webhook
verification, and the MCP tools. Record tool versions, and distinguish
automated findings from manual design conclusions.
