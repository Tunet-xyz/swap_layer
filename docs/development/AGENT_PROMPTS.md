# Agent Prompt Templates

Copy-paste prompt templates for common SwapLayer development tasks. Each prompt is self-contained — paste it into your LLM agent of choice (GitHub Copilot Chat, Claude, Cursor, etc.) and it will have enough context to do the work.

> **Tip**: These prompts reference the `.github/copilot-instructions.md` file which gives agents deeper context about the codebase. If your tool supports custom instructions, make sure it's reading that file.

---

## Table of Contents

- [New Provider](#new-provider)
- [Complete Stubs](#complete-stubs)
- [Generate Tests](#generate-tests)
- [Doc Sync](#doc-sync)
- [Code Review](#code-review)
- [Changelog](#changelog)
- [Legacy Cleanup](#legacy-cleanup)
- [New Module](#new-module)

---

## New Provider

Scaffold a complete provider implementation for an existing module.

```
Add a {PROVIDER} provider to SwapLayer's {MODULE} module.

Repository: src/swap_layer/{MODULE_PATH}/

Step 1: Read the adapter
- Read src/swap_layer/{MODULE_PATH}/adapter.py to understand the interface

Step 2: Study an existing provider
- Read src/swap_layer/{MODULE_PATH}/providers/{EXISTING_PROVIDER}.py

Step 3: Create the new provider
- Create src/swap_layer/{MODULE_PATH}/providers/{PROVIDER}.py
- Inherit from the adapter ABC
- Implement every @abstractmethod
- Use lazy imports: import the SDK inside __init__, not at module level
- If SDK is missing, raise ImportError with install instructions
- Return plain dicts from every method, never raw SDK objects

Step 4: Register in factory
- Edit src/swap_layer/{MODULE_PATH}/factory.py
- Add the new provider option

Step 5: Add dependency
- Edit pyproject.toml
- Add the SDK to [project.optional-dependencies] under a new key

Step 6: Add tests
- Create or append to tests/test_{MODULE}.py
- Mock the SDK, test all methods, test error handling
- Follow patterns from existing test files

Step 7: Update docs
- Update docs/{MODULE}.md with the new provider
- Update the provider status table in docs/architecture.md
```

### Ready-to-use examples

<details>
<summary>PayPal payments provider</summary>

```
Add a PayPal provider to SwapLayer's billing module.

Repository: src/swap_layer/billing/

Step 1: Read src/swap_layer/billing/adapter.py and the sub-adapters in
customers/adapter.py, subscriptions/adapter.py, payment_intents/adapter.py

Step 2: Study src/swap_layer/billing/providers/stripe.py

Step 3: Create src/swap_layer/billing/providers/paypal.py
- Use the paypalrestsdk Python package
- Implement CustomerAdapter, SubscriptionAdapter, PaymentAdapter
- Lazy import paypalrestsdk inside __init__

Step 4: Register "paypal" in billing/factory.py

Step 5: Add paypalrestsdk to pyproject.toml [project.optional-dependencies]
  paypal = ["paypalrestsdk>=1.13.0"]

Step 6: Add tests in tests/test_billing.py (or new test_billing_paypal.py)

Step 7: Update docs/billing.md and docs/architecture.md
```

</details>

<details>
<summary>Mailgun email provider</summary>

```
Add a Mailgun provider to SwapLayer's email module.

Repository: src/swap_layer/communications/email/

Step 1: Read src/swap_layer/communications/email/adapter.py

Step 2: Study src/swap_layer/communications/email/providers/django_email.py

Step 3: Create src/swap_layer/communications/email/providers/mailgun.py
- Use the requests library to call Mailgun's REST API directly
- Lazy import is not needed since requests is a core dependency
- Implement send_email, send_template_email, send_bulk_email

Step 4: Register "mailgun" in communications/email/factory.py

Step 5: No new dependency needed (uses requests)

Step 6: Add tests in tests/test_email.py

Step 7: Update docs/email.md and docs/architecture.md
```

</details>

<details>
<summary>S3 storage provider</summary>

```
Add an S3 provider to SwapLayer's storage module.

Repository: src/swap_layer/storage/

Step 1: Read src/swap_layer/storage/adapter.py

Step 2: Study src/swap_layer/storage/providers/local.py

Step 3: Create src/swap_layer/storage/providers/s3.py
- Use boto3 SDK
- Lazy import boto3 inside __init__
- Implement all StorageProviderAdapter methods
- Support presigned URLs for upload and download

Step 4: Register "s3" in storage/factory.py

Step 5: boto3 is already in pyproject.toml under [project.optional-dependencies] aws

Step 6: Add tests in tests/test_storage.py

Step 7: Update docs/storage.md and docs/architecture.md
```

</details>

---

## Complete Stubs

Fill in placeholder implementations that currently contain only `pass`.

```
In SwapLayer, the file src/swap_layer/{FILE_PATH} has stub methods.

Context:
- Read the adapter ABC to understand what each method should return
- Read a sibling provider that IS implemented to see the response format
- Read the provider's official API documentation

Task:
- Implement all stub methods using the provider's SDK/API
- Match the return format documented in the adapter docstrings
- Handle errors using SwapLayerError subclasses from exceptions.py
- Add appropriate logging

Do NOT change method signatures — only fill in the implementations.
```

### High-value stubs

```
Complete the stub methods in src/swap_layer/communications/sms/providers/sns.py.

The following methods are stubs:
- get_message_status() — returns "unknown", should query SNS/CloudWatch
- list_messages() — returns empty list, should use CloudWatch Logs
- get_account_balance() — returns None (acceptable for SNS pay-as-you-go, 
  but should return spend data from AWS Cost Explorer if possible)

Reference: The Twilio implementation in providers/twilio_sms.py shows the
expected return format for each method.
```

```
Create a Stripe implementation for the billing/products module.

src/swap_layer/billing/products/adapter.py defines the interface:
- create_product, get_product, update_product, list_products
- create_price, get_price, list_prices

Create src/swap_layer/billing/products/providers/stripe.py implementing
all methods using the stripe Python SDK. Follow the same patterns as
src/swap_layer/billing/providers/stripe.py.
```

---

## Generate Tests

Create tests for a specific module or provider.

```
Generate pytest tests for src/swap_layer/{MODULE_PATH}/providers/{PROVIDER}.py.

Follow these patterns from the existing test suite:
- tests/conftest.py — Django settings setup, how SWAPLAYER is configured
- tests/test_billing.py — how external SDKs are mocked
- tests/test_email.py — how provider methods are tested

Requirements:
1. Use pytest (not unittest.TestCase)
2. Mock the external SDK — never make real API calls
3. Configure SWAPLAYER in the test using @override_settings
4. Test every public method of the provider class
5. Test error paths (missing config, API errors, invalid input)
6. Test that the factory returns this provider when configured
7. Use descriptive test names: test_{method}_{scenario}

Place tests in tests/test_{MODULE}.py.
```

---

## Doc Sync

Compare code against documentation and fix discrepancies.

```
Audit SwapLayer documentation for accuracy against the current code.

Files to check:
- README.md — quick start, installation, feature list
- docs/README.md — documentation index
- docs/architecture.md — provider status table, module list
- docs/email.md, billing.md, sms.md, storage.md — module guides
- docs/identity-platform.md, identity-verification.md — identity guides
- docs/mcp.md — MCP server tools
- CHANGELOG.md — latest version matches pyproject.toml

For each file, check:
1. Do code examples use the current import paths? (swap_layer, not infrastructure)
2. Do code examples use the current API? (SwapLayerSettings, not individual settings)
3. Is the provider status table accurate? Check which providers/ dirs have
   actual implementations vs. empty __init__.py files
4. Are all documented providers actually available?
5. Does the version number match pyproject.toml?

List every discrepancy you find and fix it.
```

---

## Code Review

Review changes for architectural compliance.

```
Review these changes to SwapLayer for compliance with the project's
architecture and conventions:

{DESCRIBE OR PASTE THE CHANGES}

Checklist:
- [ ] Adapter pattern: New providers inherit from the correct ABC
- [ ] Factory registration: Provider is registered in factory.py
- [ ] Config: Pydantic config class exists in settings.py (if needed)
- [ ] Lazy imports: Optional SDKs imported inside __init__, not at top
- [ ] Error handling: Uses SwapLayerError subclasses, secrets are masked
- [ ] Response format: Methods return plain dicts, not SDK objects
- [ ] Tests: Tests exist, mock SDKs, cover all public methods
- [ ] Docs: Provider listed in module docs and architecture.md
- [ ] No secrets: No API keys, tokens, or passwords in code
- [ ] Commit message: Follows "type(scope): description" format

Flag any violations and suggest fixes.
```

---

## Changelog

Generate a changelog entry from recent changes.

```
Generate a CHANGELOG.md entry for SwapLayer version {VERSION}.

Read the existing CHANGELOG.md to understand the format.
Look at the git log since the last release tag.

Format:
## [{VERSION}] - {DATE}
### Added
- New features (one line each)
### Changed
- Changed behavior (one line each)
### Fixed
- Bug fixes (one line each)
### Breaking Changes
- Breaking changes with migration instructions

Be concise. Mention affected module names (billing, storage, sms, etc.).
```

---

## Legacy Cleanup

Identify and safely remove backward-compatibility code.

```
Analyze the legacy/backward-compatibility code in SwapLayer and determine
what can be safely removed.

Targets:
1. src/swap_layer/config.py — vestigial Django settings proxy
   - Search for any imports of this file across the codebase
   - Check if any tests reference it
   
2. Factory fallbacks — each factory file has code like:
   "Fallback to legacy Django settings for backward compatibility"
   - List all such fallbacks across all factory files
   - Check if any tests exercise the legacy path
   
3. settings.py _from_legacy_django_settings() method
   - Check what calls this method
   - Check if tests depend on it

For each item report:
- What depends on it (imports, tests, docs)
- Whether it can be removed safely
- What the migration path is for users on the old format
- Suggested deprecation timeline if not immediately removable
```

---

## New Module

Scaffold an entirely new service module from scratch.

```
Add a new "{SERVICE}" module to SwapLayer for {DESCRIPTION}.

The module should support these operations:
{LIST_OF_OPERATIONS}

Initial provider: {PROVIDER_NAME} using {SDK_NAME}

Create all files following the established pattern:

src/swap_layer/{service}/
├── __init__.py          — exports: get_{service}_provider, {Service}ProviderAdapter
├── adapter.py           — ABC with @abstractmethod for each operation
├── factory.py           — reads SWAPLAYER.{service} config, returns provider
├── apps.py              — Django AppConfig
├── models.py            — Django models (if the module needs to store state)
├── admin.py             — Django admin registration (if models exist)
├── README.md            — module documentation
└── providers/
    ├── __init__.py
    └── {provider}.py    — implementation using {sdk}

Also update:
- src/swap_layer/settings.py — add {Service}Config pydantic model
- src/swap_layer/__init__.py — add to get_provider() mapping and imports
- pyproject.toml — add optional dependency
- tests/test_{service}.py — tests
- docs/{service}.md — user documentation  
- docs/README.md — add to index

Study at least two existing modules (e.g., billing/ and communications/email/)
before starting, to match the style exactly.
```

### Examples

<details>
<summary>Feature Flags module</summary>

```
Add a new "feature_flags" module to SwapLayer for feature flag management.

Operations:
- is_enabled(flag_name, context) → bool
- get_variation(flag_name, context, default) → Any
- list_flags() → list of flag dicts
- create_flag(name, description, default_value) → flag dict
- update_flag(flag_name, updates) → flag dict

Initial provider: LaunchDarkly using launchdarkly-server-sdk

Follow the standard pattern. Study billing/ and communications/email/ first.
```

</details>

<details>
<summary>Background Jobs module</summary>

```
Add a new "jobs" module to SwapLayer for background job processing.

Operations:
- enqueue(task_name, args, kwargs, queue, delay) → job dict
- get_job(job_id) → job dict
- cancel_job(job_id) → bool
- list_jobs(queue, status) → list of job dicts
- get_queue_stats(queue) → stats dict

Initial provider: Celery using celery[redis]

Follow the standard pattern. Study billing/ and communications/sms/ first.
```

</details>
