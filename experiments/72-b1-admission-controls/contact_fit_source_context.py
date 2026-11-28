"""Admit the exact contact-fit, contact-recheck and shaped-motion successor."""
import hashlib
import json
from pathlib import Path

EXP = Path(__file__).resolve().parent
EXP72 = 'experiments/72-b1-admission-controls'
EXP73 = 'experiments/73-high-poly-eyes'
NAME = 'input-context-contact-fit-v1.json'
SHA = 'cea1fc008f19d402eb3216f6a6ebe5316974a5a54f9b69ab7fdaf029cdc76217'
ID = 'nvwa-contact-fit-source-context-v1'
PREDECESSOR = '8da2d17fcde1a43d2d52595cbf1a808ae3b270b2'
FIXTURES = 'pre-contact-fit'
FIXTURE_PATH = f'{EXP72}/{FIXTURES}/'
HELPER = f'{EXP72}/contact_fit_source_context.py'
MANIFEST = f'{EXP72}/{NAME}'
BOOTSTRAP = f'{EXP72}/contact_fit_bootstrap.py'
TEST = f'{EXP72}/test_contact_fit_context.py'
HISTORY = 'scripts/check-v15-history.py'
CORE_MANIFEST = 'crates/nvwa-core/Cargo.toml'
# 73 authenticates this manifest in its original cohort. 72 needs the same
# fixed target declarations to close Cargo's automatic target discovery.
CORE_MANIFEST_PIN = {
    'bytes': 225, 'sha256': '56edf0d7b6947b4068f9fa39b37a852bb2d13e6a0349bbb0292ad3131a4edcad',
}
SELECTORS = (f'{EXP72}/run.py', f'{EXP73}/frozen_context.py')
WORK_DIR = 'crates/nvwa-cli/tests/fixtures/contact-fit'
WORKS = {f'{WORK_DIR}/{actor}/{kind}.nvwa.json' for actor in ('iris', 'mora')
         for kind in ('start', 'reference', 'accepted')}
MODULES = {
    'crates/nvwa-cli/src/motion_query/contact_fit.rs',
    'crates/nvwa-cli/src/motion_query/contact_recheck.rs',
    'crates/nvwa-runtime/src/b1/sole_measurement.rs',
}
# This historical test was authenticated by #154 Git replay, outside both
# contact-target product maps. Retain its original identity for orphan checks.
EXTRA_BEFORE = {
    f'{EXP72}/test_running_context.py': {
        'bytes': 20348, 'sha256': 'c6d1169920fb393131e4afb5bbbe4f83e6318629be46d89e35032681a7632a4a',
    },
}
CHANGED = {
    *EXTRA_BEFORE,
    f'{EXP72}/test_waist_context.py',
    'crates/nvwa-cli/src/main.rs',
    'crates/nvwa-cli/src/motion_query.rs',
    'crates/nvwa-cli/tests/contact_query.rs',
    'crates/nvwa-core/src/b1.rs',
    'crates/nvwa-core/src/lib.rs',
    'crates/nvwa-core/src/reference_motion.rs',
    'crates/nvwa-core/src/running.rs',
    'crates/nvwa-runtime/src/appearance/mod.rs',
    'crates/nvwa-runtime/src/b1.rs',
    'crates/nvwa-runtime/src/b1/foot_clearance.rs',
    'crates/nvwa-runtime/src/b1_running.rs',
    'crates/nvwa-runtime/src/lib.rs',
    'docs/CLI-SUPPORT.md',
    f'{EXP72}/integration_context.py',
    f'{EXP72}/test_contact_target_context.py',
    f'{EXP73}/build.py',
    HISTORY,
    'scripts/check-v15-live73.py',
    *SELECTORS,
}
ADDED = MODULES | WORKS | {TEST, BOOTSTRAP} | {FIXTURE_PATH + name for name in CHANGED}


def need(ok, detail):
    if not ok:
        raise ValueError('contact-fit exact source: ' + detail)


def present(root, control_exp, v15_present, contact_target, travel):
    markers = MODULES | {WORK_DIR, 'crates/nvwa-cli/src/motion_query', f'{EXP72}/{FIXTURES}'}
    # Historical tests sometimes copy current control files into their own
    # source directory. Only their explicit historical control directory is exempt.
    if v15_present or control_exp.resolve() == EXP or root / EXP72 != control_exp:
        markers |= {HELPER, MANIFEST, BOOTSTRAP, TEST}
    for name in markers:
        path = root / name
        if path.exists() or path.is_symlink():
            return True
    if contact_target and (v15_present or control_exp.resolve() == EXP or root / EXP72 != control_exp):
        for name, before in EXTRA_BEFORE.items():
            if not (root / name).exists() or travel.replay_control_changed(root, name, before):
                return True
    # With all additions stripped, the predecessor still verifies every modified
    # product and replay control byte against its original manifest.
    return False


def template_pin(path, template, field, digest):
    # Only the designated digest literal is omitted from the manifest hash.
    # Its actual value must match the authenticated authority before admission.
    raw = path.read_bytes()
    assignment = field.encode('ascii') + b" = '"
    literal = assignment + digest.encode('ascii') + b"'\n"
    need(raw.count(literal) == 1, 'source authority binding: ' + path.name)
    canonical = raw.replace(literal, assignment + b'0' * 64 + b"'\n")
    need(template == {'bytes': len(raw), 'template_sha256': hashlib.sha256(canonical).hexdigest()},
         'source template bytes: ' + path.name)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def selector_pin(path, template, helper_sha):
    return template_pin(path, template, 'FIT_HELPER_SHA', helper_sha)


def history_pin(path, template, manifest_sha):
    return template_pin(path, template, 'FIT_MANIFEST_SHA', manifest_sha)


def verify(root, travel, contact, integration):
    v15, previous = travel.expected(integration)
    predecessor = contact.records(v15)
    previous.update(predecessor['after'])
    need(not previous.keys() & EXTRA_BEFORE.keys(), 'unexpected inherited replay control')
    previous.update(EXTRA_BEFORE)
    raw = v15.file(EXP, NAME).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == SHA, 'manifest identity')
    data = json.loads(raw)
    need(set(data) == {'format', 'predecessor_context', 'predecessor_commit', 'before', 'after',
                       'rust_inventory', 'rust_files', 'helper_template'}
         and data['format'] == ID and data['predecessor_context'] == contact.ID
         and data['predecessor_commit'] == PREDECESSOR
         and data['before'].keys() == data['after'].keys() == CHANGED | ADDED
         and {name for name, before in data['before'].items() if before is None} == ADDED
         and all(before != data['after'][name] for name, before in data['before'].items()),
         'manifest schema, predecessor or delta')
    need(v15.file(root, MANIFEST).read_bytes() == raw, 'candidate manifest identity')
    helper = Path(__file__).read_bytes()
    need(v15.file(root, HELPER).read_bytes() == helper, 'candidate helper identity')
    need(not ADDED & previous.keys(), 'successor addition already present')
    need(v15.inventory(EXP, FIXTURES) == {f'{FIXTURES}/{p}' for p in CHANGED},
         'predecessor fixture inventory')
    need(v15.inventory(root, f'{EXP72}/{FIXTURES}') == {FIXTURE_PATH + p for p in CHANGED},
         'candidate predecessor fixture inventory')
    contact_sha = hashlib.sha256(Path(contact.__file__).read_bytes()).hexdigest()
    for name in CHANGED:
        retained = v15.file(EXP, f'{FIXTURES}/{name}')
        if name in SELECTORS:
            # Resolve the old template against the retained, original selector.
            previous[name] = contact.selector_pin(retained, previous[name], contact_sha)
        need(previous[name] == data['before'][name], 'inherited pin mismatch: ' + name)
        need(v15.pin(retained) == previous[name] == data['after'][FIXTURE_PATH + name],
             'predecessor fixture: ' + name)

    expected = previous | data['after']
    expected[MANIFEST] = {'bytes': len(raw), 'sha256': SHA}
    expected[HELPER] = {'bytes': len(helper), 'sha256': hashlib.sha256(helper).hexdigest()}
    expected[HISTORY] = history_pin(v15.file(root, HISTORY), data['after'][HISTORY], SHA)
    need(expected.get(CORE_MANIFEST, CORE_MANIFEST_PIN) == CORE_MANIFEST_PIN, 'inherited core manifest identity')
    expected[CORE_MANIFEST] = CORE_MANIFEST_PIN
    for name in SELECTORS:
        expected[name] = selector_pin(v15.file(root, name), data['after'][name], hashlib.sha256(helper).hexdigest())
    # Authenticate candidate copies of all predecessor authorities, including
    # manifests which are pinned outside their own before/after maps.
    for authority in (v15.NAME, travel.NAME, contact.NAME, 'v15_source_context.py',
                      'travel_query_source_context.py', 'contact_target_source_context.py'):
        expected[f'{EXP72}/{authority}'] = v15.pin(v15.file(EXP, authority))
    need(v15.inventory(root, WORK_DIR) == WORKS, 'contact-fit Work inventory mismatch')
    rust = {name for crate in ('nvwa-cli', 'nvwa-core', 'nvwa-runtime')
            for name in v15.inventory(root, f'crates/{crate}') if name.endswith('.rs')}
    need(rust == data['rust_files'].keys()
         and hashlib.sha256('\n'.join(sorted(rust)).encode()).hexdigest() == data['rust_inventory'],
         'Rust source inventory mismatch')
    for name, pin in data['rust_files'].items():
        need(expected.get(name, pin) == pin, 'Rust pin disagrees with source context: ' + name)
        expected[name] = pin
    travel.verify_files(root, v15, expected, need)
    return ID, expected
