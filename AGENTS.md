# Release contract

- Every shipped change to server behavior, runtime dependencies or the Claude launcher
  must bump the version in `pyproject.toml`, `manifest.json` and
  `src/flin_gtm_mcp/__init__.py`, and refresh `uv.lock`.
- Every version must be published to BOTH PyPI and GitHub, including a fresh macOS
  `.mcpb`, stable `flin-gtm-mcp.mcpb` alias and SHA-256 files. The single `release.yml`
  workflow runs automatically on main; it checks macOS/Linux, publishes PyPI, checks the installed PyPI package and
  then publishes the matching GitHub release. Keep the PyPI Trusted Publisher tied
  to `release.yml` / environment `pypi`.
- Do not restore a standalone GitHub-only release flow or ship a fixed-source Claude
  bundle. The installed launcher must continue fetching the latest compatible stable
  PyPI server (currently 0.2.x, below 0.3.0) on each start without a manual MCPB replacement. Preserve credentials and read-only
  boundaries. Prereleases must not auto-install.
- Test an unchanged installed launcher against successive package versions with the
  real uv runtime. Verify the public PyPI package after publication, not only local source.
- Existing releases are immutable. Retry a failed release through the workflow on
  main; investigate any published-file hash mismatch instead of overwriting artifacts.
- Explain the distinction between server updates on restart and changes to the desktop
  extension manifest/settings, which may require a new bundle installation.
- Claude settings expose `client_id` and `client_secret` directly; keep the secret
  marked sensitive. Preserve legacy JSON configuration for existing installations.
- Preserve the side-effect-free `connection_status` contract. Local token presence is
  `unknown`, never proof of live access. Keep `gtm_auth_status` backward compatible.
