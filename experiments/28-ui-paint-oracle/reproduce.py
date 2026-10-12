"""Reproduce this exact throwaway CPU cohort, with guaranteed source restoration."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'crates/nvwa-studio/src/editor_layout.rs'
original = (OUT/'editor_layout.original.rs').read_bytes()
candidate = (OUT/'editor_layout.candidate.rs').read_bytes()
protected = json.loads((OUT/'protected-inputs-before.json').read_text())
assert SOURCE.read_bytes() == original, 'starting production source differs; refusing overwrite'
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name,digest in protected.items()), 'protected cohort changed; refusing replay'
try:
    for stage in ('green', 'paint-mutant', 'restored-green'):
        contents = candidate
        if stage == 'paint-mutant':
            assert candidate.count(b'let visuals = if selected {') == 1
            contents = candidate.replace(b'let visuals = if selected {', b'let visuals = if !selected {', 1)
        SOURCE.write_bytes(contents)
        subprocess.run(['python3', '-B', str(OUT/'run-stage.py'), stage], cwd=ROOT, check=True)
finally:
    SOURCE.write_bytes(original)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name,digest in protected.items()), 'protected inputs changed during replay'
