# SwapLayer MCP Server

## Overview

SwapLayer provides a **Model Context Protocol (MCP)** server that exposes its provider management capabilities as tools for AI assistants and LLMs. This allows AI-powered development workflows to interact with SwapLayer's infrastructure abstractions through natural language.

## What is MCP?

The Model Context Protocol (MCP) is a standard protocol that enables AI assistants to interact with external tools and data sources. By exposing SwapLayer as MCP tools, developers can:

- Configure and test providers through natural language
- Switch between providers with AI assistance
- Perform operational tasks like sending test emails or SMS
- Inspect configuration and available providers

## Installation

Install SwapLayer with MCP support:

```bash
pip install 'SwapLayer[mcp]'
```

Or for development with all features:

```bash
pip install 'SwapLayer[all]'
```

## Running the MCP Server

### As a Standalone Server

```bash
swaplayer-mcp
```

### Programmatically

```python
from swap_layer.mcp import create_mcp_server
import mcp.server.stdio
import asyncio

server = create_mcp_server()

async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

asyncio.run(run())
```

## Configuration

The MCP server uses your existing SwapLayer configuration from Django settings:

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'sendgrid', 'sendgrid': {'api_key': '...'}},
    payments={'provider': 'stripe', 'stripe': {'secret_key': '...'}},
    sms={'provider': 'twilio', 'twilio': {'account_sid': '...', 'auth_token': '...'}},
    storage={'provider': 's3', 's3': {'bucket_name': '...'}},
)
```

## Available Tools

### 1. `swaplayer_get_config`

Get current SwapLayer configuration (sensitive data is automatically redacted).

**Parameters:**
- `service` (string): Service type or "all" for all services
  - Options: `all`, `email`, `payments`, `sms`, `storage`, `identity`, `verification`

**Example:**
```json
{
  "service": "email"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "email",
  "config": {
    "provider": "sendgrid"
  }
}
```

### 2. `swaplayer_list_providers`

List all available providers for a service type.

**Parameters:**
- `service` (string): Service type
  - Options: `email`, `payments`, `sms`, `storage`, `identity`, `verification`

**Example:**
```json
{
  "service": "email"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "email",
  "providers": ["django", "smtp", "sendgrid", "mailgun", "ses"]
}
```

### 3. `swaplayer_send_test_email`

Send a test email using the configured email provider.

**Parameters:**
- `to` (string): Recipient email address
- `subject` (string): Email subject
- `body` (string): Email body (plain text)

**Example:**
```json
{
  "to": "test@example.com",
  "subject": "Test Email",
  "body": "This is a test email from SwapLayer MCP"
}
```

### 4. `swaplayer_send_test_sms`

Send a test SMS using the configured SMS provider.

**Parameters:**
- `to` (string): Recipient phone number in E.164 format
- `message` (string): SMS message text

**Example:**
```json
{
  "to": "+15555551234",
  "message": "Test SMS from SwapLayer"
}
```

### 5. `swaplayer_check_storage`

Check storage provider configuration and optionally test connectivity.

**Parameters:**
- `test_upload` (boolean, optional): Whether to perform a test file upload/delete

**Example:**
```json
{
  "test_upload": true
}
```

### 6. `swaplayer_get_provider_info`

Get detailed information about a specific provider implementation.

**Parameters:**
- `service` (string): Service type
- `provider` (string): Provider name (e.g., 'stripe', 'sendgrid', 'twilio')

**Example:**
```json
{
  "service": "email",
  "provider": "sendgrid"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "email",
  "provider": "sendgrid",
  "info": {
    "description": "SendGrid email service",
    "capabilities": ["send_email", "templates", "tracking"],
    "setup": "Requires SENDGRID_API_KEY"
  }
}
```

## Use Cases

### 1. Configuration Exploration

AI assistants can help developers understand their current SwapLayer setup:

**User:** "What email provider am I currently using?"

**AI Assistant:** *calls `swaplayer_get_config` with `service: "email"`*

### 2. Provider Switching

AI can guide developers through switching providers:

**User:** "I want to switch from SendGrid to Mailgun for email"

**AI Assistant:** 
1. *calls `swaplayer_get_provider_info` for mailgun*
2. *provides setup instructions*
3. *helps update settings.py*
4. *calls `swaplayer_send_test_email` to verify*

### 3. Testing and Validation

Quickly test provider integrations:

**User:** "Send a test email to verify my configuration"

**AI Assistant:** *calls `swaplayer_send_test_email`*

### 4. Multi-step Workflows

Complex operations with natural language:

**User:** "Set up a welcome flow: send email and SMS when user signs up"

**AI Assistant:** 
1. *checks configuration with `swaplayer_get_config`*
2. *generates Django view code using SwapLayer*
3. *helps test with `swaplayer_send_test_email` and `swaplayer_send_test_sms`*

## Security Considerations

### Sensitive Data Protection

The MCP server automatically redacts sensitive configuration values:
- API keys
- Secret keys
- Passwords
- Tokens
- Auth tokens
- Client secrets

Only non-sensitive configuration information is exposed through the tools.

### Access Control

The MCP server runs with the same permissions as your Django application. Ensure:
- Environment variables containing secrets are properly protected
- The MCP server is only accessible to authorized users
- Production credentials are never used in development/testing contexts

## Integration with AI Development Tools

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "swaplayer": {
      "command": "swaplayer-mcp",
      "env": {
        "DJANGO_SETTINGS_MODULE": "your_project.settings"
      }
    }
  }
}
```

### VS Code with Copilot

Configure the MCP server in your VS Code settings to make SwapLayer tools available to GitHub Copilot.

### Other AI Assistants

Any AI assistant that supports MCP can integrate with SwapLayer's server. Refer to your AI tool's MCP integration documentation.

## Troubleshooting

### "MCP dependencies not installed"

Install the MCP extra:
```bash
pip install 'SwapLayer[mcp]'
```

### "Django settings not configured"

Set the `DJANGO_SETTINGS_MODULE` environment variable:
```bash
export DJANGO_SETTINGS_MODULE=your_project.settings
swaplayer-mcp
```

### Tool calls fail

Ensure your SwapLayer configuration is valid:
```python
from swap_layer.settings import validate_swaplayer_config
validate_swaplayer_config()
```

## Benefits of MCP Integration

### For Developers

✅ **Natural Language Configuration** - Configure providers through conversation  
✅ **Faster Testing** - Test integrations without writing test scripts  
✅ **Guided Provider Switching** - AI assistance when changing providers  
✅ **Documentation in Context** - Get provider info while coding  

### For Teams

✅ **Onboarding** - New team members learn SwapLayer faster with AI help  
✅ **Best Practices** - AI can suggest optimal provider configurations  
✅ **Consistency** - Standardized way to interact with infrastructure  

### For SwapLayer

✅ **Enhanced DX** - Better developer experience with AI assistance  
✅ **Modern Workflow** - Aligns with AI-powered development trends  
✅ **Competitive Edge** - First-class AI assistant support  

## Future Enhancements

Planned additions to the MCP server:

- [ ] Provider comparison tools
- [ ] Cost estimation for different providers
- [ ] Migration assistance (data transfer between providers)
- [ ] Health check and monitoring tools
- [ ] Batch operations (e.g., send multiple test emails)
- [ ] Configuration templates and presets
- [ ] Performance benchmarking across providers

## Contributing

Contributions to the MCP server are welcome! See [development/contributing.md](../development/contributing.md) for guidelines.

When adding new MCP tools:
1. Add the tool definition to `list_tools()` in `server.py`
2. Implement the tool handler in `call_tool()`
3. Add helper function if needed
4. Update this documentation
5. Add tests for the new tool

## License

The MCP server is part of SwapLayer and is released under the MIT License.
