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
