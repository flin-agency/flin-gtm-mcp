# Claude Desktop on macOS

## Google setup (once)

1. In Google Cloud, create/select a project and enable **Tag Manager API**.
2. Configure Google Auth Platform / OAuth consent. For an external app in Testing,
   add your Google account as a test user. Follow Google's current verification
   requirements if distributing your OAuth app beyond permitted test users.
3. Create an OAuth client of type **Desktop app** and download its JSON file.
4. Keep the file outside this repository. Choose it in the Claude extension settings.
5. Use `gtm_authenticate` in Claude to open browser consent. The login waits up to
   120 seconds. If Claude times out first, use the CLI login below and retry.

The Google account must have access to the GTM containers. The server requests
only the read-only scope. No Google Cloud project, OAuth client or credentials are
created automatically. Google OAuth apps in Testing may require frequent re-login.

## Install the MCPB

Download [flin-gtm-mcp-0.2.1-macos.mcpb](https://github.com/flin-agency/flin-gtm-mcp/releases/download/v0.2.1/flin-gtm-mcp-0.2.1-macos.mcpb).
In Claude Desktop, open **Settings → Desktop app → Extensions → Manage →
Advanced settings → Install Extension…** (older layout: **Settings → Extensions**).
Select the downloaded file. Approve installation and
select the credentials JSON. Claude manages the Python runtime with uv and installs
locked dependencies on first start. An internet connection is required.

Requires a Claude Desktop version with MCPB v0.4 / uv support; if the bundle is
rejected as unsupported, update Claude or use the manual stdio setup below.

Try: “Melde mich beim flin Google Tag Manager an und liste meine Accounts.”
Then: “Zeige Tags und Trigger im Workspace …; ändere nichts.”

## Manual stdio setup / CLI login

From the checked-out repository:

```sh
uv sync --frozen
FLIN_GTM_CREDENTIALS_FILE="/absolute/path/google-oauth.json" uv run flin-gtm-mcp login
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
        "FLIN_GTM_CREDENTIALS_FILE": "/absolute/path/google-oauth.json"
      }
    }
  }
}
```

Restart Claude. Use either the extension or manual configuration to avoid duplicate servers.

## Authentication storage and removal

On macOS, OAuth tokens are stored under
`~/Library/Application Support/flin-gtm-mcp/token-<client-hash>.json` with mode `0600`.
Each OAuth client has a separate cache; logging in again replaces that client's account.
To switch Google accounts, run login again and choose the desired account in Google.
To remove access, revoke the app in your Google account's third-party access settings,
remove the extension in Claude, and delete its token cache. Removing an extension
alone does not revoke Google consent. Do not send credential files or tokens in chat.

Service accounts use the selected JSON directly and do not open browser consent.
Grant the service-account email only the GTM access it needs.

## Troubleshooting

- **Missing login:** choose the credentials file and run authentication.
- **403:** check Google account/container access, Tag Manager API enablement and quota.
- **429:** wait before retrying; list calls return one page to keep usage bounded.
- **Empty list:** the API returned no visible items for that collection; check the account.
- **More results:** pass `next_page_token` into the next call's `page_token` argument.
- **No live version:** the container may not have been published yet.
