Initial read-only Google Tag Manager MCP release.

- 20 MCP tools for Google authentication and reading GTM configuration.
- Claude Desktop macOS extension (`.mcpb`, MCPB v0.4 / uv runtime).
- Python wheel and source distribution for the maintainer's PyPI upload.
- GET-only allowlist, read-only Google scope, pagination and sanitized errors.

Install: download and open the macOS `.mcpb` in a current Claude Desktop with uv extension support. Select your Google Desktop OAuth client JSON, then ask Claude to authenticate. Python and dependencies are installed on first use; network access is required.

The extension is unsigned. Protocol, unit and packaging checks are automated. Live Google OAuth/API access and installation through Claude's UI have not been verified with user credentials. PyPI publication is handled separately by the maintainer.
