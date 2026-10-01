"""Reference tooling safety, without running full reference experiments."""

import ast
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from yield_curves.tooling.reference_candidates import (
    FROZEN_REFERENCES, validate_candidate_path, write_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = (
    'scripts/tests/capture_baseline_reference.py',
    'scripts/experiments/synthetic/generate_synthetic_reference_data.py',
)


def load_script(relative):
    spec = importlib.util.spec_from_file_location('reference_tool', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('relative', SCRIPTS)
@pytest.mark.parametrize('destination', [None, *FROZEN_REFERENCES, 'existing'])
def test_cli_rejects_unsafe_destination_before_financial_work(monkeypatch, tmp_path, relative, destination):
    module = load_script(relative)
    def forbidden(**kwargs):
        pytest.fail('Financial work started before output validation')
    monkeypatch.setattr(module, 'build_projected_mxmc_calendar', forbidden)
    existing = tmp_path / 'existing'
    existing.write_bytes(b'keep')
    args = ['tool']
    if destination is not None:
        target = existing if destination == 'existing' else ROOT / destination
        args += ['--output', str(target)]
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
    assert existing.read_bytes() == b'keep'


@pytest.mark.parametrize('name', FROZEN_REFERENCES)
def test_frozen_path_rejected_even_when_missing_and_through_alias(tmp_path, name):
    canonical = tmp_path / name
    with pytest.raises(ValueError, match='Frozen'):
        validate_candidate_path(canonical, root=tmp_path)
    alias = tmp_path / 'alias'
    alias.symlink_to(canonical)
    with pytest.raises(ValueError, match='Frozen'):
        write_candidate(alias, b'overwrite', root=tmp_path)
    assert not canonical.exists()


def test_exclusive_creation_handles_race(monkeypatch, tmp_path):
    target = tmp_path / 'candidate'
    original_open = Path.open
    def raced_open(path, mode='r', *args, **kwargs):
        if path == target and mode == 'xb':
            with original_open(path, 'wb') as output:
                output.write(b'other writer')
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', raced_open)
    with pytest.raises(FileExistsError):
        write_candidate(target, b'candidate', root=tmp_path)
    assert target.read_bytes() == b'other writer'


def test_candidate_writes_once(tmp_path):
    target = tmp_path / 'new' / 'candidate'
    write_candidate(target, b'candidate', root=tmp_path)
    with pytest.raises(ValueError, match='exists'):
        write_candidate(target, b'replacement', root=tmp_path)
    assert target.read_bytes() == b'candidate'


def test_capture_deterministic_public_api_and_v1_shape(monkeypatch):
    module = load_script(SCRIPTS[0])
    actual = module.build_baseline_ftiie_curve
    calls = []
    # Exercise real public results/binding/serialization on two short quotes;
    # the full 15-quote reference capture is deliberately not run here.
    reader = module.read_synthetic_ois_quotes_csv
    monkeypatch.setattr(module, 'read_synthetic_ois_quotes_csv', lambda path: reader(path)[:2])
    def build(**kwargs):
        calls.append(kwargs)
        return actual(**kwargs)
    monkeypatch.setattr(module, 'build_baseline_ftiie_curve', build)
    first = module.capture_reference(ROOT)
    assert module.capture_reference(ROOT) == first
    assert len(calls) == 2
    assert all(set(call) == {'quotes', 'calendar'} for call in calls)
    payload = json.loads(first)
    frozen = json.loads((ROOT / FROZEN_REFERENCES[0]).read_text())
    assert payload.keys() == frozen.keys()
    assert payload['acceptance'].keys() == frozen['acceptance'].keys()
    assert len(payload['nodes']) == len(payload['interior_observations']) == 2
    assert payload['acceptance']['accepted_for_use']
    assert payload['nodes'][0].keys() == frozen['nodes'][0].keys()
    assert payload['acceptance']['checks'][0].keys() == frozen['acceptance']['checks'][0].keys()
    tree = ast.parse((ROOT / SCRIPTS[0]).read_text())
    assert not any(isinstance(n, ast.ImportFrom) and n.module in {
        'yield_curves.calibration', 'yield_curves.bootstrap'
    } for n in ast.walk(tree))


def test_rejected_capture_has_no_candidate(monkeypatch, tmp_path):
    module = load_script(SCRIPTS[0])
    monkeypatch.setattr(module, 'build_baseline_ftiie_curve', lambda **kw: SimpleNamespace(
        accepted_for_use=False, acceptance=SimpleNamespace(issues=('rejected',))))
    target = tmp_path / 'candidate.json'
    monkeypatch.setattr(sys, 'argv', ['tool', '--output', str(target)])
    with pytest.raises(RuntimeError, match='rejected'):
        module.main()
    assert not target.exists()


def test_synthetic_candidate_uses_existing_serializer_without_generation(monkeypatch, tmp_path):
    module = load_script(SCRIPTS[1])
    from yield_curves.research.synthetic import read_synthetic_ois_quotes_csv
    quotes = read_synthetic_ois_quotes_csv(ROOT / FROZEN_REFERENCES[1])
    monkeypatch.setattr(module, 'generate_synthetic_ois_quotes', lambda **kwargs: quotes)
    target = tmp_path / 'candidate.csv'
    monkeypatch.setattr(sys, 'argv', ['tool', '--output', str(target)])
    module.main()
    assert target.read_bytes() == (ROOT / FROZEN_REFERENCES[1]).read_bytes()
