"""Build an allowlisted MCPB archive: never include local credentials or caches."""

import hashlib
import json
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 0.2 snapshot/pagination responses, stdio entry point, OAuth settings and token layout.
# Reassess these interfaces before allowing a new minor line in this launcher.
SERVER_UPPER_BOUND = "0.3.0"


def build():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    version = metadata["project"]["version"]
    if version != manifest["version"]:
        raise ValueError("Manifest/package versions differ")
    if not version.startswith("0.2."):
        raise ValueError("Review launcher compatibility before changing the server minor version")
    files = [
        ROOT / name
        for name in (
            "manifest.json",
            "server.py",
            "README.md",
            "PRIVACY.md",
            "SECURITY.md",
            "SUPPORT.md",
            "docs/claude-desktop.md",
            "docs/read-only-contract.md",
            "docs/release-notes.md",
            "docs/security-review.md",
        )
    ]
    for file in files:
        if not file.is_file() or any(p.is_symlink() for p in (file, *file.parents)):
            raise ValueError("Bundle inputs must be regular files, without symlinks")
    output = ROOT / "dist" / f"flin-gtm-mcp-{version}-macos.mcpb"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        contents = {file.relative_to(ROOT).as_posix(): file.read_bytes() for file in files}
        # A separate launcher project: never install the bundled application source.
        contents["pyproject.toml"] = (
            '[project]\nname = "flin-gtm-desktop-launcher"\n'
            f'version = "{version}"\nrequires-python = ">=3.11"\n'
            f'dependencies = ["flin-gtm-mcp>={version},<{SERVER_UPPER_BOUND}"]\n'
        ).encode()
        for name, content in sorted(contents.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".mcpb.sha256").write_text(f"{digest}  {output.name}\n")
    alias = output.parent / "flin-gtm-mcp.mcpb"
    alias.write_bytes(output.read_bytes())
    alias.with_suffix(".mcpb.sha256").write_text(f"{digest}  {alias.name}\n")
    print(output)


if __name__ == "__main__":
    build()
