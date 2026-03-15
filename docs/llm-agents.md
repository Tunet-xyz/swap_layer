# LLM Agent Use Cases for SwapLayer

A practical guide for using LLM agents (GitHub Copilot, Claude, ChatGPT, Cursor, etc.) to maintain and grow SwapLayer as a solo developer. Each use case includes why it matters, when to use it, and a ready-to-paste prompt.

---

## Table of Contents

1. [Scaffold a New Provider](#1-scaffold-a-new-provider)
2. [Complete Stub Implementations](#2-complete-stub-implementations)
3. [Generate Tests for a Module](#3-generate-tests-for-a-module)
4. [Sync Documentation with Code](#4-sync-documentation-with-code)
5. [Review a PR for Pattern Compliance](#5-review-a-pr-for-pattern-compliance)
6. [Generate Changelog Entry](#6-generate-changelog-entry)
7. [Remove Legacy / Dead Code](#7-remove-legacy--dead-code)
8. [Add a New Module End-to-End](#8-add-a-new-module-end-to-end)
9. [Audit Adapter Consistency](#9-audit-adapter-consistency)
10. [Write Migration Guide for Breaking Changes](#10-write-migration-guide-for-breaking-changes)

---

## 1. Scaffold a New Provider

**Why**: Adding a provider (e.g., PayPal payments, Mailgun email, Azure Blob storage) is the most common task. The adapter pattern makes it mechanical — an LLM can do 90% of the work.

**When to use**: Any time you want to support a new third-party service in an existing module.

**Prompt**:

```
I'm adding a new provider to the SwapLayer project. The module is `{module}`
(path: src/swap_layer/{module}/). The new provider is `{provider_name}`.

Look at the abstract adapter in `adapter.py` and an existing provider implementation
in `providers/` to understand the pattern.

Create a new file `providers/{provider_name}.py` that:
1. Inherits from the adapter ABC
2. Implements every @abstractmethod
3. Uses lazy imports for the provider SDK (import inside __init__)
4. Normalizes all responses to plain dicts
5. Follows the same code style as existing providers

Also update `factory.py` to register the new provider,
and add the SDK to pyproject.toml optional-dependencies.
```

**Example**: Scaffold an Azure Blob Storage provider:

```
I'm adding a new provider to the SwapLayer project. The module is `storage`
(path: src/swap_layer/storage/). The new provider is `azure_blob`.

Look at the abstract adapter in `storage/adapter.py` and the existing
`providers/local.py` implementation to understand the pattern.

Create `providers/azure_blob.py` implementing StorageProviderAdapter using
the azure-storage-blob SDK. Update factory.py to register it. Add
azure-storage-blob to pyproject.toml under [project.optional-dependencies].
```

---

## 2. Complete Stub Implementations

**Why**: The codebase has ~123 `pass` method bodies across adapter ABCs and some providers. Many are just interface definitions, but others are incomplete implementations (SNS SMS, Django email advanced features).

**When to use**: When you need a feature that currently returns empty results or raises `NotImplementedError`.

**Prompt**:

```
In the SwapLayer project, the file `src/swap_layer/{path}` has stub methods
(bodies containing only `pass` or raising NotImplementedError).

Look at the abstract adapter to understand what each method should do, and
look at a sibling provider that IS fully implemented to understand the
response format.

Implement the stub methods. Use the provider's official SDK/API.
Return normalized dicts matching the format documented in the adapter docstrings.
Handle errors consistently with how other providers handle them.
```

**High-value stubs to complete first**:
- `communications/sms/providers/sns.py` — `list_messages()`, `get_message_status()`
- `communications/email/providers/django_email.py` — `send_template_email()`, `get_send_statistics()`
- `billing/products/` — entire adapter needs a Stripe implementation

---

## 3. Generate Tests for a Module

**Why**: Test coverage is at ~45%. An LLM can look at how existing tests are written and produce new ones that follow the same patterns.

**When to use**: After adding a new provider or completing stubs. Also useful for improving coverage on existing modules.

**Prompt**:

```
Generate tests for `src/swap_layer/{module}/providers/{provider}.py`.

Follow the patterns established in these existing test files:
- tests/test_billing.py (for mocking external SDKs)
- tests/test_email.py (for testing provider operations)
- tests/conftest.py (for Django settings setup)

Requirements:
1. Mock the external SDK — never call real APIs
2. Test all public methods on the provider class
3. Test error handling (invalid config, API failures)
4. Use pytest fixtures, not unittest.TestCase
5. Test that factory.py returns this provider when configured
6. Place tests in tests/test_{module}.py (or append to existing file)
```

---

## 4. Sync Documentation with Code

**Why**: Docs drift from code. Provider status tables go stale, code examples reference old APIs, and new features go undocumented.

**When to use**: Before a release, after major changes, or as a periodic cleanup task.

**Prompt**:

```
Audit the SwapLayer documentation for accuracy. Compare the code against
the docs and fix any discrepancies.

Check:
1. docs/architecture.md — Does the provider status table match reality?
   Look at which providers actually have implementations in providers/ dirs.
2. docs/{module}.md — Do the code examples use the current API?
   Check imports, method names, and config format.
3. README.md — Is the quick-start example correct?
4. docs/README.md — Are all docs listed in the index?
5. CHANGELOG.md — Does the latest version match pyproject.toml?

Fix any stale information. Don't change the writing style.
```

---

## 5. Review a PR for Pattern Compliance

**Why**: As a solo dev, you don't have a reviewer. An LLM can check that new code follows the established adapter/factory/config pattern.

**When to use**: Before merging any PR that adds or modifies a module.

**Prompt**:

```
Review this diff for compliance with SwapLayer's architecture:

{paste diff or describe the changes}

Check for:
1. Adapter pattern — Does the new provider inherit from the correct ABC?
2. Factory registration — Is the provider registered in factory.py?
3. Config integration — Is there a Pydantic config class in settings.py?
4. Lazy imports — Are optional SDKs imported inside __init__, not at module level?
5. Error handling — Are SwapLayerError subclasses used? Are secrets masked?
6. Response normalization — Do methods return plain dicts, not SDK objects?
7. Tests — Are there tests that mock the SDK and test all methods?
8. Documentation — Is the provider listed in the module's docs?
```

---

## 6. Generate Changelog Entry

**Why**: Writing changelog entries is tedious but important for users. An LLM can diff between tags and produce a well-formatted entry.

**When to use**: Before cutting a release.

**Prompt**:

```
Generate a CHANGELOG.md entry for SwapLayer.

Look at the git log since the last version tag and the existing CHANGELOG.md
format. Group changes into:

## [X.Y.Z] - YYYY-MM-DD
### Added
### Changed
### Fixed
### Breaking Changes (if any, with migration instructions)

Follow the existing style in CHANGELOG.md. Be concise — one line per change.
Mention affected modules (e.g., billing, storage, sms).
```

---

## 7. Remove Legacy / Dead Code

**Why**: The codebase has backward-compatibility code from earlier versions. Some of it is safe to remove.

**When to use**: When preparing a major version bump, or when legacy code is causing confusion.

**Prompt**:

```
Find and remove dead or legacy code in SwapLayer. Focus on:

1. `src/swap_layer/config.py` — This is a vestigial Django settings proxy.
   Check if anything imports from it. If not, remove it.
2. Factory files — Each factory (billing, email, sms, storage, identity)
   has fallback code to read legacy individual Django settings
   (e.g., PAYMENT_PROVIDER, STRIPE_SECRET_KEY). List all such fallbacks.
3. `settings.py` — The `_from_legacy_django_settings()` method.
   Determine if any tests or docs depend on it.

For each item, tell me:
- What the legacy code does
- What depends on it (search for imports and references)
- Whether it's safe to remove
- What the migration path would be for users still using the old format
```

---

## 8. Add a New Module End-to-End

**Why**: Adding a completely new service category (e.g., search, queues, caching, feature flags) is the biggest task. An LLM can scaffold the entire thing.

**When to use**: When you want to support a new category of infrastructure service.

**Prompt**:

```
Add a new module to SwapLayer for `{service}` (e.g., search, queues, caching).

Follow the established pattern exactly. Create:

1. src/swap_layer/{service}/__init__.py — with get_provider alias
2. src/swap_layer/{service}/adapter.py — ABC with methods for: {list methods}
3. src/swap_layer/{service}/factory.py — factory reading from SWAPLAYER settings
4. src/swap_layer/{service}/apps.py — Django app config
5. src/swap_layer/{service}/providers/__init__.py
6. src/swap_layer/{service}/providers/{default_provider}.py — first implementation

Also update:
7. src/swap_layer/settings.py — add {Service}Config pydantic model
8. src/swap_layer/__init__.py — register in get_provider()
9. pyproject.toml — add optional dependency
10. tests/test_{service}.py — tests following existing patterns
11. docs/{service}.md — documentation following existing format
12. docs/README.md — add to index
```

---

## 9. Audit Adapter Consistency

**Why**: Each module's adapter was written at different times. Method naming, return types, and error handling may be inconsistent across modules.

**When to use**: Periodically, or before a major release.

**Prompt**:

```
Audit all adapter ABCs in SwapLayer for consistency:

- src/swap_layer/billing/adapter.py
- src/swap_layer/billing/customers/adapter.py
- src/swap_layer/billing/subscriptions/adapter.py
- src/swap_layer/billing/payment_intents/adapter.py
- src/swap_layer/billing/products/adapter.py
- src/swap_layer/communications/email/adapter.py
- src/swap_layer/communications/sms/adapter.py
- src/swap_layer/storage/adapter.py
- src/swap_layer/identity/platform/adapter.py
- src/swap_layer/identity/verification/adapter.py

Check:
1. Method naming — are similar operations named consistently?
   (e.g., create_X, get_X, list_X, delete_X, update_X)
2. Return types — do all methods document their return type?
3. Parameter naming — are the same concepts named the same way?
4. Docstrings — do all abstract methods have docstrings?
5. Error contracts — do adapters document what exceptions they raise?

List any inconsistencies and suggest fixes.
```

---

## 10. Write Migration Guide for Breaking Changes

**Why**: When making breaking changes (like the 0.3.0 `scope_format` change), users need clear migration instructions. An LLM can generate these by diffing the old and new APIs.

**When to use**: Before any release with breaking changes.

**Prompt**:

```
Write a migration guide for SwapLayer users upgrading from {old_version}
to {new_version}.

Compare the code at both versions. For each breaking change:

1. What changed (old API → new API)
2. Why it changed
3. Step-by-step migration instructions with before/after code examples
4. Search-and-replace patterns if applicable

Format it as a section in CHANGELOG.md under "### Migration Guide"
and also as a standalone docs/development/migration-{version}.md file.
```

---

## Tips for Working with LLM Agents

### Provide context

Always point the agent to existing examples. "Look at `billing/providers/stripe.py` and follow the same pattern" is more effective than describing the pattern from scratch.

### Use the `.github/copilot-instructions.md` file

This repository includes custom instructions for GitHub Copilot that explain the architecture, conventions, and key files. Any Copilot-powered tool will read these automatically.

### Batch related tasks

Instead of asking an agent to "add a provider" then "write tests" then "update docs," give it the full scope: "Add the provider, write tests, and update the docs."

### Verify the output

LLM agents are good at following patterns but may miss edge cases. Always:
- Run `pytest` after code changes
- Run `ruff check` for linting
- Check that lazy imports work by testing without the optional dependency installed

### Iterate on prompts

If the agent's output isn't right, refine the prompt rather than editing the output manually. Good prompts are reusable for future similar tasks.

---

## Quick Reference — What to Automate vs. Do Yourself

| Task | Agent? | Why |
|------|--------|-----|
| Scaffold a new provider | ✅ Agent | Mechanical, pattern-following |
| Complete stub methods | ✅ Agent | Needs SDK knowledge, agent can read docs |
| Write tests | ✅ Agent | Pattern-matching from existing tests |
| Update documentation | ✅ Agent | Compare code vs. docs, fix discrepancies |
| Code review | ✅ Agent | Check pattern compliance |
| Generate changelog | ✅ Agent | Read git log, format consistently |
| Remove dead code | ✅ Agent | Search for references, confirm safe removal |
| Design new adapter APIs | ❌ You | Requires product judgment |
| Choose providers to support | ❌ You | Requires market/user research |
| Handle security issues | ❌ You | Requires careful human review |
| Release decisions | ❌ You | Requires judgment on timing/scope |
