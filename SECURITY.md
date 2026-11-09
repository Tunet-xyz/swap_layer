# Security policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

Security fixes ship as new 1.0.x releases on
[PyPI](https://pypi.org/project/SwapLayer/). SwapLayer 1.0.0 is tagged (`v1.0.0`)
but not yet published there; PyPI still serves 0.3.0, and versions below 1.0
are not supported.

## Reporting a vulnerability

Do not report a suspected vulnerability in a public issue, pull request, or
discussion. Report it privately in either of these ways:

- On GitHub, open the repository's **Security** tab and choose
  **Report a vulnerability**
  ([direct link](https://github.com/Tunet-xyz/swap_layer/security/advisories/new)).
- Email **alex@tunet.xyz**.

Include a description, the affected versions, reproduction steps, the potential
impact, and any suggested mitigation. Use synthetic examples; do not send
credentials, personal data, or production samples.

## Response targets

We aim to acknowledge reports within 48 hours and provide an initial assessment
within five business days. Targets begin when severity is confirmed:

| Severity | Containment/mitigation target | Fix target |
| --- | --- | --- |
| Critical | 24 hours | 7 days |
| High | 3 business days | 14 days |
| Moderate | 10 business days | 30 days |
| Low | 30 days | 90 days |

These are maximum targets, not a promise to delay urgent fixes. If a complete
fix needs longer, we will prioritize a safe mitigation, coordinate disclosure,
and communicate a revised timeline privately. Please allow a reasonable period
for remediation before public disclosure. We will request a CVE and publish a
GitHub security advisory when impact warrants it.

## Scope

### In scope

- Storage keys or tenant scopes that escape the configured root or
  organization prefix, through traversal, absolute paths, symlinks, or
  junctions.
- Provider credentials exposed through MCP output, diagnostics, exception
  messages, or logs.
- Webhook signature verification that accepts an unsigned or forged event.
- Auth0 or WorkOS sessions or token caches shared across tenants or
  applications.
- Provider HTTP calls that can hang without a timeout.
- MCP tools marked read-only that send messages, write files, or change
  provider state.

### Out of scope

- Vulnerabilities in provider services or SDKs (Stripe, PayPal, Square,
  Twilio, AWS, Google Cloud, Azure, WorkOS, and Auth0); report them to the
  provider.
- Vulnerabilities in Django or other dependencies; report them to those
  projects.
- Provider account, credential, and webhook endpoint configuration, which the
  application owns.
- Issues that require physical access to the server.

## Secure use

- Keep provider secrets in environment variables or a secret manager, never in
  source control, and rotate provider API keys regularly.
- Use HTTPS in production, verify provider webhook signatures, and give WorkOS
  a cookie password of at least 32 characters.
- For tenant isolation, use `StorageSecurityContext` with an explicit
  `scope_format` through `storage_context()` or `ScopedStorageProvider`.
  Contexts trust identity your application has already verified. With several
  WorkOS or Auth0 apps, keep each tenant's app configuration separate.
- Keep local storage roots and their parents writable only by trusted
  application processes. Path checks do not replace a filesystem sandbox
  against concurrent replacement, and local URLs are unsigned, so control
  access to private files in your application.
- Store sealed WorkOS sessions securely in Django sessions.
- The MCP tools run locally with your own credentials. Test sends and storage
  probes can cause provider charges or file changes, so approve each such call;
  no maintainer agent, account, or token is involved.

The [threat model](docs/THREAT_MODEL.md),
[security assurance case](docs/SECURITY_ASSURANCE.md),
[audit scope](docs/AUDIT_SCOPE.md), and
[secure development](docs/SECURE_DEVELOPMENT.md) documents describe the design
assumptions, evidence, and residual risks in more detail.

## Releases and advisories

Security fixes are released from a reviewed commit on `main` through the
owner-approved trusted-publishing workflow described in
[docs/RELEASE.md](docs/RELEASE.md). Workflows run only when the owner starts
them, and PyPI uploads use short-lived OIDC credentials from a protected
environment. Stable API changes follow [VERSIONING.md](VERSIONING.md); a
security fix may intentionally reject previously accepted ambiguous input, with
the compatibility and migration impact explained in the release notes. Pin and
verify release artifacts, watch this repository's security advisories, test
your integration, and upgrade supported versions promptly.
