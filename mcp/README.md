# SwapLayer MCP server

This directory holds SwapLayer's public agent contract and a dependency-free
stdio MCP server for it. Agents can use it to discover SwapLayer's service
families and APIs, and to get guidance for provider setups and migration
checklists. This contract server runs locally under the caller's control, makes
no network connections, and needs no credentials or account. There is no hosted
SwapLayer MCP service, and nothing here gives access to the owner's
agents, accounts, or infrastructure.

SwapLayer also ships a separate runtime server, `swaplayer-mcp`, whose local
configuration, documentation, and test tools use the caller's own provider
credentials. It needs the `mcp` extra and is described in
[docs/mcp.md](../docs/mcp.md).

## Run

From a source checkout:

```bash
python mcp/server.py
```

The runtime server, after `pip install "SwapLayer[mcp]"`:

```bash
swaplayer-mcp
```

## Files

| File | Purpose |
| --- | --- |
| `README.md` | This guide. |
| `agent-contract.json` | The public agent contract, byte-identical to the packaged `src/swap_layer/mcp/agent-contract.json`. |
| `server.py` | The dependency-free contract server. |

## Methods and tools

The contract server implements `initialize`, `ping`, `resources/list`,
`resources/read`, `tools/list`, `tools/call`, `prompts/list`, and
`prompts/get`.

Every tool returns the contract's guidance for its task, with the arguments
you passed and the contract's access and safety rules. The calling agent
writes any settings or plans, for a person to review.

| Tool | Guidance on |
| --- | --- |
| `describe_offering` | SwapLayer, its service families, and the safe operating model. |
| `list_public_capabilities` | Package APIs, docs, CLI commands, and the runtime MCP tools. |
| `map_workflow_to_tools` | Mapping a goal to runtime MCP tools, Python APIs, docs, approvals, and verification. |
| `prepare_provider_setup` | An install command, settings template, environment placeholders, and verification steps. |
| `plan_provider_migration` | A migration checklist between providers that does not touch production data. |
| `operate_browser_docs` | Walking a user through public docs, PyPI, GitHub issues, or provider docs in a browser. |

Resources: `overview`, `public-apis`, `workflows`, `browser-surfaces`, and
`security-and-audit`. Prompt: `agent_onboarding`.

## Limits

The contract server reads one JSON-RPC message per line. It answers with a
JSON-RPC error, and keeps serving, when a line is longer than 1,100,000
characters (newline included), is not valid UTF-8 JSON, repeats an object key,
uses `NaN` or `Infinity`, has a number longer than 256 characters, or has an
invalid request shape.

## Boundaries

- The contract is read-only. Runtime test sends and storage writes through
  `swaplayer-mcp` use the caller's credentials, can cause provider charges or
  file changes, and need the caller's approval for each call.
- Never automate production payments, identity operations, or secret handling
  through MCP; use the Python package API in application code.
- Agents work from published package APIs, public documentation, and this
  contract. They must not assume access to private source code, unredacted
  settings, production data, or provider dashboards unless the user grants
  it.
