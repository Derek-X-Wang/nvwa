#!/usr/bin/env python3
"""Read only the task's model packages, tools, and expected cache locations."""
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess

info = {'platform': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version(),
        'packages': {name: bool(importlib.util.find_spec(name)) for name in ['kimodo', 'torch', 'mlx', 'transformers', 'llm2vec', 'numpy']},
        'executables': {name: shutil.which(name) for name in ['kimodo_gen', 'kmd-generate', 'blender']},
        'configured_cache_paths': {name: os.environ.get(name) for name in ['HF_HOME', 'HF_HUB_CACHE', 'HUGGINGFACE_HUB_CACHE', 'TORCH_HOME']},
        'model_cache_checks': {}}
paths = [Path.home()/rel for rel in ['.cache/huggingface/hub', '.cache/torch/hub/checkpoints', 'KimodoMotionRuntime', '.kimodo_venv', '.kimodo-runtime']]
paths += [Path(path) for path in info['configured_cache_paths'].values() if path]
for path in paths:
    entries = [p.name for p in path.iterdir() if any(token in p.name.lower() for token in ['kimodo', 'llama', 'llm2vec', 'soma'])] if path.is_dir() else []
    info['model_cache_checks'][str(path)] = {'exists': path.exists(), 'candidate_entries': entries}
for name in ['machdep.cpu.brand_string', 'hw.memsize']:
    result = subprocess.run(['sysctl', '-n', name], capture_output=True, text=True)
    info[name] = result.stdout.strip() if result.returncode == 0 else 'unavailable'
if info['packages']['torch']:
    import torch
    info['torch'] = {'version': torch.__version__, 'mps_built': torch.backends.mps.is_built(), 'mps_available': torch.backends.mps.is_available()}
print(json.dumps(info, indent=2))
