"""Require 73's actual integration gate to admit the exact contact-target source."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
exp = root / 'experiments/73-high-poly-eyes'
sys.path.insert(0, str(exp))
import frozen_context as f
raw = (exp / 'FROZEN-INPUTS.json').read_bytes()
inputs = json.loads(raw)
contexts = f.current_source_contexts(exp, raw, inputs)
previous = f._motion_query_source_context(exp, f._running_source_context(exp, inputs, contexts))
cpu = f._cpu_context(exp, previous[1])
name, files = f.integration_source_context(exp, cpu, root)
if name != 'nvwa-contact-target-source-context-v1':
    raise ValueError('Did not select the contact-target live context')
print(json.dumps({'id': name, 'files': len(files)}))
