# Support

First ask Claude: “Run `connection_status` for flin Google Tag Manager.” It reports
the running `server_version`, configuration, local authentication state and a next
step. `unknown` means local credentials are not live-verified; `not_checked` is
expected. After explicit login with `gtm_authenticate`, call `gtm_list_accounts`.
A successful list is the live connection test; an empty list means no visible accounts.
Do not share the account list in a public issue.

- Incomplete settings: get the matching Google Desktop OAuth client ID/secret from
  your administrator/password manager. Both are required; no JSON is needed.
- Login expired/revoked: request `gtm_authenticate` and complete Google consent.
- 403: check account access, Tag Manager API enablement and quota with the administrator.
- 429: wait before retrying. Other applications may share the Google project's quota.
- Unsupported bundle: update Claude Desktop to a version supporting MCPB v0.4/uv,
  or use the [manual stdio setup](docs/claude-desktop.md#manual-stdio-setup--cli-login).
- Startup/update failure: check access to PyPI and restart. Keep existing settings
  and tokens; reinstalling or deleting them is not the first recovery step.

## Existing-installation fallback

There is no silent offline fallback. Normal startup checks PyPI; first installation
needs internet. If the existing extension environment and Python are intact, an
administrator can temporarily start the already installed server without resolving
or installing anything:

```sh
uv run --no-config --no-env-file --offline --frozen --no-sync \
  --directory "/absolute/path/to/installed-extension" server.py
```

Use that command in a temporary manual stdio configuration with the **same OAuth
environment/settings**, disabling the duplicate extension while it is in use.
Ask the administrator to locate the installed extension directory. Do not paste
secrets into chat or terminal history. The fallback needs an intact `.venv` and
`uv.lock`; it does not bootstrap a missing installation. Google API calls still
need internet. Restore the normal extension start when PyPI is reachable to resume
updates. A running session keeps its current version during an outage.

For a [support issue](https://github.com/flin-agency/flin-gtm-mcp/issues), include the
extension version, `connection_status` result, macOS/CPU, Claude version and a
redacted error. Exclude credentials, tokens, account IDs and customer data.
