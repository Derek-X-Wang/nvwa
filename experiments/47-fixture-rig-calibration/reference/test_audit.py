#!/usr/bin/env python3
"""Mutation controls against the real public audit CLI in normal and -O modes."""
import argparse
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def checked(condition, message):
    if not condition:
        raise RuntimeError(message)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    baseline = json.loads((HERE/'authority-claims.json').read_bytes())
    results = []
    with tempfile.TemporaryDirectory(prefix='nvwa-reference-audit-') as tmp:
        folder = Path(tmp)
        controls = []
        def claim_control(name, mutation, expected):
            data = copy.deepcopy(baseline)
            mutation(data)
            path = folder/(name+'.json')
            path.write_text(json.dumps(data)+'\n')
            controls.append((name, ['--claims', str(path)], expected))
        claim_control('wrong_side', lambda c: c.update(physical_side_to_suffix={'left': 'L', 'right': 'R'}), 'wrong target physical side/suffix policy')
        claim_control('reversed_front', lambda c: c['fixture_axes'].update(front=[0, 0, -1]), 'fixture forward claim contradicts pupil/white geometry')
        claim_control('changed_source_pin', lambda c: c['original_sources']['cpp-src__skeleton.hpp'].update(sha256='0'*64), 'source pin mismatch: cpp-src__skeleton.hpp')
        claim_control('false_palm_certification', lambda c: c['anatomical_certification'].update(palm=True), 'false palm/sole/contact certification')
        claim_control('changed_retained_source_claim', lambda c: c['retained_claims'][0].update(claim='Unsupported anatomy certification'), 'retained source claim identity changed')
        blob = bytearray((ROOT/'assets/fixtures/nvwa-humanoid.glb').read_bytes())
        n = struct.unpack_from('<I', blob, 12)[0]
        gltf = json.loads(blob[20:20+n])
        node = next(x for x in gltf['nodes'] if x['name'] == 'Eye pupil -1')
        primitive = gltf['meshes'][node['mesh']]['primitives'][0]
        a = gltf['accessors'][primitive['attributes']['POSITION']]
        v = gltf['bufferViews'][a['bufferView']]
        checked(a['componentType'] == 5126 and a['type'] == 'VEC3', 'unexpected eye accessor for control')
        start = 20+n+8+v.get('byteOffset', 0)+a.get('byteOffset', 0)
        stride = v.get('byteStride', 12)
        for i in range(a['count']):
            offset = start+i*stride+8
            z = struct.unpack_from('<f', blob, offset)[0]
            struct.pack_into('<f', blob, offset, z+.01)
        changed = folder/'changed-eye.glb'
        changed.write_bytes(blob)
        controls.append(('changed_eye_geometry', ['--fixture', str(changed)], 'eye geometry mismatch: Eye pupil -1'))
        for mode in [[], ['-O']]:
            def run(extra):
                p = subprocess.run([sys.executable, *mode, str(HERE/'audit.py'), *extra], cwd=folder, capture_output=True, text=True, timeout=30)
                try:
                    result = json.loads(p.stdout)
                except json.JSONDecodeError as error:
                    raise RuntimeError('audit did not emit JSON: '+p.stdout+' '+p.stderr) from error
                return p.returncode, result
            code, result = run([])
            checked(code == 0 and result['status'] == 'PASS', 'baseline audit failed: '+str(result))
            results.append({'mode': '-O' if mode else 'normal', 'control': 'baseline', 'exit_code': code, 'status': result['status']})
            for name, extra, expected in controls:
                code, result = run(extra)
                checked(code == 1 and result.get('status') == 'FAIL' and expected in result.get('error', ''), 'mutation failed to reject at intended boundary: '+name+' '+str(result))
                results.append({'mode': '-O' if mode else 'normal', 'control': name, 'exit_code': code, 'expected_error': expected, 'actual_error': result['error']})
            code, result = run([])
            checked(code == 0 and result['status'] == 'PASS', 'restored baseline failed')
            results.append({'mode': '-O' if mode else 'normal', 'control': 'restored_baseline', 'exit_code': code, 'status': result['status']})
    report = {'status': 'PASS', 'scope': 'public authority/geometry audit CLI only; no primary calibration code read or invoked', 'checks': results, 'temporary_mutations_removed': True, 'background_processes_created': False}
    text = json.dumps(report, indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
    return 0

if __name__ == '__main__':
    sys.exit(main())
