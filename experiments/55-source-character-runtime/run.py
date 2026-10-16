#!/usr/bin/env python3
"""Offline, fail-closed Path B preparation. This is not a human-data parser."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import stat

PIN = '286d33124648501535655a0de811cef55152b9fd'
ROOT = Path(__file__).resolve().parent
INVENTORY_SHA256 = '3c0d8c4d2aac9c398d3b7eb75272ced08f6babafd6bd4577f895e50f10b661ab'
SHA = re.compile(r'^[0-9a-f]{64}$')

class Blocked(Exception):
    pass

def require(condition, reason):
    if not condition:
        raise Blocked(reason)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree_digest(root):
    """Hash all regular source files, excluding only .git and target trees."""
    items = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in ('.git', 'target') for part in rel.parts):
            continue
        require(not path.is_symlink(), 'candidate symlinks are not accepted')
        if path.is_file():
            items.append(rel.as_posix().encode() + b'\0' + digest(path).encode() + b'\n')
    require(items, 'candidate source tree is empty')
    return hashlib.sha256(b''.join(items)).hexdigest()

def verify_inventory(root, entries, local_sha256):
    """Verify immutable source bytes against upstream Git identities and local SHA256."""
    require(root.is_dir() and not root.is_symlink(), 'approved candidate source unavailable or symlinked')
    expected = {}
    for item in entries:
        rel = item['path']
        path = Path(rel)
        require(path.parts and path.as_posix() == rel and not path.is_absolute()
                and '..' not in path.parts and '.' not in path.parts,
                'upstream inventory path is unsafe')
        require(rel not in expected, 'duplicate upstream inventory path')
        require(isinstance(item['size'], int) and 0 <= item['size'] <= 1000000,
                'upstream inventory size out of bounds')
        require(re.fullmatch(r'[0-9a-f]{40}', item['git_blob_sha1']), 'invalid upstream Git blob identity')
        expected[rel] = item
    require(set(local_sha256) == set(expected), 'approved local SHA256 file allowlist mismatch')
    observed = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            path = Path(directory) / name
            require(stat.S_ISDIR(path.lstat().st_mode), 'candidate nonregular directory or symlink')
            rel = path.relative_to(root).as_posix()
            require(any(p.startswith(rel + '/') for p in expected), 'unexpected candidate directory: ' + rel)
        for name in files:
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            require(rel in expected, 'unexpected candidate file: ' + rel)
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode), 'candidate nonregular file or symlink: ' + rel)
            item = expected[rel]
            require(info.st_size == item['size'], 'candidate file size mismatch: ' + rel)
            data = path.read_bytes()
            require(len(data) == item['size'], 'candidate file size changed: ' + rel)
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(blob == item['git_blob_sha1'], 'candidate upstream Git blob mismatch: ' + rel)
            require(SHA.fullmatch(local_sha256[rel] or '') and
                    hashlib.sha256(data).hexdigest() == local_sha256[rel],
                    'candidate local SHA256 mismatch: ' + rel)
            observed.add(rel)
    require(observed == set(expected), 'required candidate source files missing')

def read_pinned_json(path, expected, kind):
    require(SHA.fullmatch(expected or ''), kind + ' expected SHA-256 is required')
    require(path.is_file(), kind + ' unavailable')
    require(digest(path) == expected, kind + ' SHA-256 mismatch')
    value = json.loads(path.read_text())
    require(isinstance(value, dict), kind + ' must be a JSON object')
    return value

def run_command(command, log):
    env = os.environ.copy()
    env.update(CARGO_NET_OFFLINE='true', CARGO_TARGET_DIR=str(ROOT / 'target'))
    with log.open('x') as stream:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=240)
    return result.returncode

def validate(args, receipt):
    approval = read_pinned_json(args.approval, args.approval_sha256, 'approval manifest')
    require(approval.get('schema_version') == 1, 'unsupported approval schema')
    require(approval.get('route_id') == 'source-runtime', 'approval route mismatch')
    require(approval.get('local_source_read_approved') is True, 'source access not approved')
    require(approval.get('candidate_commit') == PIN, 'approval candidate commit mismatch')
    require(approval.get('candidate_path') == str(args.candidate.resolve()),
            'approval candidate path mismatch')
    require(approval.get('sample_manifest_sha256') == args.sample_sha256,
            'approval and requested sample digests differ')
    sample = read_pinned_json(args.sample, args.sample_sha256, 'approved sample manifest')
    receipt['source_input_manifest_sha256'] = args.sample_sha256
    require(sample.get('schema_version') == 1, 'unsupported sample schema')
    require(sample.get('sample_class') == 'makehuman-approved-sample',
            'actual candidate requires makehuman-approved-sample')
    require(sample.get('approved') is True, 'sample has no explicit approval')
    require(sample.get('reference_manifest_sha256') and
            SHA.fullmatch(sample['reference_manifest_sha256']), 'reference manifest digest missing')
    require(sample.get('basis') and sample.get('units') and sample.get('transforms'),
            'sample coordinate/basis/unit/transform identity missing')
    files = sample.get('files', [])
    required_roles = {'basemesh', 'vertex_groups', 'target', 'rig', 'weights', 'garment', 'reference'}
    require(sample.get('parameter_schema') == 'paired-local-targets-v1',
            'candidate parameter schema unsupported; real data adapter unavailable')
    require(required_roles.issubset({f.get('role') for f in files}), 'sample required data roles missing')
    require(len({f.get('path') for f in files}) == len(files), 'duplicate sample paths')
    sample_root = args.sample.resolve().parent
    for item in files:
        path = Path(item.get('path', ''))
        require(path.parts and not path.is_absolute() and '..' not in path.parts,
                'sample file path must stay within sample directory')
        absolute = sample_root / path
        require(absolute.resolve().is_relative_to(sample_root), 'sample symlink escapes sample directory')
        require(absolute.is_file(), 'approved sample file unavailable: ' + str(path))
        require(SHA.fullmatch(item.get('sha256', '')) and digest(absolute) == item['sha256'],
                'approved sample file digest mismatch: ' + str(path))
        require(item.get('license') and item.get('source_url'), 'sample provenance missing')
    cases = sample.get('cases', [])
    require(len(cases) >= 4 and len({c.get('case_id') for c in cases}) == len(cases),
            'need distinct neutral, body, face and combined cases')
    require({'neutral', 'body', 'face', 'combined'}.issubset({c.get('kind') for c in cases}),
            'required common cases missing')
    require(all(c.get('recipe') is not None for c in cases), 'case recipe missing')
    receipt['case_ids'] = [c['case_id'] for c in cases]
    require(args.candidate.is_dir(), 'approved candidate source unavailable')
    require(approval.get('upstream_inventory_sha256') == INVENTORY_SHA256,
            'approval upstream inventory digest mismatch')
    inventory = read_pinned_json(ROOT / 'upstream-inventory.json', INVENTORY_SHA256,
                                 'fixed upstream inventory')
    require(inventory.get('candidate_commit') == PIN, 'upstream inventory commit mismatch')
    verify_inventory(args.candidate, inventory['files'], approval.get('candidate_files_sha256', {}))
    receipt['upstream_inventory_sha256'] = INVENTORY_SHA256
    receipt['candidate_tree_sha256'] = tree_digest(args.candidate)
    receipt['candidate_source_validated'] = True
    return approval

def output_paths(args):
    return [args.receipt, args.receipt.with_suffix('.metadata.log'), args.receipt.with_suffix('.build.log')]

def validate_outputs(args):
    paths = output_paths(args)
    resolved = [p.resolve() for p in paths]
    require(len(set(resolved)) == len(paths), 'output paths collide')
    inputs = {args.approval.resolve(), args.sample.resolve()}
    candidate = args.candidate.resolve()
    for path, target in zip(paths, resolved):
        require(target not in inputs and not target.is_relative_to(candidate),
                'output path collides with protected input/source')
        require(not os.path.lexists(path), 'output already exists; refusing overwrite: ' + str(path))

def write_receipt(args, receipt):
    # Exclusive creation prevents overwriting any existing file, symlink or hardlink,
    # including aliases introduced after validation. Never open outputs with mode w.
    validate_outputs(args)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=['preflight', 'check-native', 'check-wasm', 'run-cli'], default='preflight')
    parser.add_argument('--approval', type=Path, default=ROOT / 'approved-inputs/approval.json')
    parser.add_argument('--approval-sha256', default='')
    parser.add_argument('--sample', type=Path, default=ROOT / 'approved-inputs/sample.json')
    parser.add_argument('--sample-sha256', default='')
    parser.add_argument('--candidate', type=Path, default=ROOT / 'approved-inputs/Humentity')
    parser.add_argument('--receipt', type=Path, default=ROOT / 'evidence/latest.json')
    args = parser.parse_args(argv)
    receipt = dict(schema_version=1, route_id='source-runtime', sample_class='makehuman-approved-sample',
                   case_id=None, status='not_run', action=args.action, candidate_commit=PIN,
                   actual_candidate_code_executed=False, candidate_source_validated=False,
                   native_graphical_executed=False, web_graphical_executed=False,
                   reference_pipeline_executed=False, actual_command=[], exit_code=2)
    code = 2
    try:
        validate_outputs(args)
    except (Blocked, OSError) as error:
        print('NOT-RUN: unsafe output: ' + str(error))
        return 2
    try:
        approval = validate(args, receipt)
        if args.action == 'run-cli':
            raise Blocked('actual Humentity CLI adapter is not implemented; no substitute execution')
        if args.action == 'preflight':
            receipt['preflight_passed'] = True
            receipt['reason'] = 'source identity/sample presence only; actual candidate adapter unsupported and NOT-RUN'
            receipt['exit_code'] = 0
            write_receipt(args, receipt)
            print('PREPARED: ' + receipt['reason'])
            return 0
        require(approval.get('offline_build_approved') is True, 'offline build not approved')
        derived = Path(approval.get('derived_path', ''))
        require(derived.is_absolute() and derived.is_dir() and not derived.is_symlink(),
                'approved derived manifest/lock/patch package unavailable')
        require(not derived.resolve().is_relative_to(args.candidate.resolve()),
                'derived build package must be separate from immutable upstream source')
        require(SHA.fullmatch(approval.get('derived_tree_sha256', '')) and
                tree_digest(derived) == approval['derived_tree_sha256'], 'derived package digest mismatch')
        require(all((derived / name).is_file() for name in ['Cargo.toml', 'Cargo.lock', 'patch.json']),
                'derived manifest/lock/patch receipt unavailable')
        patch = json.loads((derived / 'patch.json').read_text())
        require(patch.get('upstream_inventory_sha256') == INVENTORY_SHA256,
                'derived patch upstream identity mismatch')
        cargo = ['cargo', 'metadata', '--offline', '--locked', '--format-version', '1',
                 '--manifest-path', str(derived / 'Cargo.toml')]
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        log = args.receipt.with_suffix('.metadata.log')
        receipt['log_path'] = str(log)
        receipt['actual_command'] = cargo
        result = run_command(cargo, log)
        receipt['command_exit_code'] = result
        require(result == 0, 'offline candidate manifest preflight failed; see log')
        if args.action != 'preflight':
            target = 'wasm32-unknown-unknown' if args.action == 'check-wasm' else None
            if target:
                installed = subprocess.run(['rustup', 'target', 'list', '--installed'], capture_output=True,
                                           text=True, timeout=10)
                require(installed.returncode == 0 and target in installed.stdout.split(),
                        'Wasm target unavailable; runner will not install it')
            cargo = ['cargo', 'check', '--offline', '--locked', '--lib', '--jobs', '1',
                     '--manifest-path', str(derived / 'Cargo.toml')]
            if target:
                cargo += ['--target', target]
            receipt['actual_command'] = cargo
            log = args.receipt.with_suffix('.build.log')
            receipt['build_log_path'] = str(log)
            result = run_command(cargo, log)
            receipt['command_exit_code'] = result
            receipt['build_checked'] = result == 0
            require(result == 0, 'offline candidate build failed; see log')
        # Preparation/build success is deliberately not a character-case pass.
        receipt['preflight_passed'] = True
        receipt['reason'] = 'preflight/build only; character execution and comparison NOT-RUN'
        code = 0
    except (Blocked, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        receipt['reason'] = str(error)
    receipt['exit_code'] = code
    try:
        # Logs may now exist; only receipt itself is created exclusively here.
        require(not os.path.lexists(args.receipt), 'receipt already exists; refusing overwrite')
        require(args.receipt.resolve() not in {args.approval.resolve(), args.sample.resolve()} and
                not args.receipt.resolve().is_relative_to(args.candidate.resolve()), 'protected receipt path')
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open('x') as stream:
            stream.write(json.dumps(receipt, indent=2) + '\n')
    except (Blocked, OSError) as output_error:
        print('NOT-RUN: receipt refused: ' + str(output_error))
        return 2
    print(('PREPARED' if code == 0 else 'NOT-RUN') + ': ' + receipt['reason'])
    return code

if __name__ == '__main__':
    sys.exit(main())
