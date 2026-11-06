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
    for name in ('manifest.json', 'pyproject.toml', 'uv.lock', 'server.py', 'README.md'):
        shutil.copyfile(ROOT / name, tmp_path / name)
    poison = tmp_path / 'src/flin_gtm_mcp/local_credentials.py'
    poison.write_text('SECRET_MUST_NOT_SHIP')
    (tmp_path / '.env').write_text('SECRET_MUST_NOT_SHIP')
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    builder.build()
    bundle = next((tmp_path / 'dist').glob('*.mcpb'))
    first = bundle.read_bytes()
    builder.build()
    assert bundle.read_bytes() == first
    with zipfile.ZipFile(bundle) as archive:
        assert all(b'SECRET_MUST_NOT_SHIP' not in archive.read(n) for n in archive.namelist())
        assert len(archive.namelist()) == 8
        assert "uv.lock" not in archive.namelist()
        assert not any(name.startswith("src/") for name in archive.namelist())
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
