# SwapLayer security assurance case

This document links SwapLayer's security claims to repository evidence. Passing
evidence increases confidence; it is not an independent audit, a certification,
or live certification against any provider.

## Claims and evidence

| Claim | Implementation | Automated evidence |
| --- | --- | --- |
| Local storage keys reject traversal, absolute paths, symlinks, and junctions | `storage/providers/local.py` | `tests/test_release_security.py` |
| Scoped storage needs an explicit context and checks permissions | `storage/security.py` | `tests/test_release_security.py`, `tests/test_provider_boundaries.py` |
| Storage contexts are frozen, accept only plain identity segments and placeholders they set, and grant unscoped access only through `system_context()` | `storage/security.py` | `tests/test_storage_security_context.py` |
| Webhooks are verified before use: a missing secret or malformed signature is refused, Square events must be recent, and SMTP payloads are never verified | `billing/providers/stripe.py`, `billing/providers/paypal.py`, `billing/providers/square.py`, `identity/verification/providers/stripe.py`, `communications/email/providers/smtp.py` | `tests/test_stripe_webhook_events.py`, `tests/test_paypal_provider.py`, `tests/test_square_provider.py`, `tests/test_paypal_square_guards.py`, `tests/test_identity_webhook_secret.py`, `tests/test_smtp_webhooks.py` |
| PayPal and Square invoice lists return only the requested customer's invoices | `billing/providers/paypal.py`, `billing/providers/square.py` | `tests/test_invoice_customer_scope.py` |
| WorkOS sign-in callbacks need their session's OAuth state, and WorkOS cookie passwords are Fernet keys | `identity/platform/providers/workos/client.py`, `settings.py` | `tests/test_workos_oauth_state.py`, `tests/test_workos_cookie_password.py` |
| Identifiers in provider REST paths are percent-encoded | `http.py` | `tests/test_request_path_encoding.py` |
| Credential fields are masked in errors, configuration output shows only public fields, and settings `repr()` and `str()` leave credentials out | `exceptions.py`, `_redaction.py`, `settings.py` | `tests/test_error_system.py`, `tests/test_config_output.py`, `tests/test_release_security.py`, `tests/test_settings_repr_secrets.py` |
| Settings reject unknown keys and misspelt `SWAPLAYER_` variables | `settings.py` | `tests/test_settings_strictness.py` |
| Amounts are whole minor units of at most 18 digits | `billing/adapter.py` | `tests/test_billing_amounts.py` |
| SwapLayer's own HTTP clients, SMTP email sends, and Twilio use timeouts | `http.py`, the PayPal and Square clients, the email and Twilio providers | `tests/test_provider_boundaries.py`, `tests/test_release_security.py`, `tests/test_provider_timeouts.py`, `tests/test_paypal_square_guards.py` |
| MCP tools carry read-only annotations that match what they do | `mcp/server.py` | `tests/test_mcp_server.py` |
| Optional providers import lazily | provider factories | `tests/test_optional_dependencies.py`, `tests/test_import_without_django.py` |
| One release identity across metadata and both copies of the MCP contract | `pyproject.toml`, the contracts | `tests/test_release_identity.py` |

## Evidence commands

Run from a clean checkout of the revision being assessed:

```bash
python -m pip install -e ".[all,dev]"
python -m ruff check src tests
python -m mypy src/swap_layer
python -m bandit -r src
python -m pip freeze --exclude SwapLayer > audit-requirements.txt
python -m pip_audit --strict --disable-pip --no-deps -r audit-requirements.txt
AWS_EC2_METADATA_DISABLED=true python -m pytest --cov=swap_layer --cov-branch
```

## Workflow evidence

The GitHub workflows are manual: only the owner starts them, and none runs on
a schedule (Dependabot checks dependencies weekly). Record which of them ran
for the assessed commit.

| Workflow | What it runs |
| --- | --- |
| `tests.yaml` | Ruff, mypy, and pytest with branch coverage on Python 3.10–3.13, and the tests on Django 4.2 in the `minimum-dependencies` job |
| `security.yaml` | Bandit and a strict dependency audit |
| `codeql.yaml` | CodeQL with the security-extended queries |
| `publish.yaml` | The same checks, a hash-locked build with checksums, and PyPI publication |

Keep the workflow URLs and logs, commit SHA, and release checksums as the
evidence bundle; workflow artifacts expire.

## Manual evidence still required

- Independent code review, including storage scoping, webhook verification,
  and credential handling.
- End-to-end tests against each provider's test environment, which the mocked
  suite does not replace.
- The host's filesystem permissions for local storage, and its provider
  account and webhook configuration.
- Repository settings from GitHub (see
  [secure development](SECURE_DEVELOPMENT.md#repository-controls)).
