# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [0.2.2] - 2026-01-12

### Fixed
- Removed duplicate return statement in MCP server `_get_config` function

### Changed
- Enhanced MCP documentation with detailed VS Code/GitHub Copilot setup instructions
- Updated MCP config example with `PYTHONPATH` environment variable
- Added `examples/vscode-mcp.json` template for easy VS Code integration
## [Unreleased]

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

[Unreleased]: https://github.com/Tunet-xyz/swap_layer/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.2.0
[0.1.0]: https://github.com/Tunet-xyz/swap_layer/releases/tag/v0.1.0
