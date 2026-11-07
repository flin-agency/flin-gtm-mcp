"""Publish every new main-branch version; leave completed releases immutable."""

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

from verify_pypi import verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Only stable numeric releases are supported')
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    source = (ROOT / 'src/flin_gtm_mcp/__init__.py').read_text()
    if manifest['version'] != version or f'__version__ = "{version}"' not in source:
        raise ValueError('Package, manifest and source versions must match')
    result = subprocess.run(
        ['gh', 'api', f"repos/{os.environ['GH_REPO']}/releases/tags/v{version}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode and 'HTTP 404' not in result.stderr:
        raise RuntimeError('Cannot determine GitHub release status')
    publish = True
    if not result.returncode:
        release = json.loads(result.stdout)
        if release['draft']:
            raise RuntimeError('An existing draft must be resolved before automated publication')
        required = {'flin-gtm-mcp.mcpb', 'flin-gtm-mcp.mcpb.sha256',
                    f'flin-gtm-mcp-{version}-macos.mcpb',
                    f'flin-gtm-mcp-{version}-macos.mcpb.sha256',
                    f'flin_gtm_mcp-{version}-py3-none-any.whl',
                    f'flin_gtm_mcp-{version}.tar.gz'}
        if not required <= {asset['name'] for asset in release['assets']}:
            raise RuntimeError('Existing release is incomplete; do not overwrite it silently')
        verify(version)
        publish = False
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'version={version}\npublish={str(publish).lower()}\n')
    print(f'Version {version}: ' + ('publish both channels' if publish else 'already published'))


if __name__ == '__main__':
    main()
