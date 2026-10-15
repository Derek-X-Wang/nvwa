#!/usr/bin/env python3
"""Prepare/verify a model-free C++ format probe bound to this CPU build."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / '.work/m2-provider'
BUILD = PRIVATE / 'runtime/build-cpu'
RECEIPT = HERE / 'evidence/float-prerequisite.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity():
    cache = BUILD / 'CMakeCache.txt'
    compiler_file = BUILD / 'CMakeFiles/3.31.12/CMakeCXXCompiler.cmake'
    flags_file = BUILD / 'CMakeFiles/kimodo.dir/flags.make'
    compiler = Path(re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$', cache.read_text(), re.M)[1])
    flags = shlex.split(re.search(r'^CXX_FLAGS = (.+)$', flags_file.read_text(), re.M)[1])
    libraries = json.loads((HERE / 'evidence/built-library-hashes.json').read_text())
    runtime = {'binary_sha256': sha(BUILD / 'kmd-generate'),
               'libraries': [{'path': lib['path'], 'sha256': sha(ROOT / lib['path'])} for lib in libraries]}
    return {'compiler': str(compiler), 'compiler_resolved': str(compiler.resolve()),
            'compiler_sha256': sha(compiler), 'compiler_config_sha256': sha(compiler_file),
            'compile_flags_file_sha256': sha(flags_file), 'build_cache_sha256': sha(cache),
            'compile_flags': flags, 'runtime': runtime, 'source_sha256': sha(HERE / 'float_probe.cpp')}


def execute_probe(path):
    result = subprocess.run(['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)', str(path)],
                            capture_output=True, timeout=5, env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
    if result.returncode != 0 or result.stdout != bytes.fromhex('0000803f') or result.stderr:
        raise RuntimeError('C++ float probe failed exact native binary32 output check')
    return {'returncode': result.returncode, 'native_float_one_hex': result.stdout.hex()}


def prepare():
    current = identity()
    output = PRIVATE / 'float_probe'
    argv = [current['compiler'], *current['compile_flags'], str(HERE / 'float_probe.cpp'), '-o', str(output)]
    started = time.monotonic()
    result = subprocess.run(['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)', *argv],
                            capture_output=True, text=True, timeout=30)
    receipt = {'identity': current, 'compile_argv': argv, 'compile_returncode': result.returncode,
               'compile_stdout': result.stdout, 'compile_stderr': result.stderr,
               'elapsed_seconds': time.monotonic() - started}
    if result.returncode:
        raise RuntimeError(json.dumps(receipt))
    receipt.update(probe_path=str(output), probe_sha256=sha(output), execution=execute_probe(output))
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


def verify_float_prerequisite(receipt_path=RECEIPT):
    receipt = json.loads(receipt_path.read_text())
    if receipt['compile_returncode'] != 0 or receipt['identity'] != identity():
        raise RuntimeError('C++ float prerequisite missing or stale for this compiler/runtime identity')
    probe = Path(receipt['probe_path'])
    if probe != PRIVATE / 'float_probe' or probe.is_symlink() or sha(probe) != receipt['probe_sha256']:
        raise RuntimeError('C++ float probe identity changed')
    result = execute_probe(probe)
    if result != receipt['execution']:
        raise RuntimeError('C++ float runtime assertion changed')
    return {'receipt_sha256': sha(receipt_path), 'probe_sha256': receipt['probe_sha256'],
            'binary_sha256': receipt['identity']['runtime']['binary_sha256'], **result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        print(json.dumps(verify_float_prerequisite(), indent=2))
