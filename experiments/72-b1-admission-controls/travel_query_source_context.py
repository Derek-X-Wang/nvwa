"""Authenticate the exact travel-query successor to the V15 source context."""
import hashlib
import json
from pathlib import Path
from types import ModuleType

EXP = Path(__file__).resolve().parent
NAME = 'input-context-travel-query-v1.json'
SHA = '7d495a298a06c08f8ae4f7827f9167a7fa221f6d8829a297378284e14483c09f'
ID = 'nvwa-travel-query-source-context-v1'
PREDECESSOR = '693902b8f06156401706691a40c2804c6029f535'
PREDECESSOR_ID = 'nvwa-v15-experimental-source-context-v1'
V15_HELPER_SHA = '413d6b909bf7f5df64f679a8041ab712f54d73234f4f79b375f315c2a0317e75'
FIXTURES = 'pre-travel-query'
EXP72 = 'experiments/72-b1-admission-controls'
EXP73 = 'experiments/73-high-poly-eyes'
MARKERS = {
    'crates/nvwa-cli/src/main.rs': b'TRAVEL_QUERY_USAGE',
    'crates/nvwa-cli/src/motion_query.rs': b'fn run_travel(',
}
TRAVEL_TEST = 'crates/nvwa-cli/tests/travel_query.rs'
RETAINED = {f'{FIXTURES}/{name}': name for name in MARKERS}
PREDECESSOR_REPLAY_CONTROLS = {
    f'{EXP72}/test_waist_context.py': {
        'bytes': 16262,
        'sha256': '1f052a71248cfff801beaa599c3c1e643ffe8604f5724e67406b577a7385d84d',
    },
}
CHANGED = set(MARKERS) | {
    f'{EXP72}/run.py',
    f'{EXP73}/build.py',
    f'{EXP73}/frozen_context.py',
    'scripts/check-v15-history.py',
    'scripts/check-v15-live73.py',
} | PREDECESSOR_REPLAY_CONTROLS.keys()
RETAINED_PATHS = {f'{EXP72}/{name}' for name in RETAINED}
TEST_MODULE = f'{EXP72}/test_travel_query_context.py'
ADDED = {TRAVEL_TEST, TEST_MODULE} | RETAINED_PATHS
CONTROL_FILES = {TEST_MODULE, f'{EXP72}/{NAME}', f'{EXP72}/travel_query_source_context.py'}


def present(root, control_exp, v15_present):
    if any((root / name).exists() or (root / name).is_symlink() for name in {TRAVEL_TEST} | RETAINED_PATHS):
        return True
    # Historical controls may explicitly supply a disposable control directory
    # inside the test tree. A live checkout or any V15 tree must authenticate
    # the successor files that are actually inside the requested source root.
    separate_controls = control_exp != EXP and root / EXP72 == control_exp
    if v15_present or not separate_controls:
        if any((root / name).exists() or (root / name).is_symlink() for name in CONTROL_FILES):
            return True
    # If the added test is missing, either implementation file still selects
    # this gate. The full map check rejects incomplete and modified sources.
    for name, marker in MARKERS.items():
        path = root / name
        if not path.is_symlink() and path.is_file() and marker in path.read_bytes():
            return True
    return False


def need(ok, detail):
    if not ok:
        raise ValueError('travel-query exact source: ' + detail)


def predecessor_gate():
    path = EXP / 'v15_source_context.py'
    need(not path.is_symlink() and path.is_file(), 'missing/nonregular V15 predecessor helper')
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == V15_HELPER_SHA, 'V15 predecessor helper identity')
    module = ModuleType('nvwa_v15_travel_predecessor')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def records(v15):
    raw = v15.file(EXP, NAME).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == SHA, 'manifest identity')
    value = json.loads(raw)
    need(set(value) == {'format', 'predecessor_context', 'predecessor_commit', 'before', 'after'}
         and value['format'] == ID and value['predecessor_context'] == PREDECESSOR_ID == v15.ID
         and value['predecessor_commit'] == PREDECESSOR
         and set(value['before']) == set(value['after']) == CHANGED | ADDED
         and {name for name, pin in value['before'].items() if pin is None} == ADDED
         and all(pin != value['after'][name] for name, pin in value['before'].items()),
         'manifest schema, predecessor or delta')
    return value


def verify(root, integration):
    v15 = predecessor_gate()
    value = records(v15)
    baseline = v15.records()
    for name in integration.keys() & baseline['before'].keys():
        need(integration[name] == baseline['before'][name], 'V15 predecessor pin: ' + name)
    previous = integration | baseline['after']
    # These controls were unchanged through V15 and were checked separately
    # by replay against the #154 Git tree, outside its product source map.
    need(not previous.keys() & PREDECESSOR_REPLAY_CONTROLS.keys(), 'unexpected inherited replay control')
    previous.update(PREDECESSOR_REPLAY_CONTROLS)
    for name in CHANGED:
        need(name in previous and previous[name] == value['before'][name], 'predecessor pin: ' + name)
    need(not previous.keys() & ADDED, 'pre-existing successor addition')
    need(v15.inventory(EXP, FIXTURES) == set(RETAINED), 'predecessor fixture inventory')
    for fixture, name in RETAINED.items():
        need(v15.pin(v15.file(EXP, fixture)) == previous[name], 'predecessor fixture bytes: ' + name)

    expected = previous | value['after']
    for name, pin in expected.items():
        need(v15.pin(v15.file(root, name)) == pin, 'source bytes mismatch: ' + name)
    for version in range(9, 16):
        prefix = f'assets/characters/mpfb-b1-v{version}'
        actual = v15.inventory(root, prefix)
        need(actual == {name for name in expected if name.startswith(prefix + '/')},
             'asset inventory mismatch: ' + prefix)
    return ID, expected
