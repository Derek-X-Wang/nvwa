#!/usr/bin/env python3
"""Authorized private CPU setup. No model download or inference.

fetch: fixed public source text + approved exact Kitware tool archive.
audit: print executable build hooks for review before configure/build.
build: explicitly requested, offline sandbox, 600 second group deadline.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.work/m2-provider'
SOURCES = PRIVATE / 'sources'
PINS = {'cpp': ('localai-org/kimodo.cpp', '5679ff19ba0a522c0b0516e9a9d402fe1af2c027'),
        'ggml': ('ggml-org/ggml', '8c63e70982c95ceb862e3a1073a2c1beef75d60a')}
TOOL = {'name': 'cmake-3.31.12-macos-universal.tar.gz', 'bytes': 79954716,
        'sha256': '799af7fd545db9bf1b9cfe72f8095880e727a2d4e0df0e3dffc3bc7b95c2d3b0',
        'url': 'https://github.com/Kitware/CMake/releases/download/v3.31.12/cmake-3.31.12-macos-universal.tar.gz'}


def selected(repo, path):
    if repo == 'cpp':
        return path in ['CMakeLists.txt', 'LICENSE', 'NOTICE'] or path.startswith(('src/', 'include/', 'tests/'))
    return (path in ['CMakeLists.txt', 'LICENSE', 'ggml.pc.in', 'README.md'] or
            path.startswith(('cmake/', 'include/', 'src/ggml-cpu/')) or
            (path.startswith('src/') and path.count('/') == 1))


def fetch_source(item):
    repo, entry = item
    owner, revision = PINS[repo]
    relative = Path(entry['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    url = f'https://raw.githubusercontent.com/{owner}/{revision}/{relative.as_posix()}'
    target = PRIVATE / 'runtime' / ('kimodo' if repo == 'cpp' else 'kimodo/ggml') / relative
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Nvwa-public-text-preflight/1'}), timeout=20) as response:
        data = response.read(2_097_153)
    assert len(data) <= 2_097_152 and len(data) == entry['size']
    data.decode('utf-8')
    git_hash = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    assert git_hash == entry['sha'], (relative, 'Git blob hash mismatch')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {'repo': owner, 'revision': revision, 'path': relative.as_posix(), 'url': url,
            'bytes': len(data), 'git_blob_sha1': git_hash, 'sha256': hashlib.sha256(data).hexdigest()}


def fetch():
    tasks = []
    for repo, (_, revision) in PINS.items():
        tree = json.loads((SOURCES / f'{repo}-tree.json').read_text())
        assert tree['sha'] == revision and not tree['truncated']
        tasks.extend((repo, e) for e in tree['tree'] if e['type'] == 'blob' and selected(repo, e['path']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(fetch_source, tasks))
    (PRIVATE / 'setup-source-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    tools = PRIVATE / 'tools'
    tools.mkdir(exist_ok=True)
    archive = tools / TOOL['name']
    if not archive.exists():
        partial = archive.with_suffix('.partial')
        count = 0
        with urllib.request.urlopen(TOOL['url'], timeout=30) as response, partial.open('xb') as output:
            while chunk := response.read(1 << 20):
                count += len(chunk)
                if count > TOOL['bytes']:
                    raise ValueError('Tool archive exceeds exact approved size')
                output.write(chunk)
        partial.rename(archive)
    assert archive.stat().st_size == TOOL['bytes']
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    assert digest == TOOL['sha256']
    (PRIVATE / 'setup-tool-receipt.json').write_text(json.dumps(TOOL | {'verified_sha256': digest}, indent=2) + '\n')
    with tarfile.open(archive) as tar:
        tar.extractall(tools, filter='data')
    print(json.dumps({'source_files': len(receipts), 'source_bytes': sum(r['bytes'] for r in receipts), 'tool': TOOL}, indent=2))


def audit():
    import re
    pattern = re.compile(r'execute_process|add_custom_(?:command|target)|file\s*\(\s*DOWNLOAD|FetchContent|ExternalProject|https?://|download|curl|wget', re.I)
    rows = []
    runtime = PRIVATE / 'runtime/kimodo'
    for path in sorted(runtime.rglob('*')):
        if path.is_file() and (path.name == 'CMakeLists.txt' or path.suffix == '.cmake'):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if pattern.search(line):
                    rows.append({'file': str(path.relative_to(runtime)), 'line': number, 'text': line})
    (PRIVATE / 'setup-build-hooks.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


def build():
    cmake = PRIVATE / 'tools/cmake-3.31.12-macos-universal/CMake.app/Contents/bin/cmake'
    source = PRIVATE / 'runtime/kimodo'
    out = PRIVATE / 'runtime/build-cpu'
    flags = ['-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=OFF', '-DKIMODO_BUILD_TESTS=OFF',
             '-DKIMODO_ENABLE_VULKAN=OFF', '-DGGML_METAL=OFF', '-DGGML_BLAS=OFF', '-DGGML_OPENMP=OFF',
             '-DGGML_CCACHE=OFF', '-DGGML_NATIVE=OFF', '-DGGML_CPU=ON', '-DGGML_ACCELERATE=ON',
             '-DGGML_CPU_KLEIDIAI=OFF', '-DFETCHCONTENT_FULLY_DISCONNECTED=ON', '-DGIT_EXE:FILEPATH=']
    for name in ['CUDA', 'HIP', 'CANN', 'SYCL', 'MUSA', 'RPC', 'VIRTGPU', 'VULKAN', 'WEBGPU',
                 'OPENCL', 'HEXAGON', 'ZENDNN', 'ZDNN', 'OPENVINO', 'ET']:
        flags.append(f'-DGGML_{name}=OFF')
    commands = [[str(cmake), '-S', str(source), '-B', str(out), '-G', 'Unix Makefiles', *flags],
                [str(cmake), '--build', str(out), '--target', 'kmd-generate', '--parallel', '2']]
    receipts = []
    deadline = time.monotonic() + 600
    for index, command in enumerate(commands):
        argv = ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)', *command]
        started = time.monotonic()
        with (PRIVATE / f'setup-stage-{index}.log').open('w') as log:
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            (PRIVATE / 'setup-active-process.json').write_text(json.dumps({'pid': proc.pid, 'pgid': proc.pid, 'argv': argv}) + '\n')
            try:
                code = proc.wait(timeout=max(0.1, deadline - time.monotonic()))
            except BaseException:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise
        row = {'argv': argv, 'pid': proc.pid, 'pgid': proc.pid, 'returncode': code, 'elapsed_seconds': time.monotonic() - started}
        receipts.append(row)
        (PRIVATE / 'setup-build-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
        (PRIVATE / 'setup-active-process.json').unlink(missing_ok=True)
        if code:
            raise SystemExit(f'Build stage {index} failed with {code}; no alternate route attempted')
    print(json.dumps(receipts, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['fetch', 'audit', 'build'])
    args = parser.parse_args()
    {'fetch': fetch, 'audit': audit, 'build': build}[args.stage]()
