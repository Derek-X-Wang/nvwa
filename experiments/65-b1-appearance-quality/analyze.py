#!/usr/bin/env python3
"""Offline #79 diagnosis; stdlib only, no rendering and no input mutations."""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ASSETS = REPO / 'experiments/62-b1-appearance-preview/assets'

def sub(a, b): return [x-y for x, y in zip(a, b)]
def dot(a, b): return math.fsum(x*y for x, y in zip(a, b))
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def unit(a):
    length = math.sqrt(dot(a, a))
    if not length > 1e-12 or not math.isfinite(length): raise ValueError('degenerate normal/edge')
    return [x/length for x in a]
def angle(a, b): return math.acos(max(-1., min(1., dot(unit(a), unit(b)))))

def polygons(path):
    positions, faces = [], []
    for line in path.read_text().splitlines():
        f = line.split()
        if not f: continue
        if f[0] == 'v': positions.append([float(x)*.1 for x in f[1:]])
        if f[0] == 'f': faces.append([int(t.split('/')[0])-1 for t in f[1:]])
    return positions, faces

def normals(rest, faces, polygon=False):
    sums = [[0., 0., 0.] for p in rest]
    for face in faces:
        if polygon:
            origin = rest[face[0]]
            area = [0., 0., 0.]
            for a, b in zip(face, face[1:]+face[:1]):
                area = [x+y for x, y in zip(area, cross(sub(rest[a], origin), sub(rest[b], origin)))]
            n = unit(area)
            for i, sid in enumerate(face):
                theta = angle(sub(rest[face[i-1]], rest[sid]), sub(rest[face[(i+1)%len(face)]], rest[sid]))
                sums[sid] = [x+y*theta for x, y in zip(sums[sid], n)]
        else:
            for i in range(1, len(face)-1):
                tri = [face[0], face[i], face[i+1]]
                n = cross(sub(rest[tri[1]], rest[tri[0]]), sub(rest[tri[2]], rest[tri[0]]))
                for sid in tri: sums[sid] = [x+y for x, y in zip(sums[sid], n)]
    return [unit(n) for n in sums]

def degrees(a, b): return math.degrees(angle(a, b))

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect(capture):
    spec = importlib.util.spec_from_file_location('frozen64_reference', REPO/'experiments/64-b1-accessory-preview/verification/source_reference.py')
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    reference.configure(REPO)
    manifest = json.loads((ASSETS/'asset-manifest.json').read_text())
    for rel, identity in manifest['outputs'].items():
        path = ASSETS/rel
        if sha(path) != identity['sha256'] or path.stat().st_size != identity['size']:
            raise ValueError(f'asset identity mismatch: {rel}')
    result = {'scope':'offline source/CPU diagnosis; visual improvement NOT-RUN',
              'assets_authenticated':len(manifest['outputs']), 'assets':{}, 'captures':[]}
    for name, stem, texture in [('eyes','eyes/low-poly/low-poly','eyes/materials/brown_eye.png'),
                                ('hair','hair/short04/short04','hair/short04/short04_diffuse.png')]:
        rest, faces = polygons(ASSETS/(stem+'.obj'))
        n0, n1 = normals(rest, faces), normals(rest, faces, True)
        # Source face cyclic rotation changes fan diagonals, but must not affect
        # polygon normals. This is a numerical control, not a visual oracle.
        rotated = [f[1:]+f[:1] for f in faces]
        nr0, nr1 = normals(rest, rotated), normals(rest, rotated, True)
        alpha = manifest['png'][texture]['alpha']
        result['assets'][name] = {
            'source_vertices':len(rest), 'source_faces':len(faces),
            'face_sizes':dict(collections.Counter(map(len, faces))),
            'material_sha256':sha(ASSETS/(stem+'.mhmat') if name == 'hair' else ASSETS/'eyes/materials/brown.mhmat'),
            'source_obj_sha256':sha(ASSETS/(stem+'.obj')),
            'partial_alpha_pixels':alpha['partial_pixels'],
            'partial_alpha_fraction':alpha['partial_pixels']/(manifest['png'][texture]['width']*manifest['png'][texture]['height']),
            'normal_candidate_change_max_degrees':max(degrees(a,b) for a,b in zip(n0,n1)),
            'fan_root_rotation_max_normal_degrees':max(degrees(a,b) for a,b in zip(n0,nr0)),
            'polygon_root_rotation_max_normal_degrees':max(degrees(a,b) for a,b in zip(n1,nr1)),
        }
    for path in capture:
        value = json.loads(path.read_text())
        frame = value['frame']
        rows = frame['appearance']['accessory_runtime']['accessories']
        details = {'capture_sha256':sha(path), 'request':value['request'], 'accessories':{}}
        for row in rows:
            name = row['name']
            stem = 'hair/short04/short04' if name == 'hair' else 'eyes/low-poly/low-poly'
            _, faces = polygons(ASSETS/(stem+'.obj'))
            rest = row['rest_model_m']
            n0, n1 = normals(rest, faces), normals(rest, faces, True)
            baseline_error = max(abs(x-y) for a,b in zip(n0,row['rest_normals']) for x,y in zip(a,b))
            if baseline_error > 1e-12: raise ValueError('frozen64 normal reconstruction mismatch')
            source = reference.compute(frame['snapshot'], name)
            source_positions = [source['positions'][sid] for sid,uv in row['source_uv_pairs']]
            fit_error = reference.err(source['rest_positions'], rest)
            pose_error = reference.err(source_positions, row['positions'])
            if fit_error > 1e-5 or pose_error > 1e-5: raise ValueError('signed source geometry mismatch')
            actual_weights = row['full_normalized_positive_influences']
            weight_error = 0.
            for expected, actual in zip(source['full_joint_influences'],actual_weights):
                if [j for j,w in expected] != [j for j,w in actual]: raise ValueError('full positive joint set mismatch')
                weight_error = max(weight_error, sum(abs(x[1]-y[1]) for x,y in zip(expected,actual)))
            if weight_error > 1e-12: raise ValueError('full positive source weight mismatch')
            details['accessories'][name] = {
                'baseline_rest_normal_reconstruction_max_component_error':baseline_error,
                'normal_candidate_change_max_degrees':max(degrees(a,b) for a,b in zip(n0,n1)),
                'source_vertices':len(rest), 'render_corners':len(row['positions']),
                'max_influences':max(map(len,row['full_normalized_positive_influences'])),
                'source_ids_over4':[i for i,weights in enumerate(row['full_normalized_positive_influences']) if len(weights)>4],
                'source_geometry_unchanged_by_normal_candidate':True,
                'signed_source_fit_max_component_error_m':fit_error,
                'signed_full_positive_pose_max_component_error_m':pose_error,
                'source_full_positive_weight_max_L1_error':weight_error,
                'eye_depth_fit_adjustment_m':0,
            }
        result['captures'].append(details)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='append', type=Path, default=[])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Exclusive output prevents silently replacing prior observations.
    with args.out.open('x') as f:
        json.dump(inspect(args.capture), f, indent=2, allow_nan=False)
        f.write('\n')
