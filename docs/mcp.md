# SwapLayer MCP Server

## Overview

SwapLayer provides a **Model Context Protocol (MCP)** server that exposes its provider management capabilities as tools for AI assistants and LLMs. This allows AI-powered development workflows to interact with SwapLayer's infrastructure abstractions through natural language.

**Important**: The MCP server is intentionally scoped to **configuration and testing tools** for security and practicality. It does not expose full transactional APIs (e.g., creating production customers, processing payments). See [Coverage](#coverage) section for details.

## What is MCP?

The Model Context Protocol (MCP) is a standard protocol that enables AI assistants to interact with external tools and data sources. By exposing SwapLayer as MCP tools, developers can:

- Configure and test providers through natural language
- Switch between providers with AI assistance
- Perform operational tasks like sending test emails or SMS
- Inspect configuration and available providers
- Get provider information and capabilities

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

### 7. `swaplayer_generate_code`

Generate code examples for using SwapLayer with specific operations.

**Parameters:**
- `service` (string): Service type
- `operation` (string): Operation to perform (e.g., 'send_email', 'create_customer', 'upload_file')
- `context` (string, optional): Additional context about the use case

**Example:**
```json
{
  "service": "payments",
  "operation": "create_subscription"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "payments",
  "operation": "create_subscription",
  "code": "# Create a subscription\nfrom swap_layer import get_provider\n...",
  "language": "python"
}
```

### 8. `swaplayer_get_usage_examples`

Get common usage examples and patterns for a specific service.

**Parameters:**
- `service` (string): Service type
- `pattern` (string, optional): Specific pattern (e.g., 'welcome_email', 'subscription_flow')

**Example:**
```json
{
  "service": "email",
  "pattern": "welcome_email"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "email",
  "pattern": "welcome_email",
  "description": "Send a welcome email when user signs up",
  "code": "# Welcome email pattern\nfrom swap_layer import get_provider\n..."
}
```

### 9. `swaplayer_setup_quickstart`

Generate complete quickstart configuration and setup instructions for SwapLayer with a specific service and provider. Automatically generates all configuration code - developers only need to add their credentials.

**Parameters:**
- `service` (string): Service type to set up
- `provider` (string): Provider to use (e.g., 'stripe', 'sendgrid', 'twilio', 's3')
- `project_type` (string, optional): 'new' or 'existing' Django project (default: 'existing')

**Example:**
```json
{
  "service": "payments",
  "provider": "stripe",
  "project_type": "existing"
}
```

**Response:**
```json
{
  "status": "success",
  "service": "payments",
  "provider": "stripe",
  "quickstart": "Step-by-step setup instructions...",
  "pip_install": "pip install 'SwapLayer[stripe]'",
  "settings_config": "# Complete Django settings configuration",
  "env_vars": "# Environment variables template",
  "usage_example": "# Ready-to-use code example",
  "credentials_instructions": "Get your Stripe keys from: https://dashboard.stripe.com/..."
}
```

## Coverage

### What the MCP Server Covers

The MCP server provides **configuration, testing, and code generation tools** for all SwapLayer services:

✅ **Configuration Management**
- Inspect current configuration (all services)
- List available providers (all services)
- Get provider information and capabilities

✅ **Testing & Validation**
- Send test emails (email service)
- Send test SMS (SMS service)
- Check storage connectivity (storage service)

✅ **Developer Guidance**
- Provider setup instructions
- Capability discovery
- Configuration assistance

✅ **Code Generation & Examples**
- Generate code snippets for specific operations
- Get common usage patterns (welcome emails, subscription flows, etc.)
- Access ready-to-use examples for all services

✅ **Quickstart & Auto-Configuration**
- Complete setup instructions for any service/provider combination
- Auto-generated Django settings configuration
- Environment variables templates
- Step-by-step installation guides
- Developers only need to add their credentials manually

### What the MCP Server Does NOT Cover

For security and practical reasons, the MCP server does **not** expose full transactional/operational APIs:

❌ **Billing/Payments Operations**
- Customer management (create, update, delete)
- Subscription operations (create, cancel, update)
- Payment processing (create payment intents, checkout sessions)
- Invoice management
- Production transactions

❌ **Identity Operations**
- OAuth flows and user authentication
- Session management
- User data operations

❌ **Identity Verification Operations**
- Verification session lifecycle
- Verification reports
- Production verification operations

❌ **Advanced Service Features**
- Bulk operations
- Production data management
- Complex workflows requiring multiple API calls

### Why This Scope?

**Security**: AI assistants should not perform production transactions or manage sensitive data operations.

**Practicality**: Configuration and testing tools are where AI assistance is most valuable—helping developers set up, explore, and validate their infrastructure.

**Maintenance**: Limited scope means lower complexity and maintenance burden.

### When You Need Full API Access

For production operations, use SwapLayer's Python API directly:

```python
from swap_layer import get_provider

# Full API access for production code
payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')
subscription = payments.create_subscription(
    customer_id=customer['id'],
    price_id='price_123'
)
```

The MCP server is designed to **complement** the Python API, not replace it.

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

### 3. Quickstart Setup

AI assistants automatically configure SwapLayer:

**User:** "I want to use SwapLayer with Stripe for payments"

**AI Assistant:** *calls `swaplayer_setup_quickstart` with service="payments", provider="stripe"*

Returns complete setup with:
- Installation command
- Django settings configuration
- Environment variables template
- Usage examples
- Credentials instructions

**User only needs to:** Add their Stripe API keys

### 4. Testing and Validation

Quickly test provider integrations:

**User:** "Send a test email to verify my configuration"

**AI Assistant:** *calls `swaplayer_send_test_email`*

### 5. Code Generation

AI assistants can generate SwapLayer code for you:

**User:** "Show me how to send a welcome email with SwapLayer"

**AI Assistant:** *calls `swaplayer_generate_code` with service="email", operation="send_email"*

**User:** "How do I create a subscription flow?"

**AI Assistant:** *calls `swaplayer_get_usage_examples` with service="payments", pattern="subscription_flow"*

### 6. Contextual Code Assistance

AI helps with business logic integration:

**User:** "I'm building a signup flow and need to send an email after registration"

**AI Assistant:** 
1. *calls `swaplayer_generate_code` for email sending*
2. *provides contextual integration code*
3. *shows how to handle errors and responses*

### 7. Multi-step Workflows

Complex operations with natural language:

**User:** "Set up a welcome flow: send email and SMS when user signs up"

**AI Assistant:**
1. *calls `swaplayer_generate_code` for email and SMS*
2. *provides complete code example combining both*
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

### VS Code with GitHub Copilot

Create a `.vscode/mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "swaplayer": {
      "command": "swaplayer-mcp",
      "args": [],
      "env": {
        "DJANGO_SETTINGS_MODULE": "your_project.settings",
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

Or add to your **User Settings** (`settings.json`) for global access across all projects:

```json
{
  "mcp": {
    "servers": {
      "swaplayer": {
        "command": "swaplayer-mcp",
        "env": {
          "DJANGO_SETTINGS_MODULE": "your_project.settings"
        }
      }
    }
  }
}
```

After configuration, restart VS Code. SwapLayer tools will appear in GitHub Copilot's available tools list.

### Claude Desktop

Add to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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
