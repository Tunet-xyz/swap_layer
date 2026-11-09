# SwapLayer threat model

This threat model covers the SwapLayer package at a specific source revision.
It is not a system accreditation and must be combined with the host
application's identity, data, deployment, and operational threat models, and
with each provider's own security documentation.

## Security objective

SwapLayer calls billing, email, SMS, storage, identity, and verification
providers for the application. It must use only the credentials the
application configures, keep them out of its own output, keep each tenant's
files inside that tenant's storage scope, and verify billing webhooks before
treating them as genuine.

## Assets and trust boundaries

- Protected assets are provider credentials (API keys, webhook secrets, OAuth
  client secrets, WorkOS cookie passwords), tenant files, payment and identity
  operations, verified identity data, and webhook events.
- The application calls SwapLayer in-process and is trusted. Storage security
  contexts carry identity the application has already verified.
- Provider APIs are reached over HTTPS. PayPal and Square default to their
  sandbox environments.
- Webhook requests from providers are untrusted until their signatures are
  verified.
- Local storage relies on the filesystem permissions of its root directory.
- The `swaplayer-mcp` tools run on the caller's machine with the caller's
  credentials, over stdio without authentication. The contract server in
  `mcp/` makes no network calls.

## Threats and controls

| Threat | Package control | Residual responsibility |
| --- | --- | --- |
| Credential exposure | No credentials ship with the package; settings validation hides input values in its errors; configuration errors mask secret values; MCP configuration output redacts recognized credential fields | Keep secrets in environment variables or a secret manager, and keep settings objects out of logs |
| Cross-tenant storage access | Scoped storage needs an explicit context with an organization and a `scope_format` containing `{organization_id}`, checks the permission for each operation, and fails without a context; local keys reject `..`, absolute paths, symlinks, and junctions | Build contexts from verified identity, and keep storage roots writable only by trusted processes |
| Forged billing webhooks | Stripe events use the SDK's signature check, PayPal events use PayPal's verification API, and Square events use an HMAC-SHA256 check with constant-time comparison | Configure webhook secrets, reject unverified events, and de-duplicate events durably |
| Hanging or repeated provider calls | 30-second default timeouts for SwapLayer's HTTP session and the PayPal and Square clients; bounded retries with backoff | Review each provider SDK's timeouts, and pass idempotency keys for payment writes |
| Token or session mix-up between tenants | Auth0 management tokens are cached per app, domain, and client; each WorkOS client holds its own credentials | Keep each tenant's provider app configuration separate |
| Unintended provider actions from local tools | Runtime MCP tools that send, write, or probe storage are marked as not read-only; the contract server is read-only | Approve each test send or storage probe, and use test accounts |
| Supply-chain substitution | Pinned workflow actions, hash-locked build tools, Trusted Publishing, owner-approved releases | Pin and verify releases, and keep provider SDKs updated |

## Required invariants

1. The package contains and fetches no maintainer credentials; providers are
   called only with credentials the application configures.
2. Scoped storage operations need an explicit security context; without one
   they fail.
3. Unscoped storage access needs a context explicitly marked as a system
   context.
4. Billing webhook verification rejects an event whose signature or secret is
   missing or wrong.
5. The contract server reads only its packaged contract and makes no network
   calls.

## Out of scope

Provider services, SDKs, and their data handling; the handling of payment card
data, which belongs to the providers and the application's checkout; Django and
other dependencies; application authentication and authorization; and network
and TLS configuration.

## Residual risks

- Providers differ in capabilities and behavior, and moving between providers
  can require data migration, webhook changes, and application changes.
- Settings hold credentials as plain strings, so a logged settings object can
  expose them.
- Some provider calls are retried after timeouts and server errors, which can
  repeat a write the provider already applied; use idempotency keys.
- Path checks on local storage do not replace a filesystem sandbox against
  concurrent replacement, and local file URLs are unsigned.
- Webhook event de-duplication is in memory and per process.
- Tests use mocks and SDK response objects; they are not live provider
  certification, and SwapLayer has not had an independent security audit.

## Review triggers

Review this model for every new provider or provider SDK major version, and for
every change to storage scoping or key validation, webhook verification,
credential handling or redaction, HTTP timeouts and retries, token caching, or
MCP tools. Record newly accepted residual risks before merge.
