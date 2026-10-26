"""Exact source-context admission; no historical execution or render claim."""
import hashlib
import json
from pathlib import Path

FROZEN_INPUTS_SHA = '66f024238ef009d0544d617251c46754b202b3069254ce5df47dc6dfc6debc33'
CONTEXT_NAME = 'source-context-closeout-v1.json'
CONTEXT_SHA = '0cd9302848da7a996232bca4cbb58cc6c6e12ec77263f59c53b790be2dfd3604'
SHORT01_CONTEXT_NAME = 'source-context-hair79-short01-v1.json'
SHORT01_CONTEXT_SHA = '4212de5a650eb8120c49ec985bc00928cca43af33c95a2f8bcc207158311f13f'
FIXTURES_NAME = 'fixtures/source-contexts/manifest.json'
FIXTURES_SHA = '7416580f4c087ee831f6a4c9e0722b5b5fae2e172377a048936261e0938385a6'
RIG119_CONTEXT_NAME = 'source-context-rig119-v1.json'
RIG119_CONTEXT_SHA = '29f7fcb820312ba2b87f5eb5c945981165e6263591023d7f0960891de17441c9'
RIG119_CONTEXT = 'rig119-unit-handoff-v1'
RIG119_SUPPLEMENTS = ('crates/nvwa-b1-adapter/src/prepared.rs', 'scripts/b1-prepared-source-inventory.json')
COMPAT_FIXTURES_NAME = 'compat-fixtures-rig119/manifest.json'
COMPAT_FIXTURES_SHA = 'c44459eab6eae42d36dcc1db5644a8675b5fd8bcb576ad0bd021ff6faf5e3dd1'


def require(ok, message):
    if not ok:
        raise ValueError('FROZEN-INPUTS.json source context: ' + message)


def regular_file(exp, relative):
    path = exp
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'context/fixture symlink rejected: ' + relative)
    require(path.is_file(), 'context/fixture missing: ' + relative)
    return path


def historical_sources(exp, contexts):
    """Authenticate retained historical bytes against immutable old context pins."""
    path = regular_file(exp, FIXTURES_NAME)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FIXTURES_SHA,
            'historical fixture manifest identity mismatch')
    manifest = json.loads(raw)
    require(manifest['schema_version'] == 1
            and manifest['baseline_manifest'] == 'FROZEN-INPUTS.json'
            and manifest['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA,
            'historical fixture baseline/version mismatch')
    expected = dict(contexts)
    result = {}
    declared = {FIXTURES_NAME}
    for items in manifest['contexts'].values():
        declared.update(item['fixture'] for item in items.values())
    paths = list((exp / 'fixtures/source-contexts').rglob('*'))
    require(all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths),
            'historical fixture tree contains unsafe input')
    require({str(path.relative_to(exp)) for path in paths if path.is_file()} == declared,
            'historical fixture inventory is incomplete or contains extra files')
    for context, items in manifest['contexts'].items():
        result[context] = {}
        for name, item in items.items():
            pinned = expected[context][name]
            require({'bytes': item['bytes'], 'sha256': item['sha256']} == pinned,
                    'historical fixture differs from original context pin: ' + name)
            raw = regular_file(exp, item['fixture']).read_bytes()
            require(len(raw) == pinned['bytes'] and hashlib.sha256(raw).hexdigest() == pinned['sha256'],
                    'historical fixture bytes mismatch: ' + name)
            result[context][name] = raw
    shared = compatibility_sources(exp, contexts)
    for context in ('original-frozen309', 'character-stage-closeout-v1', 'hair79-short01-product-v1'):
        result.setdefault(context, {}).update(shared)
    return result


def compatibility_sources(exp, contexts):
    """Old shared adapter bytes, separately pinned from the immutable14 blobs."""
    raw = regular_file(exp, COMPAT_FIXTURES_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == COMPAT_FIXTURES_SHA,
            'compatibility fixture manifest identity mismatch')
    manifest = json.loads(raw)
    require(set(manifest) == {'schema_version', 'baseline_manifest_sha256', 'historical_fixture_manifest_sha256', 'files'}
            and manifest['schema_version'] == 1
            and manifest['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA
            and manifest['historical_fixture_manifest_sha256'] == FIXTURES_SHA,
            'compatibility fixture baseline/version mismatch')
    allowed = {'crates/nvwa-b1-adapter/src/lib.rs': 'compat-fixtures-rig119/adapter-lib.rs',
               'crates/nvwa-b1-adapter/README.md': 'compat-fixtures-rig119/adapter-README.md'}
    require(set(manifest['files']) == set(allowed), 'compatibility fixture exact source set mismatch')
    paths = list((exp / 'compat-fixtures-rig119').rglob('*'))
    require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths),
            'compatibility fixture tree contains unsafe input')
    require({str(p.relative_to(exp)) for p in paths if p.is_file()} == {COMPAT_FIXTURES_NAME, *allowed.values()},
            'compatibility fixture inventory is incomplete or contains extra files')
    expected = dict(contexts)
    result = {}
    for name, item in manifest['files'].items():
        require(set(item) == {'bytes', 'sha256', 'fixture'} and item['fixture'] == allowed[name],
                'compatibility fixture entry mismatch: ' + name)
        pinned = {'bytes': item['bytes'], 'sha256': item['sha256']}
        for context in ('original-frozen309', 'character-stage-closeout-v1', 'hair79-short01-product-v1'):
            require(pinned == expected[context][name], 'compatibility fixture differs from historical context: ' + name)
        raw = regular_file(exp, item['fixture']).read_bytes()
        require(len(raw) == pinned['bytes'] and hashlib.sha256(raw).hexdigest() == pinned['sha256'],
                'compatibility fixture bytes mismatch: ' + name)
        result[name] = raw
    return result


def source_contexts(exp, raw, original, include_current=False):
    require(hashlib.sha256(raw).hexdigest() == FROZEN_INPUTS_SHA,
            'immutable original manifest identity mismatch')
    require(original == json.loads(raw), 'original manifest map differs')
    contexts = [('original-frozen309', original)]
    for name, expected in ((CONTEXT_NAME, CONTEXT_SHA),
                           (SHORT01_CONTEXT_NAME, SHORT01_CONTEXT_SHA)):
        path = regular_file(exp, name)
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected,
                'context manifest identity mismatch: ' + name)
        context = json.loads(raw)
        require(context['schema_version'] == 1 and context['baseline_manifest'] == 'FROZEN-INPUTS.json'
                and context['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA,
                'context baseline/version mismatch')
        current = dict(original)
        current.update(context['overrides'])
        contexts.append((context['context'], current))
    # Historical fixtures are mandatory and independently authenticated even when
    # selecting the product context. No Git history or current-byte reversal.
    historical_sources(exp, contexts)
    raw = regular_file(exp, RIG119_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == RIG119_CONTEXT_SHA,
            'context manifest identity mismatch: ' + RIG119_CONTEXT_NAME)
    context = json.loads(raw)
    require(context['schema_version'] == 1 and context['baseline_manifest'] == 'FROZEN-INPUTS.json'
            and context['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA
            and context['parent_context_sha256'] == SHORT01_CONTEXT_SHA
            and context['context'] == RIG119_CONTEXT,
            'context baseline/version/parent mismatch')
    require(set(context['overrides']) == {'crates/nvwa-b1-adapter/src/lib.rs', 'crates/nvwa-b1-adapter/README.md'}
            and set(context['supplemental_files']) == set(RIG119_SUPPLEMENTS),
            'context rig119 exact supplement mismatch')
    if include_current:
        current = dict(contexts[-1][1])
        current.update(context['overrides'])
        current.update(context['supplemental_files'])
        contexts.append((RIG119_CONTEXT, current))
    return contexts


def select_context(actual, contexts):
    for name, expected in contexts:
        if actual == expected:
            return name, expected
    raise ValueError('FROZEN-INPUTS.json source context: exact original309, reviewed closeout309, reviewed short01 product309, or reviewed rig119 current context required')
