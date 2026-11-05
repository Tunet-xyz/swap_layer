# Releasing SwapLayer 1.x

Follow [VERSIONING.md](../VERSIONING.md). Versions advance independently of the other libraries. The initial stable release is 1.0.0; use patch releases for compatible fixes, minor releases for compatible features, and major releases for breaking documented APIs. Package, runtime, public contract and MCP server identities must agree.

## Verify locally

Install `requirements/build.txt` with `python -m pip install --require-hashes -r requirements/build.txt`, then install `.[all,dev]` for source checks. Run pytest with coverage, Ruff, full-source mypy, Bandit, and a third-party dependency audit. Test supported Python versions, minimum/current Django adapters, clean core and provider extras, stdio startup and artifact contents. Changes to admin displays also need a real isolated-browser flow check.

Build from the exact intended Git tree, excluding other agents' uncommitted work. Set `SOURCE_DATE_EPOCH` from the release commit and run `python -m build --no-isolation`; run strict Twine metadata checks and record SHA-256 hashes. Inspect both wheel and sdist for the MIT license, typing marker, versioned public contract, documentation and absence of private files/secrets. Run the installed wheel in a fresh environment.

The provider suite uses mocks and SDK response objects; it is not live account certification or an independent audit. Record skipped/unavailable checks, including native platform checks that could not run.

## Publish with owner approval

Create an immutable annotated `v1.0.0` tag on the verified revision. The owner manually starts `publish.yaml` on that tag or `main` and approves the `pypi` environment. Agents must not dispatch, rerun or enable workflows or approve the environment. Every job checks the owner actor, uses pinned actions and read-only default permissions. Only the isolated upload job receives OIDC permission; no long-lived PyPI or agent tokens are required.

Configure the PyPI trusted publisher for `Tunet-xyz/swap_layer`, workflow `publish.yaml`, environment `pypi`. Verify the project/version metadata and downloaded artifact hashes on PyPI before announcing availability. Never replace a published version; fix forward with a new version.
