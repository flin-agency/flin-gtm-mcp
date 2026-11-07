import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build_mcpb.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_bundle_is_reproducible_and_excludes_unlisted_files(tmp_path, monkeypatch):
    for name in ('src', 'docs'):
        shutil.copytree(ROOT / name, tmp_path / name)
    for name in ('manifest.json', 'pyproject.toml', 'uv.lock', 'server.py', 'README.md',
                 'PRIVACY.md', 'SECURITY.md', 'SUPPORT.md'):
        shutil.copyfile(ROOT / name, tmp_path / name)
    poison = tmp_path / 'src/flin_gtm_mcp/local_credentials.py'
    poison.write_text('SECRET_MUST_NOT_SHIP')
    (tmp_path / '.env').write_text('SECRET_MUST_NOT_SHIP')
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    builder.build()
    bundle = tmp_path / 'dist/flin-gtm-mcp.mcpb'
    first = bundle.read_bytes()
    versioned = next((tmp_path / 'dist').glob('*-macos.mcpb'))
    assert versioned.read_bytes() == first
    assert bundle.with_suffix('.mcpb.sha256').read_text().split()[0] == (
        versioned.with_suffix('.mcpb.sha256').read_text().split()[0]
    )
    builder.build()
    assert bundle.read_bytes() == first
    with zipfile.ZipFile(bundle) as archive:
        assert all(b'SECRET_MUST_NOT_SHIP' not in archive.read(n) for n in archive.namelist())
        assert len(archive.namelist()) == 11
        assert "uv.lock" not in archive.namelist()
        assert not any(name.startswith("src/") for name in archive.namelist())
        assert b'<0.3.0' in archive.read('pyproject.toml')
        assert b'flin-gtm-desktop-launcher' in archive.read('pyproject.toml')
        assert json.loads(archive.read('manifest.json')) == json.loads(
            (tmp_path / 'manifest.json').read_text()
        )
        config = json.loads(archive.read('manifest.json'))
        assert set(config['user_config']) == {'client_id', 'client_secret'}
        assert config['user_config']['client_secret']['sensitive'] is True
        assert all(field['required'] for field in config['user_config'].values())
    source = tmp_path / 'server.py'
    source.unlink()
    source.symlink_to(poison)
    with pytest.raises(ValueError, match='symlinks'):
        builder.build()
