import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_pypi', ROOT / 'scripts/verify_pypi.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_published_bytes_must_match_tested_artifacts(tmp_path, monkeypatch):
    files = ['flin_gtm_mcp-0.2.2-py3-none-any.whl', 'flin_gtm_mcp-0.2.2.tar.gz']
    urls = []
    for name in files:
        (tmp_path / name).write_bytes(b'tested artifact')
        urls.append({'filename': name, 'yanked': False,
                     'digests': {'sha256': hashlib.sha256(b'tested artifact').hexdigest()}})
    monkeypatch.setattr(module.urllib.request, 'urlopen',
                        lambda *a, **kw: io.BytesIO(json.dumps({'urls': urls}).encode()))
    module.verify('0.2.2', tmp_path)
    (tmp_path / files[0]).write_bytes(b'different artifact')
    with pytest.raises(RuntimeError, match='bytes differ'):
        module.verify('0.2.2', tmp_path)


def test_incomplete_pypi_release_never_passes(monkeypatch):
    monkeypatch.setattr(module.urllib.request, 'urlopen',
                        lambda *a, **kw: io.BytesIO(b'{"urls":[]}'))
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    with pytest.raises(RuntimeError, match='not available'):
        module.verify('0.2.2')


@pytest.mark.parametrize('version', ['0.2.2rc1', '../other', '0.2.2?query=1'])
def test_invalid_release_version_rejected_before_network(version, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail('Invalid version reached network')
    monkeypatch.setattr(module.urllib.request, 'urlopen', no_network)
    with pytest.raises(ValueError):
        module.verify(version)
