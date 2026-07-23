# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added Stripe revenue discovery: `discover_revenue(month=...)` aggregates one calendar month of paid-invoice revenue per price lookup key, in minor units per currency. Aggregation happens inside the boundary, so no customer, invoice, or payment identifiers are returned; revenue from unkeyed or unknown prices is summed under a `None` lookup key instead of disappearing.

## [0.7.0] - 2026-07-15

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

## [0.6.0] - 2026-06-10

### Added
- Added a Square billing provider using Square REST APIs for customers, payments, catalog products/prices, subscriptions, checkout payment links, invoices, refunds, and webhook verification.
- Added Square configuration support through `SwapLayerSettings`, environment variables, and legacy Django settings.
- Added Square provider tests and documented Stripe, PayPal, and Square capability differences.

### Changed
- Bumped the PyPI package version to `0.6.0`.
- Updated MCP provider metadata to list Square as a payments provider.

## [0.5.0] - 2026-06-10

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

[Unreleased]: https://github.com/Tunet-xyz/swap_layer/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.6.0
[0.5.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.5.0
[0.2.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.2.0
[0.1.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.1.0
