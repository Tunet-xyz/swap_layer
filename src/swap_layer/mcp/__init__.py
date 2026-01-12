"""
SwapLayer MCP Server

Exposes SwapLayer functionality as MCP tools for AI assistants.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
