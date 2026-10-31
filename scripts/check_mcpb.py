"""Test the archived bundle in an isolated folder using its actual uv command."""

import asyncio
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def check():
    version = json.loads((ROOT / "manifest.json").read_text())["version"]
    bundle = ROOT / "dist" / f"flin-gtm-mcp-{version}-macos.mcpb"
    with tempfile.TemporaryDirectory(prefix="flin-gtm-bundle-") as directory:
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            assert not any(name.startswith((".git/", ".venv/")) for name in names)
            assert all(
                not Path(name).is_absolute() and ".." not in Path(name).parts for name in names
            )
            archive.extractall(directory)
        manifest = json.loads((Path(directory) / "manifest.json").read_text())
        config = manifest["server"]["mcp_config"]
        params = StdioServerParameters(
            command=shutil.which("uv"),
            args=[arg.replace("${__dirname}", directory) for arg in config["args"]],
            env={"FLIN_GTM_CREDENTIALS_FILE": "", "UV_PYTHON_DOWNLOADS": "automatic"},
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            assert len((await session.list_tools()).tools) == 20
            result = await session.call_tool("gtm_auth_status", {})
            assert not result.isError
    print("Archived MCPB: isolated uv launch, handshake and 20 tools verified.")


if __name__ == "__main__":
    asyncio.run(check())
