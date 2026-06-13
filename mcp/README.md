# Public Agent MCP Contract

This directory defines the public agent-operability contract for this open-source offering. It is written for external user agents that can use published package APIs, hosted or local MCP tools, public documentation, and browser-visible surfaces. It must not assume access to private source code, local repository paths, unredacted settings, production data, or vendor dashboards unless the user explicitly grants that access.

Files:

```text
mcp/
  README.md
  agent-contract.json
  server.py
```

The local stdio server is dependency-free and contract-first. It is useful for development checks and for any MCP client that can launch a local process.

```bash
python mcp/server.py
```

Supported methods:

- `initialize`
- `resources/list`
- `resources/read`
- `tools/list`
- `tools/call`
- `prompts/list`
- `prompts/get`

Production packages may expose richer runtime MCP tools, but those tools should preserve this contract's public-access boundaries, approval gates, and verification expectations.
## SwapLayer Notes

SwapLayer already ships a runtime MCP server through `swaplayer-mcp` when installed with `SwapLayer[mcp]`. This root contract describes how external agents should discover and operate the offering safely:

- use `swaplayer-mcp` for provider setup, redacted config inspection, examples, quickstarts, and non-production tests;
- use the Python package API for application code;
- use public docs/GitHub/PyPI for browser workflows;
- never automate production payments, identity operations, or secret handling through the public MCP contract.
