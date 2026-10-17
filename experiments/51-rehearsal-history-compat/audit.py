#!/usr/bin/env python3
"""Authenticate retained inputs and run unchanged historical48/49 CPU gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
MANIFEST_SHA256 = 'a94f9ddb9f9940873ef7979fc99d2e870ae3f11674ea9dac9425d91da366c780'
SOURCE_COMMIT = '50eae1979cac47c7eb53dada69f06b716436bf92'
SOURCE_TREE = '0bb87d9dc2ff324390de6e184852a87d513017fa'
E49 = 'experiments/49-runtime-pose-parity/'
COMMANDS = {
    'historical48': [E49+'historical48/audit.py'],
    'historical48-controls': [E49+'historical48/audit.py', '--check', 'controls'],
    'historical48-adapter-controls': [E49+'historical48/test_audit.py'],
    'offline-controls': [E49+'offline/test_evaluator.py'],
    'native-staging-controls': [E49+'probe/test_native_staging.py'],
    'web-staging-controls': [E49+'probe/test_web_staging.py'],
    'native-capture': [E49+'offline/compare.py', E49+'probe/results/native.json'],
    'native-visual-capture': [E49+'offline/compare.py', E49+'probe/results/native-visual.json'],
    'web-capture': [E49+'offline/compare.py', E49+'probe/results/web.json'],
    'native-failure': [E49+'verify_native_failure.py'],
    'attribution-measurement-controls': [E49+'attribution/diagnose_reproduction.py', '--self-test'],
    'attribution-measurement': [E49+'attribution/diagnose_reproduction.py'],
    'attribution-controls': [E49+'attribution/test_port.py'],
    'native-directions': [E49+'attribution/directions.py'],
    'web-directions': [E49+'attribution/directions.py', '--capture', 'web'],
}


class Rejected(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def decode(data):
    def invalid(value):
        raise Rejected('non-finite JSON: '+value)
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid)


def safe_path(relative):
    require(type(relative) is str and bool(relative) and '\\' not in relative,
            'unsafe relative path: '+str(relative))
    path = PurePosixPath(relative)
    require(not path.is_absolute() and path.as_posix() == relative and
            '..' not in path.parts and '.' not in path.parts,
            'unsafe relative path: '+relative)
    return path


def read(root, relative):
    path = root
    require(not root.is_symlink(), 'symlink root')
    for part in safe_path(relative).parts:
        path = path/part
        require(not path.is_symlink(), 'symlink input: '+relative)
    require(path.is_file(), 'missing input: '+relative)
    return path.read_bytes()


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}


def inventory(root, relative):
    """Walk only the two immutable historical trees and the source archive."""
    start = root/safe_path(relative)
    require(not root.is_symlink() and not start.is_symlink(), 'symlink inventory root')
    require(start.is_dir(), 'missing inventory root: '+relative)
    files = set()
    for directory, names, leaves in os.walk(start, followlinks=False):
        for name in names+leaves:
            path = Path(directory)/name
            require(not path.is_symlink(), 'symlink inventory input: '+path.relative_to(root).as_posix())
        for name in leaves:
            path = Path(directory)/name
            require(path.is_file(), 'nonregular inventory input')
            files.add(path.relative_to(root).as_posix())
    return files


def preflight(repo, material=HERE):
    repo, material = repo.absolute(), material.absolute()
    for boundary in (repo, material):
        for ancestor in (boundary, *boundary.parents):
            require(not ancestor.is_symlink(), 'symlink input root ancestor')
    raw = read(material, 'MANIFEST.json')
    manifest = decode(raw)
    # Validate paths before the digest so accidental broadening has a precise refusal.
    require(type(manifest.get('files')) is dict, 'missing file mapping')
    for relative, row in manifest['files'].items():
        safe_path(relative)
        require(type(row) is dict, 'invalid input identity')
        require(set(row) in ({'bytes', 'sha256', 'git_blob'},
                            {'bytes', 'sha256', 'git_blob', 'archive_path'}), 'invalid identity fields')
        if 'archive_path' in row:
            safe_path(row['archive_path'])
            require(row['archive_path'] == 'sources/'+relative+'.txt', 'archive path mapping changed')
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, 'manifest pin changed')
    require(manifest['schema_version'] == 1 and manifest['source_commit'] == SOURCE_COMMIT
            and manifest['source_tree'] == SOURCE_TREE, 'historical source identity changed')
    files = manifest['files']
    archives = {row['archive_path'] for row in files.values() if 'archive_path' in row}
    require(inventory(material, 'sources') == archives, 'missing or extra archived source path')
    for relative in manifest['exact_live_roots']:
        expected = {path for path in files if path.startswith(relative+'/')}
        require(inventory(repo, relative) == expected, 'missing or extra historical input path: '+relative)
    snapshot = {}
    for relative, row in files.items():
        origin = material if 'archive_path' in row else repo
        path = row.get('archive_path', relative)
        data = read(origin, path)
        require(identity(data) == {k: row[k] for k in ('bytes', 'sha256', 'git_blob')},
                'input identity changed: '+relative)
        snapshot[relative] = data
    return snapshot


def stage(snapshot, root):
    require(root.is_dir() and not any(root.iterdir()), 'stage must be an empty directory')
    for relative, data in snapshot.items():
        path = root/safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def run_staged(root, check, optimized=False):
    require(check in COMMANDS, 'unknown historical check')
    command = [sys.executable, '-B']+(['-O'] if optimized else [])+COMMANDS[check]
    environment = dict(os.environ)
    for key in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'PYTHONSTARTUP'):
        environment.pop(key, None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True,
                            text=True, timeout=120, check=False)
    require(result.returncode == 0, 'original '+check+' CLI exit '+str(result.returncode)+': '+result.stderr.strip())
    return {'check': check, 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def audit(repo, check='all'):
    snapshot = preflight(repo)
    selected = list(COMMANDS) if check == 'all' else [check]
    with tempfile.TemporaryDirectory(prefix='nvwa-history-compat-') as temporary:
        root = Path(temporary)
        stage(snapshot, root)
        results = [run_staged(root, name, bool(sys.flags.optimize)) for name in selected]
    require(preflight(repo) == snapshot, 'live inputs changed during historical checks')
    return {'status': 'PASS_HISTORICAL48_49', 'mode': 'optimized' if sys.flags.optimize else 'normal',
            'scope': 'retained historical48/49 source and capture context only',
            'source_commit': SOURCE_COMMIT, 'source_tree': SOURCE_TREE,
            'archived_product_source_files': 28, 'authenticated_inputs': len(snapshot),
            'current_product_checks': 'NOT-RUN', 'fresh_runtime_collection': 'NOT-RUN',
            'original_clis': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=HERE.parents[1])
    parser.add_argument('--check', choices=['all']+list(COMMANDS), default='all')
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo_root, args.check), sort_keys=True))
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, 'REJECT_HISTORY_COMPAT: '+str(error)+'\n')


if __name__ == '__main__':
    main()
