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
CHEEK_CONTEXT_NAME = 'source-context-b1-cheek-fullness-v1.json'
CHEEK_CONTEXT_SHA = '7eae6f15bd946baf7c7fdb258bd0ab8d6156012ce948e08875c6662389d151ce'
CHEEK_BASELINES_NAME = 'fixtures/b1-cheek-fullness-baselines.json'
CHEEK_BASELINES_SHA = '06a87ade124110f50738907c89913effc081183407dac0a67585d206bd74c74b'
LOWER_CONTEXT_NAME = 'source-context-b1-lower-face-squareness-v1.json'
LOWER_CONTEXT_SHA = '363f114fc1d6b2708f055c13433ef0a407d998a2813c3f283ac786f48c911b70'
LOWER_BASELINES_NAME = 'fixtures/b1-lower-contour-baselines.json'
LOWER_BASELINES_SHA = '8d5a168e2ec031c1d8a01129128b13a0cc7c7b5f9800204ba89d24164da0022b'


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
    pre_contour_baselines(exp, contexts)
    return contexts


def pre_contour_baselines(exp, contexts):
    """Retain every frozen crate input at its exact prior product identity."""
    raw = regular_file(exp, CHEEK_BASELINES_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CHEEK_BASELINES_SHA,
            'pre-contour baseline manifest identity mismatch')
    manifest = json.loads(raw)
    require(set(manifest) == {'schema_version', 'context', 'source_commit', 'files'}
            and manifest['schema_version'] == 1
            and manifest['context'] == 'b1-multisegment-product-v1'
            and manifest['source_commit'] == '96cda1b6a63d7f271389b28d293f1223028f0de6',
            'pre-contour baseline identity mismatch')
    expected = dict(contexts)[manifest['context']]
    items = manifest['files']
    require(set(items) == {name for name in expected if name.startswith('crates/')},
            'pre-contour baseline complete crate set required')
    result = {}
    declared = set()
    prefix = 'fixtures/b1-cheek-fullness-baselines/'
    for name, item in items.items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == prefix + name
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == expected[name],
                'pre-contour baseline differs from historical pin: ' + name)
        data = regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected[name],
                'pre-contour baseline bytes mismatch: ' + name)
        result[name] = data
        declared.add(item['fixture'])
    paths = list((exp / prefix).rglob('*'))
    require(all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths)
            and {str(path.relative_to(exp)) for path in paths if path.is_file()} == declared,
            'pre-contour baseline fixture inventory mismatch')
    return result


def admitted_source_contexts(exp, raw, original):
    """Append one exact current map; historical cohort enumeration stays fixed."""
    contexts = source_contexts(exp, raw, original)
    data = regular_file(exp, CHEEK_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(data).hexdigest() == CHEEK_CONTEXT_SHA,
            'cheek context manifest identity mismatch')
    context = json.loads(data)
    require(set(context) == {'schema_version', 'baseline_manifest', 'baseline_manifest_sha256',
                             'context', 'overrides', 'scope'}
            and context['schema_version'] == 1
            and context['context'] == 'b1-cheek-fullness-product-v1'
            and context['baseline_manifest'] == 'FROZEN-INPUTS.json'
            and context['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA,
            'cheek context baseline/version mismatch')
    require(context['overrides'] and set(context['overrides']) <= set(original),
            'cheek context must retain the exact original source paths')
    current = dict(original)
    current.update(context['overrides'])
    contexts.append((context['context'], current))
    return contexts



def pre_lower_contour_baselines(exp, contexts):
    """Retain all54 crate inputs from the exact preceding cheek context."""
    raw = regular_file(exp, LOWER_BASELINES_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == LOWER_BASELINES_SHA,
            'pre-lower-contour baseline manifest identity mismatch')
    manifest = json.loads(raw)
    require(set(manifest) == {'schema_version', 'context', 'source_commit', 'files'}
            and manifest['schema_version'] == 1
            and manifest['context'] == 'b1-cheek-fullness-product-v1'
            and manifest['source_commit'] == 'e3c02689d7f59d97141ffe70835fa3524231c28a',
            'pre-lower-contour baseline identity mismatch')
    expected = dict(contexts)[manifest['context']]
    require(set(manifest['files']) == {n for n in expected if n.startswith('crates/')},
            'pre-lower-contour complete crate set required')
    prefix = 'fixtures/b1-lower-contour-baselines/'
    result = {}
    for name, item in manifest['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'} and item['fixture'] == prefix + name
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == expected[name],
                'pre-lower-contour historical pin mismatch: ' + name)
        data = regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected[name],
                'pre-lower-contour baseline bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / prefix).rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {i['fixture'] for i in manifest['files'].values()},
            'pre-lower-contour baseline fixture inventory mismatch')
    return result


def current_source_contexts(exp, raw, original):
    """Append current source while old six/seven-context cohorts remain fixed."""
    contexts = admitted_source_contexts(exp, raw, original)
    pre_lower_contour_baselines(exp, contexts)
    data = regular_file(exp, LOWER_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(data).hexdigest() == LOWER_CONTEXT_SHA,
            'lower contour context manifest identity mismatch')
    context = json.loads(data)
    require(set(context) == {'schema_version', 'baseline_manifest', 'baseline_manifest_sha256',
                             'context', 'overrides', 'scope'}
            and context['schema_version'] == 1
            and context['context'] == 'b1-lower-face-squareness-product-v1'
            and context['baseline_manifest'] == 'FROZEN-INPUTS.json'
            and context['baseline_manifest_sha256'] == FROZEN_INPUTS_SHA,
            'lower contour context baseline/version mismatch')
    require(context['overrides'] and set(context['overrides']) <= set(original),
            'lower contour context must retain exact original source paths')
    current = dict(original)
    current.update(context['overrides'])
    contexts.append((context['context'], current))
    return contexts


def select_context(actual, contexts):
    for name, expected in contexts:
        if actual == expected:
            return name, expected
    raise ValueError('FROZEN-INPUTS.json source context: exact original309, reviewed closeout309, reviewed short01 product309, reviewed selector product309, reviewed B1 authoring product309, or reviewed B1 multisegment product309 required')


RUNNING_CONTEXT_NAME = 'source-context-b1-running-v1.json'
RUNNING_CONTEXT_SHA = 'bfe4866e3fa733a949a5b096300b8dc88ff48bda4545f2e8c3e7c8131ce10f7e'
RUNNING_BASELINES_NAME = 'fixtures/b1-running-predecessor-baselines.json'
RUNNING_BASELINES_SHA = '3dccb28db161e75b780872118a5c548171e643f00d72cc6c2d3f59ad2afdae05'
RUNNING_ADDITIONS = ('crates/nvwa-cli/tests/running.rs', 'crates/nvwa-core/src/running.rs', 'crates/nvwa-runtime/src/b1_running.rs', 'crates/nvwa-runtime/src/b1_running_controls.json', 'docs/b1-running-contract.md')


def running_source_context(exp, raw, original):
    """Authenticate a separate complete314 map; never alter original309."""
    contexts = current_source_contexts(exp, raw, original)
    return _running_source_context(exp, original, contexts)


def _running_source_context(exp, original, contexts):
    """Continue only with the context chain authenticated by this invocation."""
    data = regular_file(exp, RUNNING_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(data).hexdigest() == RUNNING_CONTEXT_SHA, 'running context manifest identity mismatch')
    value = json.loads(data)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'source_freeze_sha256', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-running-product-v1'
            and value['predecessor'] == 'b1-lower-face-squareness-product-v1'
            and value['source_freeze_sha256'] == 'ecc815dac0c868d1f3597324c2ca10b5f021199e87007c71fbf0cd4c33647044'
            and set(value['files']) == set(original) | set(RUNNING_ADDITIONS)
            and len(value['files']) == 314, 'running complete source union required')
    pre_running_sources(exp, contexts)
    return value['context'], value['files']


def pre_running_sources(exp, contexts):
    """Retain only replaced lower source; old gates still use current checker."""
    data = regular_file(exp, RUNNING_BASELINES_NAME).read_bytes()
    require(hashlib.sha256(data).hexdigest() == RUNNING_BASELINES_SHA, 'pre-running manifest identity mismatch')
    value = json.loads(data)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-lower-face-squareness-product-v1'
            and value['source_commit'] == '9251712313a3779bf4f0a4a854755a16f1a5df16', 'pre-running identity mismatch')
    expected = dict(contexts)[value['context']]
    result = {}
    for name, item in value['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == 'fixtures/b1-running-predecessor-baselines/' + name
                and {'bytes': item['bytes'], 'sha256': item['sha256']} == expected[name],
                'pre-running historical pin mismatch: ' + name)
        data = regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected[name],
                'pre-running bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / 'fixtures/b1-running-predecessor-baselines').rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {i['fixture'] for i in value['files'].values()}, 'pre-running fixture inventory mismatch')
    return result


MOTION_QUERY_CONTEXT = 'b1-motion-query-product-v1'
MOTION_QUERY_CONTEXT_NAME = 'source-context-b1-motion-query-v1.json'
MOTION_QUERY_CONTEXT_SHA = '12f03cc2d1cd9db12c9d5d112b52a0174d0253054a58531185ee71a4bf7dfc03'
MOTION_QUERY_NEW = ('crates/nvwa-cli/src/motion_query.rs', 'crates/nvwa-cli/tests/motion_query.rs',
                    'crates/nvwa-runtime/src/b1/foot_clearance.rs')
MOTION_QUERY_OUTSIDE = {
    'crates/nvwa-studio/examples/nvwa-preview.rs': {'bytes': 22049, 'sha256': 'c32c5bb4f71989af875ae1d24af40d6d7810ff97d4e4582d94c12311964e2452'},
}
MOTION_QUERY_ADDITIONS = (*MOTION_QUERY_NEW, *MOTION_QUERY_OUTSIDE)
MOTION_QUERY_CHANGED = ('Cargo.lock', 'crates/nvwa-cli/Cargo.toml', 'crates/nvwa-cli/src/main.rs',
                        'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/lib.rs')
MOTION_QUERY_FIXTURES = 'fixtures/pre-motion-query'


def _motion_query_source_context(exp, running):
    """Continue only with the running chain authenticated by this invocation."""
    data = regular_file(exp, MOTION_QUERY_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(data).hexdigest() == MOTION_QUERY_CONTEXT_SHA,
            'motion-query context manifest identity mismatch')
    value = json.loads(data)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_manifest_sha256',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == MOTION_QUERY_CONTEXT
            and value['predecessor'] == running[0]
            and value['predecessor_manifest_sha256'] == RUNNING_CONTEXT_SHA
            and value['predecessor_commit'] == 'd272e16fa6f5faa55337c4ae5f6ac18043f8ab01',
            'motion-query context predecessor mismatch')
    files = value['files']
    require(set(files) == set(running[1]) | set(MOTION_QUERY_ADDITIONS)
            and len(files) == 318
            and {name for name, item in running[1].items() if files[name] != item} == set(MOTION_QUERY_CHANGED),
            'motion-query complete source union required')
    _pre_motion_query_sources(exp, running)
    return value['context'], files


def _pre_motion_query_sources(exp, running):
    expected = {name: running[1][name] for name in MOTION_QUERY_CHANGED} | MOTION_QUERY_OUTSIDE
    result = {}
    declared = set()
    for name, item in expected.items():
        if name == 'crates/nvwa-cli/Cargo.toml':
            relative = 'fixtures/b1-lower-contour-baselines/' + name
        else:
            relative = MOTION_QUERY_FIXTURES + '/' + name
            declared.add(relative)
        raw = regular_file(exp, relative).read_bytes()
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == item,
                'pre-motion-query fixture bytes mismatch: ' + name)
        result[name] = raw
    paths = list((exp / MOTION_QUERY_FIXTURES).rglob('*'))
    require(all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths)
            and {str(path.relative_to(exp)) for path in paths if path.is_file()} == declared,
            'pre-motion-query fixture inventory mismatch')
    return result


def pre_motion_query_sources(exp, raw, original):
    """Return the exact displaced running inputs and pre-existing outside bytes."""
    return _pre_motion_query_sources(exp, running_source_context(exp, raw, original))


def check_no_motion_query_additions(root):
    require(not any((root / name).exists() or (root / name).is_symlink() for name in MOTION_QUERY_NEW),
            'motion-query additions in historical source')
    for name, item in MOTION_QUERY_OUTSIDE.items():
        if (root / name).exists() or (root / name).is_symlink():
            raw = regular_file(root, name).read_bytes()
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == item,
                    'motion-query outside source: ' + name)


# A separate exact product context; all historical cohort APIs and pins stay fixed.
CPU_CONTEXT_NAME = 'source-context-cpu-export-v1.json'
CPU_CONTEXT_SHA = '152d47f6e5e2b4b2d199e8707dd44e6b3175ba246531f2374e6fbcfe6b47a5d2'
CPU_BASELINES_SHA = '6d0a08f17b5ea871316e59670df4d4d8229f49958352e5badeb8282f5a55bf59'
CPU_CONTEXT_ID = 'b1-cpu-export-product-v1'
CPU_PREDECESSOR_COMMIT = '54384aeaaa70a7883978e3e33d4bf163c0c1f273'
CPU_ADDITIONS = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'docs/agents/cli-authoring.md', 'docs/agents/cpu-render.md', 'experiments/27-ci-baseline/check.sh')
CPU_NEW_FILES = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'docs/agents/cpu-render.md')
CPU_PREEXISTING = ('docs/agents/cli-authoring.md', 'experiments/27-ci-baseline/check.sh')
CPU_RETAINED = ('Cargo.lock', 'crates/nvwa-cli/Cargo.toml', 'crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/Cargo.toml', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/lib.rs', 'crates/nvwa-runtime/src/stage.rs', 'docs/agents/cli-authoring.md', 'experiments/27-ci-baseline/check.sh')

def cpu_regular_file(exp, relative):
    path = exp
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'CPU source context symlink: ' + relative)
    require(path.is_file(), 'CPU source context missing: ' + relative)
    return path


def has_cpu_inputs(root):
    return any((root / n).exists() or (root / n).is_symlink() for n in CPU_NEW_FILES)


def _pre_cpu_sources(exp, previous):
    path = cpu_regular_file(exp, 'fixtures/pre-cpu-export/manifest.json')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CPU_BASELINES_SHA,
            'CPU predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-motion-query-product-v1'
            and value['source_commit'] == CPU_PREDECESSOR_COMMIT
            and set(value['files']) == set(CPU_RETAINED), 'CPU predecessor complete inventory required')
    result = {}
    for name, item in value['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == 'fixtures/pre-cpu-export/' + name,
                'CPU predecessor fixture path mismatch')
        expected = {k: item[k] for k in ('bytes', 'sha256')}
        if name in previous:
            require(expected == previous[name], 'CPU predecessor historical pin mismatch: ' + name)
        data = cpu_regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected,
                'CPU predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / 'fixtures/pre-cpu-export').rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {'fixtures/pre-cpu-export/manifest.json'} | {i['fixture'] for i in value['files'].values()},
            'CPU predecessor fixture inventory mismatch')
    return result


def _cpu_context(exp, previous):
    _pre_cpu_sources(exp, previous)
    raw = cpu_regular_file(exp, CPU_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CPU_CONTEXT_SHA, 'CPU source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == CPU_CONTEXT_ID
            and value['predecessor'] == 'b1-motion-query-product-v1'
            and value['predecessor_commit'] == CPU_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(CPU_ADDITIONS),
            'CPU source context complete union required')
    return value['context'], value['files']


def pre_cpu_sources(exp, raw, original):
    return _pre_cpu_sources(exp, _motion_query_source_context(exp, running_source_context(exp, raw, original))[1])


def cpu_source_context(exp, raw, original):
    return _cpu_context(exp, _motion_query_source_context(exp, running_source_context(exp, raw, original))[1])


def check_cpu_preexisting(root, retained):
    for name in CPU_PREEXISTING:
        if (root / name).exists() or (root / name).is_symlink():
            require(cpu_regular_file(root, name).read_bytes() == retained[name],
                    'CPU source context mismatch: historical outside source: ' + name)


# The exact reference motion source is an additive successor to CPU export.
REFERENCE_MOTION_CONTEXT_NAME = 'source-context-reference-motion-v1.json'
REFERENCE_MOTION_CONTEXT_SHA = '8731414a1fe9c3b402ecda348472aba2f78326e0e47af838ed4f710de27cd397'
REFERENCE_MOTION_CONTEXT_ID = 'b1-reference-motion-product-v1'
REFERENCE_MOTION_PREDECESSOR_COMMIT = '875213616aa68d81dbfcd6378f4e2292f5b24004'
REFERENCE_MOTION_CHANGED = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-core/src/lib.rs',
                            'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-studio/src/lib.rs')
REFERENCE_MOTION_ADDITIONS = ('crates/nvwa-cli/tests/reference_motion.rs',
                              'crates/nvwa-core/src/reference_motion.rs',
                              'docs/agents/reference-motion.md')
REFERENCE_MOTION_FIXTURES = 'fixtures/pre-reference-motion'


def has_reference_motion_inputs(root):
    return any((root / name).exists() or (root / name).is_symlink()
               for name in REFERENCE_MOTION_ADDITIONS)


def _pre_reference_motion_sources(exp, previous):
    """Read the displaced CPU source bytes against the authenticated CPU pins."""
    result = {}
    for name in REFERENCE_MOTION_CHANGED:
        path = regular_file(exp, REFERENCE_MOTION_FIXTURES + '/' + name)
        data = path.read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == previous[name],
                'reference motion predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / REFERENCE_MOTION_FIXTURES).rglob('*'))
    require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths)
            and {p.relative_to(exp / REFERENCE_MOTION_FIXTURES).as_posix()
                 for p in paths if p.is_file()} == set(REFERENCE_MOTION_CHANGED),
            'reference motion predecessor fixture inventory mismatch')
    return result


def _reference_motion_context(exp, cpu):
    predecessor, previous = cpu
    raw = regular_file(exp, REFERENCE_MOTION_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == REFERENCE_MOTION_CONTEXT_SHA,
            'reference motion source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == REFERENCE_MOTION_CONTEXT_ID
            and value['predecessor'] == predecessor
            and value['predecessor_commit'] == REFERENCE_MOTION_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(REFERENCE_MOTION_ADDITIONS),
            'reference motion source context complete union required')
    require({name for name in previous if value['files'][name] != previous[name]}
            == set(REFERENCE_MOTION_CHANGED), 'reference motion source context exact changes required')
    _pre_reference_motion_sources(exp, previous)
    return value['context'], value['files']


def pre_reference_motion_sources(exp, raw, original):
    return _pre_reference_motion_sources(exp, cpu_source_context(exp, raw, original)[1])

# A separate exact product context; all historical cohort APIs and pins stay fixed.
WAIST_CONTEXT_NAME = 'source-context-waist-v1.json'
WAIST_CONTEXT_SHA = '43493146880230b5ee1246658b97eef88afbcfd39d227cccc86c9fe56899627b'
WAIST_BASELINES_SHA = 'e42a0ec7fbb47fc3c52edd2948cf8f92ed1d52d20b77959f7da3f5a0add2a891'
WAIST_CONTEXT_ID = 'b1-waist-circumference-product-v1'
WAIST_PREDECESSOR_COMMIT = '875213616aa68d81dbfcd6378f4e2292f5b24004'
WAIST_ADDITIONS = ('assets/characters/mpfb-b1-v5/base.obj', 'assets/characters/mpfb-b1-v5/body.mhclo', 'assets/characters/mpfb-b1-v5/composite.json', 'assets/characters/mpfb-b1-v5/empty.macro', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.obj', 'assets/characters/mpfb-b1-v5/licenses/CC0-1.0.txt', 'assets/characters/mpfb-b1-v5/licenses/CHEEK-VOLUME-DERIVATION-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/LOWER-FACE-SQUARING-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/MPFB-LICENSE.md', 'assets/characters/mpfb-b1-v5/licenses/PARAMETER-SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/provenance.json', 'assets/characters/mpfb-b1-v5/manifest.json', 'assets/characters/mpfb-b1-v5/provenance/README.md', 'assets/characters/mpfb-b1-v5/provenance/cheek-volume-derivation.json', 'assets/characters/mpfb-b1-v5/provenance/chin-bones-source.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/parameter-source-receipt.json', 'assets/characters/mpfb-b1-v5/provenance/runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json', 'assets/characters/mpfb-b1-v5/provenance/waist-source-validation.json', 'assets/characters/mpfb-b1-v5/rig.game_engine.json', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-decr.target', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-incr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-decr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-incr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-decr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-incr.target', 'assets/characters/mpfb-b1-v5/vertex_groups.json', 'assets/characters/mpfb-b1-v5/weights.game_engine.json', 'crates/nvwa-cli/tests/waist.rs', 'crates/nvwa-core/tests/waist.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')
WAIST_NEW_FILES = ('assets/characters/mpfb-b1-v5/base.obj', 'assets/characters/mpfb-b1-v5/body.mhclo', 'assets/characters/mpfb-b1-v5/composite.json', 'assets/characters/mpfb-b1-v5/empty.macro', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v5/garment/female_sportsuit01.obj', 'assets/characters/mpfb-b1-v5/licenses/CC0-1.0.txt', 'assets/characters/mpfb-b1-v5/licenses/CHEEK-VOLUME-DERIVATION-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/LOWER-FACE-SQUARING-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/MPFB-LICENSE.md', 'assets/characters/mpfb-b1-v5/licenses/PARAMETER-SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/SOURCE-NOTICE.md', 'assets/characters/mpfb-b1-v5/licenses/provenance.json', 'assets/characters/mpfb-b1-v5/manifest.json', 'assets/characters/mpfb-b1-v5/provenance/README.md', 'assets/characters/mpfb-b1-v5/provenance/cheek-volume-derivation.json', 'assets/characters/mpfb-b1-v5/provenance/chin-bones-source.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v2-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v3-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-manifest.json', 'assets/characters/mpfb-b1-v5/provenance/legacy-v4-runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/parameter-source-receipt.json', 'assets/characters/mpfb-b1-v5/provenance/runtime-payloads.json', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/l-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/cheek/r-cheek-volume-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/data/targets/chin/chin-bones-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-decr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/source/torso/measure-waist-circ-incr.target.gz', 'assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json', 'assets/characters/mpfb-b1-v5/provenance/waist-source-validation.json', 'assets/characters/mpfb-b1-v5/rig.game_engine.json', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-decr.target', 'assets/characters/mpfb-b1-v5/targets/cheek-volume-bilateral-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-bones-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-jaw-drop-incr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-decr.target', 'assets/characters/mpfb-b1-v5/targets/chin-width-incr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/head-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/hip-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-decr.target', 'assets/characters/mpfb-b1-v5/targets/measure-waist-circ-incr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/mouth-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/neck-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-decr.target', 'assets/characters/mpfb-b1-v5/targets/nose-scale-horiz-incr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-decr.target', 'assets/characters/mpfb-b1-v5/targets/torso-scale-vert-incr.target', 'assets/characters/mpfb-b1-v5/vertex_groups.json', 'assets/characters/mpfb-b1-v5/weights.game_engine.json', 'crates/nvwa-cli/tests/waist.rs', 'crates/nvwa-core/tests/waist.rs')
WAIST_PREEXISTING = ('crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')
WAIST_RETAINED = ('crates/nvwa-cli/src/cpu_render.rs', 'crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/appearance.rs', 'crates/nvwa-cli/tests/cpu_render.rs', 'crates/nvwa-core/src/appearance.rs', 'crates/nvwa-core/src/b1.rs', 'crates/nvwa-core/tests/appearance.rs', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-runtime/src/b1/cpu_render.rs', 'crates/nvwa-studio/src/appearance_ui.rs', 'crates/nvwa-studio/src/lib.rs', 'crates/nvwa-studio/src/lower_contour_ui_tests.rs', 'docs/agents/cpu-render.md', 'scripts/build-web.sh', 'scripts/package-cli.py', 'scripts/package-native.py', 'scripts/test-cli-package.py')

def waist_regular_file(exp, relative):
    path = exp
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'WAIST source context symlink: ' + relative)
    require(path.is_file(), 'WAIST source context missing: ' + relative)
    return path


def has_waist_inputs(root):
    return any((root / n).exists() or (root / n).is_symlink() for n in WAIST_NEW_FILES)


def _pre_waist_sources(exp, previous):
    path = waist_regular_file(exp, 'fixtures/pre-waist/manifest.json')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == WAIST_BASELINES_SHA,
            'WAIST predecessor manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'source_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == 'b1-cpu-export-product-v1'
            and value['source_commit'] == WAIST_PREDECESSOR_COMMIT
            and set(value['files']) == set(WAIST_RETAINED), 'WAIST predecessor complete inventory required')
    result = {}
    for name, item in value['files'].items():
        require(set(item) == {'fixture', 'bytes', 'sha256'}
                and item['fixture'] == 'fixtures/pre-waist/' + name,
                'WAIST predecessor fixture path mismatch')
        expected = {k: item[k] for k in ('bytes', 'sha256')}
        if name in previous:
            require(expected == previous[name], 'WAIST predecessor historical pin mismatch: ' + name)
        data = waist_regular_file(exp, item['fixture']).read_bytes()
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected,
                'WAIST predecessor bytes mismatch: ' + name)
        result[name] = data
    paths = list((exp / 'fixtures/pre-waist').rglob('*'))
    require(all(not p.is_symlink() for p in paths)
            and {str(p.relative_to(exp)) for p in paths if p.is_file()}
                == {'fixtures/pre-waist/manifest.json'} | {i['fixture'] for i in value['files'].values()},
            'WAIST predecessor fixture inventory mismatch')
    return result


def _waist_context(exp, previous):
    _pre_waist_sources(exp, previous)
    raw = waist_regular_file(exp, WAIST_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == WAIST_CONTEXT_SHA, 'WAIST source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == WAIST_CONTEXT_ID
            and value['predecessor'] == 'b1-cpu-export-product-v1'
            and value['predecessor_commit'] == WAIST_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(WAIST_ADDITIONS),
            'WAIST source context complete union required')
    return value['context'], value['files']


def pre_waist_sources(exp, raw, original):
    return _pre_waist_sources(exp, cpu_source_context(exp, raw, original)[1])


def waist_source_context(exp, raw, original):
    return _waist_context(exp, cpu_source_context(exp, raw, original)[1])


def check_waist_preexisting(root, retained):
    for name in WAIST_PREEXISTING:
        if (root / name).exists() or (root / name).is_symlink():
            require(waist_regular_file(root, name).read_bytes() == retained[name],
                    'WAIST source context mismatch: historical outside source: ' + name)

COMBINED_CONTEXT_NAME = 'source-context-waist-reference-motion-v1.json'
COMBINED_CONTEXT_SHA = '355e1a19843d23284e5cddb85e39b279ef7ef0361682ba853528aaefaaabe738'
COMBINED_CONTEXT_ID = 'b1-waist-reference-motion-product-v1'
COMBINED_PREDECESSOR_COMMIT = '9031ce7f82167621e8b7fed2b7a0af5a899b8a17'
COMBINED_FIXTURES = 'fixtures/pre-waist-reference-motion'
COMBINED_REFERENCE_RETAINED = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/src/b1.rs', 'crates/nvwa-studio/src/lib.rs')


def _combined_predecessors(exp, waist, reference):
    variants = (('waist', REFERENCE_MOTION_CHANGED, waist[1]),
                ('reference-motion', COMBINED_REFERENCE_RETAINED, reference[1]))
    expected_paths = {f'{label}/{name}' for label, names, _ in variants for name in names}
    fixture_root = exp / COMBINED_FIXTURES
    paths = list(fixture_root.rglob('*'))
    require(not fixture_root.is_symlink()
            and all(not path.is_symlink() and (path.is_file() or path.is_dir()) for path in paths)
            and {path.relative_to(fixture_root).as_posix() for path in paths if path.is_file()}
            == expected_paths, 'combined source predecessor fixture inventory mismatch')
    result = {}
    for label, names, pins in variants:
        retained = {}
        for name in names:
            data = regular_file(exp, f'{COMBINED_FIXTURES}/{label}/{name}').read_bytes()
            require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == pins[name],
                    'combined source predecessor bytes mismatch: ' + name)
            retained[name] = data
        result[label] = retained
    return result


def _combined_context(exp, cpu):
    waist = _waist_context(exp, cpu[1])
    reference = _reference_motion_context(exp, cpu)
    _combined_predecessors(exp, waist, reference)
    raw = regular_file(exp, COMBINED_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == COMBINED_CONTEXT_SHA,
            'combined source context manifest identity mismatch')
    value = json.loads(raw)
    previous = waist[1]
    require(set(value) == {'schema_version', 'context', 'predecessor', 'predecessor_commit', 'files'}
            and value['schema_version'] == 1 and value['context'] == COMBINED_CONTEXT_ID
            and value['predecessor'] == waist[0]
            and value['predecessor_commit'] == COMBINED_PREDECESSOR_COMMIT
            and set(value['files']) == set(previous) | set(REFERENCE_MOTION_ADDITIONS),
            'combined source context complete union required')
    require({name for name in previous if value['files'][name] != previous[name]}
            == set(REFERENCE_MOTION_CHANGED), 'combined source context exact changes required')
    return value['context'], value['files']


LEG_CONTEXT_NAME = '../72-b1-admission-controls/input-context-legs-v1.json'
LEG_CONTEXT_SHA = '955d7a1c5ff4481ccf14d3fe7b393a482c71a325d770067b8e52d1b96d0a4665'
LEG_CONTEXT_ID = 'b1-leg-morphology-product-v1'


def has_leg_inputs(root):
    return (root / 'assets/characters/mpfb-b1-v6').exists()


def leg_source_context(exp, cpu):
    """Admit only the exact v6 successor, retaining the combined predecessor gate."""
    combined = _combined_context(exp, cpu)
    raw = regular_file(exp, LEG_CONTEXT_NAME).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == LEG_CONTEXT_SHA,
            'leg source context manifest identity mismatch')
    value = json.loads(raw)
    require(set(value) == {'schema_version', 'context', 'predecessor',
                           'predecessor_commit', 'files'}
            and value['schema_version'] == 1
            and value['context'] == LEG_CONTEXT_ID
            and value['predecessor'] == combined[0]
            and value['predecessor_commit'] == 'e21322c95b3b9ca40334206de135a19b1ad6cb0f',
            'leg source context predecessor/version mismatch')
    files = dict(combined[1])
    files.update(value['files'])
    require(len(files) == 482 and len(value['files']) == 194,
            'leg source context complete union required')
    return LEG_CONTEXT_ID, files
