#!/usr/bin/env python3
"""Run original experiment38 evidence checks in authenticated historical context."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
HISTORICAL = 'experiments/38-agent-cli'
MANIFEST_SHA256 = '29dfda68a974addc2c71685343b79e1f193c126922ac40c299322303a4bbd075'
SOURCE_COMMIT = '50eae1979cac47c7eb53dada69f06b716436bf92'
SOURCE_TREE = '0bb87d9dc2ff324390de6e184852a87d513017fa'
COMMANDS = {'audit': 'verify.py', 'controls': 'verify_controls.py'}
# Both original scripts use assert. Refuse to execute either without assertions.
BOOTSTRAP = '''import runpy, sys
if sys.flags.optimize != 0 or not __debug__:
    raise SystemExit("original verifier requires normal Python assertions")
script = sys.argv[1]
sys.argv = [script]
runpy.run_path(script, run_name="__main__")
'''


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
    require(not path.is_absolute() and path.as_posix() == relative and bool(path.parts) and '..' not in path.parts,
            'unsafe relative path: '+relative)
    return path


def read(root, relative):
    path = root
    for part in safe_path(relative).parts:
        path = path/part
        require(not path.is_symlink(), 'symlink input: '+relative)
    require(path.is_file(), 'missing input: '+relative)
    return path.read_bytes()


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}


def inventory(root, relative):
    start = root
    for part in safe_path(relative).parts:
        start = start/part
        require(not start.is_symlink(), 'symlink inventory root: '+relative)
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
    require(type(manifest.get('files')) is dict, 'missing file mapping')
    for relative, row in manifest['files'].items():
        safe_path(relative)
        require(type(row) is dict and set(row) in
                ({'bytes', 'sha256', 'git_blob'}, {'bytes', 'sha256', 'git_blob', 'archive_path'}),
                'invalid identity fields')
        if 'archive_path' in row:
            safe_path(row['archive_path'])
            require(row['archive_path'] == 'sources/'+relative+'.txt', 'archive path mapping changed')
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, 'manifest pin changed')
    require(manifest['schema_version'] == 1 and manifest['source_commit'] == SOURCE_COMMIT
            and manifest['source_tree'] == SOURCE_TREE and manifest['historical_root'] == HISTORICAL,
            'historical source identity changed')
    files = manifest['files']
    archives = {row['archive_path'] for row in files.values() if 'archive_path' in row}
    require(inventory(material, 'sources') == archives, 'missing or extra archived source path')
    retained = {relative for relative in files if relative.startswith(HISTORICAL+'/')}
    require(inventory(repo, HISTORICAL) == retained, 'missing or extra historical input path')
    snapshot = {}
    for relative, row in files.items():
        data = read(material if 'archive_path' in row else repo, row.get('archive_path', relative))
        require(identity(data) == {key: row[key] for key in ('bytes', 'sha256', 'git_blob')},
                'input identity changed: '+relative)
        snapshot[relative] = data
    accepted = decode(snapshot[HISTORICAL+'/accepted-run/source-manifest.json'])['sources']
    substituted = {path: row['sha256'] for path, row in files.items() if 'archive_path' in row}
    require(len(accepted) == 8 and substituted == accepted, 'accepted source mapping changed')
    return snapshot


def stage(snapshot, root):
    require(root.is_dir() and not any(root.iterdir()), 'stage must be an empty directory')
    for relative, data in snapshot.items():
        path = root/safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def run_staged(root, check):
    require(check in COMMANDS, 'unknown historical check')
    # -I ignores interpreter environment; clearing PYTHONOPTIMIZE also protects
    # verify_controls.py's own unchanged child command (which does not use -I).
    environment = dict(os.environ)
    for key in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'PYTHONSTARTUP'):
        environment.pop(key, None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    script = root/HISTORICAL/COMMANDS[check]
    result = subprocess.run([sys.executable, '-I', '-B', '-c', BOOTSTRAP, str(script)],
                            cwd=root, env=environment, capture_output=True, text=True,
                            timeout=30, check=False)
    require(result.returncode == 0, 'original '+check+' CLI exit '+str(result.returncode)+': '+result.stderr.strip())
    output = decode(result.stdout)
    if check == 'audit':
        require(output.get('portable_retained_evidence_audit') is True
                and output.get('source_manifests_checked') == 2
                and output.get('transport_probe_calls_checked') == 9
                and output.get('closed_stderr_controls_checked') == 2
                and len(output.get('runs', [])) == 2
                and all(run.get('verified_process_receipts') == 9 for run in output['runs']),
                'original audit result changed')
    else:
        require(output.get('portable_baseline') == 'passed'
                and output.get('tamper_rejected_and_restored') == 5, 'original five controls incomplete')
    return {'check': check, 'exit_code': result.returncode,
            'child_mode': 'normal_python_assertions_enforced', 'original_cli': output}


def audit(repo, check='all'):
    snapshot = preflight(repo)
    selected = list(COMMANDS) if check == 'all' else [check]
    with tempfile.TemporaryDirectory(prefix='nvwa-cli-history-') as temporary:
        root = Path(temporary).resolve()
        stage(snapshot, root)
        results = [run_staged(root, name) for name in selected]
    require(preflight(repo) == snapshot, 'inputs changed during historical checks')
    return {'status': 'PASS_HISTORICAL38', 'scope': 'retained historical CLI source/receipt context only',
            'source_commit': SOURCE_COMMIT, 'source_tree': SOURCE_TREE,
            'authenticated_inputs': len(snapshot), 'archived_source_files': 8,
            'wrapper_optimized': bool(sys.flags.optimize),
            'current_product_checks': 'NOT-RUN', 'fresh_binary_execution': 'NOT-RUN',
            'original_clis': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=HERE.parents[1])
    parser.add_argument('--check', choices=['all']+list(COMMANDS), default='all')
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo_root, args.check), sort_keys=True))
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, 'REJECT_CLI_HISTORY: '+str(error)+'\n')


if __name__ == '__main__':
    main()
