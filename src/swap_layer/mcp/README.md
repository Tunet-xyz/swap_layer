# SwapLayer MCP server

`swap_layer.mcp` is the local stdio MCP server that the `swaplayer-mcp` command
and `python -m swap_layer.mcp` run. It serves SwapLayer's public agent contract
and packaged guides: resources under `opensource://swap_layer/`, 17 tools, and
4 prompts.

## Quick start

```bash
pip install SwapLayer
swaplayer-mcp
```

The command needs no MCP SDK. `create_mcp_server()` builds an MCP SDK server
from the same contract for use in your own process; it needs
`pip install "SwapLayer[mcp]"`.

## Tools

- Guidance: `describe_offering`, `list_public_capabilities`,
  `map_workflow_to_tools`, `prepare_provider_setup`, `plan_provider_migration`,
  and `operate_browser_docs`.
- Documentation and configuration: `explain`, `compare_providers`,
  `troubleshoot`, `list_providers`, `get_provider_info`, `generate_code`,
  `get_usage_examples`, and `get_config`.
- Tests with the caller's provider accounts, which need approval for each call:
  `send_test_email`, `send_test_sms`, and `check_storage`.

The server does not expose transactional APIs such as creating customers or
processing payments. `get_config` returns only public settings fields; do not
put credentials in tool arguments.

## Files

| File | Purpose |
| --- | --- |
| `server.py` | The stdio server, `main()`, and `create_mcp_server()`. |
| `agent-contract.json` | The public agent contract. |
| `guidance.json` | Packaged copies of the README, SECURITY.md, and the docs guides, which `explain` and the `docs/` resources serve. |

See [docs/mcp.md](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/mcp.md) for configuration, each tool, and the
approval rules.
