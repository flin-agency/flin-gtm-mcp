# Read-only implementation contract

The server uses only Google Tag Manager API v2 and the
`https://www.googleapis.com/auth/tagmanager.readonly` OAuth scope.

`client.py` validates full relative resource paths against fixed patterns before
creating a network session. Only numeric resource IDs and allowlisted GET endpoints
are accepted. Redirects are disabled. Tools cannot select arbitrary URLs, methods,
OAuth scopes or token destinations. There are no GTM mutation tools or write switches.

All GTM tools carry `readOnlyHint=true` and `destructiveHint=false`. Authentication
is separately marked as a local write because it stores OAuth credentials. Metadata
is descriptive; enforcement comes from the API allowlist and OAuth scope.

Lists expose one API page with a continuation token. API errors are not reported as
empty success. Raw HTTP/auth exceptions are suppressed to avoid returning credentials.
Calls have a 30-second network timeout; browser login has a 120-second timeout.
Workspace drafts are distinguished from the published version. Tag contents, including
Custom HTML, are data, not executable instructions.

Tests cover rejected paths before network access, pagination, API error handling,
OAuth scope restrictions, private token storage and a real MCP stdio handshake.
Live Google login and reads must also be checked with an authorized test account;
unit/protocol tests do not prove the user's Google permissions or consent setup.
