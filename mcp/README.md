# SwapLayer MCP server

This directory holds a copy of SwapLayer's public agent contract and a launcher
that runs the MCP server from a source checkout. The server is the installed
`swaplayer-mcp` command. Agents use it to discover SwapLayer's service families
and APIs, to get guidance for provider setups and migration checklists, to read
the packaged guides, and, with the caller's approval, to run test sends and
storage checks with the caller's own credentials. It runs locally under the
caller's control. There is no hosted SwapLayer MCP service, and nothing here
gives access to the owner's agents, accounts, or infrastructure.

## Run

After `pip install SwapLayer` (the command needs no MCP SDK):

```bash
swaplayer-mcp
python -m swap_layer.mcp     # the same server
```

From a source checkout:

```bash
python mcp/server.py
```

## Files

| File | Purpose |
| --- | --- |
| `README.md` | This guide. |
| `agent-contract.json` | The public agent contract, byte-identical to the packaged `src/swap_layer/mcp/agent-contract.json`. |
| `server.py` | Runs the packaged server (`src/swap_layer/mcp/server.py`) from a source checkout. |

## Methods and tools

The server implements `initialize`, `ping`, `resources/list`,
`resources/read`, `tools/list`, `tools/call`, `prompts/list`, and
`prompts/get`.

| Tools | What they do |
| --- | --- |
| `describe_offering`, `list_public_capabilities`, `map_workflow_to_tools`, `prepare_provider_setup`, `plan_provider_migration`, `operate_browser_docs` | Return the contract's guidance for the task, with the arguments you passed and the contract's access and safety rules. The calling agent writes any settings or plans, for a person to review. |
| `explain`, `compare_providers`, `troubleshoot`, `list_providers`, `get_provider_info`, `generate_code`, `get_usage_examples`, `get_config` | Return the packaged guides, provider comparisons and examples, and the caller's public configuration. |
| `send_test_email`, `send_test_sms`, `check_storage` | Send one test email or SMS, or check storage, with the caller's provider accounts. |

[docs/mcp.md](../docs/mcp.md) describes each tool and its arguments.
Resources, under `opensource://swap_layer/`: `agent-contract`, `overview`,
`public-apis`, `workflows`, `browser-surfaces`, `security-and-audit`, and
`docs/<topic>` for the packaged guides. Prompts: `agent_onboarding`,
`onboard_service`, `choose_provider`, and `migrate_provider`.

## Limits

The server reads one JSON-RPC message per line. It answers with a JSON-RPC
error, and keeps serving, when a line is longer than 1,100,000 characters
(newline included), is not valid UTF-8 JSON, repeats an object key, uses `NaN`
or `Infinity`, has a number longer than 256 characters, or has an invalid
request shape.

## Boundaries

- The guidance tools are read-only. Test sends and storage writes use the
  caller's credentials, can cause provider charges or file changes, and need
  the caller's approval for each call.
- Never automate production payments, identity operations, or secret handling
  through MCP; use the Python package API in application code.
- Agents work from published package APIs, public documentation, and this
  contract. They must not assume access to private source code, unredacted
  settings, production data, or provider dashboards unless the user grants
  it.
