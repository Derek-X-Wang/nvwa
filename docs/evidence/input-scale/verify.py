"""Offline checks of published observations; this never drives or simulates UI."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OBSERVED = HERE / 'observed'


def read(path):
    return json.loads(path.read_text())


def require(value, message):
    if not value:
        raise AssertionError(message)


def load_checker(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify():
    manifest = read(OBSERVED / 'MANIFEST.json')
    names = [entry['file'] for entry in manifest['entries']]
    require(len(names) == len(set(names)), 'duplicate manifest entry')
    require(set(names) == {p.name for p in OBSERVED.iterdir() if p.name != 'MANIFEST.json'},
            'manifest must inventory every observed artifact')
    for entry in manifest['entries']:
        data = (OBSERVED / entry['file']).read_bytes()
        require(len(data) == entry['bytes'], 'artifact size mismatch: ' + entry['file'])
        require(hashlib.sha256(data).hexdigest() == entry['sha256'],
                'artifact hash mismatch: ' + entry['file'])
    package = read(HERE / 'observer-package.json')
    for name, sha in package['observer_files'].items():
        require(hashlib.sha256((HERE / 'reproduce' / name).read_bytes()).hexdigest() == sha,
                'executed observer hash mismatch: ' + name)
    source_manifest = read(ROOT / 'docs/evidence/m1-1-ui/build/build-inputs-final-before.json')
    for name, entry in source_manifest['files'].items():
        data = (ROOT / name).read_bytes()
        require(len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'],
                'production source changed from tested cohort: ' + name)
    geometry = load_checker('scale_boundary', 'experiments/20-scale-boundary/check.py')
    recovery = load_checker('input_recovery', 'experiments/19-input-focus-recovery/check.py')
    inventories = {}
    for case in ('chrome-tab-return', 'chrome-zoom125', 'chrome-reset100', 'chrome-human'):
        combined = read(OBSERVED / (case + '-observed.json'))
        require(combined['sourceHead'] == manifest['base_main'], 'wrong runtime source head')
        for section in ('scale', 'recovery'):
            require(combined[section] == read(OBSERVED / (case + '-' + section + '.json')),
                    'split capture mismatch: ' + case + '/' + section)
        trace = combined['recovery']
        sequences = [row['sequence'] for row in trace['rows']]
        require(trace['dropped'] == 0 and sequences == list(range(1, len(sequences) + 1)),
                'recovery capture has overflow or gaps: ' + case)
        inventories[case] = geometry.inventory(combined['scale'])
        require(inventories[case]['strictly_increasing'] and not inventories[case]['gaps']
                and not inventories[case]['duplicate_indices'], 'scale capture gaps: ' + case)
    intervals = []
    for case, pointer, row, dpr, css in (
            ('chrome-tab-return', 70, 127, 2, [1512, 806]),
            ('chrome-zoom125', 296, 361, 2.5, [1209.6, 644.8]),
            ('chrome-reset100', 496, 560, 2, [1512, 806])):
        result = geometry.check_geometry(read(OBSERVED / (case + '-scale.json')),
            SimpleNamespace(pointer=pointer, row=row, expected_dpr=dpr,
                            expected_css=css, work_rect=[257, 1, 222, 22]))
        intervals.append({'case': case, 'pointer': pointer, 'row': row,
                          'dpr': result['dpr'], 'age_ms': result['age_ms']})
    focus = recovery.check(read(OBSERVED / 'chrome-tab-return-recovery.json'),
                           read(HERE / 'tab-return-observation.json'))
    require(focus['status'] == 'PASS', 'actual tab-return evidence rejected')
    base = read(ROOT / 'examples/m1-sequence.nvwa.json')
    require(base == read(OBSERVED / 'chrome-focus-after.nvwa.json'),
            'tab return altered complete Work')
    edited = read(OBSERVED / 'chrome-zoom125-drag.nvwa.json')
    undo = read(OBSERVED / 'chrome-zoom125-undo.nvwa.json')
    command = geometry.check_work(base, edited, undo, 'jaw_width', .05)
    reset = read(OBSERVED / 'chrome-reset100.nvwa.json')
    require(reset == undo, 'zoom reset/input altered complete Work')
    human = read(OBSERVED / 'chrome-human-after.nvwa.json')
    require(geometry.without_revision(human) == geometry.without_revision(reset)
            and human['revision'] == 7 and reset['revision'] == 3,
            'human handback content/revision differs from reported aggregate')
    human_trace = read(OBSERVED / 'chrome-human-recovery.json')
    untrusted = [row for row in human_trace['rows'] if row.get('trusted') is False
                 and row['type'] in ('input', 'compositionstart', 'compositionend')]
    require([(row['sequence'], row['type']) for row in untrusted] == [(710, 'compositionend')],
            'untrusted event inventory differs; review provenance before claiming acceptance')
    # Preserve the conservative checker result. Human acceptance is separately attributed.
    human_check = recovery.check(human_trace)
    require(human_check['status'] == 'PARTIAL', 'human trace must not become an automatic PASS')
    require(inventories['chrome-human']['prefix_truncated'],
            'human scale trace is a retained tail, not whole-session proof')
    return {'status': 'PASS', 'scope': 'offline packet consistency and bounded checks only',
            'artifact_count': len(names), 'unchanged_production_inputs': len(source_manifest['files']),
            'click_intervals': intervals, 'tool_command': command, 'inventories': inventories,
            'human_handback': {'revisions': [3, 7], 'whole_content_restored': True,
                              'gesture_count_inferred': False, 'trace_verdict': 'PARTIAL',
                              'untrusted_compositionend_origin': 'UNKNOWN'},
            'not_run': ['original IAB DPR-emulation failure', 'physical display migration',
                        'fresh native Studio run', 'browser UI replay by this script']}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
