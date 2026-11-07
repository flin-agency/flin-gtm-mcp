# Privacy

This MCP runs locally. On explicit login, your browser connects to Google and a
loopback callback receives the authorization code. OAuth credentials and refresh
tokens are sent to Google's fixed HTTPS token endpoint. Read tools send identifiers
and read requests to the Google Tag Manager API. No flin proxy or telemetry is used.

GTM configuration returned by tools goes to Claude or your chosen MCP client and
may be processed by its model provider according to that client's settings. Tags,
custom HTML and templates can contain confidential data; this server never executes
them. Snapshots are held only in process memory, for at most five minutes.

The two OAuth fields come from your administrator/password manager. Claude manages
its extension settings; the secret field is marked sensitive. The server receives
these settings as environment variables. **OAuth tokens and a copy of the OAuth
client details are stored as unencrypted JSON**, protected by owner-only filesystem
permissions (directory `0700`, file `0600`), not by this server using Keychain:

- macOS: `~/Library/Application Support/flin-gtm-mcp/token-<client-hash>.json`
- Linux: `~/.config/flin-gtm-mcp/token-<client-hash>.json`

Legacy OAuth/service-account JSON stays at the path you select. Reusing the same
OAuth client ID preserves the token location. Login with another Google account
replaces that client's saved token.

Startup contacts PyPI to resolve/download compatible server releases and dependencies;
uv may download Python if needed. Those download services receive normal request
metadata. They do not receive OAuth settings from this application's download code.

To disconnect, revoke consent in [Google account connections](https://myaccount.google.com/connections),
remove the Claude extension/settings, and delete its local token files. Also remove
manual configuration and any legacy JSON you no longer need. Service-account access
must be removed in GTM and its key revoked in Google Cloud by an administrator.
Uninstalling alone does not revoke Google access.

See [setup and storage](docs/claude-desktop.md) and [security](SECURITY.md).
