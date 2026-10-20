"""Exact source-context admission; no historical execution or render claim."""
import hashlib
import json

FROZEN_INPUTS_SHA = '66f024238ef009d0544d617251c46754b202b3069254ce5df47dc6dfc6debc33'
CONTEXT_NAME = 'source-context-closeout-v1.json'
CONTEXT_SHA = '0cd9302848da7a996232bca4cbb58cc6c6e12ec77263f59c53b790be2dfd3604'


def require(ok, message):
    if not ok:
        raise ValueError('FROZEN-INPUTS.json source context: ' + message)


def source_contexts(exp, raw, original):
    require(hashlib.sha256(raw).hexdigest() == FROZEN_INPUTS_SHA,
            'immutable original manifest identity mismatch')
    path = exp / CONTEXT_NAME
    require(path.is_file() and not path.is_symlink(), 'context manifest missing/unsafe')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == CONTEXT_SHA,
            'context manifest identity mismatch')
    context = json.loads(path.read_bytes())
    require(context['schema_version'] == 1 and context['baseline_manifest'] == 'FROZEN-INPUTS.json'
            and context['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA,
            'context baseline/version mismatch')
    current = dict(original)
    current.update(context['overrides'])
    return [('original-frozen309', original), (context['context'], current)]


def select_context(actual, contexts):
    for name, expected in contexts:
        if actual == expected:
            return name, expected
    raise ValueError('FROZEN-INPUTS.json source context: exact original309 or reviewed complete closeout309 required')
