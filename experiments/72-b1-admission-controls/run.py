#!/usr/bin/env python3
"""Offline production CPU compatibility/mutation controls, disposable-copy only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import time

BASELINE = '581f6c8329c984bf55a913ca999830430334e5a1'
RUNTIME = 'crates/nvwa-runtime/src/b1.rs'
RUNTIME_SHA = 'e798765fbe44f2ecbc7e0f4b96c71a89ebfe23492b39d696a78a0e9bedf8d687'
PINS_SHA = '02637d4de1f782658c6363e88c92e22ed6384db2f20ea468d73a28b74f257208'
CONTEXT_SHA = '48667ae5e9e0dc706c3c9b25f8c7cc3b23e99c37f72cb8a346002e4001b91b9c'
CLOSEOUT_CONTEXT_SHA = '0f9015fefeff7897b814691a990f9b0c46d621a7d7b611e887fd8b28f18de210'
SHORT01_CONTEXT_SHA = 'ed7accc23126ca827d21e25675148a34c00b8d550a09ff54944f183eca2bf84c'
CHEEK_CONTEXT_SHA = 'd743b42f361cf271603b7cbba950bd5005989aacff5a137804f776ebb7f6dc14'
LOWER_CONTEXT_SHA = '5663c4470d9332f8e3fc02da1d094b48c39c5b9903caa1ce8a22aac45307b2e9'
LOWER_BASELINES_SHA = '993525f21e2f298b46373f3609319e6b1a1db50ef9cb01dbe488d406a64c861f'
HERE = Path(__file__).resolve().parent
PACKAGE = ('run.py', 'test_controls.py', 'compatibility.rs', 'cases.json', 'pins.json', 'README.md', 'REVIEW.md', 'input-context-v1.json', 'input-context-v2.json', 'input-context-v3.json')
PACKAGE += ('input-context-v4.json', 'input-context-v5.json')
PACKAGE += ('input-context-legs-v1.json', 'test_leg_context.py')
PACKAGE += ('input-context-upper-body-v1.json', 'test_upper_body_context.py')
PACKAGE += ('input-context-hip-contour-v1.json', 'test_hip_contour_context.py')
PACKAGE += ('input-context-arm-proportions-v1.json', 'test_arm_proportions_context.py')
PACKAGE += ('input-context-hand-size-v1.json', 'test_hand_size_context.py')
PACKAGE += ('input-context-shoulder-form-v1.json', 'test_shoulder_form_context.py')
PACKAGE += ('input-context-forearm-form-v1.json', 'test_forearm_form_context.py')
ENDPOINT = 'b1::tests::new_base_zero_is_exact_and_every_signed_parameter_drives_actual_uploaded_geometry'
ZERO = 'b1::tests::admission72_zero_exact_uploaded_buffers_and_all_bone_fields'
FORTY = 'b1::tests::admission72_original_eight_recipes_five_diagnostics_real_production_compatibility'
INCLUDE_ANCHOR = '\n}\n\n#[derive(Clone, Debug, PartialEq)]\nstruct FrameSample {'
INCLUDE = '\n    include!("admission72_tests.rs");\n'
VALUE_SEAM = '            let value = values[targets.id];'
WEIGHT_SEAM = '''            ] {
                // Legacy zero entries retain their original behavior.'''
FAULTS = (
    {'id': 'omit-new-target', 'before': WEIGHT_SEAM,
     'after': '''            ] {
                if targets.id == "head_width" && name == targets.decrease { continue; }
                // Legacy zero entries retain their original behavior.''',
     'marker': 'head_width -1 must reach actual Mesh POSITION'},
    {'id': 'wrong-target-name-id', 'before': WEIGHT_SEAM,
     'after': '''            ] {
                let name = if targets.id == "head_width" {
                    if name == targets.decrease { "nose-scale-horiz-decr" } else { "nose-scale-horiz-incr" }
                } else { name };
                // Legacy zero entries retain their original behavior.''',
     'marker': 'head_width -1, source ', 'marker2': 'selected signed target/units must reach fitted body'},
    {'id': 'wrong-sign', 'before': VALUE_SEAM,
     'after': '            let value = if targets.id == "head_width" { -values[targets.id] } else { values[targets.id] };',
     'marker': 'head_width -1, source ', 'marker2': 'selected signed target/units must reach fitted body'},
    {'id': 'second-times-point-one', 'before': VALUE_SEAM,
     'after': '            let value = values[targets.id] * if targets.id == "head_width" { 0.1 } else { 1.0 };',
     'marker': 'head_width -1, source ', 'marker2': 'selected signed target/units must reach fitted body'},
    {'id': 'ignore-new-field', 'before': VALUE_SEAM,
     'after': '            let value = if targets.id == "head_width" { 0.0 } else { values[targets.id] };',
     'marker': 'head_width -1 must reach actual Mesh POSITION'},
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def patch_once(original, before, after):
    require(original.count(before) == 1, 'source seam must occur exactly once')
    return original.replace(before, after)


def inject(original):
    return patch_once(original, INCLUDE_ANCHOR, INCLUDE + INCLUDE_ANCHOR)


def mutate(original, fault):
    return patch_once(original, fault['before'], fault['after'])


def verdict(exit_code, text, test, fault=None):
    """Compiler/authentication/timeouts/unrelated panics are never mutation reds."""
    require('error[E' not in text and 'could not compile' not in text, 'compilation failed: not semantic evidence')
    expected = 'FAILED. 0 passed; 1 failed' if fault else 'ok. 1 passed; 0 failed'
    require(exit_code == (101 if fault else 0), 'unexpected actual exit code')
    require('running 1 test' in text and test in text, 'named actual test did not execute')
    require('test result: ' + expected in text, 'wrong test result/count')
    state = 'FAILED' if fault else 'ok'
    require(re.search(r'(?m)^test ' + re.escape(test) + r' \.\.\. (?:[^\n]*\n)*?' + state + r'\s*$', text) is not None
            or re.search(r'(?m)^test ' + re.escape(test) + r' \.\.\. ' + state + r'\s*$', text) is not None,
            'missing named terminal test result')
    if fault:
        require(fault['marker'] in text and fault.get('marker2', '') in text,
                'intended POSITION/signed target assertion not reached')
    return True


def source_contexts(pins):
    """Load exact, code-pinned complete contexts, never per-file alternatives."""
    contexts = [('baseline581', dict(pins['files']))]
    for name, expected in (('input-context-v1.json', CONTEXT_SHA),
                           ('input-context-v2.json', CLOSEOUT_CONTEXT_SHA),
                           ('input-context-v3.json', SHORT01_CONTEXT_SHA)):
        manifest = HERE / name
        require(manifest.is_file() and not manifest.is_symlink() and file_sha(manifest) == expected,
                'input context manifest identity mismatch: ' + name)
        bridge = json.loads(manifest.read_text())
        require(bridge['schema_version'] == 1 and bridge['baseline_commit'] == BASELINE,
                'input context version/baseline mismatch')
        current = dict(pins['files'])
        current.update(bridge['overrides'])
        contexts.append((bridge['context'], current))
    return contexts


def select_source_context(actual, contexts, historical_only=False):
    """The whole authenticated file map must match one reviewed context."""
    for name, expected in contexts:
        if actual == expected and (not historical_only or name == 'baseline581'):
            return name
    raise ValueError('source input context mismatch: exact baseline581, reviewed issue86 pair, or reviewed closeout, or reviewed short01 product context required')


def admitted_source_contexts(pins):
    """Keep the old four-context cohort and append one exact current product."""
    contexts = source_contexts(pins)
    path = HERE / 'input-context-v4.json'
    require(path.is_file() and not path.is_symlink() and file_sha(path) == CHEEK_CONTEXT_SHA,
            'cheek input context manifest identity mismatch')
    bridge = json.loads(path.read_text())
    require(set(bridge) == {'schema_version', 'baseline_commit', 'context', 'overrides', 'scope'}
            and bridge['schema_version'] == 1 and bridge['baseline_commit'] == BASELINE
            and bridge['context'] == 'b1-cheek-fullness-product-v1',
            'cheek input context version/baseline mismatch')
    require(bridge['overrides'] and set(bridge['overrides']) <= set(pins['files']),
            'cheek input context must retain exact historical source paths')
    current = dict(pins['files'])
    current.update(bridge['overrides'])
    contexts.append((bridge['context'], current))
    return contexts



def pre_lower_contour_root(pins):
    """Authenticate the complete former live cheek source, without Git history."""
    root = HERE / 'fixtures/pre-lower-contour'
    path = root / 'manifest.json'
    require(path.is_file() and not path.is_symlink() and file_sha(path) == LOWER_BASELINES_SHA,
            'pre-lower-contour fixture manifest identity mismatch')
    manifest = json.loads(path.read_text())
    expected = dict(admitted_source_contexts(pins))['b1-cheek-fullness-product-v1']
    require(set(manifest) == {'schema_version', 'context', 'source_commit', 'files'}
            and manifest['schema_version'] == 1
            and manifest['context'] == 'b1-cheek-fullness-product-v1'
            and manifest['source_commit'] == 'e3c02689d7f59d97141ffe70835fa3524231c28a'
            and set(manifest['files']) == set(expected), 'pre-lower-contour complete cheek fixture required')
    for name, digest in expected.items():
        item = manifest['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'} and item['fixture'] == name
                and item['sha256'] == digest, 'pre-lower-contour historical pin mismatch: ' + name)
        path = root
        for part in Path(name).parts:
            path = path / part
            require(not path.is_symlink(), 'pre-lower-contour fixture symlink: ' + name)
        require(path.is_file() and path.stat().st_size == item['bytes'] and file_sha(path) == digest,
                'pre-lower-contour fixture bytes mismatch: ' + name)
    declared = set(expected) | {'manifest.json'}
    paths = list(root.rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(root)) for p in paths if p.is_file()} == declared,
            'pre-lower-contour fixture inventory mismatch')
    return root


def current_source_contexts(pins):
    """Append the exact new product without changing the old five-context cohort."""
    contexts = admitted_source_contexts(pins)
    path = HERE / 'input-context-v5.json'
    require(path.is_file() and not path.is_symlink() and file_sha(path) == LOWER_CONTEXT_SHA,
            'lower contour input context manifest identity mismatch')
    bridge = json.loads(path.read_text())
    require(set(bridge) == {'schema_version', 'baseline_commit', 'context', 'overrides', 'scope'}
            and bridge['schema_version'] == 1 and bridge['baseline_commit'] == BASELINE
            and bridge['context'] == 'b1-lower-face-squareness-product-v1',
            'lower contour input context version/baseline mismatch')
    require(bridge['overrides'] and set(bridge['overrides']) <= set(pins['files']),
            'lower contour input context must retain exact historical source paths')
    current = dict(pins['files'])
    current.update(bridge['overrides'])
    contexts.append((bridge['context'], current))
    return contexts


RUNNING_CONTEXT_SHA = 'd1615c80710c85c70fa1a4108d0da7f0ecde3f906fced2b87f91cc2b5752893b'
RUNNING_BASELINES_SHA = 'b2e254dde16306b51b1fb2433a82383d1b47d31bbdcf7eded8b1a58aafc682d9'
RUNNING_ADDITIONS = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/running.rs', 'crates/nvwa-core/src/running.rs', 'crates/nvwa-runtime/src/b1_running.rs', 'crates/nvwa-runtime/src/b1_running_controls.json', 'crates/nvwa-runtime/src/lib.rs', 'crates/nvwa-studio/src/appearance_ui_tests.rs', 'crates/nvwa-studio/src/lib.rs', 'docs/b1-running-contract.md')
RUNNING_PREEXISTING = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/src/lib.rs',
                       'crates/nvwa-studio/src/appearance_ui_tests.rs', 'crates/nvwa-studio/src/lib.rs')


def running_source_context(pins):
    """One fixed union; original17 and all historical cohort APIs stay fixed."""
    return _running_source_context(pins, current_source_contexts(pins))


def _running_source_context(pins, contexts):
    path = HERE / 'input-context-v6.json'
    require(path.is_file() and not path.is_symlink() and file_sha(path) == RUNNING_CONTEXT_SHA,
            'running source input context manifest identity mismatch')
    value = json.loads(path.read_bytes())
    require(set(value) == {'schema_version', 'context', 'predecessor', 'source_freeze_sha256', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-running-product-v1'
            and value['predecessor'] == 'b1-lower-face-squareness-product-v1'
            and value['source_freeze_sha256'] == 'ecc815dac0c868d1f3597324c2ca10b5f021199e87007c71fbf0cd4c33647044'
            and set(value['files']) == set(pins['files']) | set(RUNNING_ADDITIONS)
            and len(value['files']) == 26, 'running source input complete union required')
    _pre_running_sources(pins, contexts)
    return value['context'], value['files']


def pre_running_sources(pins):
    """Only displaced lower source; no duplicated assets or old checker."""
    return _pre_running_sources(pins, current_source_contexts(pins))


def _pre_running_sources(pins, contexts):
    root = HERE / 'fixtures/pre-running'
    manifest = root / 'manifest.json'
    require(manifest.is_file() and not manifest.is_symlink() and file_sha(manifest) == RUNNING_BASELINES_SHA,
            'pre-running fixture manifest identity mismatch')
    value = json.loads(manifest.read_bytes())
    expected = dict(contexts)[value['context']]
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files', 'historical_outside', 'historical_original'}
            and value['schema_version'] == 1
            and value['context'] == 'b1-lower-face-squareness-product-v1'
            and value['source_commit'] == '9251712313a3779bf4f0a4a854755a16f1a5df16', 'pre-running fixture identity mismatch')
    result = {}
    for name, item in value['files'].items():
        require(item['fixture'] == 'fixtures/pre-running/' + name and item['sha256'] == expected[name],
                'pre-running historical source pin mismatch: ' + name)
        path = HERE
        for part in Path(item['fixture']).parts:
            path = path / part
            require(not path.is_symlink(), 'pre-running fixture symlink: ' + name)
        require(path.is_file() and path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'pre-running fixture bytes mismatch: ' + name)
        result[name] = path.read_bytes()
    declared = {'fixtures/pre-running/manifest.json'} | {i['fixture'] for i in value['files'].values()}
    require(set(value['historical_outside']) == {name for name, _ in contexts},
            'pre-running historical cohort inventory mismatch')
    retained = list(value['historical_original'].items())
    for name, item in value['historical_original'].items():
        require(item['sha256'] == pins['files'][name], 'pre-running original pin mismatch: ' + name)
    for variants in value['historical_outside'].values():
        require(variants, 'pre-running historical variants required')
        for variant in variants:
            require(set(variant['files']) == set(RUNNING_PREEXISTING), 'pre-running historical outside paths mismatch')
            retained.extend(variant['files'].items())
    for name, item in retained:
        path = HERE
        for part in Path(item['fixture']).parts:
            path = path / part
            require(not path.is_symlink(), 'pre-running fixture symlink: ' + name)
        require(path.is_file() and path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'pre-running historical outside bytes mismatch: ' + name)
        declared.add(item['fixture'])
    paths = list(root.rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(HERE)) for p in paths if p.is_file()} == declared,
            'pre-running fixture inventory mismatch')
    return result


MOTION_QUERY_CONTEXT = 'b1-motion-query-product-v1'
MOTION_QUERY_CONTEXT_NAME = 'input-context-v7.json'
MOTION_QUERY_CONTEXT_SHA = 'c4701231f75f94f00c6df90cf5d9562ae0421f4cbcf75a34a81f09b98c1bffa7'
MOTION_QUERY_NEW = ('crates/nvwa-cli/src/motion_query.rs', 'crates/nvwa-cli/tests/motion_query.rs',
                    'crates/nvwa-runtime/src/b1/foot_clearance.rs')
MOTION_QUERY_OUTSIDE = {
    'crates/nvwa-cli/Cargo.toml': {'bytes': 236, 'sha256': '8393f7aa78a68a1cc6781c8e8d3d211226be5e809cc7fe84821a56e3c9fbb508'},
    'crates/nvwa-studio/examples/nvwa-preview.rs': {'bytes': 22049, 'sha256': 'c32c5bb4f71989af875ae1d24af40d6d7810ff97d4e4582d94c12311964e2452'},
}
MOTION_QUERY_ADDITIONS = (*MOTION_QUERY_NEW, *MOTION_QUERY_OUTSIDE)
MOTION_QUERY_CHANGED = ('Cargo.lock', 'crates/nvwa-cli/src/main.rs', RUNTIME, 'crates/nvwa-runtime/src/lib.rs')
MOTION_QUERY_FIXTURES = 'fixtures/pre-motion-query'


def _motion_query_source_context(running):
    path = source_file(HERE, MOTION_QUERY_CONTEXT_NAME)
    raw = path.read_bytes()
    require(sha(raw) == MOTION_QUERY_CONTEXT_SHA, 'motion-query source input context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_manifest_sha256',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == MOTION_QUERY_CONTEXT
            and value['predecessor'] == running[0]
            and value['predecessor_manifest_sha256'] == RUNNING_CONTEXT_SHA
            and value['predecessor_commit'] == 'd272e16fa6f5faa55337c4ae5f6ac18043f8ab01',
            'motion-query source input context predecessor mismatch')
    files = value['files']
    require(set(files) == set(running[1]) | set(MOTION_QUERY_ADDITIONS)
            and len(files) == 31
            and {name for name, item in running[1].items() if files[name] != item} == set(MOTION_QUERY_CHANGED),
            'motion-query source input context complete union required')
    _pre_motion_query_sources(running)
    return value['context'], files


def _pre_motion_query_sources(running):
    expected = {name: running[1][name] for name in MOTION_QUERY_CHANGED} | MOTION_QUERY_OUTSIDE
    result = {}
    declared = set()
    for name, item in expected.items():
        if name == 'Cargo.lock':
            relative = 'fixtures/pre-lower-contour/Cargo.lock'
        else:
            relative = MOTION_QUERY_FIXTURES + '/' + name
            declared.add(relative)
        raw = source_file(HERE, relative).read_bytes()
        require({'bytes': len(raw), 'sha256': sha(raw)} == item,
                'pre-motion-query fixture bytes mismatch: ' + name)
        result[name] = raw
    paths = list((HERE / MOTION_QUERY_FIXTURES).rglob('*'))
    require(all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths)
            and {str(path.relative_to(HERE)) for path in paths if path.is_file()} == declared,
            'pre-motion-query fixture inventory mismatch')
    return result


def pre_motion_query_sources(pins):
    """Return the exact displaced running inputs and pre-existing outside bytes."""
    return _pre_motion_query_sources(running_source_context(pins))


def source_file(root, relative):
    path = root
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'source input context mismatch: symlink: ' + relative)
    require(path.is_file(), 'source input context mismatch: missing: ' + relative)
    return path


def check_no_motion_query_additions(root):
    require(not any((root / name).exists() or (root / name).is_symlink() for name in MOTION_QUERY_NEW),
            'source input context mismatch: motion-query additions in historical source')
    for name, item in MOTION_QUERY_OUTSIDE.items():
        if (root / name).exists() or (root / name).is_symlink():
            path = source_file(root, name)
            require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                    'source input context mismatch: motion-query outside source: ' + name)


# A separate exact product context; all historical cohort APIs and pins stay fixed.
CPU_CONTEXT_NAME = 'input-context-cpu-export-v1.json'
CPU_CONTEXT_SHA = '333acadd76ef9a8141cbb27625bb93b3eb8a7e40b3aee4f7fbd914b8cd005293'
CPU_BASELINES_SHA = '6d0a08f17b5ea871316e59670df4d4d8229f49958352e5badeb8282f5a55bf59'
CPU_CONTEXT_ID = 'b1-cpu-export-product-v1'
CPU_PREDECESSOR_COMMIT = '54384aeaaa70a7883978e3e33d4bf163c0c1f273'
CPU_ADDITIONS = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-runtime/Cargo.toml', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'crates/nvwa-runtime/src/stage.rs', 'docs/agents/cli-authoring.md', 'docs/agents/cpu-render.md', 'experiments/27-ci-baseline/check.sh')
CPU_NEW_FILES = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'docs/agents/cpu-render.md')
CPU_PREEXISTING = ('crates/nvwa-runtime/Cargo.toml', 'crates/nvwa-runtime/src/stage.rs', 'docs/agents/cli-authoring.md', 'experiments/27-ci-baseline/check.sh')
CPU_RETAINED = ('Cargo.lock', 'crates/nvwa-cli/Cargo.toml', 'crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/Cargo.toml', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/lib.rs', 'crates/nvwa-runtime/src/stage.rs', 'docs/agents/cli-authoring.md', 'experiments/27-ci-baseline/check.sh')

def cpu_regular_file(exp, relative):
    path = exp
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'CPU source context symlink: ' + relative)
    require(path.is_file(), 'CPU source context missing: ' + relative)
    return path


def has_cpu_inputs(root):
    return any((root / n).exists() or (root / n).is_symlink() for n in CPU_NEW_FILES)


def _pre_cpu_sources(exp, previous):
    path = cpu_regular_file(exp, 'fixtures/pre-cpu-export/manifest.json')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CPU_BASELINES_SHA,
            'CPU predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-motion-query-product-v1'
            and value['source_commit'] == CPU_PREDECESSOR_COMMIT
            and set(value['files']) == set(CPU_RETAINED), 'CPU predecessor complete inventory required')
    result = {}
    for name, item in value['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == 'fixtures/pre-cpu-export/' + name,
                'CPU predecessor fixture path mismatch')
        expected = {k: item[k] for k in ('bytes', 'sha256')}
        if name in previous:
            require(expected == previous[name], 'CPU predecessor historical pin mismatch: ' + name)
        data = cpu_regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected,
                'CPU predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / 'fixtures/pre-cpu-export').rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {'fixtures/pre-cpu-export/manifest.json'} | {i['fixture'] for i in value['files'].values()},
            'CPU predecessor fixture inventory mismatch')
    return result


def _cpu_context(exp, previous):
    _pre_cpu_sources(exp, previous)
    raw = cpu_regular_file(exp, CPU_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CPU_CONTEXT_SHA, 'CPU source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == CPU_CONTEXT_ID
            and value['predecessor'] == 'b1-motion-query-product-v1'
            and value['predecessor_commit'] == CPU_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(CPU_ADDITIONS),
            'CPU source context complete union required')
    return value['context'], value['files']


def pre_cpu_sources(pins):
    return _pre_cpu_sources(HERE, _motion_query_source_context(running_source_context(pins))[1])


def cpu_source_context(pins):
    return _cpu_context(HERE, _motion_query_source_context(running_source_context(pins))[1])


def check_cpu_preexisting(root, retained):
    for name in CPU_PREEXISTING:
        if (root / name).exists() or (root / name).is_symlink():
            require(cpu_regular_file(root, name).read_bytes() == retained[name],
                    'CPU source context mismatch: historical outside source: ' + name)


# The exact reference motion source is an additive successor to CPU export.
REFERENCE_MOTION_CONTEXT_NAME = 'input-context-reference-motion-v1.json'
REFERENCE_MOTION_CONTEXT_SHA = '314e447a9ac66d355a33f68fe4e44dc8366a8946eb2e280413fa7510929ad348'
REFERENCE_MOTION_CONTEXT_ID = 'b1-reference-motion-product-v1'
REFERENCE_MOTION_PREDECESSOR_COMMIT = '875213616aa68d81dbfcd6378f4e2292f5b24004'
REFERENCE_MOTION_CHANGED = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-core/src/lib.rs',
                            'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-studio/src/lib.rs')
REFERENCE_MOTION_ADDITIONS = ('crates/nvwa-cli/tests/reference_motion.rs',
                              'crates/nvwa-core/src/reference_motion.rs',
                              'docs/agents/reference-motion.md')
REFERENCE_MOTION_FIXTURES = 'fixtures/pre-reference-motion'


def has_reference_motion_inputs(root):
    return any((root / name).exists() or (root / name).is_symlink()
               for name in REFERENCE_MOTION_ADDITIONS)


def _pre_reference_motion_sources(exp, previous):
    """Read the displaced CPU source bytes against the authenticated CPU pins."""
    result = {}
    for name in REFERENCE_MOTION_CHANGED:
        path = source_file(exp, REFERENCE_MOTION_FIXTURES + '/' + name)
        data = path.read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == previous[name],
                'reference motion predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / REFERENCE_MOTION_FIXTURES).rglob('*'))
    require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(exp / REFERENCE_MOTION_FIXTURES).as_posix()
                 for p in paths if p.is_file()} == set(REFERENCE_MOTION_CHANGED),
            'reference motion predecessor fixture inventory mismatch')
    return result


def _reference_motion_context(exp, cpu):
    predecessor, previous = cpu
    raw = source_file(exp, REFERENCE_MOTION_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == REFERENCE_MOTION_CONTEXT_SHA,
            'reference motion source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == REFERENCE_MOTION_CONTEXT_ID
            and value['predecessor'] == predecessor
            and value['predecessor_commit'] == REFERENCE_MOTION_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(REFERENCE_MOTION_ADDITIONS),
            'reference motion source context complete union required')
    require({name for name in previous if value['files'][name] != previous[name]}
            == set(REFERENCE_MOTION_CHANGED), 'reference motion source context exact changes required')
    _pre_reference_motion_sources(exp, previous)
    return value['context'], value['files']


def pre_reference_motion_sources(pins):
    return _pre_reference_motion_sources(HERE, cpu_source_context(pins)[1])

# A separate exact product context; all historical cohort APIs and pins stay fixed.
WAIST_CONTEXT_NAME = 'input-context-waist-v1.json'
WAIST_CONTEXT_SHA = 'a0852ff6bf8da1e454257228cef706797764ab4a528bbdd1d63d1644dc398b8e'
WAIST_BASELINES_SHA = 'e42a0ec7fbb47fc3c52edd2948cf8f92ed1d52d20b77959f7da3f5a0add2a891'
WAIST_CONTEXT_ID = 'b1-waist-circumference-product-v1'
WAIST_PREDECESSOR_COMMIT = '875213616aa68d81dbfcd6378f4e2292f5b24004'
WAIST_ADDITIONS = ('assets/characters/mpfb-b1-v5/base.obj', 'assets/characters/mpfb-b1-v5/body.mhclo', 'assets/characters/mpfb-b1-v5/composite.json', 'assets/characters/mpfb-b1-v5/empty.macro', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.obj', 'assets/characters/mpfb-b1-v5/licenses/CC0-1.0.txt', 'assets/characters/mpfb-b1-v5/licenses/CHEEK-VOLUME-DERIVATION-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/LOWER-FACE-SQUARING-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/MPFB-LICENSE.md', 'assets/characters/mpfb-b1-v5/licenses/PARAMETER-SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/provenance.json', 'assets/characters/mpfb-b1-v5/manifest.json', 'assets/characters/mpfb-b1-v5/provenance/README.md', 'assets/characters/mpfb-b1-v5/provenance/cheek-volume-derivation.json', 'assets/characters/mpfb-b1-v5/provenance/chin-bones-source.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/parameter-source-receipt.json', 'assets/characters/mpfb-b1-v5/provenance/runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json', 'assets/characters/mpfb-b1-v5/provenance/waist-source-validation.json', 'assets/characters/mpfb-b1-v5/rig.game_engine.json', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-decr.target', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-incr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-decr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-incr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-decr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-incr.target', 'assets/characters/mpfb-b1-v5/vertex_groups.json', 'assets/characters/mpfb-b1-v5/weights.game_engine.json', 'crates/nvwa-cli/tests/appearance.rs', 'crates/nvwa-cli/tests/waist.rs', 'crates/nvwa-core/tests/appearance.rs', 'crates/nvwa-core/tests/waist.rs', 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')
WAIST_NEW_FILES = ('assets/characters/mpfb-b1-v5/base.obj', 'assets/characters/mpfb-b1-v5/body.mhclo', 'assets/characters/mpfb-b1-v5/composite.json', 'assets/characters/mpfb-b1-v5/empty.macro', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.obj', 'assets/characters/mpfb-b1-v5/licenses/CC0-1.0.txt', 'assets/characters/mpfb-b1-v5/licenses/CHEEK-VOLUME-DERIVATION-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/LOWER-FACE-SQUARING-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/MPFB-LICENSE.md', 'assets/characters/mpfb-b1-v5/licenses/PARAMETER-SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/provenance.json', 'assets/characters/mpfb-b1-v5/manifest.json', 'assets/characters/mpfb-b1-v5/provenance/README.md', 'assets/characters/mpfb-b1-v5/provenance/cheek-volume-derivation.json', 'assets/characters/mpfb-b1-v5/provenance/chin-bones-source.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/parameter-source-receipt.json', 'assets/characters/mpfb-b1-v5/provenance/runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json', 'assets/characters/mpfb-b1-v5/provenance/waist-source-validation.json', 'assets/characters/mpfb-b1-v5/rig.game_engine.json', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-decr.target', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-incr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-decr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-incr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-decr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-incr.target', 'assets/characters/mpfb-b1-v5/vertex_groups.json', 'assets/characters/mpfb-b1-v5/weights.game_engine.json', 'crates/nvwa-cli/tests/waist.rs', 'crates/nvwa-core/tests/waist.rs')
WAIST_PREEXISTING = ('crates/nvwa-cli/tests/appearance.rs', 'crates/nvwa-core/tests/appearance.rs', 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')
WAIST_RETAINED = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/appearance.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-core/src/appearance.rs', 'crates/nvwa-core/src/b1.rs', 'crates/nvwa-core/tests/appearance.rs', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'docs/agents/cpu-render.md', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')

def waist_regular_file(exp, relative):
    path = exp
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'WAIST source context symlink: ' + relative)
    require(path.is_file(), 'WAIST source context missing: ' + relative)
    return path


def has_waist_inputs(root):
    return any((root / n).exists() or (root / n).is_symlink() for n in WAIST_NEW_FILES)


def _pre_waist_sources(exp, previous):
    path = waist_regular_file(exp, 'fixtures/pre-waist/manifest.json')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == WAIST_BASELINES_SHA,
            'WAIST predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-cpu-export-product-v1'
            and value['source_commit'] == WAIST_PREDECESSOR_COMMIT
            and set(value['files']) == set(WAIST_RETAINED), 'WAIST predecessor complete inventory required')
    result = {}
    for name, item in value['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == 'fixtures/pre-waist/' + name,
                'WAIST predecessor fixture path mismatch')
        expected = {k: item[k] for k in ('bytes', 'sha256')}
        if name in previous:
            require(expected == previous[name], 'WAIST predecessor historical pin mismatch: ' + name)
        data = waist_regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected,
                'WAIST predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / 'fixtures/pre-waist').rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {'fixtures/pre-waist/manifest.json'} | {i['fixture'] for i in value['files'].values()},
            'WAIST predecessor fixture inventory mismatch')
    return result


def _waist_context(exp, previous):
    _pre_waist_sources(exp, previous)
    raw = waist_regular_file(exp, WAIST_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == WAIST_CONTEXT_SHA, 'WAIST source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == WAIST_CONTEXT_ID
            and value['predecessor'] == 'b1-cpu-export-product-v1'
            and value['predecessor_commit'] == WAIST_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(WAIST_ADDITIONS),
            'WAIST source context complete union required')
    return value['context'], value['files']


def pre_waist_sources(pins):
    return _pre_waist_sources(HERE, cpu_source_context(pins)[1])


def waist_source_context(pins):
    return _waist_context(HERE, cpu_source_context(pins)[1])


def check_waist_preexisting(root, retained):
    for name in WAIST_PREEXISTING:
        if (root / name).exists() or (root / name).is_symlink():
            require(waist_regular_file(root, name).read_bytes() == retained[name],
                    'WAIST source context mismatch: historical outside source: ' + name)



COMBINED_CONTEXT_NAME = 'input-context-waist-reference-motion-v1.json'
COMBINED_CONTEXT_SHA = '03b7c7002e087e61620d372a399b45a9fa6bece5d52b951e3b9cd4261b92f93f'
COMBINED_CONTEXT_ID = 'b1-waist-reference-motion-product-v1'
COMBINED_PREDECESSOR_COMMIT = '9031ce7f82167621e8b7fed2b7a0af5a899b8a17'
COMBINED_FIXTURES = 'fixtures/pre-waist-reference-motion'
COMBINED_REFERENCE_RETAINED = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-studio/src/lib.rs')


def _combined_predecessors(exp, waist, reference):
    variants = (('waist', REFERENCE_MOTION_CHANGED, waist[1]),
                ('reference-motion', COMBINED_REFERENCE_RETAINED, reference[1]))
    expected_paths = {f'{label}/{name}' for label, names, _ in variants for name in names}
    fixture_root = exp / COMBINED_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths)
            and {path.relative_to(fixture_root).as_posix() for path in paths if path.is_file()}
            == expected_paths, 'combined source predecessor fixture inventory mismatch')
    result = {}
    for label, names, pins in variants:
        retained = {}
        for name in names:
            data = source_file(exp, f'{COMBINED_FIXTURES}/{label}/{name}').read_bytes()
            require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == pins[name],
                    'combined source predecessor bytes mismatch: ' + name)
            retained[name] = data
        result[label] = retained
    return result


def _combined_context(exp, cpu):
    waist = _waist_context(exp, cpu[1])
    reference = _reference_motion_context(exp, cpu)
    _combined_predecessors(exp, waist, reference)
    raw = source_file(exp, COMBINED_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == COMBINED_CONTEXT_SHA,
            'combined source context manifest identity mismatch')
    value = json.loads(raw)
    previous = waist[1]
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == COMBINED_CONTEXT_ID
            and value['predecessor'] == waist[0]
            and value['predecessor_commit'] == COMBINED_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(REFERENCE_MOTION_ADDITIONS),
            'combined source context complete union required')
    require({name for name in previous if value['files'][name] != previous[name]}
            == set(REFERENCE_MOTION_CHANGED), 'combined source context exact changes required')
    return value['context'], value['files']


# An exact successor to the waist/reference-motion product. The prior context
# and its mutation witnesses are retained against authenticated pre-leg bytes.
LEG_CONTEXT_NAME = 'input-context-legs-v1.json'
LEG_CONTEXT_SHA = '955d7a1c5ff4481ccf14d3fe7b393a482c71a325d770067b8e52d1b96d0a4665'
LEG_BASELINES_SHA = '61a22c7c8ec538b8c0194c456bc55eb2d39b569e26c7988c874b6b3416b8a1af'
LEG_CONTEXT_ID = 'b1-leg-morphology-product-v1'
LEG_PREDECESSOR_COMMIT = 'e21322c95b3b9ca40334206de135a19b1ad6cb0f'
LEG_FIXTURES = 'fixtures/pre-leg'
LEG_CHANGED = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/src/main.rs',
               'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-core/src/appearance.rs',
               'crates/nvwa-core/src/b1.rs', 'crates/nvwa-runtime/src/b1.rs',
               'crates/nvwa-runtime/src/b1/cpu_render.rs',
               'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs',
               'scripts/build-web.sh', 'scripts/package-cli.py',
               'scripts/package-native.py', 'scripts/test-cli-package.py')
LEG_NEW_CODE = ('crates/nvwa-cli/tests/legs.rs', 'crates/nvwa-core/tests/legs.rs',
                'docs/research/character-foundation/leg-control-plan.md')
LEG_ASSET_PREFIX = 'assets/characters/mpfb-b1-v6/'


def has_leg_inputs(root):
    path = root / LEG_ASSET_PREFIX
    return path.exists() or path.is_symlink()


UPPER_CONTEXT_NAME = 'input-context-upper-body-v1.json'
UPPER_CONTEXT_SHA = 'a11c03173769831c45f9cda63506634adea0e92718910f521d6b4e947c44fbd2'
UPPER_BASELINES_SHA = '70aaa662cb57f289ca4f8299d1e7aba0652b65d2ecf82413da5bbe35d24242f5'
UPPER_CONTEXT_ID = 'b1-upper-body-morphology-product-v1'
UPPER_PREDECESSOR_COMMIT = 'd5bc346ff96213a0337a167bc60e5d1834b81bf0'
UPPER_FIXTURES = 'fixtures/pre-upper-body'
UPPER_CHANGED = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/src/cpu_render.rs',
                 'crates/nvwa-cli/tests/cpu_render.rs',
                 'crates/nvwa-core/src/appearance.rs', 'crates/nvwa-core/src/b1.rs',
                 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs',
                 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs',
                 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py',
                 'scripts/test-cli-package.py')
UPPER_NEW_CODE = ('crates/nvwa-cli/tests/upper_body.rs', 'crates/nvwa-core/tests/upper_body.rs',
                  'docs/research/character-foundation/upper-body-control-plan.md',
                  'scripts/build-upper-body-v7.py')
UPPER_ASSET_PREFIX = 'assets/characters/mpfb-b1-v7/'

HIP_CONTEXT_NAME = 'input-context-hip-contour-v1.json'
HIP_CONTEXT_SHA = '441d9b64b08fc138a67ae13a88831f037082a60cdccb19eafa6876fc351baa38'
HIP_BASELINES_SHA = 'f4269275a93c30e566de7a814e10b2f0d488cda060e4e0444a38a48991bdfeaa'
HIP_CONTEXT_ID = 'b1-hip-contour-product-v1'
HIP_PREDECESSOR_COMMIT = 'e433bd3a430f457d120187823d549daf30b41e64'
HIP_FIXTURES = 'fixtures/pre-hip-contour'
HIP_CHANGED = UPPER_CHANGED
HIP_NEW_CODE = ('crates/nvwa-cli/tests/hip_contour.rs', 'crates/nvwa-core/tests/hip_contour.rs',
                'docs/research/character-foundation/body-control-coverage.md',
                'scripts/build-hip-contour-v8.py')
HIP_ASSET_PREFIX = 'assets/characters/mpfb-b1-v8/'

ARM_CONTEXT_NAME = 'input-context-arm-proportions-v1.json'
ARM_CONTEXT_SHA = '9b00a24d037abc21b3b13a21222ad1e1e37a9d307391f252276413b1f1c8835b'
ARM_BASELINES_SHA = '2981c726a1ba8f83dad54529838c927de525d48a22881cb03e6a899c8f8e2337'
ARM_CONTEXT_ID = 'b1-arm-proportions-product-v1'
ARM_PREDECESSOR_COMMIT = 'ff536bc417ec5f8ff5311fe5f8e7a53c20226c03'
ARM_FIXTURES = 'fixtures/pre-arm-proportions'
ARM_CHANGED = HIP_CHANGED + ('docs/research/character-foundation/body-control-coverage.md',)
ARM_NEW_CODE = ('crates/nvwa-cli/tests/arm_proportions.rs',
                'crates/nvwa-core/tests/arm_proportions.rs',
                'scripts/build-arm-proportions-v9.py')
ARM_ASSET_PREFIX = 'assets/characters/mpfb-b1-v9/'

BODY_REFERENCE_CONTEXT_NAME = 'input-context-body-reference-v1.json'
BODY_REFERENCE_CONTEXT_SHA = '451b150461319889ace4211838748177640d3cd89ab27a26e58fa508328e6e80'
BODY_REFERENCE_CONTEXT_ID = 'b1-body-reference-product-v1'
BODY_REFERENCE_CHANGED = ('crates/nvwa-cli/src/cpu_render.rs',
                          'crates/nvwa-cli/tests/cpu_render.rs',
                          'crates/nvwa-runtime/src/b1.rs',
                          'crates/nvwa-runtime/src/b1/cpu_render.rs',
                          'crates/nvwa-runtime/src/lib.rs',
                          'docs/agents/cpu-render.md')
BODY_REFERENCE_ADDED = 'scripts/render-body-reference.py'
BODY_REFERENCE_FIXTURES = 'fixtures/pre-body-reference'
BODY_REFERENCE_BASELINES_SHA = 'ce83e2433a77d41b591af765d5feb22aa626267f51d71a5c893ac4c912f73bf5'
HAND_CONTEXT_NAME = 'input-context-hand-size-v1.json'
HAND_CONTEXT_SHA = '9922760204d771cbdbaa742944f81dd6d023df55e1ca5748aeba80834ec94016'
HAND_CONTEXT_ID = 'b1-hand-size-v11-product-v1'
HAND_PREDECESSOR_COMMIT = '91f4187a8fc66ac1baa41a771045ef9ca2b4384b'
HAND_FIXTURES = 'fixtures/pre-hand-size'
HAND_BASELINES_SHA = '84265be2e081758a0fa1e7156e9fc1bfd79039cae92aac7e191d4b3cd6d73c41'
HAND_ASSET_PREFIX = 'assets/characters/mpfb-b1-v11/'
HAND_CHANGED = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/src/main.rs',
                'crates/nvwa-core/src/appearance.rs', 'crates/nvwa-core/src/b1.rs',
                'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs',
                'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs',
                'docs/agents/cpu-render.md',
                'docs/research/character-foundation/body-control-coverage.md',
                'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py')
HAND_NEW_CODE = ('crates/nvwa-cli/tests/hand_size.rs', 'crates/nvwa-core/tests/hand_size.rs',
                 'scripts/build-hand-size-v11.py', 'scripts/render-hand-size-review.py',
                 'scripts/test-hand-size-v11.py')
SHOULDER_CONTEXT_NAME = 'input-context-shoulder-form-v1.json'
SHOULDER_CONTEXT_SHA = '49c7504006c1bfa624dda9bb8843fdfd73c12a15f10a3d1cc0e158e308d2edf2'
SHOULDER_CONTEXT_ID = 'b1-shoulder-form-v12-product-v1'
SHOULDER_PREDECESSOR_COMMIT = 'a0e484f717012bb1b5ab436cd94a50be7006698c'
SHOULDER_FIXTURES = 'fixtures/pre-shoulder-form'
SHOULDER_BASELINES_SHA = '7b15d7a59cd9972d992b2de4ea2a316bd3b6bf6f3f10df743f3a6fadd9a64d97'
SHOULDER_ASSET_PREFIX = 'assets/characters/mpfb-b1-v12/'
SHOULDER_CHANGED = HAND_CHANGED
SHOULDER_NEW_CODE = ('crates/nvwa-cli/tests/shoulder_form.rs',
                     'crates/nvwa-core/tests/shoulder_form.rs',
                     'scripts/build-shoulder-form-v12.py',
                     'scripts/render-shoulder-form-review.py',
                     'scripts/test-shoulder-form-v12.py')

FOREARM_CONTEXT_NAME = 'input-context-forearm-form-v1.json'
FOREARM_CONTEXT_SHA = '4274c8761fe03b1a85436168fc1eeaf8db211bc7a8a2e16eb756e629c7e7ae45'
FOREARM_CONTEXT_ID = 'b1-forearm-form-v13-product-v1'
FOREARM_PREDECESSOR_COMMIT = 'd09ef1f12efa752a33a65b0fadfdaaae7f3c1d95'
FOREARM_FIXTURES = 'fixtures/pre-forearm-form'
FOREARM_BASELINES_SHA = 'dbbf89ae3f64f38d24a4c840d8771ca4fdb155f016ba2490044f9b5b8ba780d3'
FOREARM_ASSET_PREFIX = 'assets/characters/mpfb-b1-v13/'
FOREARM_CHANGED = SHOULDER_CHANGED
FOREARM_NEW_CODE = ('crates/nvwa-cli/tests/forearm_form.rs',
                     'crates/nvwa-core/tests/forearm_form.rs',
                     'scripts/build-forearm-form-v13.py',
                     'scripts/render-forearm-form-review.py',
                     'scripts/test-forearm-form-v13.py')


def pre_body_reference_file(name):
    historical = HERE / BODY_REFERENCE_FIXTURES / name
    if historical.is_file():
        return historical
    before_hand = HERE / HAND_FIXTURES / name
    return before_hand if before_hand.is_file() else HERE.parents[1] / name


def has_body_reference_inputs(root):
    path = root / BODY_REFERENCE_ADDED
    return path.exists() or path.is_symlink()


def _body_reference_context(exp, previous):
    manifest_path = source_file(exp, f'{BODY_REFERENCE_FIXTURES}/manifest.json')
    baseline_raw = manifest_path.read_bytes()
    require(sha(baseline_raw) == BODY_REFERENCE_BASELINES_SHA,
            'body reference predecessor manifest identity mismatch')
    baseline = json.loads(baseline_raw)
    require(set(baseline) == {'schema_version', 'context', 'source_commit', 'files'}
            and baseline['schema_version'] == 1
            and baseline['context'] == previous[0]
            and baseline['source_commit'] == 'ba9883ed4e510ec612569a0796732e25d888a6d4'
            and set(baseline['files']) == set(BODY_REFERENCE_CHANGED),
            'body reference predecessor identity mismatch')
    for name, item in baseline['files'].items():
        path = source_file(exp, item['fixture'])
        require({'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name]
                and item['fixture'] == f'{BODY_REFERENCE_FIXTURES}/{name}'
                and path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'body reference predecessor bytes mismatch: ' + name)
    fixture_root = exp / BODY_REFERENCE_FIXTURES
    fixture_paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in fixture_paths)
            and {p.relative_to(fixture_root).as_posix() for p in fixture_paths if p.is_file()}
                == {'manifest.json'} | set(BODY_REFERENCE_CHANGED),
            'body reference predecessor fixture inventory mismatch')
    raw = source_file(exp, BODY_REFERENCE_CONTEXT_NAME).read_bytes()
    require(sha(raw) == BODY_REFERENCE_CONTEXT_SHA,
            'body reference source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'files'}
            and value['schema_version'] == 1
            and value['context'] == BODY_REFERENCE_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and set(value['files']) == set(BODY_REFERENCE_CHANGED) | {BODY_REFERENCE_ADDED},
            'body reference source context exact delta required')
    require(all(name in previous[1] and value['files'][name] != previous[1][name]
                for name in BODY_REFERENCE_CHANGED)
            and BODY_REFERENCE_ADDED not in previous[1],
            'body reference source context predecessor mismatch')
    files = dict(previous[1]); files.update(value['files'])
    require(len(files) == 525, 'body reference complete source union required')
    return value['context'], files


def has_arm_inputs(root):
    path = root / ARM_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def has_hand_inputs(root):
    path = root / HAND_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def has_shoulder_inputs(root):
    path = root / SHOULDER_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def _shoulder_context(exp, previous):
    """Admit one exact v12 successor while keeping all v11 historical bytes pinned."""
    require(previous[0] == HAND_CONTEXT_ID and len(previous[1]) == 661,
            'shoulder predecessor must be exact hand context')
    raw = source_file(exp, f'{SHOULDER_FIXTURES}/manifest.json').read_bytes()
    require(sha(raw) == SHOULDER_BASELINES_SHA, 'shoulder predecessor manifest identity mismatch')
    baseline = json.loads(raw)
    require(set(baseline) == {'schema_version', 'context', 'source_commit', 'files'}
            and baseline['schema_version'] == 1 and baseline['context'] == previous[0]
            and baseline['source_commit'] == SHOULDER_PREDECESSOR_COMMIT
            and set(baseline['files']) == set(SHOULDER_CHANGED),
            'shoulder predecessor changed-file inventory mismatch')
    for name in SHOULDER_CHANGED:
        item = baseline['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{SHOULDER_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'shoulder predecessor pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'shoulder predecessor bytes mismatch: ' + name)
    fixture_root = exp / SHOULDER_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(SHOULDER_CHANGED),
            'shoulder predecessor fixture inventory mismatch')
    raw = source_file(exp, SHOULDER_CONTEXT_NAME).read_bytes()
    require(sha(raw) == SHOULDER_CONTEXT_SHA, 'shoulder context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == SHOULDER_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == SHOULDER_PREDECESSOR_COMMIT
            and len(files) == 158 and len(additions) == 145
            and sum(p.startswith(SHOULDER_ASSET_PREFIX) for p in additions) == 140
            and additions == {p for p in additions if p.startswith(SHOULDER_ASSET_PREFIX)}
                             | set(SHOULDER_NEW_CODE)
            and {p for p in previous[1] if p in files} == set(SHOULDER_CHANGED)
            and all(files[p] != previous[1][p] for p in SHOULDER_CHANGED),
            'shoulder exact successor delta required')
    result = dict(previous[1]); result.update(files)
    require(len(result) == 806, 'shoulder complete source union required')
    return value['context'], result


def has_forearm_inputs(root):
    path = root / FOREARM_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def _forearm_context(exp, previous):
    """Admit one exact v13 successor while keeping all v12 historical bytes pinned."""
    require(previous[0] == SHOULDER_CONTEXT_ID and len(previous[1]) == 806,
            'forearm predecessor must be exact shoulder context')
    raw = source_file(exp, f'{FOREARM_FIXTURES}/manifest.json').read_bytes()
    require(sha(raw) == FOREARM_BASELINES_SHA, 'forearm predecessor manifest identity mismatch')
    baseline = json.loads(raw)
    require(set(baseline) == {'schema_version', 'context', 'source_commit', 'files'}
            and baseline['schema_version'] == 1 and baseline['context'] == previous[0]
            and baseline['source_commit'] == FOREARM_PREDECESSOR_COMMIT
            and set(baseline['files']) == set(FOREARM_CHANGED),
            'forearm predecessor changed-file inventory mismatch')
    for name in FOREARM_CHANGED:
        item = baseline['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{FOREARM_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'forearm predecessor pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'forearm predecessor bytes mismatch: ' + name)
    fixture_root = exp / FOREARM_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(FOREARM_CHANGED),
            'forearm predecessor fixture inventory mismatch')
    raw = source_file(exp, FOREARM_CONTEXT_NAME).read_bytes()
    require(sha(raw) == FOREARM_CONTEXT_SHA, 'forearm context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == FOREARM_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == FOREARM_PREDECESSOR_COMMIT
            and len(files) == 167 and len(additions) == 154
            and sum(p.startswith(FOREARM_ASSET_PREFIX) for p in additions) == 149
            and additions == {p for p in additions if p.startswith(FOREARM_ASSET_PREFIX)}
                             | set(FOREARM_NEW_CODE)
            and {p for p in previous[1] if p in files} == set(FOREARM_CHANGED)
            and all(files[p] != previous[1][p] for p in FOREARM_CHANGED),
            'forearm exact successor delta required')
    result = dict(previous[1]); result.update(files)
    require(len(result) == 960, 'forearm complete source union required')
    return value['context'], result


def _hand_context(exp, previous):
    """Admit one exact hand successor while preserving body-reference history."""
    require(previous[0] == BODY_REFERENCE_CONTEXT_ID and len(previous[1]) == 525,
            'hand predecessor must be exact body reference')
    raw = source_file(exp, f'{HAND_FIXTURES}/manifest.json').read_bytes()
    require(sha(raw) == HAND_BASELINES_SHA, 'hand predecessor manifest identity mismatch')
    baseline = json.loads(raw)
    require(set(baseline) == {'schema_version', 'context', 'source_commit', 'files'}
            and baseline['schema_version'] == 1 and baseline['context'] == previous[0]
            and baseline['source_commit'] == HAND_PREDECESSOR_COMMIT
            and set(baseline['files']) == set(HAND_CHANGED),
            'hand predecessor complete changed-file inventory required')
    for name in HAND_CHANGED:
        item = baseline['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{HAND_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'hand predecessor pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'hand predecessor bytes mismatch: ' + name)
    fixture_root = exp / HAND_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(HAND_CHANGED),
            'hand predecessor fixture inventory mismatch')
    raw = source_file(exp, HAND_CONTEXT_NAME).read_bytes()
    require(sha(raw) == HAND_CONTEXT_SHA, 'hand context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == HAND_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == HAND_PREDECESSOR_COMMIT
            and len(files) == 149 and len(additions) == 136
            and sum(p.startswith(HAND_ASSET_PREFIX) for p in additions) == 131
            and additions == {p for p in additions if p.startswith(HAND_ASSET_PREFIX)} | set(HAND_NEW_CODE)
            and {p for p in previous[1] if p in files} == set(HAND_CHANGED)
            and all(files[p] != previous[1][p] for p in HAND_CHANGED),
            'hand exact successor delta required')
    result = dict(previous[1]); result.update(files)
    require(len(result) == 661, 'hand complete source union required')
    return value['context'], result


def _pre_arm_sources(exp, previous):
    manifest = source_file(exp, f'{ARM_FIXTURES}/manifest.json')
    raw = manifest.read_bytes()
    require(sha(raw) == ARM_BASELINES_SHA, 'arm predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == previous[0]
            and value['source_commit'] == ARM_PREDECESSOR_COMMIT
            and set(value['files']) == set(ARM_CHANGED),
            'arm predecessor complete inventory required')
    for name in ARM_CHANGED:
        item = value['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{ARM_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'arm predecessor historical pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'arm predecessor bytes mismatch: ' + name)
    fixture_root = exp / ARM_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(ARM_CHANGED),
            'arm predecessor fixture inventory mismatch')


def _arm_context(exp, previous):
    _pre_arm_sources(exp, previous)
    raw = source_file(exp, ARM_CONTEXT_NAME).read_bytes()
    require(sha(raw) == ARM_CONTEXT_SHA, 'arm source context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == ARM_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == ARM_PREDECESSOR_COMMIT
            and set(previous[1]) <= set(files)
            and len(files) == 524 and len(additions) == 123
            and additions == {p for p in additions if p.startswith(ARM_ASSET_PREFIX)} | set(ARM_NEW_CODE)
            and {p for p in previous[1] if files[p] != previous[1][p]} == set(ARM_CHANGED),
            'arm source context exact union required')
    return value['context'], files


def has_hip_inputs(root):
    path = root / HIP_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def _pre_hip_sources(exp, previous):
    manifest = source_file(exp, f'{HIP_FIXTURES}/manifest.json')
    raw = manifest.read_bytes()
    require(sha(raw) == HIP_BASELINES_SHA, 'hip predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == previous[0]
            and value['source_commit'] == HIP_PREDECESSOR_COMMIT
            and set(value['files']) == set(HIP_CHANGED),
            'hip predecessor complete inventory required')
    for name in HIP_CHANGED:
        item = value['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{HIP_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'hip predecessor historical pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'hip predecessor bytes mismatch: ' + name)
    fixture_root = exp / HIP_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(HIP_CHANGED),
            'hip predecessor fixture inventory mismatch')


def _hip_context(exp, previous):
    _pre_hip_sources(exp, previous)
    raw = source_file(exp, HIP_CONTEXT_NAME).read_bytes()
    require(sha(raw) == HIP_CONTEXT_SHA, 'hip source context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == HIP_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == HIP_PREDECESSOR_COMMIT
            and set(previous[1]) <= set(files)
            and len(files) == 401 and len(additions) == 109
            and additions == {p for p in additions if p.startswith(HIP_ASSET_PREFIX)} | set(HIP_NEW_CODE)
            and {p for p in previous[1] if files[p] != previous[1][p]} == set(HIP_CHANGED),
            'hip source context exact union required')
    return value['context'], files


def has_upper_inputs(root):
    path = root / UPPER_ASSET_PREFIX
    return path.exists() or path.is_symlink()


def _pre_upper_sources(exp, previous):
    manifest = source_file(exp, f'{UPPER_FIXTURES}/manifest.json')
    raw = manifest.read_bytes()
    require(sha(raw) == UPPER_BASELINES_SHA, 'upper predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == previous[0]
            and value['source_commit'] == UPPER_PREDECESSOR_COMMIT
            and set(value['files']) == set(UPPER_CHANGED),
            'upper predecessor complete inventory required')
    for name in UPPER_CHANGED:
        item = value['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{UPPER_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'upper predecessor historical pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'upper predecessor bytes mismatch: ' + name)
    fixture_root = exp / UPPER_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(UPPER_CHANGED),
            'upper predecessor fixture inventory mismatch')


def _upper_context(exp, previous):
    _pre_upper_sources(exp, previous)
    path = source_file(exp, UPPER_CONTEXT_NAME)
    raw = path.read_bytes()
    require(sha(raw) == UPPER_CONTEXT_SHA, 'upper source context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == UPPER_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == UPPER_PREDECESSOR_COMMIT
            and set(previous[1]) <= set(files)
            and len(files) == 292 and len(additions) == 98
            and additions == {p for p in additions if p.startswith(UPPER_ASSET_PREFIX)} | set(UPPER_NEW_CODE)
            and {p for p in previous[1] if files[p] != previous[1][p]} == set(UPPER_CHANGED),
            'upper source context exact union required')
    return value['context'], files


def _pre_leg_sources(exp, previous):
    manifest = source_file(exp, f'{LEG_FIXTURES}/manifest.json')
    raw = manifest.read_bytes()
    require(sha(raw) == LEG_BASELINES_SHA, 'leg predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == previous[0]
            and value['source_commit'] == LEG_PREDECESSOR_COMMIT
            and set(value['files']) == set(LEG_CHANGED),
            'leg predecessor complete inventory required')
    for name in LEG_CHANGED:
        item = value['files'][name]
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == f'{LEG_FIXTURES}/{name}'
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == previous[1][name],
                'leg predecessor historical pin mismatch: ' + name)
        path = source_file(exp, item['fixture'])
        require(path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'],
                'leg predecessor bytes mismatch: ' + name)
    fixture_root = exp / LEG_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(fixture_root).as_posix() for p in paths if p.is_file()}
                == {'manifest.json'} | set(LEG_CHANGED),
            'leg predecessor fixture inventory mismatch')


def _leg_context(exp, previous):
    _pre_leg_sources(exp, previous)
    manifest = source_file(exp, LEG_CONTEXT_NAME)
    raw = manifest.read_bytes()
    require(sha(raw) == LEG_CONTEXT_SHA, 'leg source context manifest identity mismatch')
    value = json.loads(raw)
    files = value['files']
    additions = set(files) - set(previous[1])
    require(set(value) == {'schema_version', 'context', 'predecessor',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == LEG_CONTEXT_ID
            and value['predecessor'] == previous[0]
            and value['predecessor_commit'] == LEG_PREDECESSOR_COMMIT
            and set(previous[1]) <= set(files)
            and len(files) == 194 and len(additions) == 82
            and additions == {p for p in additions if p.startswith(LEG_ASSET_PREFIX)} | set(LEG_NEW_CODE)
            and {p for p in previous[1] if files[p] != previous[1][p]} == set(LEG_CHANGED),
            'leg source context exact union required')
    return value['context'], files


def check_source_context(root, pins, historical_only=False):
    """Authenticate one complete source context; never mix baseline/current files."""
    contexts = current_source_contexts(pins)
    actual = {}
    for relative in pins['files']:
        path = root
        for part in Path(relative).parts:
            path = path / part
            require(not path.is_symlink(), 'source input symlink: ' + relative)
        require(path.is_file(), 'source input missing: ' + relative)
        actual[relative] = file_sha(path)
    reference_motion = has_reference_motion_inputs(root)
    waist = has_waist_inputs(root)
    if has_arm_inputs(root):
        require(not historical_only, 'source input context mismatch: arm source is not historical')
        cpu = _cpu_context(HERE, _motion_query_source_context(_running_source_context(pins, contexts))[1])
        leg = _leg_context(HERE, _combined_context(HERE, cpu))
        upper = _upper_context(HERE, leg)
        hip = _hip_context(HERE, upper)
        arm = _arm_context(HERE, hip)
        body_reference = has_body_reference_inputs(root)
        body = _body_reference_context(HERE, arm) if body_reference else arm
        hand = has_hand_inputs(root)
        shoulder = has_shoulder_inputs(root)
        forearm = has_forearm_inputs(root)
        context, expected = _forearm_context(HERE, _shoulder_context(HERE, _hand_context(HERE, body))) if forearm else _shoulder_context(HERE, _hand_context(HERE, body)) if shoulder else _hand_context(HERE, body) if hand else body
        asset_root = root / ARM_ASSET_PREFIX
        paths = list(asset_root.rglob('*'))
        require(not asset_root.is_symlink()
                and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                    == {p for p in expected if p.startswith(ARM_ASSET_PREFIX)},
                'arm source asset inventory mismatch')
        if hand:
            asset_root = root / HAND_ASSET_PREFIX
            paths = list(asset_root.rglob('*'))
            require(not asset_root.is_symlink()
                    and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                    and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                        == {p for p in expected if p.startswith(HAND_ASSET_PREFIX)},
                    'hand source asset inventory mismatch')
        if shoulder:
            asset_root = root / SHOULDER_ASSET_PREFIX
            paths = list(asset_root.rglob('*'))
            require(not asset_root.is_symlink()
                    and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                    and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                        == {p for p in expected if p.startswith(SHOULDER_ASSET_PREFIX)},
                    'shoulder source asset inventory mismatch')
        if forearm:
            asset_root = root / FOREARM_ASSET_PREFIX
            paths = list(asset_root.rglob('*'))
            require(not asset_root.is_symlink()
                    and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                    and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                        == {p for p in expected if p.startswith(FOREARM_ASSET_PREFIX)},
                    'forearm source asset inventory mismatch')
        actual = {}
        for relative, item in expected.items():
            path = source_file(root, relative)
            require(path.stat().st_size == item['bytes'],
                    ('forearm' if forearm else 'shoulder' if shoulder else 'hand' if hand else 'body reference' if body_reference else 'arm')
                    + ' source context byte count mismatch: ' + relative)
            actual[relative] = file_sha(path)
        require(actual == {name: item['sha256'] for name, item in expected.items()},
                'source input context mismatch: exact '
                + ('forearm' if forearm else 'shoulder' if shoulder else 'hand' if hand else 'body reference' if body_reference else 'arm') + ' source required')
    elif has_hip_inputs(root):
        require(not historical_only, 'source input context mismatch: hip source is not historical')
        cpu = _cpu_context(HERE, _motion_query_source_context(_running_source_context(pins, contexts))[1])
        leg = _leg_context(HERE, _combined_context(HERE, cpu))
        upper = _upper_context(HERE, leg)
        context, expected = _hip_context(HERE, upper)
        asset_root = root / HIP_ASSET_PREFIX
        paths = list(asset_root.rglob('*'))
        require(not asset_root.is_symlink()
                and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                    == {p for p in expected if p.startswith(HIP_ASSET_PREFIX)},
                'hip source asset inventory mismatch')
        actual = {}
        for relative, item in expected.items():
            path = source_file(root, relative)
            require(path.stat().st_size == item['bytes'],
                    'hip source context byte count mismatch: ' + relative)
            actual[relative] = file_sha(path)
        require(actual == {name: item['sha256'] for name, item in expected.items()},
                'source input context mismatch: exact hip source required')
    elif has_upper_inputs(root):
        require(not historical_only, 'source input context mismatch: upper source is not historical')
        cpu = _cpu_context(HERE, _motion_query_source_context(_running_source_context(pins, contexts))[1])
        leg = _leg_context(HERE, _combined_context(HERE, cpu))
        context, expected = _upper_context(HERE, leg)
        asset_root = root / UPPER_ASSET_PREFIX
        paths = list(asset_root.rglob('*'))
        require(not asset_root.is_symlink()
                and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
                and {p.relative_to(root).as_posix() for p in paths if p.is_file()}
                    == {p for p in expected if p.startswith(UPPER_ASSET_PREFIX)},
                'upper source asset inventory mismatch')
        actual = {}
        for relative, item in expected.items():
            path = source_file(root, relative)
            require(path.stat().st_size == item['bytes'],
                    'upper source context byte count mismatch: ' + relative)
            actual[relative] = file_sha(path)
        require(actual == {name: item['sha256'] for name, item in expected.items()},
                'source input context mismatch: exact upper source required')
    elif has_leg_inputs(root):
        require(not historical_only, 'source input context mismatch: leg source is not historical')
        cpu = _cpu_context(HERE, _motion_query_source_context(_running_source_context(pins, contexts))[1])
        context, expected = _leg_context(HERE, _combined_context(HERE, cpu))
        asset_root = root / LEG_ASSET_PREFIX
        asset_paths = list(asset_root.rglob('*'))
        require(not asset_root.is_symlink()
                and all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in asset_paths)
                and {p.relative_to(root).as_posix() for p in asset_paths if p.is_file()}
                    == {p for p in expected if p.startswith(LEG_ASSET_PREFIX)},
                'leg source asset inventory mismatch')
        actual = {}
        for relative, item in expected.items():
            path = source_file(root, relative)
            require(path.stat().st_size == item['bytes'],
                    'leg source context byte count mismatch: ' + relative)
            actual[relative] = file_sha(path)
        require(actual == {name: item['sha256'] for name, item in expected.items()},
                'source input context mismatch: exact leg source required')
    elif reference_motion or waist or has_cpu_inputs(root):
        label = ('combined' if waist and reference_motion else 'WAIST' if waist
                 else 'reference motion' if reference_motion else 'CPU')
        require(not historical_only, 'source input context mismatch: ' + label + ' source is not historical')
        cpu = _cpu_context(HERE, _motion_query_source_context(_running_source_context(pins, contexts))[1])
        if waist and reference_motion:
            context, expected = _combined_context(HERE, cpu)
        elif waist:
            context, expected = _waist_context(HERE, cpu[1])
        elif reference_motion:
            context, expected = _reference_motion_context(HERE, cpu)
            check_waist_preexisting(root, _pre_waist_sources(HERE, cpu[1]))
        else:
            context, expected = cpu
            check_waist_preexisting(root, _pre_waist_sources(HERE, cpu[1]))
        regular = waist_regular_file if waist else source_file if reference_motion else cpu_regular_file
        actual = {}
        for relative, item in expected.items():
            path = regular(root, relative)
            require(path.stat().st_size == item['bytes'], label + ' source context byte count mismatch: ' + relative)
            actual[relative] = file_sha(path)
        expected_hashes = {n: i['sha256'] for n, i in expected.items()}
        if reference_motion:
            require(actual == expected_hashes, 'source input context mismatch: exact ' + label + ' source required')
        else:
            context = select_source_context(actual, [(context, expected_hashes)])
    elif not historical_only and not any(actual == expected for _, expected in contexts):
        running = _running_source_context(pins, contexts)
        if all(running[1][name]['sha256'] == digest for name, digest in actual.items()):
            check_no_motion_query_additions(root)
            context, expected = running
        else:
            context, expected = _motion_query_source_context(running)
            check_cpu_preexisting(root, _pre_cpu_sources(HERE, expected))
        for relative, item in expected.items():
            path = source_file(root, relative)
            require(path.stat().st_size == item['bytes'], 'source input context mismatch: byte count: ' + relative)
            actual[relative] = file_sha(path)
        context = select_source_context(actual, [(context, {n: i['sha256'] for n, i in expected.items()})])
    else:
        context = select_source_context(actual, contexts, historical_only)
        check_no_motion_query_additions(root)
        # Five paths are new source. Four additions to this admission set already
        # existed historically and must match one authenticated predecessor.
        require(not any((root / n).exists() or (root / n).is_symlink()
                        for n in set(RUNNING_ADDITIONS) - set(RUNNING_PREEXISTING)),
                'source input context mismatch: running additions in historical source')
        present = [n for n in RUNNING_PREEXISTING if (root / n).exists() or (root / n).is_symlink()]
        if present:
            _pre_running_sources(pins, contexts)
            variants = json.loads((HERE / 'fixtures/pre-running/manifest.json').read_bytes())['historical_outside'][context]
            outside = {}
            for relative in present:
                path = root
                for part in Path(relative).parts:
                    path = path / part
                    require(not path.is_symlink(), 'source input context mismatch: historical outside symlink: ' + relative)
                require(path.is_file(), 'source input context mismatch: historical outside missing: ' + relative)
                outside[relative] = {'bytes': path.stat().st_size, 'sha256': file_sha(path)}
            require(any(all(outside[n] == {k: variant['files'][n][k] for k in ('bytes', 'sha256')}
                            for n in present) for variant in variants),
                    'source input context mismatch: historical outside source mixture')
    bridge = json.loads((HERE / 'input-context-v1.json').read_text())
    check_unchanged_sections((root / RUNTIME).read_text(), bridge)
    return {'id': context, 'files': actual, 'current_rust_execution': 'NOT-RUN',
            'execution_source': 'immutable baseline581 archive only'}


def check_unchanged_sections(raw, bridge):
    """Source equality witnesses, not a substitute for executing numeric gates."""
    for section in bridge['unchanged_runtime_sections']:
        require(raw.count(section['start']) == 1, 'numeric section start is not unique: ' + section['id'])
        start = raw.index(section['start'])
        end = raw.index(section['end'], start + len(section['start']))
        require(sha(raw[start:end].encode()) == section['sha256'],
                'unchanged numeric section mismatch: ' + section['id'])


def check_inputs(root):
    pins_path = HERE / 'pins.json'
    require(pins_path.is_file() and not pins_path.is_symlink() and file_sha(pins_path) == PINS_SHA,
            'immutable baseline pins identity mismatch')
    pins = json.loads((HERE / 'pins.json').read_text())
    require(pins['baseline_commit'] == BASELINE and pins['files'][RUNTIME] == RUNTIME_SHA, 'immutable baseline pin mismatch')
    context = check_source_context(root, pins)
    raw = (root / RUNTIME).read_text()
    inject(raw)
    for fault in FAULTS:
        mutated = mutate(raw, fault)
        require(mutated != raw and raw.count(fault['before']) == 1, 'mutation is not exact/active')
    plan = json.loads((HERE / 'cases.json').read_text())
    frozen = json.loads((root / plan['frozen_reference_manifest']['path']).read_text())
    expected = [{k: row[k] for k in ('case_id', 'recipe_id', 'recipe', 'pose_id')} for row in frozen['cases']]
    require(plan['baseline_commit'] == BASELINE, 'case baseline mismatch')
    require(plan['bounds'] == {'body_position_m': 1e-3, 'garment_position_m': 3e-3,
                             'bone_matrix': 1e-4, 'joint_head_m': 1e-5, 'full_positive_lbs_m': 1e-5},
            'original numeric bounds changed')
    require(plan['zero_extension'] == ['head_width', 'nose_width', 'mouth_width', 'chin_width', 'neck_width', 'hip_width'],
            'zero extension fields changed')
    require(plan['cases'] == expected and len(expected) == 40, 'original40 case/recipe/pose drift')
    require(len({row['recipe_id'] for row in expected}) == 8 and len({row['pose_id'] for row in expected}) == 5, 'original8x5 coverage mismatch')
    for key in ('frozen_reference_manifest', 'frozen_poses'):
        p = plan[key]
        require(file_sha(root / p['path']) == p['sha256'], 'frozen identity mismatch')
    for name in PACKAGE:
        require((HERE / name).is_file() and not (HERE / name).is_symlink(), 'control package file missing/unsafe: ' + name)
    return dict(pins, checked_input_context=context)


def closure(root):
    return {str(p.relative_to(root)): file_sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def command(test):
    return ['cargo', 'test', '--workspace', '--lib', '--locked', '--offline', test,
            '--', '--exact', '--test-threads=1', '--nocapture']


def run(args):
    root = args.source_root.resolve(strict=True)
    pins = check_inputs(root)
    if args.check_inputs:
        return {'status': 'inputs_verified_only', 'baseline': BASELINE, 'files': pins['files'],
                'checked_input_context': pins['checked_input_context'],
                'rust_execution': 'NOT-RUN', 'faults': [f['id'] for f in FAULTS]}
    require(args.out is not None and args.out.is_absolute(), '--out must be an absolute fresh path')
    out = args.out
    require(not out.is_symlink(), 'output symlink rejected')
    out.mkdir(parents=True, exist_ok=False)
    require(out.resolve() == out, 'output must use its canonical absolute path')
    receipt = {'schema_version': 1, 'status': 'running', 'baseline_commit': BASELINE,
               'checked_input_context': pins['checked_input_context'],
               'production_runtime_sha256': RUNTIME_SHA, 'commands': [], 'mutations': [],
               'scope': 'CPU real production only; no GPU/UI; no original full-reference oracle rerun claim',
               'control_hashes': {name: file_sha(HERE / name) for name in PACKAGE}}
    write_json(out / 'receipt.json', receipt)
    source = out / 'source'
    target = out / 'target'
    logs = out / 'logs'
    measures = out / 'measurements'
    logs.mkdir()
    measures.mkdir()
    original = None
    production = source / RUNTIME
    environment = os.environ.copy()
    environment.update({'CARGO_TARGET_DIR': str(target), 'CARGO_BUILD_JOBS': '1',
                        'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
                        'CARGO_NET_OFFLINE': 'true', 'CARGO_TERM_COLOR': 'never', 'NVWA_ADMISSION72_RECEIPTS': str(measures)})
    receipt['environment_overrides'] = {key: environment[key] for key in (
        'CARGO_TARGET_DIR', 'CARGO_BUILD_JOBS', 'CARGO_PROFILE_DEV_DEBUG', 'CARGO_PROFILE_TEST_DEBUG',
        'CARGO_NET_OFFLINE', 'CARGO_TERM_COLOR', 'NVWA_ADMISSION72_RECEIPTS')}
    receipt['target_reuse'] = 'new run-owned target; no shared/failed cache edited or reused'

    def execute(label, argv, cwd, semantic_test=None, fault=None):
        log = logs / (label + '.log')
        started = time.monotonic()
        entry = {'label': label, 'argv': argv, 'cwd': str(cwd), 'log': str(log.relative_to(out))}
        receipt['commands'].append(entry)
        write_json(out / 'receipt.json', receipt)
        with log.open('xb') as stream:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=args.command_timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                entry.update({'exit_code': process.returncode, 'timed_out': True,
                              'seconds': time.monotonic() - started, 'log_sha256': file_sha(log)})
                write_json(out / 'receipt.json', receipt)
                raise ValueError(label + ': bounded command timeout, not evidence')
        entry.update({'exit_code': code, 'seconds': time.monotonic() - started, 'log_sha256': file_sha(log)})
        write_json(out / 'receipt.json', receipt)
        if semantic_test is None:
            require(code == 0, label + ': actual command failed')
        else:
            verdict(code, log.read_text(errors='replace'), semantic_test, fault)
            entry['intended_semantics_verified'] = True
            write_json(out / 'receipt.json', receipt)
        return entry

    try:
        for name in PACKAGE:
            shutil.copy2(HERE / name, out / name)
            require(file_sha(out / name) == receipt['control_hashes'][name], 'control package changed during copy')
        execute('checkout-head', ['git', 'rev-parse', 'HEAD'], root)
        receipt['source_checkout_head'] = (logs / 'checkout-head.log').read_text().strip()
        require(re.fullmatch(r'[0-9a-f]{40}', receipt['source_checkout_head']) is not None, 'invalid checkout HEAD')
        archive = out / 'baseline.tar'
        execute('source-archive', ['git', 'archive', '--format=tar', '--output=' + str(archive), BASELINE], root)
        receipt['source_archive_sha256'] = file_sha(archive)
        source.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter='data')
        initial = closure(source)
        write_json(out / 'source-closure.json', initial)
        for relative, expected in pins['files'].items():
            require(initial.get(relative) == expected, 'archive is not selected baseline: ' + relative)
        receipt['execution_input_context'] = check_source_context(source, pins, historical_only=True)
        original = production.read_bytes()
        require(sha(original) == RUNTIME_SHA, 'wrong production baseline')
        execute('pristine-endpoint-green', command(ENDPOINT), source, ENDPOINT)
        scratch_controls = source / 'experiments/72-b1-admission-controls'
        scratch_controls.mkdir(parents=True, exist_ok=False)
        for name in PACKAGE:
            shutil.copy2(out / name, scratch_controls / name)
        shutil.copy2(out / 'compatibility.rs', source / 'crates/nvwa-runtime/src/admission72_tests.rs')
        injected = inject(original.decode()).encode()
        production.write_bytes(injected)
        receipt['cfg_test_injected_runtime_sha256'] = sha(injected)
        write_json(out / 'faults.json', list(FAULTS))
        execute('zero-green', command(ZERO), source, ZERO)
        zero = json.loads((measures / 'zero.json').read_text())
        require(zero['passed'] is True and len(zero['comparisons']) == 2, 'missing complete zero proof')
        require(zero['comparisons'][1]['parts'][0]['uv0_present'] is True, 'actual body UV0 gate absent')
        execute('original40-green', command(FORTY), source, FORTY)
        plan = json.loads((HERE / 'cases.json').read_text())
        for case in plan['cases']:
            row = json.loads((measures / (case['case_id'] + '.json')).read_text())
            require(row['case'] == case and row['bones'] == 53 and row['bone_fields'] == 11, 'incomplete original40 proof')
        receipt['original40_cases_verified'] = len(plan['cases'])
        for fault in FAULTS:
            mutated = mutate(injected.decode(), fault).encode()
            record = {'id': fault['id'], 'before_sha256': sha(injected),
                      'mutant_sha256': sha(mutated), 'semantic_red': False, 'restored_green': False}
            receipt['mutations'].append(record)
            deferred = None
            try:
                production.write_bytes(mutated)
                execute(fault['id'] + '-red', command(ENDPOINT), source, ENDPOINT, fault)
                record['semantic_red'] = True
            except Exception as error:
                deferred = error
                record['red_error'] = str(error)
            finally:
                production.write_bytes(injected)
                record['restored_sha256'] = file_sha(production)
                write_json(out / 'receipt.json', receipt)
            require(production.read_bytes() == injected, 'mapping restoration failed')
            execute(fault['id'] + '-restored-green', command(ENDPOINT), source, ENDPOINT)
            record['restored_green'] = True
            write_json(out / 'receipt.json', receipt)
            if deferred is not None:
                raise deferred
        production.write_bytes(original)
        execute('pristine-final-endpoint-green', command(ENDPOINT), source, ENDPOINT)
        final = {relative: file_sha(source / relative) for relative in initial}
        require(final == initial, 'baseline tracked-source changed; no pass')
        write_json(out / 'source-closure-final.json', final)
        receipt.update({'status': 'passed', 'exact_production_restored': True,
                        'final_runtime_sha256': file_sha(production), 'measurements': closure(measures)})
    except Exception as error:
        receipt.update({'status': 'failed', 'error': str(error)})
        write_json(out / 'failure.json', {'status': 'failed', 'error': str(error),
                                        'remaining_checks': 'NOT-RUN after first failed gate'})
        raise
    finally:
        if original is not None:
            production.write_bytes(original)
            receipt['finally_restored_runtime_sha256'] = file_sha(production)
            receipt['exact_production_restored'] = production.read_bytes() == original
        write_json(out / 'receipt.json', receipt)
        exported = {p.name: file_sha(p) for p in out.iterdir() if p.is_file() and p.name != 'export-manifest.json'}
        exported.update({str(p.relative_to(out)): file_sha(p) for p in logs.iterdir() if p.is_file()})
        exported.update({str(p.relative_to(out)): file_sha(p) for p in measures.iterdir() if p.is_file()})
        write_json(out / 'export-manifest.json', exported)
    return {'status': receipt['status'], 'out': str(out), 'original40': receipt['original40_cases_verified'],
            'mutations': len(receipt['mutations']), 'rust_execution': 'actual CPU tests; no graphics'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[1])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--command-timeout', type=int, default=3600)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-inputs', action='store_true')
    modes.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(1 <= args.command_timeout <= 7200, 'timeout must be bounded 1..7200 seconds')
    print(json.dumps(run(args), indent=2))


if __name__ == '__main__':
    main()
