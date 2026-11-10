# Release procedure

Follow the shared [versioning policy](../VERSIONING.md). The GitHub Actions
workflows are manual-only: only the owner (`@bezu-1`) starts, reruns, or
re-enables them, and only the owner approves the protected `pypi` environment.
Agents run the equivalent checks locally and never dispatch, rerun, re-enable,
or approve a workflow. Pull requests, issues, comments, and mentions never
start one.

## 1. Prepare

1. Confirm one release identity: `version` in `pyproject.toml`,
   `swap_layer.__version__`, `server.version` in both copies of the MCP
   contract (`mcp/agent-contract.json` and
   `src/swap_layer/mcp/agent-contract.json`), the dated `CHANGELOG.md` entry,
   and the supported-versions table in `SECURITY.md`.
2. Review the compatibility impact, migration notes, provider guides, and
   documentation. Versions advance independently of the other Tunet libraries.

## 2. Verify

Run the checks the release workflow runs, on the supported Python versions, the
minimum and current Django, and both the core install and the provider extras:

```bash
python -m pip install -e ".[all,dev]"
python -m ruff check src tests
python -m mypy src/swap_layer
python -m bandit -r src
AWS_EC2_METADATA_DISABLED=true python -m pytest --cov=swap_layer --cov-branch
```

Audit the installed dependencies with `pip-audit` (the security workflow runs
it with `--strict`), start `swaplayer-mcp` over stdio, check affected Django
admin pages in an isolated browser profile, inspect the source and history for
secrets, and record any check you could not run. The provider suite uses mocks
and SDK response objects; it is not live account certification or an
independent audit. The owner runs the manual test, security, and CodeQL
workflows on the release commit.

## 3. Build

```bash
python -m pip install --require-hashes -r requirements/build.txt
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
python -m build --no-isolation
python -m twine check dist/*
```

`requirements/build.txt` is the hash-locked output of the `uv pip compile`
command in its header. Dependabot leaves it and `requirements/build.in` alone,
so to update the release tools, edit `build.in` and run that command again.

Build from the exact intended Git tree, with no uncommitted changes. Record
SHA-256 checksums, inspect both archives (the MIT license, `py.typed`, the
versioned public contract, the documentation, and no private files or secrets),
and smoke-test the exact wheel in a clean environment.

## 4. Publish

1. Commit and push the verified source under the owner's authorization, then
   create an annotated `v<version>` tag on that exact commit. Only repository
   administrators can create `v*` tags, and nobody can move or delete one.
2. The owner starts `publish.yaml` from `main` or that tag; it stops on any
   other ref, including a tag that does not match the package version. The
   build job repeats the lint, type, Bandit, and test checks, builds the
   distributions with the hash-locked tools, runs `twine check`, and writes
   `SHA256SUMS`.
3. The upload job runs in the `pypi` environment, which only `main` and `v*`
   tags may use and which needs the owner's approval; administrators cannot
   bypass it, and agents cannot give that approval. PyPI Trusted Publishing
   gives the job a short-lived OIDC token, so no long-lived PyPI token exists.
   The trusted publisher must name `Tunet-xyz/swap_layer`, `publish.yaml`, and
   the `pypi` environment; otherwise a workflow edited on another branch could
   publish.

Do not publish when a check was skipped without a recorded reason, evidence is
missing, the checkout is dirty, the tag and version disagree, or a security
finding is unresolved. A rerun must start from the same commit or from a new,
reviewed release candidate.

## 5. After publication

Verify the version, file hashes, metadata, and links on PyPI, and install the
release in a clean environment before announcing it. A prepared or tagged
version is not a release until it is on PyPI.

Then update anything that described the publication as pending, such as the
changelog heading or the README's release status.

Never put PyPI credentials, agent tokens, or production data in release
artifacts or workflow logs. Never move a release tag, overwrite PyPI files, or
reuse a published version; fix a bad release with a new version.
