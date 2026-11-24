"""Authenticate the named contact-target successor to the travel-query Work and CLI."""
import hashlib
import json
from pathlib import Path

EXP = Path(__file__).resolve().parent
EXP72 = 'experiments/72-b1-admission-controls'
EXP73 = 'experiments/73-high-poly-eyes'
NAME = 'input-context-contact-target-v1.json'
SHA = '695212b6cce6ee2a2414567eb210c830e1362bd23951983ab55b540885de44bc'
ID = 'nvwa-contact-target-source-context-v1'
PREDECESSOR = 'e7574dfaaa13d769e824630a32d60ea536c15a83'
FIXTURES = 'pre-contact-target'
HELPER = f'{EXP72}/contact_target_source_context.py'
MANIFEST = f'{EXP72}/{NAME}'
TEST = 'crates/nvwa-cli/tests/contact_query.rs'
PRODUCT = {
    'crates/nvwa-core/src/stage.rs': b'StageContactTarget',
    'crates/nvwa-core/src/lib.rs': b'StageContactTarget',
    'crates/nvwa-runtime/src/b1.rs': b'b1_running_left_index_position',
    'crates/nvwa-runtime/src/lib.rs': b'b1_running_left_index_position',
    'crates/nvwa-cli/src/main.rs': b'CONTACT_QUERY_USAGE',
    'crates/nvwa-cli/src/motion_query.rs': b'fn run_contact(',
    'docs/CLI-SUPPORT.md': b'contact-query',
    'crates/nvwa-studio/src/stage_ui.rs': b'contact_target',
}
CHANGED = set(PRODUCT) | {
    f'{EXP72}/travel_query_source_context.py',
    f'{EXP72}/run.py',
    f'{EXP72}/test_travel_query_context.py',
    f'{EXP72}/test_waist_context.py',
    f'{EXP72}/integration_context.py',
    f'{EXP73}/build.py',
    f'{EXP73}/frozen_context.py',
    'scripts/check-v15-history.py',
    'scripts/check-v15-live73.py',
}
TRAVEL_EXTRA_PINS = {
    'crates/nvwa-studio/src/stage_ui.rs': {
        'bytes': 28403, 'sha256': 'cc10a4c29c7c9b3efd3e31fc4e31a3c318e346e9d6b65eced9d0b723834730db',
    },
    'crates/nvwa-core/src/stage.rs': {
        'bytes': 6274, 'sha256': '27acf1d66321c39a5cbc88f0502204b6c689d5bc7f8c02d1c641a7fb529ba21a',
    },
    'docs/CLI-SUPPORT.md': {
        'bytes': 14994, 'sha256': '63ac1c16aa74ba1388246556169843cf1fcfaf34fd0e3bdc0d5db38b1293d420',
    },
    'experiments/72-b1-admission-controls/travel_query_source_context.py': {
        'bytes': 6083, 'sha256': 'bf01f726dea63bd9277837208b6fe153561b64105285d690235607c0c20e5d32',
    },
}
FIXTURE_PATH = f'{EXP72}/{FIXTURES}/'
ADDED = {TEST, f'{EXP72}/test_contact_target_context.py'} | {FIXTURE_PATH + name for name in CHANGED}


def need(ok, detail):
    if not ok:
        raise ValueError('contact-target exact source: ' + detail)


def present(root, control_exp, v15_present, travel, travel_query):
    def exists(name):
        path = root / name
        return path.exists() or path.is_symlink()

    if exists(TEST) or exists(f'{EXP72}/{FIXTURES}'):
        return True
    separate_controls = control_exp.resolve() != EXP and root / EXP72 == control_exp
    if v15_present or not separate_controls:
        if any(exists(name) for name in (MANIFEST, HELPER, f'{EXP72}/test_contact_target_context.py')):
            return True
    # The travel map omitted its helper and CLI guide in both cohorts, and
    # stage sources outside their original maps. Their original source identities distinguish a lone
    # successor edit even after every newly introduced marker is removed.
    if travel_query and (v15_present or not separate_controls):
        for name, before in TRAVEL_EXTRA_PINS.items():
            if not exists(name) or travel.replay_control_changed(root, name, before):
                return True
    for name, marker in PRODUCT.items():
        path = root / name
        if not path.is_symlink() and path.is_file() and marker in path.read_bytes():
            return True
    return False


def records(v15):
    raw = v15.file(EXP, NAME).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == SHA, 'manifest identity')
    data = json.loads(raw)
    need(set(data) == {'format', 'predecessor_context', 'predecessor_commit', 'before', 'after', 'rust_inventory', 'helper_template'}
         and data['format'] == ID and data['predecessor_context'] == 'nvwa-travel-query-source-context-v1'
         and data['predecessor_commit'] == PREDECESSOR
         and data['before'].keys() == data['after'].keys() == CHANGED | ADDED
         and {name for name, before in data['before'].items() if before is None} == ADDED
         and all(before != data['after'][name] for name, before in data['before'].items()),
         'manifest schema, predecessor or delta')
    return data


SELECTORS = (f'{EXP72}/run.py', f'{EXP73}/frozen_context.py')


def selector_pin(path, template, helper_sha):
    # The helper contains the manifest digest, and each selector authenticates
    # this helper before execution. Store only the fixed-position digest field
    # as zeroes in the manifest template to break that mutual hash dependency.
    raw = path.read_bytes()
    literal = b"CONTACT_HELPER_SHA = '" + helper_sha.encode('ascii') + b"'\n"
    need(raw.count(literal) == 1, 'selector helper binding: ' + path.name)
    zero = b"CONTACT_HELPER_SHA = '" + b'0' * 64 + b"'\n"
    canonical = raw.replace(literal, zero)
    need(template == {'bytes': len(raw), 'template_sha256': hashlib.sha256(canonical).hexdigest()},
         'selector template bytes: ' + path.name)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify(root, travel, integration):
    v15, previous = travel.expected(integration)
    data = records(v15)
    need(v15.file(root, MANIFEST).read_bytes() == v15.file(EXP, NAME).read_bytes(), 'candidate manifest identity')
    need(v15.file(root, HELPER).read_bytes() == Path(__file__).read_bytes(), 'candidate helper identity')
    need(not ADDED & previous.keys(), 'successor addition already present')
    need(v15.inventory(EXP, FIXTURES) == {FIXTURES + '/' + p for p in CHANGED}, 'predecessor fixture inventory')
    for name in CHANGED:
        before = data['before'][name]
        need(previous.get(name, TRAVEL_EXTRA_PINS.get(name)) == before, 'inherited pin mismatch: ' + name)
        if name in TRAVEL_EXTRA_PINS:
            need(before == TRAVEL_EXTRA_PINS[name], 'retained travel pin mismatch: ' + name)
        need(v15.pin(v15.file(EXP, FIXTURES + '/' + name)) == before, 'predecessor fixture: ' + name)
        need(data['after'][FIXTURE_PATH + name] == before, 'candidate predecessor bytes: ' + name)
    expected = previous | data['after']
    helper_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name in SELECTORS:
        expected[name] = selector_pin(v15.file(root, name), data['after'][name], helper_sha)
    travel.verify_files(root, v15, expected, need)
    names = []
    for crate in ('nvwa-cli', 'nvwa-core', 'nvwa-runtime'):
        for directory in ('src', 'tests'):
            prefix = 'crates/' + crate + '/' + directory
            if (root / prefix).is_dir():
                names.extend(name for name in v15.inventory(root, prefix) if name.endswith('.rs'))
    need(hashlib.sha256('\n'.join(sorted(names)).encode()).hexdigest() == data['rust_inventory'],
         'Rust source inventory mismatch')
    return ID, expected
