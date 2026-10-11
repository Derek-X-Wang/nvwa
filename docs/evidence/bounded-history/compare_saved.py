#!/usr/bin/env python3
"""Recheck complete saved GUI documents; does not drive or replace GUI execution."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]
load = lambda path: json.loads(path.read_text())
documents = [load(here / f'history-{name}.json') for name in ['base', 'edit', 'undo', 'redo']]
assert documents[0] == load(root / 'docs/evidence/m1/web-sequence.nvwa.json')
assert [document['revision'] for document in documents] == [6, 7, 8, 9]
content = lambda document: {key: value for key, value in document.items() if key != 'revision'}
assert content(documents[0]) == content(documents[2])
assert content(documents[1]) == content(documents[3])
expected = json.loads(json.dumps(documents[0]))
expected['revision'] = 7
expected['character']['parameters']['jaw_width'] = 0.9
assert documents[1] == expected
assert load(here / 'history-reloaded.json') == documents[3]
assert all('editor_retention' not in document for document in documents)
print('PASS: actual saved full documents, revisions6→7→8→9, complete Undo/Redo/reload equality')
