"""Prove one installed launcher moves between stable releases without a new MCPB."""

import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import zipfile
from base64 import urlsafe_b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build_mcpb.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fake_wheel(directory, version):
    info = f'flin_gtm_mcp-{version}.dist-info'
    files = {
        'flin_gtm_mcp/__init__.py': f'__version__ = "{version}"\n'.encode(),
        'flin_gtm_mcp/__main__.py': f'def main():\n    print("{version}")\n'.encode(),
        f'{info}/METADATA': (
            f'Metadata-Version: 2.3\nName: flin-gtm-mcp\nVersion: {version}\n'
            'Requires-Python: >=3.11\n'
        ).encode(),
        f'{info}/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
    }
    records = io.StringIO()
    writer = csv.writer(records)
    for name, content in files.items():
        digest = urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
        writer.writerow([name, f'sha256={digest}', len(content)])
    writer.writerow([f'{info}/RECORD', '', ''])
    files[f'{info}/RECORD'] = records.getvalue().encode()
    with zipfile.ZipFile(directory / f'flin_gtm_mcp-{version}-py3-none-any.whl', 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_same_installed_bundle_loads_new_stable_version(tmp_path, monkeypatch):
    project = tmp_path / 'source'
    project.mkdir()
    shutil.copytree(ROOT / 'docs', project / 'docs')
    for name in ('manifest.json', 'pyproject.toml', 'server.py', 'README.md'):
        shutil.copyfile(ROOT / name, project / name)
    monkeypatch.setattr(builder, 'ROOT', project.resolve())
    builder.build()
    installed = tmp_path / 'installed'
    with zipfile.ZipFile(next((project / 'dist').glob('*.mcpb'))) as archive:
        archive.extractall(installed)
    manifest = json.loads((installed / 'manifest.json').read_text())
    version = manifest['version']
    major, minor, patch = map(int, version.split('.'))
    newer = f'{major}.{minor}.{patch + 1}'
    prerelease = f'{major}.{minor}.{patch + 2}rc1'
    wheels = tmp_path / 'wheels'
    wheels.mkdir()
    fake_wheel(wheels, version)
    args = [arg.replace('${__dirname}', str(installed))
            for arg in manifest['server']['mcp_config']['args']]
    args[-1:-1] = ['--no-index', '--find-links', str(wheels)]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('UV_', 'PYTHON'))}
    env.update(UV_CACHE_DIR=str(tmp_path / 'uv-cache'), UV_PYTHON_DOWNLOADS='never')

    def launch():
        return subprocess.run([shutil.which('uv'), *args], env=env, text=True,
                              capture_output=True, check=True, timeout=45).stdout.strip()

    assert launch() == version
    assert (installed / 'uv.lock').exists()
    fake_wheel(wheels, newer)
    fake_wheel(wheels, prerelease)
    assert launch() == newer  # The old generated lock must not pin the first release.
    assert launch() == newer  # Pre-releases must never be selected.
    assert json.loads((installed / 'manifest.json').read_text()) == manifest
