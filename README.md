# flin Google Tag Manager MCP

Read-only Google Tag Manager MCP server for Claude Desktop and other stdio MCP clients.

## Install in Claude Desktop on macOS

1. Use the locally built `dist/flin-gtm-mcp-0.2.1-macos.mcpb`, or [download the macOS installer](https://github.com/flin-agency/flin-gtm-mcp/releases/download/v0.2.1/flin-gtm-mcp-0.2.1-macos.mcpb).
2. Open the bundle with a current Claude Desktop version supporting MCPB v0.4 / uv extensions.
3. Select your Google **Desktop app** OAuth credentials JSON in the extension settings.
4. Ask Claude to authenticate with flin Google Tag Manager, then complete Google's browser consent.
5. Ask Claude to list your GTM accounts.

The bundle contains the server source and a dependency lockfile. Claude's uv runtime
installs Python and dependencies on first use (internet required); no PyPI release of
`flin-gtm-mcp` is needed. Supports Apple Silicon and Intel through uv-managed Python.
Older Claude versions without uv extension support must be updated or use manual setup.

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
uv run bandit -q -r src
uv run python -m build
uv run twine check dist/*.whl dist/*.tar.gz
uv run python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
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
