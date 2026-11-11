# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A Contributor Covenant 2.1 code of conduct, and issue templates for bug
  reports and feature requests that send vulnerability reports to private
  reporting.
- A CodeQL workflow (`codeql.yaml`) with the security-extended queries, which
  only the owner starts, and weekly Dependabot updates for pip and GitHub
  Actions dependencies, as in the other Tunet libraries.
- `verification.stripe_webhook_secret` (environment
  `SWAPLAYER_VERIFICATION_STRIPE_WEBHOOK_SECRET`) holds the Stripe Identity
  webhook signing secret; the legacy `STRIPE_IDENTITY_WEBHOOK_SECRET` setting is
  still read.
- Auth0 apps accept `management_client_id` and `management_client_secret` for
  the Management API.
- `IdentityPlatformError`, and its subclass `OAuthStateError`, in
  `swap_layer.identity.platform.adapter`.
- `TwilioSMSProvider(timeout=...)` and
  `SquarePaymentProvider(webhook_max_age=...)`.
- The MCP `explain` tool and the `opensource://swap_layer/docs/<topic>`
  resources serve the README, SECURITY.md, and the docs guides as packaged with
  the release; `tools/sync_mcp_guidance.py` refreshes the packaged copies.
- `get_payment_provider(provider)` (also `swap_layer.billing.get_provider`)
  builds a named billing provider from its own settings block, or else its
  legacy Django settings, instead of the configured one.

### Changed

- The security policy uses the layout shared by the Tunet libraries: private
  reporting through the Security tab or by email, one set of response targets
  (critical fixes within 7 days instead of 14), package scope, and secure-use
  guidance. Its supported-versions table lists 1.0.x only, replacing rows for
  0.3.x and for a 0.4.x line that was never released.
- `VERSIONING.md` is worded for outside readers; its rules are unchanged.
- Documentation has the layout shared by the Tunet libraries: a reworked docs
  index, the same sections in the release procedure and MCP README, and new
  threat model, security assurance, audit scope, and secure-development
  documents. Guides are corrected against the code (for example, the `smtp`
  email provider sends through Django's `EMAIL_BACKEND`), and historical design
  notes are labelled.
- Changelog: 0.5.0 to 0.7.0 are marked as never published to PyPI, entries
  are added for the published 0.2.1 and 0.2.4 to 0.2.6, and version links
  point at existing tags and PyPI pages.
- README sections follow the order the Tunet libraries share: features, version
  status, installation, quick start, usage, MCP server, scope and limitations,
  documentation, development, contributing, and license, with PyPI, Python, and
  license badges. Install commands no longer pin the unpublished 1.0.0, and the
  version section says how to install from `main` until the next release.
- The Product URL points at `www.tunet.xyz`, which serves the product page, and
  the README names the other Tunet libraries. Doc titles no longer carry the
  version, the docs call the owner the owner, and the development notes folder
  points at CONTRIBUTING.md instead of repeating it.
- The identity management design note moved to
  `docs/development/identity-management-implementation.md`, matching the other
  kebab-case names.
- The copyright year in LICENSE and the README is 2026, the year the project
  started.
- One MCP server: `swaplayer-mcp` (also `python -m swap_layer.mcp`, and
  `python mcp/server.py` from a checkout) serves the public agent contract as
  `swap-layer-public-contract-mcp`, with resources under
  `opensource://swap_layer/`, 17 tools, and 4 prompts, and needs no MCP SDK;
  `SwapLayer[mcp]` is needed only for `create_mcp_server()`. Tools have plain
  names such as `get_config` and `send_test_email`
  (`swaplayer_setup_quickstart` is now `prepare_provider_setup`, and
  `swaplayer_get_migration_guide` is `plan_provider_migration`), arguments are
  camelCase (`projectType`, `fromProvider`, `toProvider`, `useCase`,
  `errorMessage`, `testUpload`), and the `explain` topics are the packaged
  guides.
- MCP `get_config` returns only public settings fields, and
  `swaplayer_check --verbose` masks every other value. `troubleshoot` matches
  `errorMessage` without returning it, and `check_storage(testUpload=true)`
  works under `swaplayer-mcp-check/`. The MCP client examples name the server
  `swaplayer-mcp` and use `SWAPLAYER_` variables, and the VS Code example uses
  VS Code's `servers` format.
- The billing service is `billing` in the docs, the MCP tools, and error
  messages; `get_provider("payments")` and `"payment"` still work.
- Stripe and Square reject a fraction of a minor unit with
  `PaymentValidationError` instead of truncating it, and read an integral
  string as minor units. Stripe, Square, and PayPal reject amounts of more than
  18 digits or 64 characters; for a PayPal value string, which is in major
  units, the 18 digits count minor units.
- PayPal `verify_webhook_signature(payload, signature, headers=request.headers)`
  reads the `PAYPAL-*` transmission headers, and a missing header raises. The
  PayPal customer methods manage a local `paypal:<email>` handle and say so
  with `"local_only": True`, and `create_billing_portal_session` is unsupported
  for PayPal.
- Square webhooks need a signed `created_at` at most 25 hours old and at most
  5 minutes in the future (`webhook_max_age=None` turns the check off), and
  Stripe Identity `handle_webhook` needs a webhook secret.
- A WorkOS `cookie_password` must be a Fernet key, which WorkOS SDK 10 uses to
  seal sessions, in `identity.workos_apps` and the legacy `WORKOS_APPS` alike.
- WorkOS `get_authorization_url` keeps the OAuth state in the session, and
  `exchange_code_for_user(request, code)` accepts a callback only with that
  state, once, within 10 minutes; otherwise it raises `OAuthStateError`.
- Identity clients and `get_management_client()` read `SWAPLAYER.identity`
  (`provider`, `workos_apps`, `auth0_apps`, `auth0_domain`) before the legacy
  `IDENTITY_PROVIDER`, `WORKOS_APPS`, `AUTH0_APPS`, and
  `AUTH0_DEVELOPER_DOMAIN` settings.
- Identifiers in Auth0, WorkOS, Square, and PayPal REST paths are
  percent-encoded, and empty or dot-only identifiers raise `ValueError`. Auth0
  log helpers validate log types and date bounds and quote user IDs, and the
  Auth0 management token cache key starts with `swap_layer:`.
- `StorageSecurityContext` is immutable. `organization_id`, `platform`, and
  `role` must be plain path segments, a scope may use only the plain
  `{organization_id}`, `{platform}`, and `{role}` placeholders and only ones the
  context sets, and permissions come from a known role or an explicit
  permission set (a context with neither has none). System access is only
  through `system_context(reason=...)`, `upload_file(public=True)` needs the
  `ADMIN` permission, and in `upload_file` and `upload_from_string` caller
  metadata cannot replace `uploaded_by`, `organization_id`, or `platform`.
- Local storage keys must match stored names exactly, so on a case-insensitive
  file system a key that differs only in case is refused; on Windows, device
  names such as `CON` and `NUL` and segments ending in a dot or space are
  refused. Local metadata keys cannot contain `:`, values must be single-line,
  and metadata sidecars are UTF-8.
- Email sends get a 30-second SMTP timeout when `EMAIL_TIMEOUT` (or the
  mailer's `timeout`) is unset, and Twilio requests time out after 30 seconds.
  Email `metadata` goes to Anymail's `metadata` and `tags` (a `tags` string is
  one tag), not to message headers.
- The SMTP provider's `validate_webhook_signature` returns `False`, Twilio
  `opt_out_number` and `opt_in_number` return the status `not_supported`, and
  SNS validates numbers with the provider's own AWS settings.
- Django app configs are `BillingAppConfig`, `EmailAppConfig`, `SMSAppConfig`,
  `IdentityPlatformAppConfig`, `IdentityVerificationAppConfig`, and
  `StorageAppConfig`, with the labels `swap_layer_billing`, `swap_layer_email`,
  `swap_layer_sms`, `swap_layer_identity_platform`,
  `swap_layer_identity_verification`, and `swap_layer_storage`.
- Every service error (`PaymentError`, `EmailSendError`,
  `TemplateNotFoundError`, `SMSError`, `IdentityVerificationError`,
  `StorageError`, and the new `IdentityPlatformError`) derives from
  `SwapLayerError`.
- Settings reject unknown nested keys (legacy `WORKOS_APPS` and `AUTH0_APPS`
  entries may still carry extra keys), and every settings field, identity and
  verification included, can come from a `SWAPLAYER_` variable; a misspelt
  variable fails validation. Configuration errors describe a rejected value
  without repeating it, show only public settings values (every other value,
  including one under a misspelt key, is masked), name real settings paths,
  and link to the `docs/<area>.md` guides.
- Package metadata lists the Django 4.2, 5.2, and 6.1 series and
  `Typing :: Typed`, and its keywords are sorted, add `mcp`, and drop
  `python`. The sdist includes `examples/`, `tools/`, and `CODE_OF_CONDUCT.md`.
- `publish.yaml` runs `twine check --strict`, and the tests workflow also runs
  the suite on Django 4.2 in a `minimum-dependencies` job.
- The billing migration command is `swaplayer_migrate_billing_provider`, with
  the same arguments (`from_provider to_provider`, `--dry-run` or `--confirm`,
  `--model app.Model`), so SwapLayer's management commands share the
  `swaplayer_` prefix. The docs describe it and `swaplayer_check`.
- The MCP server cuts the method names, parameters, and parse errors it
  quotes back in error replies to 200 characters, as the other Tunet MCP
  servers do.

**Upgrading:**

- Look Django apps up by their new labels, for example
  `apps.get_app_config("swap_layer_billing")` instead of `"billing"`.
- Give WorkOS a Fernet key as its `cookie_password`, for example from
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Pass the request headers to PayPal webhook verification, keep Square
  `event_id` values for at least 25 hours, and configure a Stripe Identity
  webhook secret before handling those webhooks.
- Call `exchange_code_for_user` from the callback for a sign-in that
  `get_authorization_url` started in the same session.
- Build system storage contexts with `system_context(reason=...)`, give tenant
  contexts a role or explicit permissions, and give `public=True` uploads the
  `ADMIN` permission.
- Update MCP clients to the new tool names and camelCase arguments, and remove
  unknown keys from nested settings.

### Deprecated

- The former Django app config class names (`BillingConfig`, `EmailConfig`,
  `SmsConfig`, `AuthenticationConfig`, `IdentityConfig`, `StorageConfig`) still
  import through 1.x, with a `DeprecationWarning`.
- The `migrate_payment_provider` command, which prints a deprecation notice and
  runs `swaplayer_migrate_billing_provider` through 1.x.

### Removed

- The `swaplayer_*` MCP tool names, with no aliases, and the `installation`,
  `django-integration`, and `providers` topics of `explain`.
- The unused `swap_layer.config` module, and an Auth0 `management.py` module
  that the `management` package shadowed.
- `AGENTS.md`, `CLAUDE.md`, and `.github` from the sdist.

### Fixed

- The email and SMS Django apps load: their app names pointed at
  `swap_layer.email` and `swap_layer.sms`. Docstring imports use the
  `swap_layer.communications` paths.
- The Auth0 client saves its OAuth state and nonce, so the callback no longer
  fails with `MismatchingStateError`.
- The Django email provider returns Anymail's message ID (a sorted list when
  the service returns one per recipient) instead of raising after a successful
  send.
- A missing or non-ASCII Square webhook signature is rejected as invalid, and
  PayPal webhook verification accepts a text payload.
- The billing migration command creates customers in the target provider: in
  a project configured through `SWAPLAYER` it created them in the configured
  provider again. An unknown or unconfigured target is a `CommandError`.

## [1.0.0] - 2026-11-05 (tagged; not yet published to PyPI)

### Added

- Added provider-neutral webhook endpoint lifecycle operations and Stripe discovery,
  create, update, and explicit delete support with a one-time signing-secret boundary.

### Changed

- Established the stable Python adapter contract and independent SemVer policy.
- Aligned package, runtime, and MCP versions; updated provider guides and installation metadata.
- Gated every release job on an owner-started manual workflow with pinned actions,
  protected OIDC publishing, and hash-locked build tools.

### Fixed

- Converted PayPal HUF, JPY and TWD using their zero-decimal rules; rejected fractional/non-finite minor amounts and prevented decimal truncation.
- Restricted the MCP SDK to its supported 1.x API and tested the actual tool registry.
- Used the storage adapter API in MCP upload probes and the current settings API in
  the WorkOS management factory.
- Aligned WorkOS management operations with the shared adapter interfaces and current
  SDK session API. Rejected unsupported user-specific event queries explicitly.
- Fixed standalone Stripe/Twilio initialization, SNS configuration and imports, native
  GCS settings, and compound environment-variable field names.
- Normalized Django storage listing and Stripe Identity responses, updated promotion
  codes for the current Stripe API, and preserved positional idempotency arguments.
- Fixed empty admin displays and numeric quota formatting on current Django; preserved
  display metadata using Django's supported decorators. Full source type checks pass.

### Security

- Rejected traversal, absolute paths, symlinks, and junctions in local storage keys;
  enforced safe tenant identities and organization-scoped storage paths.
- Redacted nested credentials from current MCP settings models and omitted raw provider
  exception messages from operational MCP responses.
- Bounded legacy Auth0 management HTTP calls with a 30-second timeout.
- Required an explicit storage security context; isolated Auth0 token caches by
  tenant and client, and suppressed credential-bearing validation input in diagnostics.

## [0.7.0] - 2026-07-15 (not published to PyPI; included in 1.0.0)

### Added

- Added Stripe catalog-admin discovery for billing meters, products, prices, and Entitlements features.
- Added complete auto-paginated Stripe catalog listing helpers.
- Added mutable price updates and guarded immutable price replacement with lookup-key transfer.
- Added Stripe Entitlements feature and product-feature attachment operations.
- Added a framework-neutral configuration core with thin Django and FastAPI adapters.
- Added the public agent-operability contract and expanded `swaplayer-mcp` guidance surfaces.

### Changed

- Expanded normalized Stripe catalog objects with the fields required for desired-state reconciliation.
- Stabilized optional-provider imports and normalized provider behavior for installed-package use.

## [0.6.0] - 2026-06-10 (not published to PyPI; included in 1.0.0)

### Added

- Added a Square billing provider using Square REST APIs for customers, payments, catalog products/prices, subscriptions, checkout payment links, invoices, refunds, and webhook verification.
- Added Square configuration support through `SwapLayerSettings`, environment variables, and legacy Django settings.
- Added Square provider tests and documented Stripe, PayPal, and Square capability differences.

### Changed

- Bumped the PyPI package version to `0.6.0`.
- Updated MCP provider metadata to list Square as a payments provider.

## [0.5.0] - 2026-06-10 (not published to PyPI; included in 1.0.0)

### Added

- Added a PayPal billing provider using PayPal REST APIs for products, plans, subscriptions, checkout orders, invoices, refunds, and webhook verification.
- Added PayPal configuration support through `SwapLayerSettings`, environment variables, and legacy Django settings.
- Added PayPal provider tests and settings/factory coverage.

### Changed

- Bumped the PyPI package version to `0.5.0`.
- Documented the PayPal install/config flow and PayPal versus Stripe billing capability differences.

## [0.3.0] - 2026-02-26

### Changed

- **BREAKING**: `scope_format` is now a **required** parameter on `StorageSecurityContext`. Callers must explicitly declare their path scoping convention (e.g. `scope_format='{organization_id}'`). No implicit fallback.
- Removed `path_prefix` field from `StorageSecurityContext` - use `scope_format` instead.
- Removed hardcoded `orgs/` path prefix. Path convention is now fully user-controlled via `scope_format`.
- Centralised prefix resolution into `_resolve_prefix()` (used by both `scope_path()` and `validate_scoped_path()`).

**Upgrading:**

- Replace `StorageSecurityContext(organization_id='org-456', ...)` with `StorageSecurityContext(scope_format='{organization_id}', organization_id='org-456', ...)`
- Replace any `path_prefix='custom/prefix'` with `scope_format='custom/prefix'`

## [0.2.7] - 2026-02-11

### Added

- **Storage Security**: Added `ScopedStorageProvider` for tenant-isolated storage operations
- **Storage Security Context**: Added `StorageSecurityContext` for RLS-style access control in storage layer
- **Storage Permissions**: Added `StoragePermission` enum for fine-grained access control
- **Context Manager**: Added `storage_context()` context manager for scoped storage operations
- **Validation**: Added `validate_storage_context()` for security context validation
- **GCS Provider**: Enhanced GCS storage provider integration with security context support

### Changed

- Storage module now supports automatic path prefixing with `orgs/{organization_id}/` for multi-tenant isolation
- Storage operations now validate security context before executing

## [0.2.6] - 2026-01-18

### Added

- `clear_session()` on the identity platform adapter, implemented for Auth0 and
  WorkOS, removes provider-specific session data at logout.

### Fixed

- Start WorkOS AuthKit sign-in with the `"authkit"` provider string and serialize
  the WorkOS user with `model_dump()`, as the WorkOS SDK 5.x API expects.

## [0.2.5] - 2026-01-13

### Changed

- Each `WorkOSClient` creates its own WorkOS SDK 5.x client with its own
  credentials, replacing global SDK configuration and thread locking.

## [0.2.4] - 2026-01-13

### Fixed

- Stop passing an unused `client_id` to WorkOS `authenticate_with_code`.

## [0.2.3] - 2026-01-13

### Fixed

- **CRITICAL**: Fixed provider dependencies being loaded even when not used. All provider modules now use lazy imports via `__getattr__`, ensuring that:
  - You can use WorkOS without having Stripe installed
  - You can use Stripe without having Twilio installed
  - Optional dependencies are truly optional
  - No import errors for unused providers
- **SECURITY**: Fixed secret values being exposed in error messages. All sensitive configuration errors now properly mask secrets while still providing helpful debugging information:
  - Stripe API keys are masked (shows only prefix/suffix like `sk_t********abcd`)
  - Twilio Account SIDs are masked
  - Phone numbers are masked (CRITICAL: previously exposed full phone numbers)
  - Cookie passwords remain completely hidden (only length shown)
  - Added `_mask_secret()` helper function for consistent masking across all error messages

### Added

- Test suite for optional dependencies (`test_optional_dependencies.py`)
- Enhanced README documentation about optional dependency installation
- Security tests verifying that secrets are properly masked in error messages

## [0.2.2] - 2026-01-12

### Fixed

- Removed duplicate return statement in MCP server `_get_config` function

### Changed

- Enhanced MCP documentation with detailed VS Code/GitHub Copilot setup instructions
- Updated MCP config example with `PYTHONPATH` environment variable
- Added `examples/vscode-mcp.json` template for easy VS Code integration

## [0.2.1] - 2026-01-12

### Changed

- Import the Stripe, Twilio, and local storage providers inside their factory
  functions, so unused providers are not imported.

## [0.2.0] - 2026-01-12

### Added

- Initial release of SwapLayer
- Email module with Django/SMTP providers
- Billing module with Stripe provider
- SMS module with Twilio and AWS SNS providers
- Storage module with local and Django storage providers
- Identity Platform module with WorkOS and Auth0 providers
- Identity Verification module with Stripe Identity provider
- MCP (Model Context Protocol) server for AI assistant integration
  - Configuration inspection and provider discovery
  - Test email/SMS sending capabilities
  - Storage connectivity verification
  - Provider information lookup
  - CLI command: `swaplayer-mcp`
- Unified `get_provider()` API for all modules
- Pydantic-based settings management with validation
- Rich error messages with hints and documentation links
- Django admin mixins for all modules
- Abstract model mixins for common patterns

### Security

- Added request timeouts to all HTTP calls (30s default)
- Thread-safe WorkOS client implementation
- Sensitive configuration values masked in error output
- Automatic credential redaction in MCP server responses

## [0.1.0] - 2026-01-07

### Added

- Initial beta release

[Unreleased]: https://github.com/Tunet-xyz/swap_layer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v1.0.0
[0.3.0]: https://pypi.org/project/SwapLayer/0.3.0/
[0.2.7]: https://pypi.org/project/SwapLayer/0.2.7/
[0.2.6]: https://pypi.org/project/SwapLayer/0.2.6/
[0.2.5]: https://pypi.org/project/SwapLayer/0.2.5/
[0.2.4]: https://pypi.org/project/SwapLayer/0.2.4/
[0.2.3]: https://pypi.org/project/SwapLayer/0.2.3/
[0.2.2]: https://pypi.org/project/SwapLayer/0.2.2/
[0.2.1]: https://pypi.org/project/SwapLayer/0.2.1/
[0.2.0]: https://pypi.org/project/SwapLayer/0.2.0/
[0.1.0]: https://pypi.org/project/SwapLayer/0.1.0/
