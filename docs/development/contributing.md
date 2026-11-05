# Contributing to SwapLayer

The current rules are [CONTRIBUTING.md](../../CONTRIBUTING.md), [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md), and [VERSIONING.md](../../VERSIONING.md). Root policy files are intentional. Keep public guidance under `docs/`; mark historical design notes clearly.

Install `.[all,dev]` in an isolated environment. Run `python -m pytest --cov=swap_layer --cov-branch`, `python -m ruff check src tests`, `python -m mypy src/swap_layer`, and `python -m bandit -r src`. Use mocked provider accounts in automated checks. Verify affected Django flows in an isolated browser when changing UI. Never reuse a person's browser profile or sessions.

Public PRs are welcome, but require owner review. Do not dispatch, rerun or enable GitHub Actions as an agent; run the equivalent checks locally. The user starts all workflows and approves the PyPI environment. Release instructions are in [RELEASE.md](../RELEASE.md).

Other files in this directory retain historical implementation decisions. Current provider support is listed in [the documentation index](../README.md).
