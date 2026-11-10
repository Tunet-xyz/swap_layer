# SwapLayer security assurance case

This document links SwapLayer's security claims to repository evidence. Passing
evidence increases confidence; it is not an independent audit, a certification,
or live certification against any provider.

## Claims and evidence

| Claim | Implementation | Automated evidence |
| --- | --- | --- |
| Local storage keys reject traversal, absolute paths, symlinks, and junctions | `storage/providers/local.py` | `tests/test_release_security.py` |
| Scoped storage needs an explicit context and checks permissions | `storage/security.py` | `tests/test_release_security.py`, `tests/test_provider_boundaries.py` |
| PayPal and Square webhooks are verified before use | `billing/providers/paypal.py`, `billing/providers/square.py` | `tests/test_paypal_provider.py`, `tests/test_square_provider.py` |
| Credential fields are masked in errors, and configuration output shows only public fields | `exceptions.py`, `_redaction.py` | `tests/test_error_system.py`, `tests/test_config_output.py`, `tests/test_release_security.py` |
| SwapLayer's own HTTP clients use timeouts | `http.py`, the PayPal and Square clients | `tests/test_provider_boundaries.py`, `tests/test_release_security.py` |
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
