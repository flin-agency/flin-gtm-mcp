# flin Google Tag Manager MCP

Read-only Google Tag Manager MCP server for Claude Desktop and other stdio MCP clients.

## Claude Desktop on Apple Silicon (M1 or newer)

1. **[Download flin-gtm-mcp.mcpb](https://github.com/flin-agency/flin-gtm-mcp/releases/latest/download/flin-gtm-mcp.mcpb)**
   and open it with a current Claude Desktop version supporting MCPB v0.4 / uv.
2. Install the extension. Enter **OAuth client ID** and **OAuth client secret** from
   your administrator/password manager. They must belong to the same Google
   **Desktop app** OAuth client. The secret field is sensitive; no JSON file is needed.
3. Ask Claude: “Authenticate with flin Google Tag Manager using `gtm_authenticate`.”
   Complete Google's browser consent using an account with GTM access.
4. Ask: “Run `connection_status`, then `gtm_list_accounts`.” The first reports local
   setup and the running server version without contacting Google. The second is
   the live connection test; a successful empty list means no visible GTM accounts.

**Updates:** the current launcher automatically loads compatible stable **0.2.x**
PyPI updates on restart (`>=0.2.4,<0.3.0`, no prereleases). Running sessions keep their
version. Settings and tokens stay in place when the OAuth client ID is unchanged.
The **extension version** identifies the installed starter/settings; **`server_version`**
from `connection_status` identifies the process actually running. A stored token is
`unknown`, not proof of live access; `live_access` stays `not_checked` in this local check.
The existing `gtm_auth_status` tool also remains available and may refresh tokens.

**One-time import:** install the current bundle once to adopt the tested 0.2 compatibility
boundary. Older 0.2.2/0.2.3 starters have no upper version limit; bundles up to 0.2.1 do
not auto-update. Later starter/UI changes can also require a fresh import. Ordinary
compatible server updates need only a restart. The boundary preserves the existing
0.2 stdio, snapshot/pagination, OAuth-setting and token-storage interfaces; a new
minor line must be reviewed before adoption.

Internet is needed for normal startup/update checks. If PyPI is unavailable, retain
the installation and use the documented [existing-environment fallback](SUPPORT.md#existing-installation-fallback)
with administrator help. There is no silent automatic offline fallback.
Intel Mac support is retained; manual Python/stdio use also supports Linux.
[Versioned packages and SHA-256 files](https://github.com/flin-agency/flin-gtm-mcp/releases)
remain available alongside the stable download name.

[Google setup and manual configuration](docs/claude-desktop.md) · [Privacy](PRIVACY.md)
· [Security](SECURITY.md) · [Support](SUPPORT.md)

## Features

35 tools cover authentication, accounts, containers, workspaces, tags, triggers,
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
launcher loading successive compatible packages with preserved settings/tokens and
rejecting prereleases, the next minor line and a new major version. The offline
existing-environment fallback is also exercised. Local macOS arm64 testing is distinct
from Linux CI; neither replaces installation in Claude or a real Google account test.
For a pre-publication bundle test, build a wheel and run
`uv run python scripts/check_mcpb.py --wheel-dir dist`.

## Automatic releases: PyPI and Claude Desktop

Every new version pushed to `main` runs **Release to PyPI and Claude Desktop**
(`release.yml`) automatically:

1. Validate matching package/source/manifest versions; skip a completed release.
2. Run tests, security scans, builds and bundle startup on macOS and Linux.
3. Publish the tested wheel/source to PyPI with Trusted Publishing.
4. Verify PyPI file hashes and start the bundle using the public PyPI package.
5. Publish the matching versioned `.mcpb`, stable `flin-gtm-mcp.mcpb` alias, checksums, wheel and source archive on GitHub.

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

Google receives OAuth credentials/tokens for authentication and GTM API requests.
Local credential storage and removal are described in [PRIVACY.md](PRIVACY.md).
Returned GTM configuration is shared with the MCP client and its model according to
that client's settings. No flin telemetry or hosted proxy is used. OAuth tokens are
stored in a per-client file with owner-only permissions, not in the macOS Keychain.
Custom HTML and configuration strings are untrusted data and are never executed.
The extension is unsigned. Real Google access requires your own credentials and consent.
Automatic updates trust the stable releases published by this project on PyPI and
resolve dependencies using the package constraints. The launcher deliberately accepts
compatible stable 0.2.x updates within its explicit version boundary.

[Google authorization reference](https://developers.google.com/tag-platform/tag-manager/api/v2/authorization)
· [Read-only contract](docs/read-only-contract.md)
