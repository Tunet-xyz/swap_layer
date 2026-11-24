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
- The `swaplayer-mcp` server runs on the caller's machine with the caller's
  credentials, over stdio without authentication. Its guidance tools make no
  network calls.

## Threats and controls

| Threat | Package control | Residual responsibility |
| --- | --- | --- |
| Credential exposure | No credentials ship with the package; settings validation hides input values in its errors; configuration errors mask secret values; MCP configuration output shows only public settings fields; `repr()` and `str()` of settings models leave credentials out | Keep secrets in environment variables or a secret manager, and keep settings objects out of logs |
| Cross-tenant storage access | Scoped storage needs an explicit, frozen context with an organization and a `scope_format` containing `{organization_id}`; identity values must be plain path segments and placeholders must be ones the context sets; each operation checks its permission, unscoped access needs `system_context(reason=...)`, and an operation without a context fails; local keys reject `..`, absolute paths, symlinks, junctions, keys that differ from the stored name only in case, and Windows device names | Build contexts from verified identity, and keep storage roots writable only by trusted processes |
| Cross-customer billing data | PayPal and Square `list_invoices(customer_id)` return only that customer's invoices | Check that the caller may see a customer before listing its invoices |
| Forged or replayed webhooks | Stripe events use the SDK's signature check, PayPal events use PayPal's verification API with the `PAYPAL-*` headers, and Square events use an HMAC-SHA256 check with constant-time comparison and a signed `created_at` no more than 25 hours old; a missing secret or malformed signature is refused, and the SMTP provider never reports a payload as verified | Configure webhook secrets, reject unverified events, and de-duplicate events durably (Square event IDs for at least 25 hours) |
| Forged sign-in callbacks | WorkOS accepts a callback only with the OAuth state that the same session stored, once, within 10 minutes; Auth0 keeps its OAuth state and nonce; WorkOS sessions are sealed with a Fernet `cookie_password` | Start and finish each sign-in in the same Django session |
| Injection into provider requests | Identifiers in Auth0, WorkOS, Square, and PayPal REST paths are percent-encoded, empty or dot-only identifiers are refused, and the Auth0 log helpers quote user IDs and validate log types and date bounds (`list_logs` sends its query as given) | Validate user-supplied identifiers before passing them on |
| Hanging or repeated provider calls | 30-second default timeouts for SwapLayer's HTTP session, the PayPal and Square clients, SMTP email sends, and Twilio; bounded retries with backoff; amounts longer than 18 digits are refused before conversion | Review each provider SDK's timeouts, and pass idempotency keys for payment writes |
| Token or session mix-up between tenants | Auth0 management tokens are cached per app, domain, and client; each WorkOS client holds its own credentials | Keep each tenant's provider app configuration separate |
| Unintended provider actions from local tools | MCP tools that send, write, or probe storage are marked as not read-only; the guidance tools are read-only | Approve each test send or storage probe, and use test accounts |
| Supply-chain substitution | Pinned workflow actions, hash-locked build tools, Trusted Publishing, owner-approved releases | Pin and verify releases, and keep provider SDKs updated |

## Required invariants

1. The package contains and fetches no credentials of its own; providers are
   called only with credentials the application configures.
2. Scoped storage operations need an explicit security context; without one
   they fail.
3. Unscoped storage access needs a context built by
   `StorageSecurityContext.system_context(reason=...)`.
4. Billing webhook verification rejects an event whose signature or secret is
   missing or wrong.
5. The MCP guidance tools read only the packaged contract and guides and make
   no network calls.
6. A WorkOS sign-in callback is accepted only with the OAuth state that its own
   session stored.

## Out of scope

Provider services, SDKs, and their data handling; the handling of payment card
data, which belongs to the providers and the application's checkout; Django and
other dependencies; application authentication and authorization; and network
and TLS configuration.

## Residual risks

- Providers differ in capabilities and behavior, and moving between providers
  can require data migration, webhook changes, and application changes.
- Settings hold credentials as plain strings. `repr()` and `str()` leave them
  out, but `model_dump()` and attribute access return them, so a settings
  object logged through those can expose them.
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
