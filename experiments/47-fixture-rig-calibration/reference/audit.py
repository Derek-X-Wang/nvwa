#!/usr/bin/env python3
"""Independent fixture/source-reference audit; stdlib only, no cached text required.

Checks current geometry/metadata and retained source-claim identity. This is not a
fresh inspection of upstream source text, a retargeter test, or admission.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT_REGISTRY_SHA256 = 'cc0a405557fb6bbeb545ecd05af91b3f54aaf29b6f21d61aa206a067c5625c1d'
RETAINED_CLAIMS_SHA256 = 'cc00c4f29cc7575e5492a2bc93358f6e9316dbc8119b49bf2e808b79edd2835b'
FIRST_FREEZE_SHA256 = '9e9c880f214b0d77ea27fc893df2b3b577263212f7e5b5d8b5c93722a34b5043'

class AuditError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise AuditError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def close(a, b, tolerance=1e-6):
    return len(a) == len(b) and all(abs(x-y) <= tolerance for x, y in zip(a, b))

def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def identity():
    return [[int(i == j) for j in range(4)] for i in range(4)]

def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def trs(node):
    require('matrix' not in node, 'unexpected node matrix in pinned fixture')
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    scale = node.get('scale', [1, 1, 1])
    t = node.get('translation', [0, 0, 0])
    r = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    result = identity()
    for i in range(3):
        for j in range(3):
            result[i][j] = r[i][j]*scale[j]
        result[i][3] = t[i]
    return result

def read_glb(blob):
    require(blob[:4] == b'glTF', 'invalid GLB magic')
    version, length = struct.unpack_from('<II', blob, 4)
    require(version == 2 and length == len(blob), 'invalid GLB version/length')
    n, kind = struct.unpack_from('<II', blob, 12)
    require(kind == 0x4e4f534a, 'missing JSON chunk')
    document = json.loads(blob[20:20+n])
    start = 20+n
    m, kind = struct.unpack_from('<II', blob, start)
    require(kind == 0x004e4942 and start+8+m == len(blob), 'invalid BIN chunk')
    binary = blob[start+8:start+8+m]
    def accessor(idx):
        a = document['accessors'][idx]
        require('sparse' not in a, 'sparse accessor unsupported in pinned fixture')
        v = document['bufferViews'][a['bufferView']]
        require(v['buffer'] == 0, 'external buffer unsupported')
        fmt, size = {5126: ('f', 4), 5123: ('H', 2), 5121: ('B', 1), 5125: ('I', 4)}[a['componentType']]
        width = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        offset = v.get('byteOffset', 0)+a.get('byteOffset', 0)
        stride = v.get('byteStride', size*width)
        require(a['count'] > 0, 'empty accessor')
        require(offset+(a['count']-1)*stride+size*width <= len(binary), 'accessor out of range')
        rows = [struct.unpack_from('<'+fmt*width, binary, offset+i*stride) for i in range(a['count'])]
        require(all(math.isfinite(x) for row in rows for x in row), 'nonfinite accessor')
        return rows
    return document, accessor

def audit(claims_path, fixture_path, skeleton_path, receipts_path):
    claims = json.loads(claims_path.read_bytes())
    receipts_blob = receipts_path.read_bytes()
    receipts = json.loads(receipts_blob)
    retained = json.loads((HERE/'original-receipt-matches.json').read_bytes())
    pins = json.loads((HERE/'input-hashes.json').read_bytes())
    require(digest((HERE/'input-hashes.json').read_bytes()) == INPUT_REGISTRY_SHA256, 'portable original input registry identity changed')
    retained_claims_bytes = json.dumps(claims['retained_claims'], sort_keys=True, separators=(',', ':')).encode()
    require(digest(retained_claims_bytes) == RETAINED_CLAIMS_SHA256, 'retained source claim identity changed')
    require(len(pins) == 21 and len(retained) == 8, 'original input/receipt counts changed')
    for row in retained:
        matches = [r for r in receipts if r['file'] == row['file']]
        require(len(matches) == 1 and matches[0]['url'] == row['url'] and matches[0]['sha256'] == row['sha256'], 'original receipt binding mismatch: '+row['file'])
    require(digest(receipts_blob) == pins['experiments/41-real-short-motion/evidence/source-receipts.json']['sha256'], 'archived41 receipt file changed')
    known = {r['file']: r for r in retained}
    require(set(claims['original_sources']) == set(known), 'source authority set changed')
    for name, row in claims['original_sources'].items():
        require(row['sha256'] == known[name]['sha256'] and row['url'] == known[name]['url'], 'source pin mismatch: '+name)
    require(claims['anatomical_certification'] == {'palm': False, 'sole': False, 'contact': False}, 'false palm/sole/contact certification')
    require(claims['ci_scope'] == 'geometry_metadata_pins_and_retained_claim_identity_only', 'CI authority overstated')
    require(claims['source_axes']['up'] == [0, 1, 0] and claims['source_axes']['front'] == [0, 0, 1], 'retained official axis claim changed')
    require(claims['source_axes']['body_left'] == [1, 0, 0], 'source body-left claim changed')
    axis_binding = claims['source_axes']['binding']
    require(axis_binding == {'source': 'official-output-formats.md', 'lines': [72, 73]}, 'official axis line binding changed')
    frozen = json.loads((HERE/'original-first-freeze.json').read_bytes())
    require(claims['first_pass']['manifest_sha256'] == FIRST_FREEZE_SHA256, 'first-pass manifest pin changed')
    require(digest((HERE/'original-first-freeze.json').read_bytes()) == claims['first_pass']['manifest_sha256'], 'first-pass manifest identity changed')
    require(frozen['files']['derived.json']['sha256'] == digest((HERE/'original-derived.json').read_bytes()), 'original derived evidence changed')
    require(frozen['files']['INDEPENDENT-FIRST-REPORT.md']['sha256'] == claims['first_pass']['report_sha256'], 'first-pass report identity changed')
    require(frozen['files']['receipt-checks.json']['sha256'] == digest((HERE/'original-receipt-matches.json').read_bytes()), 'first-pass receipt matches identity changed')

    source_blob = skeleton_path.read_bytes()
    s = json.loads(source_blob)
    names, parents, offsets = s['joint_names'], s['parents'], s['rest_local_translations']
    require(len(names) == len(parents) == len(offsets) == 30 and len(set(names)) == 30, 'invalid source layout')
    require(s['source_sha256'] == known['cpp-src__skeleton.hpp']['sha256'], 'source metadata original pin mismatch')
    require(s['up_axis'] == '+Y' and s['forward_axis'] == '+Z' and s['units'] == 'meters', 'source metadata axes/units mismatch')
    require(all(q == [0, 0, 0, 1] for q in s['rest_local_rotations_xyzw']), 'source neutral rotations changed')
    require(all(v == [1, 1, 1] for v in s['rest_local_scales']), 'source rest scales changed')
    world = []
    for i, (parent, offset) in enumerate(zip(parents, offsets)):
        require(parent == -1 if i == 0 else 0 <= parent < i, 'source parent order invalid')
        world.append([offset[k]+(world[parent][k] if parent >= 0 else 0) for k in range(3)])
    sj = dict(zip(names, world))
    require(all(sj[n][0] > 0 for n in ['LeftArm', 'LeftHand', 'LeftLeg', 'LeftEye']), 'source named-left side changed')
    require(all(sj[n][0] < 0 for n in ['RightArm', 'RightHand', 'RightLeg', 'RightEye']), 'source named-right side changed')
    require(sj['Head'][1] > sj['Hips'][1], 'source up geometry changed')
    require(all(offsets[names.index(n)][2] > 0 for n in ['LeftEye', 'RightEye', 'Jaw', 'LeftToeBase', 'RightToeBase']), 'source front landmarks changed')
    areas = {}
    for side in ['Left', 'Right']:
        middle = [sj[side+'HandMiddleEnd'][k]-sj[side+'Hand'][k] for k in range(3)]
        thumb = [sj[side+'HandThumbEnd'][k]-sj[side+'Hand'][k] for k in range(3)]
        c = cross(middle, thumb)
        areas[side] = math.sqrt(dot(c, c))
        require(areas[side] > .01, 'source digital plane degenerate')

    fixture_blob = fixture_path.read_bytes()
    g, accessor = read_glb(fixture_blob)
    nodes = g['nodes']
    names_to_ids = {n['name']: i for i, n in enumerate(nodes)}
    ancestry = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
    matrices = {}
    def wm(i):
        if i not in matrices:
            matrices[i] = multiply(wm(ancestry[i]), trs(nodes[i])) if i in ancestry else trs(nodes[i])
        return matrices[i]
    conversion = claims['fixture_axes']['blender_to_glb']
    require(conversion == [[1, 0, 0], [0, 0, 1], [0, -1, 0]], 'Blender conversion changed')
    require(dot(conversion[0], cross(conversion[1], conversion[2])) == 1, 'Blender conversion parity changed')
    eye_centers = {}
    for label, x in [('Eye pupil -1', -.078), ('Eye pupil 1', .078), ('Eye white -1', -.078), ('Eye white 1', .078)]:
        node = nodes[names_to_ids[label]]
        require(wm(names_to_ids[label]) == identity(), 'eye mesh world transform changed')
        pts = [p for primitive in g['meshes'][node['mesh']]['primitives'] for p in accessor(primitive['attributes']['POSITION'])]
        center = [(min(p[k] for p in pts)+max(p[k] for p in pts))/2 for k in range(3)]
        # Immutable authored Blender coordinates, independent of candidate calibration.
        authored = [x, -.172 if 'pupil' in label else -.148, 1.672]
        expected = [dot(row, authored) for row in conversion]
        require(close(center, expected), 'eye geometry mismatch: '+label)
        eye_centers[label] = center
    require(claims['fixture_axes']['front'] == [0, 0, 1], 'fixture forward claim contradicts pupil/white geometry')
    require(claims['fixture_axes']['up'] == [0, 1, 0], 'fixture up claim contradicts bind geometry')
    origin = lambda name: [wm(names_to_ids[name])[k][3] for k in range(3)]
    require(origin('head')[1] > origin('pelvis')[1] > origin('root')[1], 'target up bind geometry changed')
    require(cross(claims['fixture_axes']['up'], claims['fixture_axes']['front']) == [1, 0, 0], 'target physical left derivation changed')
    require(claims['fixture_axes']['body_left'] == [1, 0, 0], 'target physical left claim changed')
    require(claims['physical_side_to_suffix'] == {'left': 'R', 'right': 'L'}, 'wrong target physical side/suffix policy')
    for suffix, sign in [('L', -1), ('R', 1)]:
        require(abs(origin('hand.'+suffix)[0]-sign*.57) < 1e-5, 'target hand suffix geometry changed')
        require(abs(origin('foot.'+suffix)[0]-sign*.155) < 1e-5, 'target foot suffix geometry changed')
    residual = 0
    skin = g['skins'][0]
    require(len(skin['joints']) == 18, 'target joint count changed')
    for i, values in zip(skin['joints'], accessor(skin['inverseBindMatrices'])):
        inverse = [[values[c*4+r] for c in range(4)] for r in range(4)]
        product = multiply(wm(i), inverse)
        residual = max(residual, max(abs(product[r][c]-int(r == c)) for r in range(4) for c in range(4)))
    require(residual < 1e-6, 'fixture inverse-bind mismatch')
    # Geometry runs before final exact-byte pins, so geometry mutation controls
    # prove the substantive checks rather than only a checksum failure.
    require(digest(source_blob) == pins['experiments/41-real-short-motion/source-skeleton.json']['sha256'], 'frozen source metadata changed')
    require(digest(fixture_blob) == pins['assets/fixtures/nvwa-humanoid.glb']['sha256'], 'frozen fixture changed')
    require(digest((ROOT/'tools/blender/generate_fixture.py').read_bytes()) == pins['tools/blender/generate_fixture.py']['sha256'], 'authored generator pin changed')
    return {'status': 'PASS', 'scope': claims['ci_scope'], 'fresh_upstream_text_inspection': 'NOT-RUN', 'anatomical_certification': claims['anatomical_certification'], 'original_input_count': len(pins), 'retained_receipt_count': len(retained), 'target_physical_left_suffix': 'R', 'hand_plane_areas_m2': areas, 'inverse_bind_residual': residual, 'eye_centers': eye_centers}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claims', type=Path, default=HERE/'authority-claims.json')
    parser.add_argument('--fixture', type=Path, default=ROOT/'assets/fixtures/nvwa-humanoid.glb')
    parser.add_argument('--source-skeleton', type=Path, default=ROOT/'experiments/41-real-short-motion/source-skeleton.json')
    parser.add_argument('--receipts', type=Path, default=ROOT/'experiments/41-real-short-motion/evidence/source-receipts.json')
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.claims, args.fixture, args.source_skeleton, args.receipts), indent=2))
        return 0
    except (AuditError, KeyError, ValueError, TypeError, OSError, IndexError, struct.error) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}))
        return 1

if __name__ == '__main__':
    sys.exit(main())
