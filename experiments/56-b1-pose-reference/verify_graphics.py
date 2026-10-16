"""Audit retained actual native/Web captures; this command launches no renderer."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('strict_parity', REPO / 'experiments/58-b1-desktop-web/compare_frames.py')
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)
require = strict.require

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--web', type=Path, required=True)
    parser.add_argument('--return-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    inputs = {}
    def read(path):
        data = path.read_bytes()
        inputs[str(path)] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        return json.loads(data)
    def frame(path, native=False):
        value = read(path)
        if native:
            require(value.get('graphical_path_attached') is True, 'native process not graphical')
            require(value.get('phase') == 4 and not value.get('error'), 'native report not healthy')
            require(value['state'] == value['frame']['state'], 'outer frame state drift')
            return value['frame']
        return value
    asset_root = REPO / '.work/b1-pose-viewer/site/assets'
    cases = []
    for name in ('neutral__neutral', 'combined__shoulder', 'combined__elbow',
                 'combined__knee', 'combined__combined', 'body-positive__combined'):
        cases.append(strict.compare_frames(frame(args.native / (name + '.json'), True),
                                           frame(args.web / (name + '.json')), asset_root))
    accepted = frame(args.web / 'body-positive__combined.json')
    require(read(args.web / 'invalid-preserved.json') == accepted, 'invalid import changed frame')
    restored, camera = frame(args.web / 'restored.json'), frame(args.web / 'camera-only.json')
    require(restored['parts'] == camera['parts'] and restored['sequence'] == camera['sequence'], 'camera recomputed skin')
    require(restored['state']['camera_yaw'] == 25 and camera['state']['camera_yaw'] == 45, 'camera check absent')
    native_camera = frame(args.native / 'camera-recovered.json', True)
    outbound = strict.compare_frames(native_camera, frame(args.web / 'native-roundtrip.json'), asset_root)
    inbound = strict.compare_frames(frame(args.return_report, True), camera, asset_root)
    fatal = read(args.web / 'fatal-checks.json')
    require(len(fatal['checks']) == 3 and read(args.web / 'fatal-null-frame.json') is None, 'fatal checks incomplete')
    for i, check in enumerate(fatal['checks'], 1):
        require(check['actual_exported_state'] == fatal['before_state'], 'fatal command changed state')
        status = check['actual_dom_status']
        require('phase 255;' in status and 'error: Explicit target missing: chin-jaw-drop-incr; fatal_reload_required: true;' in status
                and status.endswith(f'rejected_commands: {i}'), 'fatal error/acknowledgment lost')
    result = {'schema_version': 1, 'status': 'PASS', 'cases': cases,
              'native_to_web': outbound, 'web_to_native': inbound,
              'invalid_import_preserved_exact_frame': True, 'camera_did_not_reskin': True,
              'fatal_commands_rejected_with_error_preserved': 3,
              'gpu_vertex_readback': False, 'pixel_parity': False,
              'input_receipts': inputs}
    with args.out.open('x') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': 'PASS', 'cases': len(cases), 'output': str(args.out)}))

if __name__ == '__main__':
    main()
