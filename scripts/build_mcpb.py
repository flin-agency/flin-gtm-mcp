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
    assert version == manifest["version"], "Manifest/package versions differ"
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
        )
    ]
    files += sorted((ROOT / "src/flin_gtm_mcp").glob("*.py"))
    output = ROOT / "dist" / f"flin-gtm-mcp-{version}-macos.mcpb"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.relative_to(ROOT))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".mcpb.sha256").write_text(f"{digest}  {output.name}\n")
    print(output)


if __name__ == "__main__":
    build()
