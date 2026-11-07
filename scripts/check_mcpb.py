"""Test the archived bundle in an isolated folder using its actual uv command."""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def check(wheel_dir=None, expected_version=None):
    version = json.loads((ROOT / "manifest.json").read_text())["version"]
    bundle = ROOT / "dist" / f"flin-gtm-mcp-{version}-macos.mcpb"
    expected = bundle.with_suffix(".mcpb.sha256").read_text().split()[0]
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == expected
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
        args = [arg.replace("${__dirname}", directory) for arg in config["args"]]
        if wheel_dir:
            # Exercise the exact release wheel before it is available on PyPI.
            args[-1:-1] = ["--find-links", str(Path(wheel_dir).resolve())]
        values = {"client_id": "bundle-test.apps.googleusercontent.com",
                  "client_secret": "synthetic-bundle-test-secret"}
        env = {key: value.replace("${user_config.client_id}", values["client_id"])
               .replace("${user_config.client_secret}", values["client_secret"])
               for key, value in config["env"].items()}
        home = Path(directory) / "test-home"
        home.mkdir()
        env.update(HOME=str(home), FLIN_GTM_CREDENTIALS_FILE="", UV_PYTHON_DOWNLOADS="automatic",
                   UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", str(Path(directory) / "uv-cache")))
        params = StdioServerParameters(
            command=shutil.which("uv"),
            args=args,
            env=env,
            cwd=directory,
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            assert len((await session.list_tools()).tools) == 35
            local = await session.call_tool("connection_status", {})
            state = local.structuredContent or json.loads(local.content[0].text)
            assert not local.isError
            assert state["server_version"] == (expected_version or version)
            assert state["configuration_status"] == "configured"
            assert state["auth_status"] == "unauthenticated"
            assert state["live_access"] == "not_checked"
            assert not list(home.rglob("token-*.json"))
            assert values["client_secret"] not in json.dumps(state)
            result = await session.call_tool("gtm_auth_status", {})
            assert not result.isError
            status = result.structuredContent or json.loads(result.content[0].text)
            assert status["server_version"] == (expected_version or version)
            assert not status["authenticated"] and "login missing" in status["message"]
            assert values["client_secret"] not in json.dumps(status)
    print("Archived MCPB: isolated uv launch, handshake and 35 tools verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir")
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    asyncio.run(check(args.wheel_dir, args.expected_version))
