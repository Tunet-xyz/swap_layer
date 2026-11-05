# Local MCP tools in SwapLayer 1.0

Install `SwapLayer[mcp]` and launch `swaplayer-mcp` (or `python -m swap_layer.mcp`). It uses the MCP Python SDK 1.x over stdio. Package and server version are 1.0.0.

This is a local process controlled by its caller. There is no hosted maintainer MCP endpoint, shared provider credential, paid agent account, or maintainer token supplied by the package. GitHub issues, public PRs and comments cannot authorize repository jobs or maintainer agents.

## Configuration

The CLI reads the caller's `SWAPLAYER_` environment configuration. For example:

```bash
# PowerShell: set $env:SWAPLAYER_STORAGE_PROVIDER = "local" instead of export.
export SWAPLAYER_STORAGE_PROVIDER=local
export SWAPLAYER_STORAGE_MEDIA_ROOT=./media
swaplayer-mcp
```

For Django configuration, set `DJANGO_SETTINGS_MODULE` and initialize Django before calling the CLI's `main()` or `create_mcp_server()`. Merely setting the module name does not initialize Django in this CLI. Programmatic callers may instead call `swap_layer.configure(...)` before creating the server. Provider extras are separate from the MCP extra.

## Tools

| Tool | Effect |
| --- | --- |
| `swaplayer_explain` | Current concepts, installation, security and framework guidance |
| `swaplayer_compare_providers` | Capability comparison, including backend selection notes |
| `swaplayer_troubleshoot` | Setup guidance; do not include credentials in error text |
| `swaplayer_get_migration_guide` | Migration checklist and provider data boundaries |
| `swaplayer_get_config` | Current configuration with nested credential fields omitted |
| `swaplayer_list_providers` | Actual factory provider values |
| `swaplayer_get_provider_info` | Provider/backend information |
| `swaplayer_generate_code` | Python examples; returns text without executing it |
| `swaplayer_get_usage_examples` | Example patterns; returns text |
| `swaplayer_setup_quickstart` | Current settings and installation examples |
| `swaplayer_send_test_email` | Sends email using the caller's provider account |
| `swaplayer_send_test_sms` | Sends SMS using the caller's provider account |
| `swaplayer_check_storage` | Configuration check; `test_upload=true` writes and deletes a test file |

Clients must obtain explicit approval before test sends or writes. They can incur charges or modify caller infrastructure. A label saying "test" does not switch provider credentials into sandbox mode. Configure a test account and approved recipient yourself. Do not expose this stdio process as an unauthenticated network service.

Credential fields are removed recursively from configuration output; operational errors omit raw exception messages. This is not a universal secret scanner for arbitrary user text, SDK logging or application data. Do not paste credentials into tool arguments. Application production transactions use the Python adapters behind application authorization, not autonomous documentation tools.

## Public contract

The packaged `swap_layer/mcp/agent-contract.json` describes public capabilities and approval boundaries. From a source checkout, `python mcp/server.py` runs a dependency-free, read-only contract server with resources, prompts and discovery tools. It validates JSON-RPC input, limits message size, and recovers after malformed input. The repository URL is documentation, not a hosted agent endpoint.

Third-party client settings determine model access and approval behavior. Configure the client to approve sensitive operations; repository and package policies do not grant that approval on your behalf.
