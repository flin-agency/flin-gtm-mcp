# Read-only implementation contract

The server uses only Google Tag Manager API v2 and the
`https://www.googleapis.com/auth/tagmanager.readonly` OAuth scope.

`client.py` validates full relative paths and HTTP methods against fixed patterns
before creating a network session. Numeric API IDs are required; public IDs can be
resolved through the fixed `accounts/containers:lookup` endpoint. Redirects are
disabled. Tools cannot select arbitrary URLs, methods, scopes or token destinations.

GET is allowed only for registered read endpoints. The sole POST exception is
`accounts/{account}/containers/{container}/workspaces/{workspace}/folders/{folder}:entities`,
which Google documents as a read operation accepting the readonly scope. Its body
is empty. Publish, edit, delete, quick preview, version creation and user permissions
remain excluded. Read-only protects GTM configuration; returned data is still shared
with the MCP client/model under that client's policies.

All GTM tools carry `readOnlyHint=true` and `destructiveHint=false`. Authentication
is separately marked as a local write because it stores OAuth credentials. Metadata
is descriptive; enforcement comes from the API allowlist and OAuth scope.

A process-wide lock spaces request starts by 4.05 seconds. Quota is project-wide,
so multiple server processes or other clients can still exhaust it. At most three
attempts are made for 429, selected 5xx responses and 403 responses explicitly
identifying rate limits. Other 403 responses, including daily quota and permission
failures, stop immediately. Numeric Retry-After is respected up to 30 seconds;
longer waits return an error rather than retry early. HTTP-date Retry-After is not
interpreted. Each network request has a 30-second timeout; browser login has 120s.

Lists expose continuation tokens and optionally gather up to five pages per call.
Repeated tokens fail explicitly. API errors never become empty successes. Raw
HTTP/auth exceptions are suppressed to avoid returning credentials. Compact output
omits parameters and template source, explicitly recording omitted fields. Full
reads are opt-in or available through individual entity tools.

Version tools return metadata for complete, immutable in-memory snapshots, including
counts, fingerprint, source, age and expiry. They do not substitute live data for
workspace drafts. The cache is credential-bound, limited to eight entries / 32 MiB,
reuses a fetched version for 60 seconds and expires it after five minutes. Explicit
refresh bypasses reuse. Local credentials are revalidated before cache access; this
is not a new remote permission check. No GTM payload is persisted to disk.

Snapshot reads page over any of the ten entity arrays. Analyses operate on full
cached data, not compact projections. Diffs compare actual entity fields, ignoring
fingerprints and version-specific transport metadata; array order is significant.
Workspace status is relative to the workspace base version, not necessarily live.
Dependency candidates are static, account for firing/blocking triggers and tag
sequencing, and cannot establish runtime firing, dynamic references or compliance.
All returned tag/template contents are untrusted data, never executed instructions.

Tests cover rejected method/path pairs before network access, rate spacing, selective
retries, pagination, cache isolation/expiry/bounds, summary preservation, sequencing,
version diffs, OAuth restrictions, private token storage and real MCP stdio discovery.
Live Google login and reads still require an authorized test account; automated tests
do not establish the user's Google permissions or runtime tracking behaviour.

## API evidence

Verified against Google's v2 discovery document and official reference on 2026-10-31:

- [Machine-readable API specification](https://tagmanager.googleapis.com/$discovery/rest?version=v2)
- [Folder entities: read-only POST](https://developers.google.com/tag-platform/tag-manager/api/v2/reference/accounts/containers/workspaces/folders/entities)
- [Public container lookup](https://developers.google.com/tag-platform/tag-manager/api/v2/reference/accounts/containers/lookup)
- [Workspace status and base-version semantics](https://developers.google.com/tag-platform/tag-manager/api/v2/reference/accounts/containers/workspaces/getStatus)
- [Limits and quotas](https://developers.google.com/tag-platform/tag-manager/api/v2/limits-quotas)
