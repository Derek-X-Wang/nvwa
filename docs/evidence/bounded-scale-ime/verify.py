"""Verify committed bounded observations without a browser, dist or .work cache."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checker(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify():
    manifest = read(HERE / 'MANIFEST.json')
    paths = [entry['file'] for entry in manifest['entries']]
    require(len(paths) == len(set(paths)), 'duplicate evidence inventory')
    actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file()
              and p.name not in ('MANIFEST.json', 'verify.py', 'verification-result.json', 'ACCEPTANCE.md')
              and '__pycache__' not in p.parts}
    require(set(paths) == actual, 'evidence inventory differs')
    for entry in manifest['entries']:
        path = HERE / entry['file']
        require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'],
                'evidence bytes differ: ' + entry['file'])
    for name, digest in manifest['checker_files'].items():
        require(sha(ROOT / name) == digest, 'executed checker differs: ' + name)
    source = read(ROOT / 'docs/evidence/m1-1-ui/build/build-inputs-final-before.json')
    for name, entry in source['files'].items():
        require((ROOT / name).stat().st_size == entry['bytes'] and sha(ROOT / name) == entry['sha256'],
                'frozen production source differs: ' + name)
    scale = checker('bounded_scale', 'experiments/22-fixed-css-dpr/check.py')
    ime = checker('bounded_ime', 'experiments/23-ime-event-provenance/check.py')
    packages = {}
    for name in ('web-normal', 'web-fixed', 'web-normal-v2', 'web-fixed-v2'):
        folder = HERE / 'issue3' / name
        package = read(folder / 'probe-package.json')
        require(sha(folder / 'index.html') == package['wrapperSha256'], 'wrapper hash differs')
        for filename, digest in package['source']['observerFiles'].items():
            require(sha(folder / filename) == digest, 'observer hash differs')
        packages[name] = package['source']
    prep = read(HERE / 'issue32/package/preparation.json')
    for name, digest in prep['diagnostics'].items():
        require(sha(HERE / 'issue32/package' / name) == digest, 'IME diagnostic differs: ' + name)
    observations = read(HERE / 'observations.json')
    results = []
    for case in observations['scale_cases']:
        args = SimpleNamespace(pointer=case['pointer'], row=case['settled'],
                               expected_dpr=case['dpr'], expected_css=case['css'],
                               work_rect=case['work_rect'])
        result = scale.geometry(read(HERE / 'issue3' / case['capture']), args, packages[case['package']])
        results.append({'case': case['capture'], 'dpr': result['dpr'], 'age_ms': result['age_ms']})
    fixed = observations['scale_cases'][3:]
    transition = scale.transition([read(HERE / 'issue3' / c['capture']) for c in fixed],
                                  [c['pointer'] for c in fixed], [c['settled'] for c in fixed],
                                  [c['dpr'] for c in fixed], [c['work_rect'] for c in fixed],
                                  packages['web-fixed-v2'])
    for name in ('normal-v2-reset.json', 'fixed-final.json'):
        trace = read(HERE / 'issue3' / name)
        scale.inventory(trace)
        require(trace['stopped'] and trace['inventory']['dropped'] == 0, 'trace lacks complete stopped interval')
    rejected = read(HERE / 'issue3/v1-observation-limits.json')
    for case in rejected['cases']:
        name = Path(case['capture']).name
        require(sha(HERE / 'issue3' / name) == case['sha256'], 'rejected capture changed')
        try:
            scale.geometry(read(HERE / 'issue3' / name),
                           SimpleNamespace(pointer=case['pointer'], row=case['settled'],
                                           expected_dpr=case['dpr'],
                                           expected_css=[case['css']['width'], case['css']['height']],
                                           work_rect=[258, 3, 220, 22]), packages['web-normal'])
        except AssertionError as error:
            require('window-blur' in str(error), 'v1 rejection changed')
        else:
            raise AssertionError('v1 capture must remain rejected')
    commands = []
    for phase in ('100', '125', 'reset'):
        docs = [read(HERE / 'issue3' / f'fixed{phase}-{kind}.nvwa.json')
                for kind in ('base', 'click', 'undo')]
        result = scale.old.check_work(*docs, 'jaw_width', .05)
        commands.append({'phase': phase, 'kind': 'click; continuous drag NOT-RUN', 'result': result})
    drag_trace = read(HERE / 'issue3/fixed-final.json')
    attempted_drag = [r for r in drag_trace['rows'] if 51 <= r['index'] <= 52]
    require([r['kind'] for r in attempted_drag] == ['pointerdown', 'pointerup'],
            'tool drag endpoint record differs')
    ime_results = []
    run_ids = []
    for case in observations['ime_cases']:
        capture = read(HERE / 'issue32' / case['capture'])
        require(capture['runId'] == case['runId'] and capture['pageKind'] == case['pageKind'],
                'IME capture attribution differs')
        require(case['package_sha256'] == sha(HERE / 'issue32/package/preparation.json'),
                'IME capture package attribution differs')
        result, code = ime.check(capture, case['pageKind'] == 'synthetic-selftest')
        require(code == case['expected_exit'] and result['status'] == case['expected_status'],
                'IME verdict differs: ' + case['capture'])
        run_ids.append(capture['runId'])
        ime_results.append({'capture': case['capture'], 'result': result})
    require(len(run_ids) == len(set(run_ids)), 'IME run IDs reused')
    native = read(HERE / 'native-evidence.json')['runtime']
    require(native['ready'] and native['capture_callback'] and not native['timeout'] and native['error'] is None,
            'native capture did not confirm readiness')
    require(native['physical_window'] == {'height': 1440, 'scale_factor': 2.0, 'width': 2560},
            'native physical geometry differs')
    require((native['meshes'], native['skins'], native['joints'], native['morph_weights'], native['timeline_count'])
            == (9, 9, 18, 4, 3), 'native character/Work readiness differs')
    return {'status': 'PASS', 'scope': 'archived packet consistency; no UI simulation',
            'production_inputs': len(source['files']), 'scale_intervals': results,
            'actual_fixed_dprs': transition['actual_dprs'], 'commands': commands,
            'ime': ime_results, 'native': 'actual2x capture; separate GUI click/Undo/zoom observations',
            'not_run': observations['not_run']}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
