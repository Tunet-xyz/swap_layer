# SwapLayer MCP Server

Model Context Protocol (MCP) server for SwapLayer - exposes provider management as AI assistant tools.

## Quick Start

Install:
```bash
pip install 'SwapLayer[mcp]'
```

Run:
```bash
swaplayer-mcp
```

## What This Does

Exposes SwapLayer **configuration, testing, and code generation tools** as AI assistant tools:

- **Configuration Inspection**: Check which providers are configured
- **Provider Discovery**: List available providers for each service
- **Testing**: Send test emails, SMS, check storage connectivity
- **Provider Information**: Get setup instructions and capabilities
- **Code Generation**: Generate code snippets and usage examples

**Note**: For security, the MCP server does NOT expose full transactional APIs (e.g., creating customers, processing payments). It's focused on configuration, testing, and helping developers write code. See docs/mcp.md for details.

## Security

Automatically redacts sensitive data (API keys, secrets, tokens) from all responses.

## Documentation

See [docs/mcp.md](../../../docs/mcp.md) for complete documentation.

## Example Tools

```python
# Available tools:
- swaplayer_get_config           # Get configuration
- swaplayer_list_providers       # List available providers
- swaplayer_send_test_email      # Send test email
- swaplayer_send_test_sms        # Send test SMS
- swaplayer_check_storage        # Check storage config
- swaplayer_get_provider_info    # Get provider details
- swaplayer_generate_code        # Generate code examples
- swaplayer_get_usage_examples   # Get common patterns
- swaplayer_setup_quickstart     # Auto-generate complete setup
```

## Integration

Works with any MCP-compatible AI assistant:
- Claude Desktop
- VS Code with Copilot
- Custom AI tools

## Why MCP?

AI assistants can help you:
- **Auto-configure**: Say "I want to use Stripe" → get complete setup instantly
- Configure SwapLayer providers through conversation
- Switch providers with guided assistance
- Test integrations without writing scripts
- Learn provider capabilities on demand
- Generate code examples for common operations
- Get ready-to-use patterns (welcome emails, subscriptions, etc.)
- **Contextual assistance**: "Send email after signup" → get integration code

This aligns perfectly with SwapLayer's anti-vendor-lock-in philosophy by making provider switching even easier.
