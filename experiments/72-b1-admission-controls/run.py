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
    if not historical_only and not any(actual == expected for _, expected in contexts):
        running = _running_source_context(pins, contexts)
        if all(running[1][name]['sha256'] == digest for name, digest in actual.items()):
            check_no_motion_query_additions(root)
            context, expected = running
        else:
            context, expected = _motion_query_source_context(running)
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
