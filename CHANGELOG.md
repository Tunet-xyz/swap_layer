# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A Contributor Covenant 2.1 code of conduct, and issue templates for bug
  reports and feature requests that send vulnerability reports to private
  reporting.

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
  documents. Guides are corrected against the code: the management client
  follows Django `IDENTITY_PROVIDER`, PayPal webhook verification reads its
  transmission fields from the payload, Stripe and Square truncate fractional
  amounts, Twilio opt-out/opt-in only return a status, the `smtp` email provider
  sends through Django's `EMAIL_BACKEND`, and identity and verification settings
  cannot come from environment variables. Historical design notes are labelled.
- Changelog: 0.5.0 to 0.7.0 are marked as never published to PyPI, entries
  are added for the published 0.2.1 and 0.2.4 to 0.2.6, and version links
  point at existing tags and PyPI pages.
- README sections follow the order the Tunet libraries share: features, version
  status, installation, quick start, usage, MCP server, scope and limitations,
  documentation, development, contributing, and license, with PyPI, Python, and
  license badges. Install commands no longer pin the unpublished 1.0.0; the
  version section says how to install it from the tag, and the configuration
  notes say identity and verification settings cannot come from environment
  variables.
- The Product URL points at `www.tunet.xyz`, which serves the product page, and
  the README names the other Tunet libraries. Doc titles no longer carry the
  version, the docs call the owner the owner, and the development notes folder
  points at CONTRIBUTING.md instead of repeating it.

## [1.0.0] - 2026-11-05 (tagged; not yet published to PyPI)

### Changed

- Established the stable Python adapter contract and independent SemVer policy.
- Aligned package, runtime, and MCP versions; updated provider guides and installation metadata.
- Gated every release job on an owner-started manual workflow with pinned actions,
  protected OIDC publishing, and hash-locked build tools.

### Security

- Rejected traversal, absolute paths, symlinks, and junctions in local storage keys;
  enforced safe tenant identities and organization-scoped storage paths.
- Redacted nested credentials from current MCP settings models and omitted raw provider
  exception messages from operational MCP responses.
- Bounded legacy Auth0 management HTTP calls with a 30-second timeout.
- Required an explicit storage security context; isolated Auth0 token caches by
  tenant and client, and suppressed credential-bearing validation input in diagnostics.

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

### Added

- Added provider-neutral webhook endpoint lifecycle operations and Stripe discovery,
  create, update, and explicit delete support with a one-time signing-secret boundary.

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

### Migration

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
