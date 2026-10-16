"""Capture the already-running task-owned graphical viewer through its command seam."""
import argparse, hashlib, importlib.util, json, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAB = REPO / 'experiments/58-b1-desktop-web'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=REPO / '.work/b1-pose-viewer/root-native-acceptance')
parser.add_argument('--live', type=Path, default=REPO / '.work/b1-pose-viewer/native-live')
args = parser.parse_args()
OUT = args.out
OUT.mkdir(exist_ok=False)
spec = importlib.util.spec_from_file_location('strict_parity', LAB / 'compare_frames.py')
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)
assets, bones = strict.expectations(REPO / '.work/b1-pose-viewer/site/assets')
live = args.live

def read_report(predicate):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            value = json.loads((live / 'report.json').read_text())
            if predicate(value):
                return value
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(.1)
    raise RuntimeError('actual graphical report did not reach expected state')

def command(value):
    value = dict(value, request_id=str(time.time_ns()))
    temporary = live / 'command.new'
    temporary.write_text(json.dumps(value))
    temporary.replace(live / 'command.json')

records = []
for recipe, pose in [('neutral', 'neutral'), ('combined', 'shoulder'),
                     ('combined', 'elbow'), ('combined', 'knee'),
                     ('combined', 'combined'), ('body-positive', 'combined')]:
    state = dict(format='nvwa-b1-pose-prototype', schema_version=1,
                 recipe=recipe, pose=pose, backend='full-weight-cpu', camera_yaw=25.)
    command(dict(action='import', state=state))
    report = read_report(lambda x: x.get('phase') == 4 and not x.get('error')
                         and x.get('state') == state and x.get('frame', {}).get('state') == state)
    strict.require(report['graphical_path_attached'] is True, 'graphical path not attached')
    coverage = strict.admit(report['frame'], assets, bones)
    for relative, digest in report['frame']['build_identity']['source_files'].items():
        source = REPO / 'experiments/57-b1-pose-runtime' / relative
        strict.require(hashlib.sha256(source.read_bytes()).hexdigest() == digest, 'live source identity mismatch')
    for binding in report['frame']['actual_display_bindings']:
        strict.require(not any(binding[k] for k in ('skinned_mesh_component', 'morph_stream_present',
                                                   'joint_index_attribute', 'joint_weight_attribute')),
                       'CPU display would deform again or select a skin shader')
        strict.require(max(abs(a-b) for a,b in zip(binding['display_transform'],
                       report['frame']['actual_skeleton_display_root'])) <= 1e-6, 'display root applied incorrectly')
    path = OUT / f'{recipe}__{pose}.json'
    path.write_text(json.dumps(report, allow_nan=False))
    records.append(dict(path=path.name, state=state, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        coverage=coverage, actual_display_bindings=report['frame']['actual_display_bindings']))

accepted = report
invalid = dict(accepted['state'], recipe='INVALID')
command(dict(action='import', state=invalid))
rejected = read_report(lambda x: bool(x.get('error')))
strict.require(rejected['state'] == accepted['state'] and rejected['frame'] == accepted['frame'],
               'invalid import changed the active character')
(OUT / 'invalid-import.json').write_text(json.dumps(rejected))
restored = dict(accepted['state'], camera_yaw=45.)
command(dict(action='import', state=restored))
recovered = read_report(lambda x: not x.get('error') and x.get('state') == restored
                        and x.get('frame', {}).get('state') == restored)
strict.require(recovered['frame']['parts'] == accepted['frame']['parts']
               and recovered['frame']['sequence'] == accepted['frame']['sequence'],
               'camera-only recovery recomputed or changed skin')
(OUT / 'camera-recovered.json').write_text(json.dumps(recovered))
(OUT / 'summary.json').write_text(json.dumps(dict(cases=records,
    invalid_import_preserved_exact_active_state_and_frame=True, camera_only_metadata_atomic=True,
    camera_only_skin_sequence_unchanged=True, graphical_process_attached=True,
    screenshot_acceptance_separate=True, gpu_vertex_readback=False), indent=2) + '\n')
print(json.dumps(dict(cases=len(records), invalid_preserved=True, camera_recovered=True, out=str(OUT))))
