# Architecture

`swap_layer.configure` stores process-local validated settings. `get_provider(service)` selects adapters for `email`, `billing` (`payments` is still accepted), `sms`, `storage`, `identity`, or `verification`. Factories import optional providers when requested. Core imports do not configure Django or require every optional SDK.

Configuration groups are `billing`, `communications.email`, `communications.sms`, `storage`, `identity`, and `verification`. Plain Python can configure supported standalone adapters explicitly. Django loads `SWAPLAYER` or legacy settings; email and OAuth use Django facilities, and the Django apps carry `swap_layer_<area>` labels such as `swap_layer_billing`. With `swap_layer` in `INSTALLED_APPS`, `python manage.py swaplayer_check` validates the configuration (`--module billing` checks one area, and `--verbose` shows the settings with every non-public value masked); `swap_layer.billing` adds `swaplayer_migrate_billing_provider`, described in the [billing guide](billing.md#moving-customers-to-another-provider). The FastAPI adapter stores configuration on application state and does not supply authentication, routes or middleware.

Adapters expose common method signatures and normalized results. They do not erase vendor differences. Vendor SDK objects, provider-specific extensions, dashboard state, customer IDs, webhooks and feature availability require application review. Unsupported operations must remain explicit.

Storage contexts consume trusted identity, check permissions, prefix object keys and audit operations. Applications verify identity, choose organizations and keep storage credentials/ACLs private. Local filesystem checks assume trusted OS writers and do not replace an OS sandbox.

The MCP server (`swaplayer-mcp`) is a caller-owned stdio process that serves the public agent contract, the packaged guides, configuration inspection and approved test operations. It does not connect users to the owner's agents or accounts. Public contribution text is untrusted and cannot authorize paid work, credentials, merges or publishing.

Applications own concrete Django models/migrations, callback URLs and session checks, provider account policies, queueing, retry/idempotency design, privacy retention and end-user authorization. Keep those controls at the application boundary; do not infer authorization from normalized provider data.

See the current [module guides](README.md), [security policy](../SECURITY.md), and [release standards](../VERSIONING.md). Older implementation notes describe previous designs and planned features rather than the 1.0 compatibility contract.
