#!/usr/bin/env python3
"""Exercise manifest rejection of changed bytes; no Cargo, source or GUI changes."""
import importlib.util
import json
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('experiment', Path(__file__).with_name('experiment.py'))
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)
experiment.WORK.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='packaging-check-', dir=experiment.WORK) as scratch:
    bundle = Path(scratch)
    for name in experiment.FIRST_SCREEN + ['works/m1-sequence.nvwa.json']:
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('fixture:' + name).encode())
        experiment.gzip_file(path)
    experiment.manifest(bundle)
    raw = bundle / experiment.FIRST_SCREEN[0]
    sidecar = raw.with_name(raw.name + '.gz')
    original_gzip = sidecar.read_bytes()
    experiment.gzip_file(raw)
    assert sidecar.read_bytes() == original_gzip, 'gzip output is not deterministic'
    raw.write_bytes(b'changed-after-gzip')
    try:
        experiment.manifest(bundle)
    except SystemExit as failure:
        rejected = str(failure)
    else:
        raise AssertionError('Manifest accepted changed raw bytes with stale gzip')
    raw.write_bytes(('fixture:' + experiment.FIRST_SCREEN[0]).encode())
    experiment.manifest(bundle)
baseline = experiment.manifest(experiment.BASELINE / 'web')
report = {
    'gzip_identity_green': True,
    'deterministic_gzip_repeated': True,
    'identity_mutation_rejected': rejected,
    'restore_green': True,
    'baseline_first_screen_encoded_bytes': baseline['first_screen_encoded_bytes'],
    'baseline_player_encoded_bytes': baseline['player_encoded_bytes'],
    'note': 'stdlib packaging checks only; no Cargo or GUI; owned fixture removed',
}
experiment.save('stdlib-checks.json', report)
print(json.dumps(report, indent=2))
