# flin Google Tag Manager MCP

Read-only Google Tag Manager MCP server for Claude Desktop and other stdio MCP clients.

## Install in Claude Desktop on macOS

1. Download `flin-gtm-mcp-0.1.0-macos.mcpb` from
   [GitHub Releases](https://github.com/flin-agency/flin-gtm-mcp/releases).
2. Open the bundle with a current Claude Desktop version supporting MCPB v0.4 / uv extensions.
3. Select your Google **Desktop app** OAuth credentials JSON in the extension settings.
4. Ask Claude to authenticate with flin Google Tag Manager, then complete Google's browser consent.
5. Ask Claude to list your GTM accounts.

The bundle contains the server source and a dependency lockfile. Claude's uv runtime
installs Python and dependencies on first use (internet required); no PyPI release of
`flin-gtm-mcp` is needed. Supports Apple Silicon and Intel through uv-managed Python.
Older Claude versions without uv extension support must be updated or use manual setup.

See [Claude setup and Google credentials](docs/claude-desktop.md).

## Features

20 tools: authentication status/login; lists of accounts, containers, workspaces, tags,
triggers, variables, folders, built-in variables and version headers; individual
accounts, containers, workspaces, tags, triggers, variables, folders and versions;
and the published container version. Lists return one page with `next_page_token`.

Google access uses only `https://www.googleapis.com/auth/tagmanager.readonly`.
All GTM API operations use an explicit GET allowlist. No editing, deleting,
importing, publishing, preview creation or version creation. Login writes a local
token cache, but never changes GTM configuration.

## Python installation

Python 3.11+:

```sh
python3 -m pip install .
export FLIN_GTM_CREDENTIALS_FILE="/absolute/path/to/google-oauth.json"
flin-gtm-mcp login
flin-gtm-mcp status
flin-gtm-mcp serve
```

`serve` (the default) uses stdio. Protocol output is reserved for MCP; diagnostics
use stderr. OAuth credentials are loaded lazily, so the server starts and lists
tools before login. Service-account JSON is also supported when the service-account
email has explicitly been granted access to the desired GTM container.

## Development and packaging

```sh
uv sync --extra dev --frozen
uv run pytest
uv run ruff check .
uv run python -m build
uv run twine check dist/*.whl dist/*.tar.gz
uv run python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb validate manifest.json
```

The MCPB builder includes only explicit project files, never `.env`, local credentials,
tokens, virtual environments or Git metadata. SHA-256 accompanies the bundle.
CI runs tests and builds on macOS and Linux. The manual GitHub Release workflow (`github-release.yml`) publishes wheel, source
distribution and MCPB. The separate PyPI workflow (`release.yml`) publishes the
existing release distributions using PyPI Trusted Publishing.

## PyPI release

Configure a Trusted Publisher in PyPI with:

- Project: `flin-gtm-mcp`
- Owner: `flin-agency`
- Repository: `flin-gtm-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

For the first publication, register a pending publisher at
https://pypi.org/manage/account/publishing/ while signed in to the intended owner account.
Then run **Actions → Publish release to PyPI → Run workflow** on `main`, with the
existing release tag (for example `v0.1.0`). No stored API token is needed.
The workflow validates the package name, version and metadata before uploading
only the wheel and source archive. It never uploads the Claude bundle to PyPI.

After successful publication: `pip install flin-gtm-mcp`.

## Privacy and limits

Credentials stay on your computer; Google receives authentication and GTM API requests.
Returned GTM configuration is shared with the MCP client and its model according to
that client's settings. No flin telemetry or hosted proxy is used. OAuth tokens are
stored in a per-client file with owner-only permissions, not in the macOS Keychain.
Custom HTML and configuration strings are untrusted data and are never executed.
The extension is unsigned. Real Google access requires your own credentials and consent.

[Google authorization reference](https://developers.google.com/tag-platform/tag-manager/api/v2/authorization)
· [Read-only contract](docs/read-only-contract.md)
