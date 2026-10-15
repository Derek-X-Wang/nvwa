#!/usr/bin/env python3
"""Bounded local capability inventory. No torch import, tensor work, or secrets."""
import datetime
import importlib.metadata
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess


def main():
    result = {
        'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'platform': platform.platform(), 'machine': platform.machine(),
        'python': platform.python_version(),
        'scope': 'Current Python, PATH, named known runtime/cache roots only. No full disk scan.',
        'packages': {}, 'paths': {},
        'executables': {name: shutil.which(name) for name in ['kimodo_gen', 'kmd-generate', 'kmd-encode', 'python3', 'cmake', 'ninja', 'clang++']},
        'no_model_or_gpu_run': True,
    }
    for name in ['kimodo', 'torch', 'transformers', 'llm2vec', 'mlx', 'numpy']:
        found = importlib.util.find_spec(name) is not None
        try:
            version = importlib.metadata.version(name) if found else None
        except importlib.metadata.PackageNotFoundError:
            version = 'module exists; no distribution metadata'
        result['packages'][name] = {'present': found, 'version': version}
    roots = [Path.home() / p for p in ['.cache/huggingface/hub', '.cache/torch/hub/checkpoints', 'KimodoMotionRuntime', '.kimodo_venv', '.kimodo-runtime']]
    for key in ['HF_HOME', 'HF_HUB_CACHE', 'HUGGINGFACE_HUB_CACHE', 'HUGGINGFACE_CACHE_DIR', 'TORCH_HOME', 'CHECKPOINT_DIR', 'TEXT_ENCODERS_DIR']:
        value = os.environ.get(key)
        result.setdefault('configured_paths', {})[key] = value
        if value:
            roots.append(Path(value).expanduser())
    for path in roots:
        result['paths'][str(path)] = {
            'exists': path.exists(),
            'candidate_entries': sorted(p.name for p in path.iterdir() if any(s in p.name.lower() for s in ['kimodo', 'llama', 'llm2vec', 'soma'])) if path.is_dir() else [],
        }
    for key in ['machdep.cpu.brand_string', 'hw.memsize']:
        run = subprocess.run(['sysctl', '-n', key], capture_output=True, text=True, check=False)
        result[key] = run.stdout.strip() if run.returncode == 0 else 'unavailable'
    disk = shutil.disk_usage(Path.cwd())
    result['workspace_volume_free_bytes'] = disk.free
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
