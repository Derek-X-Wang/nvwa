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
HERE = Path(__file__).resolve().parent
PACKAGE = ('run.py', 'test_controls.py', 'compatibility.rs', 'cases.json', 'pins.json', 'README.md', 'REVIEW.md', 'input-context-v1.json')
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


def check_source_context(root, pins, historical_only=False):
    """Authenticate one complete source context; never mix baseline/current files."""
    manifest = HERE / 'input-context-v1.json'
    require(manifest.is_file() and not manifest.is_symlink() and file_sha(manifest) == CONTEXT_SHA,
            'input context manifest identity mismatch')
    bridge = json.loads(manifest.read_text())
    require(bridge['schema_version'] == 1 and bridge['baseline_commit'] == BASELINE,
            'input context version/baseline mismatch')
    current = dict(pins['files'])
    current.update(bridge['overrides'])
    actual = {}
    for relative in pins['files']:
        path = root
        for part in Path(relative).parts:
            path = path / part
            require(not path.is_symlink(), 'source input symlink: ' + relative)
        require(path.is_file(), 'source input missing: ' + relative)
        actual[relative] = file_sha(path)
    if actual == pins['files']:
        context = 'baseline581'
    else:
        require(not historical_only and actual == current,
                'source input context mismatch: exact baseline581 or reviewed issue86 pair required')
        context = bridge['context']
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
    require(file_sha(HERE / 'pins.json') == PINS_SHA, 'immutable baseline pins identity mismatch')
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
