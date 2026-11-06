# Security review — 0.2.1

Review date: 2026-11-06. Scope: all application modules, OAuth and token storage,
MCP tools/resources/prompts, dependency lockfile, packaging and GitHub workflows.
This is a code and automated-test review, not an independent penetration test or
security certification.

## Findings and fixes

- **Known vulnerable dependency:** the lockfile contained oauthlib 4.0.0, flagged
  for [CVE-2026-49272 / GHSA-3jp2-3mrg-2vxc](https://github.com/oauthlib/oauthlib/security/advisories/GHSA-3jp2-3mrg-2vxc).
  Updated to 4.0.1 and added a minimum version constraint. The advisory concerns
  OAuth device-grant server validation; this project uses Google's authorization-code
  client flow and does not implement the affected server flow. No exploit of this
  application's flow was established.
- **Credential transport hardening:** login token exchange and refresh now disable
  redirects and use 30-second HTTP timeouts. Refresh accepts only POST to Google's
  fixed token endpoint. PKCE S256 is explicitly enabled; the library validates OAuth
  state. Unexpected granted scopes after refresh are rejected before caching.
  An API 401 returns an actionable error instead of an implicit in-request refresh;
  expired tokens refresh through the checked credential-loading path.
- **Local cache hardening:** on macOS/Linux, token directories must be real directories
  owned by the current user. Cache reads reject symlinks, hardlinks and non-regular files;
  existing directory/file permissions are repaired to 0700/0600. Writes remain atomic.
  This does not protect against malware already running as the same OS user.
- **Release integrity:** fixed GitHub Action commit hashes, disabled persisted checkout
  credentials, main-only serialized releases and explicit release asset names. CI and
  releases run dependency auditing and static security checks. The bundle uses a fixed
  file allowlist, rejects symlink inputs, has deterministic ZIP metadata and includes
  a SHA-256 checksum checked during its startup test.

## Retained security boundaries

- Only the `tagmanager.readonly` scope and a fixed method/path allowlist are exposed.
  All API URLs use Google's fixed HTTPS origin; no arbitrary URLs or mutations.
  The sole POST reads folder contents, as documented by Google.
- No shell, code execution, write-to-GTM or publishing tool. Tag/template contents
  remain untrusted data; instructions warn the client not to execute or obey them.
  Prompt injection in retrieved content remains a client/model concern.
- OAuth callback binds only to IPv4 loopback on an ephemeral port, with a 120-second
  consent wait. Raw credential-bearing exceptions and callback URL logs are suppressed.
- Snapshots are kept in bounded process memory, expire after five minutes and are
  tied to local credentials. Revalidation does not recheck remote permissions on
  every cached read. Tokens are local files, not macOS Keychain entries.
- GTM configuration is passed to the MCP client/model under its privacy settings.
  No flin telemetry or hosted proxy is used. Google receives auth and API requests;
  first launch also contacts Python/package distribution services for dependencies.

## Verification and limitations

Local macOS verification passed: 54 tests, Ruff, Bandit, strict wheel/source metadata
validation, official MCPB 2.1.2 manifest validation and the extracted-bundle startup
test. `pip-audit` reported no known vulnerabilities in 83 applicable pinned runtime
and development packages after the update. Gitleaks 8.30.1 found no secrets in the
four existing Git commits or the complete tracked/new source snapshot. These
scanner results are limited to their rules and published advisory data.

Regression tests cover forbidden methods/paths, OAuth scope restrictions, PKCE,
redirect/timeout controls, cache links and permissions, redacted errors, pagination,
rate limits, snapshot isolation and reproducible bundle exclusion rules. The actual
archive is extracted into a temporary folder and started using its manifest's uv
command; MCP initialization and all 34 tools are checked without real credentials.

`pip-audit` checks pinned runtime/development dependencies against published advisory
records; `bandit` scans application code. Two documented static-analysis suppressions
cover a public token-endpoint URL and non-security retry jitter. A clean scan means
no matching known advisories at scan time, not proof of absence of vulnerabilities.

Live Google consent/API access and installation through Claude Desktop's UI require
an authorized user account and were not exercised by the automated review. The MCPB
is unsigned and requires a current Claude Desktop with MCPB v0.4 / uv support.
SHA-256 detects accidental changes but is not an independent publisher signature.


## 0.2.2 distribution change

The 0.2.1 review above describes its fixed-source bundle. Starting with 0.2.2 the
MCPB contains only the launcher and documentation, not server source or `uv.lock`.
It uses the official HTTPS PyPI index, checks for a newer flin-gtm-mcp release on
each startup and excludes prereleases. This intentionally trusts future stable
PyPI releases; installed server code is no longer frozen to the initial bundle's
checksum. Dependencies resolve under the published package's version constraints.
The read-only API and credential boundaries remain unchanged.

The unified release workflow tests on macOS/Linux, publishes through the existing
PyPI Trusted Publisher, compares published distribution hashes to the tested files
and starts the actual public PyPI package before offering the GitHub MCPB. Tests
also exercise an unchanged launcher upgrading from one stable version to another
while ignoring a newer prerelease. Normal server updates take effect on restart;
metadata/permission changes to the side-loaded extension may still need reinstallation.
