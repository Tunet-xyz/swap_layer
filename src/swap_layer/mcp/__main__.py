#!/usr/bin/env python
"""
SwapLayer MCP Server CLI

Entry point for running the SwapLayer MCP server.
"""

import asyncio
import sys


def main():
    """Run the SwapLayer MCP server."""
    try:
        import mcp.server.stdio

        from swap_layer.mcp import create_mcp_server
    except ImportError:
        print(
            "Error: MCP dependencies not installed.\nInstall with: pip install 'SwapLayer[mcp]'",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_mcp_server()

    async def run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
