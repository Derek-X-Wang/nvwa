"""Exact source-context admission; no historical execution or render claim."""
import hashlib
import json
from pathlib import Path

FROZEN_INPUTS_SHA = '66f024238ef009d0544d617251c46754b202b3069254ce5df47dc6dfc6debc33'
CONTEXT_NAME = 'source-context-closeout-v1.json'
CONTEXT_SHA = '0cd9302848da7a996232bca4cbb58cc6c6e12ec77263f59c53b790be2dfd3604'
SHORT01_CONTEXT_NAME = 'source-context-hair79-short01-v1.json'
SHORT01_CONTEXT_SHA = '4212de5a650eb8120c49ec985bc00928cca43af33c95a2f8bcc207158311f13f'
SELECTOR_CONTEXT_NAME = 'source-context-hair79-selector-v1.json'
SELECTOR_CONTEXT_SHA = 'c0416baa1cf9cb49e34217173ff37d00f02299fb782c83815602dab1977c5d35'
AUTHORING_CONTEXT_NAME = 'source-context-b1-motion-authoring-v1.json'
AUTHORING_CONTEXT_SHA = '9b518892e4317693d1b5ef43ec60665ce0fca9c030da817789a5ef9f4aba6c5b'
AUTHORING_BASELINES = {
    'crates/nvwa-studio/src/lib.rs': 'fixtures/b1-motion-authoring-baselines/studio-lib.rs',
    'crates/nvwa-studio/src/editor_layout.rs': 'fixtures/b1-motion-authoring-baselines/editor-layout.rs',
}
MULTISEGMENT_CONTEXT_NAME = 'source-context-b1-multisegment-v1.json'
MULTISEGMENT_CONTEXT_SHA = '3a2a387c0753ee0104fecff4d91e67ef0aa15a93cca62e356fef300bdd763b9a'
MULTISEGMENT_BASELINES = {
    'crates/nvwa-studio/src/lib.rs': 'fixtures/b1-multisegment-baselines/studio-lib.rs',
}
FIXTURES_NAME = 'fixtures/source-contexts/manifest.json'
FIXTURES_SHA = 'b70450a16e7fa59b13fc333de598864ed6e995b88522b04cf520ab75e239de3a'


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
    return result


def authoring_baselines(exp, original):
    """Shared old UI bytes remain pinned by the immutable original309 map."""
    result = {}
    for name, relative in AUTHORING_BASELINES.items():
        raw = regular_file(exp, relative).read_bytes()
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == original[name],
                'authoring baseline differs from original context pin: ' + name)
        result[name] = raw
    return result


def multisegment_baselines(exp, contexts):
    """Retain the preceding authoring UI bytes under their existing exact pin."""
    result = {}
    authoring = dict(contexts)['b1-motion-authoring-product-v1']
    for name, relative in MULTISEGMENT_BASELINES.items():
        raw = regular_file(exp, relative).read_bytes()
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == authoring[name],
                'multisegment baseline differs from authoring context pin: ' + name)
        result[name] = raw
    return result


def source_contexts(exp, raw, original):
    require(hashlib.sha256(raw).hexdigest() == FROZEN_INPUTS_SHA,
            'immutable original manifest identity mismatch')
    require(original == json.loads(raw), 'original manifest map differs')
    contexts = [('original-frozen309', original)]
    for name, expected in ((CONTEXT_NAME, CONTEXT_SHA),
                           (SHORT01_CONTEXT_NAME, SHORT01_CONTEXT_SHA),
                           (SELECTOR_CONTEXT_NAME, SELECTOR_CONTEXT_SHA),
                           (AUTHORING_CONTEXT_NAME, AUTHORING_CONTEXT_SHA),
                           (MULTISEGMENT_CONTEXT_NAME, MULTISEGMENT_CONTEXT_SHA)):
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
    authoring_baselines(exp, original)
    multisegment_baselines(exp, contexts)
    return contexts


def select_context(actual, contexts):
    for name, expected in contexts:
        if actual == expected:
            return name, expected
    raise ValueError('FROZEN-INPUTS.json source context: exact original309, reviewed closeout309, reviewed short01 product309, reviewed selector product309, reviewed B1 authoring product309, or reviewed B1 multisegment product309 required')
