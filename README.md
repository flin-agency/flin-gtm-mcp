# flin Google Tag Manager MCP

Read-only Google Tag Manager MCP server for Claude Desktop and other stdio MCP clients.

## Install in Claude Desktop on macOS

1. Use the locally built `dist/flin-gtm-mcp-0.2.3-macos.mcpb`, or [download the macOS installer](https://github.com/flin-agency/flin-gtm-mcp/releases/download/v0.2.3/flin-gtm-mcp-0.2.3-macos.mcpb).
2. Open the bundle with a current Claude Desktop version supporting MCPB v0.4 / uv extensions.
3. Enter your Google **Desktop app** **OAuth client ID** and **OAuth client secret**
   in the extension settings. The secret is a protected input field; no JSON file is required.
4. Ask Claude to authenticate with flin Google Tag Manager, then complete Google's browser consent.
5. Ask Claude to list your GTM accounts.

The bundle is a small launcher. Each extension/server start uses Claude's uv runtime
to fetch the newest stable `flin-gtm-mcp` release from PyPI. A running process keeps
its version until Claude/the server restarts. Internet is required to check/install
updates; no terminal command or new MCPB download is needed for server updates.
Supports Apple Silicon and Intel through uv-managed Python.

**Settings update:** install the 0.2.3 bundle once to get the two OAuth input fields.
Existing 0.2.2 launchers still receive server updates using their selected JSON file.
Older fixed-source bundles (up to 0.2.1) need a new bundle for automatic updates.
Using the same OAuth client ID preserves the existing local token cache. The extension's displayed version
is the launcher version; ask for `gtm_auth_status` to see `server_version`.
Changes to extension settings, permissions or the launcher itself can still require
a new MCPB installation. The server version updates automatically.

See [Claude setup and Google credentials](docs/claude-desktop.md) and the
[0.2.1 security review](docs/security-review.md).

## Features

34 tools cover authentication, accounts, containers, workspaces, tags, triggers,
variables, folders, built-ins, version headers and versions, plus:

- Public-ID lookup, workspace status and paginated folder contents.
- Custom templates, Google tag configs, server-side clients and transformations.
- Published/saved version snapshots, paginated snapshot details, dependency analysis
  and structured version comparisons.
- Three guided prompts (`audit_container`, `best_practices_review`,
  `generate_tracking_plan`) and resources for conventions, accounts, live snapshots
  and workspace collections.

Google access uses only `https://www.googleapis.com/auth/tagmanager.readonly`.
An explicit method/path allowlist permits GET reads and exactly one read-only POST:
folder contents. No editing, deleting, importing, publishing, preview creation or
version creation. Login writes a local token cache, never GTM configuration.

### Audit workflow and response changes in 0.2

1. Resolve public IDs with `gtm_lookup_container(tag_id="GTM-...")`.
2. Call `gtm_get_live_version(parent="accounts/123/containers/456")`.
3. Use its `snapshot_id` with `gtm_read_snapshot`, selecting an entity `kind` and
   following `next_offset`. Set `full=true` for parameters or template source.
4. Run `gtm_analyze_dependencies(snapshot_id=...)` for structural candidates.
5. Fetch another version using `gtm_get_version`, then compare the two snapshot IDs
   using `gtm_diff_versions`. Follow `next_offset` for all changes.

**Version tools now return snapshot metadata and counts**, rather than the entire
raw container. All ten entity kinds remain accessible through `gtm_read_snapshot`.
Lists, folder contents and workspace status default to compact responses that omit
`parameter` and `templateData` with explicit `_omitted_fields`; `full=true` opts in.
Individual entity get tools return full details. Existing list pagination parameters
still work. List tools (except accounts) and folder contents optionally read up to
five pages with `max_pages`; always follow `next_page_token` until null.

Snapshots are memory-only, scoped to the current local credentials, reusable for
60 seconds and readable for five minutes. Use `refresh=true` on version tools to
check Google again. The cache holds at most eight snapshots / 32 MiB; expiration,
eviction or a changed login requires a new fetch. Cached data reflects fetch time,
not necessarily the current published configuration.

Requests are spaced by 4.05 seconds across this server process, with at most three
attempts for transient failures. Permission and daily-quota errors are not retried.
Other processes/apps sharing a Google project still share its quota. Multi-page
calls and retries can take longer than a single request; client timeouts must allow
for this. Explicit `full=true` responses can be large.

Workspace status is relative to its **base version**, not necessarily live.
Dependency findings are static candidates, not deletion advice. Consent settings
alone cannot certify compliance or actual runtime behaviour. No tag code is executed.

## Python installation

Python 3.11+:

```sh
python3 -m pip install .
export FLIN_GTM_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export FLIN_GTM_CLIENT_SECRET="your-client-secret"
flin-gtm-mcp login
flin-gtm-mcp status
flin-gtm-mcp serve
```

`serve` (the default) uses stdio. Protocol output is reserved for MCP; diagnostics
use stderr. OAuth credentials are loaded lazily, so the server starts and lists
tools before login. Both OAuth values must be set together. They take precedence
over `FLIN_GTM_CREDENTIALS_FILE`; an incomplete pair fails instead of selecting another account.
The JSON-file option remains available for existing clients and CLI use. Service-account
JSON is supported when its email has explicitly been granted access to the GTM container.

## Development and packaging

```sh
uv sync --extra dev --frozen
uv run pytest
uv run ruff check .
uv run bandit -q -r src
uv run python -m build
uv run twine check dist/*.whl dist/*.tar.gz
uv run python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
```

The MCPB builder includes only explicit project files, never `.env`, local credentials,
tokens, virtual environments or Git metadata. SHA-256 accompanies the bundle.
CI runs tests and builds on macOS and Linux, including an unchanged installed
launcher loading two successive package versions and rejecting a newer prerelease.
For a pre-publication bundle test, build a wheel and run
`uv run python scripts/check_mcpb.py --wheel-dir dist`.

## Automatic releases: PyPI and Claude Desktop

Every new version pushed to `main` runs **Release to PyPI and Claude Desktop**
(`release.yml`) automatically:

1. Validate matching package/source/manifest versions; skip a completed release.
2. Run tests, security scans, builds and bundle startup on macOS and Linux.
3. Publish the tested wheel/source to PyPI with Trusted Publishing.
4. Verify PyPI file hashes and start the bundle using the public PyPI package.
5. Publish the matching `.mcpb`, checksum, wheel and source archive on GitHub.

For each release, bump `pyproject.toml`, `manifest.json` and
`src/flin_gtm_mcp/__init__.py`, refresh `uv.lock` and update release notes.
A code-only commit without a new version does not replace an existing release.
A failed run can be retried under Actions; no separate PyPI action is needed.
GitHub publication waits for successful PyPI publication and the public-package test.

The existing PyPI Trusted Publisher must retain owner `flin-agency`, repository
`flin-gtm-mcp`, workflow `release.yml` and environment `pypi`. No stored API token
is needed. Only wheel/source distributions go to PyPI; MCPB files go to GitHub.

[PyPI package](https://pypi.org/project/flin-gtm-mcp/)
· [GitHub releases](https://github.com/flin-agency/flin-gtm-mcp/releases)

## Privacy and limits

Credentials stay on your computer; Google receives authentication and GTM API requests.
Returned GTM configuration is shared with the MCP client and its model according to
that client's settings. No flin telemetry or hosted proxy is used. OAuth tokens are
stored in a per-client file with owner-only permissions, not in the macOS Keychain.
Custom HTML and configuration strings are untrusted data and are never executed.
The extension is unsigned. Real Google access requires your own credentials and consent.
Automatic updates trust the stable releases published by this project on PyPI and
resolve dependencies using the package constraints. The launcher deliberately does
not freeze the application to the version it originally installed.

[Google authorization reference](https://developers.google.com/tag-platform/tag-manager/api/v2/authorization)
· [Read-only contract](docs/read-only-contract.md)
