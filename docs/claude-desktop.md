# Claude Desktop on macOS

## Google setup (once)

1. In Google Cloud, create/select a project and enable **Tag Manager API**.
2. Configure Google Auth Platform / OAuth consent. For an external app in Testing,
   add your Google account as a test user. Follow Google's current verification
   requirements if distributing your OAuth app beyond permitted test users.
3. Create an OAuth client of type **Desktop app**. Obtain its client ID and client secret from the responsible administrator/password manager.
4. Enter them in the extension settings under **OAuth client ID** and **OAuth client secret**.
   No JSON download is necessary. The secret field is marked sensitive; Claude manages the setting storage.
5. Use `gtm_authenticate` in Claude to open browser consent. The login waits up to
   120 seconds. If Claude times out first, use the CLI login below and retry.

The Google account must have access to the GTM containers. The server requests
only the read-only scope. No Google Cloud project, OAuth client or credentials are
created automatically. Google OAuth apps in Testing may require frequent re-login.

## Install the MCPB

Download [flin-gtm-mcp.mcpb](https://github.com/flin-agency/flin-gtm-mcp/releases/latest/download/flin-gtm-mcp.mcpb).
In Claude Desktop, open **Settings → Desktop app → Extensions → Manage →
Advanced settings → Install Extension…** (older layout: **Settings → Extensions**).
Select the downloaded file. Approve installation and
enter the OAuth client ID and client secret. Claude manages Python with uv. On every
server start it checks PyPI for the newest compatible stable flin-gtm-mcp 0.2.x version (`>=0.2.4,<0.3.0`) and updates its isolated environment. Internet is required.
New code becomes active after the next server/Claude restart. Credentials stay in
the same location; a normal server update does not require reauthentication.

Requires a Claude Desktop version with MCPB v0.4 / uv support; if the bundle is
rejected as unsupported, update Claude or use the manual stdio setup below.

Try: “Melde mich beim flin Google Tag Manager an und liste meine Accounts.”
Then: “Zeige Tags und Trigger im Workspace …; ändere nichts.”

## Automatic updates and one-time migration

Install the current 0.2.4 bundle once to adopt the explicit 0.2 compatibility boundary.
The extension ID and OAuth field names are unchanged from 0.2.3. Earlier 0.2.2/0.2.3
launchers auto-update without an upper bound; 0.2.2 uses a JSON file and needs a new
import for the direct OAuth fields. Bundles up to 0.2.1 execute fixed local source.
Keep the same OAuth client ID to retain the token cache; legacy JSON remains supported.

Ordinary compatible server updates come from PyPI at startup, without replacing a
running conversation. The extension's version identifies the starter/settings;
`connection_status.server_version` reports the actual process version. Changes to
extension settings or the starter can require a new MCPB import. The 0.2 interface
boundary covers stdio entry point, snapshot and pagination responses, direct/legacy
OAuth configuration and token paths. A different minor/major line requires review;
prereleases are excluded.

`connection_status` reads only local configuration/token presence: no browser, token
refresh, Google request or filesystem write. An existing token or service account
returns `auth_status: unknown`, because it has not been live-verified. Its
`live_access` is always `not_checked`. `gtm_auth_status` retains its original fields
and behavior, including possible token refresh. To actually check access, call
`gtm_list_accounts` after explicit login. A successful empty list means no accounts
are visible to that identity; a denied request is not successful live access.

Normal startup needs PyPI connectivity. There is no silent offline fallback; see
[the existing-environment fallback](../SUPPORT.md#existing-installation-fallback).
Neither restart nor server update deletes credentials/settings. Real browser consent
and Claude's settings/import UI need a user account and are not automated test claims.

## Manual stdio setup / CLI login

From the checked-out repository:

```sh
uv sync --frozen
export FLIN_GTM_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export FLIN_GTM_CLIENT_SECRET="your-client-secret"
uv run flin-gtm-mcp login
```

For manual Claude configuration, add the following server to the existing
`mcpServers` object in `~/Library/Application Support/Claude/claude_desktop_config.json`.
Replace all paths with your actual absolute paths. Preserve existing servers.

```json
{
  "mcpServers": {
    "flin-gtm-mcp": {
      "command": "/absolute/path/to/uv",
      "args": ["run", "--frozen", "--directory", "/absolute/path/to/flin-gtm-mcp", "flin-gtm-mcp"],
      "env": {
        "FLIN_GTM_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "FLIN_GTM_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

Restart Claude. Use either the extension or manual configuration to avoid duplicate servers.
For existing JSON or service-account setups, omit both inline variables and set
`FLIN_GTM_CREDENTIALS_FILE` to the absolute JSON path instead. When both inline values
are present they take precedence; an incomplete pair is rejected without falling back.
Never paste client secrets or token files into chat.

## Authentication storage and removal

On macOS, OAuth tokens are stored under
`~/Library/Application Support/flin-gtm-mcp/token-<client-hash>.json` with mode `0600` in a `0700` directory. These JSON files also contain OAuth client
details and are not encrypted by this server. Linux uses `~/.config/flin-gtm-mcp/`.
Each OAuth client has a separate cache; logging in again replaces that client's account.
To switch Google accounts, run login again and choose the desired account in Google.
To remove access, revoke the app in your Google account's third-party access settings,
remove the extension in Claude, and delete its token cache. Removing an extension
alone does not revoke Google consent. Do not send credential files or tokens in chat.

Service accounts use the legacy JSON/CLI configuration above and do not open browser consent.
Grant the service-account email only the GTM access it needs.

## Troubleshooting

- **Missing login:** enter both OAuth values and run authentication.
- **Both OAuth values required:** fill in the ID and secret for the same Desktop app client.
- **403:** check Google account/container access, Tag Manager API enablement and quota.
- **429:** wait before retrying; list calls return one page to keep usage bounded.
- **Empty list:** the API returned no visible items for that collection; check the account.
- **More results:** pass `next_page_token` into the next call's `page_token` argument.
- **No live version:** the container may not have been published yet.
