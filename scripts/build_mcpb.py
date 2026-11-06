"""Build an allowlisted MCPB archive: never include local credentials or caches."""

import hashlib
import json
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    version = metadata["project"]["version"]
    if version != manifest["version"]:
        raise ValueError("Manifest/package versions differ")
    files = [
        ROOT / name
        for name in (
            "manifest.json",
            "pyproject.toml",
            "uv.lock",
            "server.py",
            "README.md",
            "docs/claude-desktop.md",
            "docs/read-only-contract.md",
            "docs/release-notes.md",
            "docs/security-review.md",
        )
    ]
    files += [ROOT / "src/flin_gtm_mcp" / name for name in (
        "__init__.py", "__main__.py", "auth.py", "client.py", "server.py",
        "snapshots.py", "analysis.py",
    )]
    for file in files:
        if not file.is_file() or any(p.is_symlink() for p in (file, *file.parents)):
            raise ValueError("Bundle inputs must be regular files, without symlinks")
    output = ROOT / "dist" / f"flin-gtm-mcp-{version}-macos.mcpb"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(files):
            info = zipfile.ZipInfo(file.relative_to(ROOT).as_posix(), (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, file.read_bytes())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".mcpb.sha256").write_text(f"{digest}  {output.name}\n")
    print(output)


if __name__ == "__main__":
    build()
