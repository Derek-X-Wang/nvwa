"""Publish only explicitly named diagnostic evidence. Never dump environment/source trees."""
import json
import os
from pathlib import Path
import sys
from codec import encode
HERE = Path(__file__).resolve().parent
allowed = ['SETUP.json', 'EXTERNAL.json', 'guard-run/ROOT-RESULT.json',
           'guard-run/driver.stdout', 'guard-run/driver.stderr', 'guard-run/hard-budget.log',
           'run/RECEIPT.json', 'run/FINAL-ELAPSED.txt', 'run/source-before.json', 'run/hard-budget.log']
allowed += [f'run/child-{i:02d}.raw.json' for i in range(1,25)]
files = {}
for name in allowed:
    path = HERE / name
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('invalid evidence file')
        raw = path.read_bytes()
        if b'/Users/' in raw or b'/opt/homebrew/' in raw:
            raise RuntimeError('private host path in public evidence; refuse export')
        files[name] = raw
identity = {key: os.environ[key] for key in ('GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')}
sys.stdout.buffer.write(encode(files, identity))
sys.stdout.buffer.flush()
