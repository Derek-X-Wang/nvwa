#!/usr/bin/env python3
"""Run two independent Blender processes and record byte hashes, without hiding drift."""
import hashlib
import json
from pathlib import Path
import subprocess
import os
from validate_fixture import validate, read_glb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'experiments/01-character'
ENV = dict(os.environ, NVWA_RENDER_PREVIEWS='0')
paths = ['nvwa-humanoid.glb', 'nvwa-humanoid.blend', 'source-structure.json']
runs = []
structures = []
chunk_hashes = []
command = ['/opt/homebrew/bin/blender', '-b', '-t', '2', '--python', 'tools/blender/generate_fixture.py']
for idx in range(2):
    output = OUT / 'reexports' / f'run-{idx+1}'
    output.mkdir(parents=True, exist_ok=True)
    environment = dict(ENV, NVWA_FIXTURE_OUTPUT=str(output))
    log = OUT / f'repro-export-{idx+1}.log'
    with log.open('w') as handle:
        subprocess.run(command, cwd=ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT, check=True)
    runs.append({name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in paths})
    structure = validate(output / paths[0])
    for key in ('glb_sha256', 'glb_bytes'):
        structure.pop(key)
    structures.append(structure)
    doc, binary = read_glb(output / paths[0])
    chunk_hashes.append({'json_sorted_sha256': hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest(),
                         'binary_sha256': hashlib.sha256(binary).hexdigest()})
result = {'command': ' '.join(command), 'independent_process_count': 2, 'runs': runs,
          'output_directory_pattern': 'experiments/01-character/reexports/run-{1,2}',
          'byte_identical': {name: runs[0][name] == runs[1][name] for name in paths},
          'structural_metrics_and_morph_delta_hashes_identical': structures[0] == structures[1],
          'chunk_hashes': chunk_hashes,
          'run_structures': structures,
          'limit': 'Repeatability measured on Blender 3.3.1 arm64 on this host only. No claim across Blender/exporter versions or platforms. Native .blend includes nondeterministic save metadata if hashes differ.'}
(OUT / 'reproducibility.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
# This experiment never changes the published main GLB/profile. Discard only
# automatic backup files in these explicitly owned isolated output folders.
for output in (OUT / 'reexports').glob('run-*'):
    backup = output / 'nvwa-humanoid.blend1'
    if backup.exists():
        backup.unlink()
