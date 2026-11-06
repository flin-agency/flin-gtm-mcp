"""Verify release visibility and SHA-256 without installing unpublished source."""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


def verify(version, directory=None):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Expected a stable numeric release version')
    expected = {f'flin_gtm_mcp-{version}-py3-none-any.whl', f'flin_gtm_mcp-{version}.tar.gz'}
    for attempt in range(12):
        try:
            with urllib.request.urlopen(
                f'https://pypi.org/pypi/flin-gtm-mcp/{version}/json', timeout=15,
            ) as response:
                data = json.load(response)
            files = {item['filename']: item for item in data['urls'] if not item['yanked']}
            if expected <= files.keys():
                break
        except (urllib.error.URLError, TimeoutError):
            pass
        if attempt == 11:
            raise RuntimeError('PyPI release is not available with both expected distributions')
        time.sleep(5)
    if directory:
        for name in expected:
            digest = hashlib.sha256((Path(directory) / name).read_bytes()).hexdigest()
            if digest != files[name]['digests']['sha256']:
                raise RuntimeError(f'PyPI bytes differ from tested artifact: {name}')
    print(f'PyPI {version}: both distributions verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version')
    parser.add_argument('--dist')
    args = parser.parse_args()
    verify(args.version, args.dist)
