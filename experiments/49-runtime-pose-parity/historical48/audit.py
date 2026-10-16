#!/usr/bin/env python3
"""Run unchanged experiment48 CLIs against an explicitly pinned historical snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
RUNTIME = 'experiments/48-genuine-fixture-work/runtime'
POLICY_SHA256 = 'e202ec97bbe51d8e4f29329d8df131f09cd29a4172c48befada19ad01bd4044a'
SUBSTITUTIONS = {
    'crates/nvwa-studio/Cargo.toml': 'sources/nvwa-studio-Cargo.toml.txt',
    'crates/nvwa-studio/src/lib.rs': 'sources/nvwa-studio-lib.rs.txt',
}


class Rejected(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode(data):
    def invalid(value):
        raise Rejected('non-finite JSON value: ' + value)
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid)


def info(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def read(root, relative):
    path = PurePosixPath(relative)
    require(isinstance(relative, str) and not path.is_absolute()
            and relative == path.as_posix() and '..' not in path.parts
            and bool(path.parts), 'unsafe relative path: ' + str(relative))
    target = root
    for part in path.parts:
        target = target / part
        require(not target.is_symlink(), 'symlink input: ' + relative)
    require(target.is_file(), 'missing input: ' + relative)
    return target.read_bytes()


def checked(root, path, expected):
    data = read(root, path)
    require(info(data) == expected, 'input identity changed: ' + path)
    return data


def preflight(repo, material=HERE):
    policy_bytes = read(material, 'POLICY.json')
    policy = decode(policy_bytes)
    substitutions = policy.get('substitutions')
    require(isinstance(substitutions, list) and len(substitutions) == 2,
            'substitutions must contain exactly two entries')
    names = [entry.get('repo_path') for entry in substitutions]
    require(len(set(names)) == 2 and set(names) == set(SUBSTITUTIONS),
            'missing, extra, or duplicate substitution')
    for entry in substitutions:
        require(entry.get('archive_path') == SUBSTITUTIONS[entry['repo_path']],
                'archive substitution path changed')
    require(info(policy_bytes)['sha256'] == POLICY_SHA256, 'policy pin changed')
    require(set(policy['current_cohorts']) == {'native', 'web'}, 'current cohort set changed')
    snapshot = {}
    for path, identity in policy['runtime_files'].items():
        snapshot[path] = checked(repo, path, identity)
    runtime_dir = repo / RUNTIME
    actual = {p.relative_to(repo).as_posix() for p in runtime_dir.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    require(actual == set(policy['runtime_files']), 'historical runtime file set changed')
    cohort = decode(snapshot[RUNTIME + '/source-cohort.json'])
    require(cohort['source_commit'] == policy['historical_cohort_source_commit'],
            'historical source commit changed')
    require(len(cohort['files']) == 54, 'historical source count changed')
    by_name = {entry['repo_path']: entry for entry in substitutions}
    for path, recorded in cohort['files'].items():
        historical = {'bytes': recorded['bytes'], 'sha256': recorded['sha256'],
                      'git_blob': recorded['retained_git_blob']}
        if path in by_name:
            entry = by_name[path]
            require(entry['historical'] == historical, 'archive differs from historical cohort: ' + path)
            checked(repo, path, entry['current'])
            snapshot[path] = checked(material, entry['archive_path'], historical)
        else:
            snapshot[path] = checked(repo, path, historical)
    for path, identity in policy['artifacts'].items():
        snapshot[path] = checked(repo, path, identity)
    current_proof = {}
    for platform, pin in policy['current_cohorts'].items():
        cohort_bytes = checked(repo, pin['path'], {k: pin[k] for k in ('bytes', 'sha256', 'git_blob')})
        current = decode(cohort_bytes)
        build = current['snapshot_build']
        require(current['platform'] == platform and build['platform'] == platform,
                'crossed current cohort platform: ' + platform)
        require(current['snapshot_matches_current'] is True and build['status'] == 'complete'
                and type(build['exit_code']) is int and build['exit_code'] == 0,
                'current cohort is not a completed matching build: ' + platform)
        require(current['artifact'] == build['artifact'] == pin['artifact'],
                'current artifact binding changed: ' + platform)
        for field, mapping in [('files', current['files']), ('source_files', build['source_files'])]:
            require(isinstance(mapping, dict) and bool(mapping), 'empty current source map')
            for path, sha in mapping.items():
                require(info(read(repo, path))['sha256'] == sha,
                        'current cohort source changed: ' + path)
            for path, entry in by_name.items():
                require(mapping.get(path) == entry['current']['sha256'],
                        'current Studio binding missing from ' + field)
        current_proof[platform] = {'cohort_sha256': pin['sha256'], 'artifact': pin['artifact']}
    return {'snapshot': snapshot, 'current49_retained_builds': current_proof}


def stage_snapshot(plan, destination):
    for relative, data in plan['snapshot'].items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def run_staged(snapshot, check='audit', optimized=False, python_executable=sys.executable):
    require(check in ('audit', 'controls'), 'unknown check')
    script = 'verify_evidence.py' if check == 'audit' else 'test_controls.py'
    command = [str(python_executable)] + (['-O'] if optimized else [])
    command += [str(snapshot / RUNTIME / script)]
    if check == 'audit':
        command += ['--runtime-root', str(snapshot / RUNTIME), '--repo-root', str(snapshot)]
    environment = dict(os.environ)
    environment.pop('PYTHONOPTIMIZE', None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run(command, capture_output=True, text=True, env=environment,
                            timeout=90, check=False)
    require(result.returncode == 0,
            'original ' + check + ' CLI exit ' + str(result.returncode) + ': ' + result.stderr.strip())
    output = decode(result.stdout)
    if check == 'audit':
        require(output == {'status': 'PASS_RETAINED_AUDIT', 'work_files': 5, 'images': 13,
                           'source_inputs': 54, 'quality': 'HOLD', 'fresh_GUI_replay': 'NOT-RUN',
                           'runtime_pose_numbers': 'NOT-RUN'}, 'unexpected original audit result')
    else:
        require(output.get('status') == 'PASS' and output.get('mode') == ('optimized' if optimized else 'normal')
                and output.get('mutation_red') == 26 and output.get('restored_green') == 26
                and output.get('baseline_green') == 1 and len(output.get('cases', [])) == 26,
                'original controls did not complete all 26 red/restored cases')
        require(all(type(case.get('red_exit')) is int and case['red_exit'] != 0
                    and type(case.get('restored_exit')) is int and case['restored_exit'] == 0
                    for case in output['cases']), 'original control exit evidence invalid')
    return output


def audit(repo, check='audit'):
    plan = preflight(repo)
    with tempfile.TemporaryDirectory(prefix='nvwa-historical48-') as directory:
        snapshot = Path(directory)
        stage_snapshot(plan, snapshot)
        result = run_staged(snapshot, check, bool(sys.flags.optimize))
    # Refuse a result if a checked live input changed while the child was running.
    require(preflight(repo) == plan, 'inputs changed during historical audit')
    return {'status': 'PASS_HISTORICAL48_' + check.upper(), 'check': check,
            'mode': 'optimized' if sys.flags.optimize else 'normal',
            'scope': 'retained experiment48 historical snapshot; not current runtime replay',
            'substituted_sources': 2, 'unchanged_sources': 52, 'fresh_GUI_replay': 'NOT-RUN',
            'current49_retained_builds': plan['current49_retained_builds'], 'original_cli': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=HERE.parents[2])
    parser.add_argument('--check', choices=('audit', 'controls'), default='audit')
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo_root.resolve(), args.check), sort_keys=True))
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, 'REJECT_HISTORICAL48: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
