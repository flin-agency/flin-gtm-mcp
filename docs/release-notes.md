# 0.2.1 — Security review and macOS installer

Download **flin-gtm-mcp-0.2.1-macos.mcpb** below for Claude Desktop on Mac
(Apple Silicon and Intel; current Claude with MCPB v0.4 / uv support).
In Claude settings, open Extensions → Advanced settings → Install Extension,
then select your Google Desktop app OAuth JSON and request authentication.
The first launch requires internet for Python/dependencies. The bundle is unsigned.

- Updated oauthlib to 4.0.1 to remove a known dependency advisory; its affected
  device-grant server flow is not used by this application.
- Hardened OAuth token transport, explicitly enabled PKCE and checked refreshed scopes.
- Hardened local token cache permissions and rejected symlinks/hardlinks.
- Reproducible, allowlisted bundle with SHA-256; pinned CI actions and added
  dependency auditing and static security checks before releases.
- All 34 tools retain read-only GTM access. No GTM data is modified.

See [setup](https://github.com/flin-agency/flin-gtm-mcp/blob/v0.2.1/docs/claude-desktop.md)
and [security review](https://github.com/flin-agency/flin-gtm-mcp/blob/v0.2.1/docs/security-review.md)
for findings, verification and remaining limits. Live Google access and the Claude
installation UI need user credentials and were not tested in this review.

# 0.2.0 — Read-only audits and snapshots

- 34 tools, including public-ID lookup, workspace status, folder contents, templates,
  Google tag configs, server-side clients and transformations.
- Complete version snapshots with credential-bound, bounded memory caching,
  paginated detail reads, dependency candidates and structured version diffs.
- Process-wide throttling, selective bounded retries and optional multi-page reads.
- Compact list/status responses, three audit/documentation prompts and four resource
  registrations (two fixed resources and two URI templates).
- Strict readonly OAuth and method/path allowlist; the only POST reads folder contents.

Migration: version tools now return snapshot IDs and counts. Use
`gtm_read_snapshot` for entities and `full=true` for parameters/template source.
Lists retain continuation tokens and default to compact output. Individual entity
get tools still return full data. Workspace status describes base-version changes.

Install the generated macOS `.mcpb` in a Claude Desktop version supporting MCPB
v0.4 / uv extensions, then select your Google Desktop OAuth JSON. Dependencies need
internet on first launch. The extension is unsigned. Live OAuth/API reads and
installation through Claude's UI require a separate authorized-account check.

# 0.1.0

Initial release with 20 read-only authentication and GTM configuration tools.
