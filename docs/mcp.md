# MCP server

`swaplayer-mcp` is SwapLayer's local stdio MCP server. `pip install SwapLayer` installs it, and it needs no MCP SDK. `python -m swap_layer.mcp` starts the same server, and so does `python mcp/server.py` from a source checkout. Package and server version are 1.0.0.

This is a local process controlled by its caller. There is no hosted MCP endpoint, shared provider credential, paid agent account, or owner token supplied by the package. GitHub issues, public PRs and comments cannot authorize repository jobs or the owner's agents.

## Configuration

The server reads the caller's `SWAPLAYER_` environment configuration. For example:

```bash
# PowerShell: set $env:SWAPLAYER_STORAGE_PROVIDER = "local" instead of export.
export SWAPLAYER_STORAGE_PROVIDER=local
export SWAPLAYER_STORAGE_MEDIA_ROOT=./media
swaplayer-mcp
```

Every settings field has an environment path, identity and verification included (for example `SWAPLAYER_IDENTITY_WORKOS_APPS_DEFAULT_API_KEY`, `SWAPLAYER_VERIFICATION_STRIPE_SECRET_KEY` and `SWAPLAYER_RAISE_ON_ERROR`), and a misspelt `SWAPLAYER_` variable fails validation. The command does not read `DJANGO_SETTINGS_MODULE`. Programmatic callers may instead configure SwapLayer (`swap_layer.configure(...)`, or Django settings after `django.setup()`) before calling `main()` or `create_mcp_server()`. Provider extras such as `SwapLayer[stripe]` are separate. [`mcp-config-example.json`](mcp-config-example.json) and [`examples/vscode-mcp.json`](../examples/vscode-mcp.json) show client settings, the second in VS Code's `servers` format.

## Contract, resources and prompts

The server serves the packaged public agent contract (`swap_layer/mcp/agent-contract.json`) as `swap-layer-public-contract-mcp`. Its resources are under `opensource://swap_layer/`: `agent-contract`, `overview`, `public-apis`, `workflows`, `browser-surfaces`, `security-and-audit`, and `docs/<topic>` for the 11 packaged guides. Its prompts are `agent_onboarding`, `onboard_service`, `choose_provider` and `migrate_provider`, with snake_case arguments such as `user_goal` and `from_provider`. It validates JSON-RPC input, limits message size, and recovers after malformed input. The repository URL is documentation, not a hosted agent endpoint.

## Tools

Tool arguments are camelCase, and the services are `billing`, `email`, `sms`, `storage`, `identity` and `verification`.

| Tool | Effect |
| --- | --- |
| `describe_offering` | SwapLayer, its service families, and the safe operating model |
| `list_public_capabilities` | Package APIs, docs, CLI commands, and these tools |
| `map_workflow_to_tools` | Tools, Python APIs, docs, approvals and verification for a goal |
| `operate_browser_docs` | Guidance for public docs, PyPI, GitHub issues or provider docs in a browser |
| `prepare_provider_setup` | Install command, settings template, environment placeholders and provider notes (`service`, `provider`, `projectType`) |
| `plan_provider_migration` | Migration checklist between two providers that touches no data (`fromProvider`, `toProvider`) |
| `explain` | One packaged guide (`topic`) |
| `compare_providers` | Provider comparison for a service, with an optional `useCase` |
| `troubleshoot` | A known setup problem; `errorMessage` is matched to symptoms and never returned |
| `list_providers` | Provider values the factory accepts |
| `get_provider_info` | One provider's capabilities, settings example and install command |
| `generate_code` | A Python example; returns text without executing it |
| `get_usage_examples` | Usage patterns for a service |
| `get_config` | The caller's configuration, public fields only |
| `send_test_email` | Sends one email using the caller's provider account |
| `send_test_sms` | Sends one SMS using the caller's provider account |
| `check_storage` | Storage configuration check; `testUpload: true` writes, then deletes, one file under `swaplayer-mcp-check/` |

`explain` topics are `overview` (the README), `docs-index`, `architecture`, `billing`, `email`, `sms`, `storage`, `identity-platform`, `identity-verification`, `mcp`, `security` (SECURITY.md), `philosophy` and `faq`.

Clients must obtain explicit approval before test sends or writes. They can incur charges or modify caller infrastructure. A label saying "test" does not switch provider credentials into sandbox mode. Configure a test account and approved recipient yourself. Do not expose this stdio process as an unauthenticated network service.

`get_config` returns only public settings fields (providers, options and public IDs), never credentials, and `swaplayer_check --verbose` masks every other value; operational errors omit raw exception messages. This is not a universal secret scanner for arbitrary user text, SDK logging or application data. Do not paste credentials into tool arguments. Application production transactions use the Python adapters behind application authorization, not autonomous documentation tools.

## Embedding

`swap_layer.mcp.create_mcp_server()` builds an MCP SDK server with the same contract, tools and prompts, to run inside your own process. It needs `SwapLayer[mcp]` (MCP Python SDK 1.x).

Third-party client settings determine model access and approval behavior. Configure the client to approve sensitive operations; repository and package policies do not grant that approval on your behalf.
