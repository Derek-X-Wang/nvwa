#!/usr/bin/env python3
"""One frozen local-offset candidate; replay30 actual retained frames, no product change."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'experiments/60-b1-continuous-motion'))
from checker import mat, point
from geometry import BVH, norm, sub, strain

CORE = frozenset((182, 244, 246))
SAFETY = frozenset((281, 288, 376, 485, 523, 534, 599, 612))
CLIPS = ('b1_arm_rehearsal_v1', 'b1_knee_flex_v1')
ASSET = REPO / 'assets/characters/mpfb-b1-v1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def unique(part, key):
    result = {}
    require(len(part['source_ids']) == len(part[key]), 'source/render vertex coverage')
    for source, row in zip(part['source_ids'], part[key]):
        require(all(math.isfinite(v) for v in row), 'nonfinite source array')
        if source in result:
            require(max(abs(a-b) for a, b in zip(row, result[source])) <= 1e-5, 'inconsistent duplicated source vertex')
        else:
            result[source] = tuple(row)
    return result


def triangles(part):
    ids = part['source_ids']
    require(len(part['indices']) % 3 == 0, 'triangle index coverage')
    return [tuple(ids[i] for i in part['indices'][k:k+3]) for k in range(0, len(part['indices']), 3)]


def mapping():
    rows = []
    rules = []
    reading = False
    for line in (ASSET / 'garment/female_sportsuit01.mhclo').read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        if fields[0] in ('x_scale', 'y_scale', 'z_scale'):
            rules.append({'axis': ('x_scale', 'y_scale', 'z_scale').index(fields[0]), 'helper_ids': list(map(int, fields[1:3])), 'reference': float(fields[3])})
        if fields[0] == 'verts':
            reading = True
            continue
        if reading:
            if fields[0] == 'delete_verts':
                break
            require(len(fields) == 9, 'unexpected approved MHCLO row')
            weights = list(map(float, fields[3:6]))
            total = sum(weights)
            require(abs(total) > 1e-12, 'zero helper coefficient sum')
            rows.append({'helpers': list(map(int, fields[:3])), 'coefficients': [w/total for w in weights], 'offset': list(map(float, fields[6:9]))})
    require(len(rows) == 1797 and {r['axis'] for r in rules} == {0, 1, 2}, 'approved mapping/rule coverage')
    return rows, sorted(rules, key=lambda r: r['axis'])


def frames(captures):
    paths = sorted(captures.glob('*.json.gz'))
    require(len(paths) == 30, 'exact30 retained keyframes required')
    expected = {(float(t), c, float(k)) for t in (-1, 0, 1) for c in CLIPS for k in range(5)}
    seen = set()
    for path in paths:
        record = json.loads(gzip.decompress(path.read_bytes()))
        snap = record['snapshot']
        request = record['request']
        key = (float(snap['parameters']['torso_length']), snap['sample']['clip_id'], float(snap['sample']['source_seconds']))
        require(key in expected and key not in seen and snap['parameters']['jaw_drop'] == 0, 'unexpected/duplicate frame cohort')
        require(record['kind'] == 'matrix' and request['clip_id'] == key[1] and request['seconds'] == key[2] and snap['sample']['position_seconds'] == key[2], 'actual frame/request binding')
        require(snap['profile_id'] == 'nvwa-mpfb-b1-motion-v1' and len(snap['bones']) == 53, 'wrong source profile/rig')
        seen.add(key)
        yield path, snap, key
    require(seen == expected, 'incomplete30-frame cohort')


def build(captures):
    paths = sorted(captures.glob('*.json.gz'))
    require(len(paths) == 30, 'exact30 input files required')
    first = json.loads(gzip.decompress(paths[0].read_bytes()))['snapshot']
    part = next(p for p in first['parts'] if p['name'] == 'garment')
    tri = triangles(part)
    require(set(tri[200]) == CORE, 'frozen displayed triangle200 changed')
    ring = {i for t in tri if CORE.intersection(t) for i in t} - CORE
    region = sorted(CORE | ring)
    require(len(region) <= 64 and not SAFETY.intersection(region), 'affected boundary/safety identity changed')
    rows, rules = mapping()
    deltas = [{'source_id': i, 'delta': [(0.5 if i in CORE else 0.75) * v - v for v in rows[i]['offset']]} for i in region]
    sources = ['assets/characters/mpfb-b1-v1/manifest.json', 'assets/characters/mpfb-b1-v1/base.obj', 'assets/characters/mpfb-b1-v1/garment/female_sportsuit01.mhclo', 'assets/characters/mpfb-b1-v1/weights.game_engine.json', 'experiments/61-b1-garment-ab/CONTRACT.md', 'experiments/61-b1-garment-ab/rest-fit/compare.py', 'experiments/60-b1-continuous-motion/checker.py', 'experiments/60-b1-continuous-motion/geometry.py']
    provenance = {p: sha(REPO / p) for p in sources}
    return {'schema_version': 1, 'id': 'rest-local-v1', 'source_profile': 'nvwa-mpfb-b1-motion-v1', 'region_source_ids': region, 'weight_overrides': [], 'offset_deltas': deltas, 'offset_scale_rules': rules, 'rule': 'Single fixed local original-offset retention:0.5 on core source IDs182,244,246;0.75 on one incident vertex ring (union of vertices of unchanged triangles touching core minus core);1 outside. Fixed exterior, max64 affected IDs. Delta=(retention-1)*original admitted MHCLO offset, before actual helper pair/reference scaling. Weights, signed coefficients, rig, motion, body, topology unchanged. No tuning, global offset deletion, source clamp or production admission.', 'provenance': provenance}


def area(points, tri):
    a, b, c = [points[i] for i in tri]
    from geometry import cross
    return norm(cross(sub(b, a), sub(c, a))) * 0.5


def groups(tri, region):
    ring = set(region) - CORE
    core_incident = [i for i, t in enumerate(tri) if CORE.intersection(t)]
    ring_incident = [i for i, t in enumerate(tri) if ring.intersection(t) and not CORE.intersection(t)]
    return {'all_affected_incident': [i for i, t in enumerate(tri) if set(region).intersection(t)], 'core_triangle200': [200], 'core_incident': core_incident, 'ring_incident': ring_incident, 'safety_fold_incident': [i for i, t in enumerate(tri) if SAFETY.intersection(t)]}


def descriptors(original, altered, rest, altered_rest, tri, tids):
    subset = [tri[i] for i in tids]
    edges = sorted({tuple(sorted((a, b))) for t in subset for a, b in zip(t, (t[1], t[2], t[0]))})
    absolute = {'triangle_areas_m2': [{'triangle_id': i, 'original': area(original, tri[i]), 'altered': area(altered, tri[i]), 'rest_original': area(rest, tri[i]), 'rest_altered': area(altered_rest, tri[i])} for i in tids], 'edge_lengths_m': [{'source_ids': [a, b], 'original': norm(sub(original[a], original[b])), 'altered': norm(sub(altered[a], altered[b])), 'rest_original': norm(sub(rest[a], rest[b])), 'rest_altered': norm(sub(altered_rest[a], altered_rest[b]))} for a, b in edges]}
    return {'triangle_ids': tids, 'absolute': absolute, 'original': strain(original, rest, subset), 'altered': strain(altered, altered_rest, subset), 'altered_against_original_rest': strain(altered, rest, subset), 'absolute_area_sum_original_m2': sum(area(original, t) for t in subset), 'absolute_area_sum_altered_m2': sum(area(altered, t) for t in subset), 'rest_area_sum_original_m2': sum(area(rest, t) for t in subset), 'rest_area_sum_altered_m2': sum(area(altered_rest, t) for t in subset)}


def query(bvh, points, ids):
    rows = []
    for source in sorted(ids):
        hit = bvh.nearest(points[source])
        rows.append({'source_id': source, 'unsigned_m': hit['distance'], 'local_signed_m': hit['local_signed_projection'], 'nearest_triangle': hit['triangle']})
    return {'vertices': rows, 'negative_over_2mm': sum(r['local_signed_m'] < -.002 for r in rows), 'negative_over_5mm': sum(r['local_signed_m'] < -.005 for r in rows), 'minimum_unsigned_m': min(r['unsigned_m'] for r in rows), 'minimum_local_signed_m': min(r['local_signed_m'] for r in rows), 'claim': 'Nearest oriented triangle-side descriptor; not physical penetration, collision or inside/outside.'}


def body_triangles():
    result = []
    for line in (ASSET / 'base.obj').read_text().splitlines():
        if line.startswith('f '):
            ids = [int(f.split('/')[0])-1 for f in line.split()[1:]]
            if all(i < 13380 for i in ids):
                result.extend((ids[0], ids[k], ids[k+1]) for k in range(1, len(ids)-1))
    return result


def apply_offsets(rest, posed, delta, scales, influences, skins):
    """Apply the same signed rest delta and full-positive LBS path for B and no-op."""
    altered_rest, altered = dict(rest), dict(posed)
    for source, d in delta.items():
        scaled = tuple(scales[k]*d[k] for k in range(3))
        altered_rest[source] = tuple(rest[source][k]+scaled[k] for k in range(3))
        # Actual uploaded baseline remains exact outside the region. Matrix
        # translations cancel in this linear rest-delta skinning response.
        displacement = [0.0]*3
        for j, w in influences[source]:
            for axis in range(3):
                displacement[axis] += w*sum(skins[j][axis][k]*scaled[k] for k in range(3))
        altered[source] = tuple(posed[source][k]+displacement[k] for k in range(3))
    return altered_rest, altered


def evaluate(captures, spec, output):
    require(spec == build(captures), 'candidate differs from the single frozen rule/source set')
    delta = {r['source_id']: tuple(r['delta']) for r in spec['offset_deltas']}
    region = set(spec['region_source_ids'])
    mapping_rows, _ = mapping()
    body_tri = body_triangles()
    records = []
    topology = None
    for path, snap, key in frames(captures):
        body, garment = (next(p for p in snap['parts'] if p['name'] == name) for name in ('body', 'garment'))
        tri = triangles(garment)
        if topology is None:
            topology = tri
        require(tri == topology, 'actual garment topology changed')
        rest, posed = unique(garment, 'rest_positions'), unique(garment, 'positions')
        helpers, body_posed = unique(body, 'rest_positions'), unique(body, 'positions')
        scales = {r['axis']: (helpers[r['helper_ids'][1]][r['axis']] - helpers[r['helper_ids'][0]][r['axis']]) / r['reference'] for r in spec['offset_scale_rules']}
        reconstruction_error = 0.0
        for source, row in enumerate(mapping_rows):
            rebuilt = tuple(sum(helpers[h][axis]*w for h, w in zip(row['helpers'], row['coefficients'])) + scales[axis]*row['offset'][axis] for axis in range(3))
            reconstruction_error = max(reconstruction_error, max(abs(a-b) for a, b in zip(rebuilt, rest[source])))
        require(reconstruction_error <= 1e-5, 'actual helper-reference rest reconstruction mismatch')
        influences = {}
        for source, row in zip(garment['source_ids'], garment['full_joint_influences']):
            total = sum(w for _, w in row)
            require(total > 0 and all(w > 0 and math.isfinite(w) and 0 <= j < 53 for j, w in row), 'invalid complete positive influences')
            normalized = tuple((j, w/total) for j, w in row)
            require(abs(sum(w for _, w in normalized)-1) <= 1e-6, 'normalized influence sum')
            if source in influences:
                require(normalized == influences[source], 'duplicated source influence mismatch')
            influences[source] = normalized
        skins = [mat(b['skin']) for b in snap['bones']]
        lbs_error = 0.0
        for source, p in rest.items():
            rebuilt = [0.0]*3
            for j, w in influences[source]:
                q = point(skins[j], p)
                for axis in range(3):
                    rebuilt[axis] += w*q[axis]
            lbs_error = max(lbs_error, max(abs(a-b) for a, b in zip(rebuilt, posed[source])))
        require(lbs_error <= 1e-5, 'baseline independent LBS disagrees with actual upload')
        altered_rest, altered = apply_offsets(rest, posed, delta, scales, influences, skins)
        noop_rest, noop = apply_offsets(rest, posed, {i: (0., 0., 0.) for i in delta}, scales, influences, skins)
        require(noop == posed and noop_rest == rest, 'same-path no-op control changed actual positions/rest')
        require(all(altered[i] == posed[i] and altered_rest[i] == rest[i] for i in rest if i not in region), 'fixed exterior changed')
        require(all(altered[i] == posed[i] and altered_rest[i] == rest[i] for i in SAFETY), 'independent neutral fold region changed')
        require(all(math.isfinite(v) for points in (altered, altered_rest) for p in points.values() for v in p), 'candidate nonfinite')
        boundary_edges = sorted({tuple(sorted((a, b))) for t in tri for a, b in zip(t, (t[1], t[2], t[0])) if (a in region) != (b in region)})
        grouped = {name: descriptors(posed, altered, rest, altered_rest, tri, tids) for name, tids in groups(tri, region).items()}
        bvh = BVH(body_posed, body_tri)
        signs = {'original_region': query(bvh, posed, region), 'altered_region': query(bvh, altered, region), 'original_safety': query(bvh, posed, SAFETY), 'altered_safety': query(bvh, altered, SAFETY)}
        record = {'frame': path.name, 'capture_sha256': sha(path), 'torso': key[0], 'clip': key[1], 'source_seconds': key[2], 'source_kind': 'actual retained r4 baseline; altered positions are offline f64 rest-delta/full-positive-LBS replay', 'offset_scales': scales, 'groups': grouped, 'full_original_fold': strain(posed, rest, tri), 'full_altered_fold': strain(altered, altered_rest, tri), 'rest_original_fold': strain(rest, rest, tri), 'rest_altered_fold': strain(altered_rest, altered_rest, tri), 'max_rest_displacement_m': max(norm(sub(altered_rest[i], rest[i])) for i in region), 'max_posed_displacement_m': max(norm(sub(altered[i], posed[i])) for i in region), 'core_max_posed_displacement_m': max(norm(sub(altered[i], posed[i])) for i in CORE), 'ring_max_posed_displacement_m': max(norm(sub(altered[i], posed[i])) for i in region-CORE), 'boundary_edges': [{'source_ids': [a,b], 'original_length_m': norm(sub(posed[a],posed[b])), 'altered_length_m': norm(sub(altered[a],altered[b])), 'rest_original_length_m': norm(sub(rest[a],rest[b])), 'rest_altered_length_m': norm(sub(altered_rest[a],altered_rest[b]))} for a,b in boundary_edges], 'local_sign': signs, 'controls': {'no_op_exact': True, 'exterior_exact': True, 'safety_positions_exact': True, 'weights_unchanged': True, 'weight_override_count': 0, 'normalized_weights_source_vertices': len(influences), 'baseline_lbs_max_component_error_m': lbs_error, 'fitted_rest_reconstruction_max_component_error_m': reconstruction_error, 'body_rig_motion_unchanged': True}}
        records.append(record)
        with (output/'frames.jsonl').open('a') as stream:
            stream.write(json.dumps(record, separators=(',', ':'), allow_nan=False)+'\n')
        print(json.dumps({'frame': path.name, 'completed': len(records), 'core_original_area_ratio': grouped['core_triangle200']['original']['maximum_area_ratio'], 'core_altered_area_ratio': grouped['core_triangle200']['altered']['maximum_area_ratio']}), flush=True)
    require(len(records) == 30, 'exact30 evaluations required')
    apex = [r for r in records if r['clip'] == CLIPS[0] and r['source_seconds'] == 2]
    summary = {'candidate_id': spec['id'], 'candidate_sha256': sha(output/'candidate.json') if (output/'candidate.json').exists() else hashlib.sha256(canonical(spec)).hexdigest(), 'frames': len(records), 'affected_ids': sorted(region), 'core_ids': sorted(CORE), 'ring_ids': sorted(region-CORE), 'core_arm_apex_by_torso': [{'torso': r['torso'], **r['groups']['core_triangle200']} for r in apex], 'max_posed_displacement_m': max(r['max_posed_displacement_m'] for r in records), 'max_ring_area_ratio_original': max(r['groups']['ring_incident']['original']['maximum_area_ratio'] for r in records), 'max_ring_area_ratio_altered': max(r['groups']['ring_incident']['altered']['maximum_area_ratio'] for r in records), 'max_full_fold_count_original': max(r['full_original_fold']['fold_candidates_over_150_degrees'] for r in records), 'max_full_fold_count_altered': max(r['full_altered_fold']['fold_candidates_over_150_degrees'] for r in records), 'all_controls_pass': all(all(r['controls'][key] for key in ('no_op_exact','exterior_exact','safety_positions_exact','weights_unchanged','body_rig_motion_unchanged')) for r in records), 'claim': 'One fixed experimental rest-fit comparison; no automatic quality/admission verdict, collision classification, new actual runtime, visual approval or full jaw matrix.'}
    write(output/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('build','evaluate','both'), default='both')
    parser.add_argument('--candidate', type=Path)
    args = parser.parse_args()
    captures, output = args.captures.resolve(), args.output.resolve()
    require(captures.is_dir(), 'capture directory missing')
    output.mkdir(parents=True, exist_ok=False)
    spec = build(captures)
    require(spec == build(captures), 'candidate build is not deterministic')
    if args.candidate:
        require(json.loads(args.candidate.read_bytes()) == spec, 'provided candidate not exact frozen recipe')
    require(args.mode != 'evaluate' or args.candidate is not None, '--mode evaluate requires --candidate')
    write(output/'candidate.json', spec)
    write(output/'inputs.json', {'captures': str(captures), 'output': str(output), 'argv': sys.argv, 'source_profile': spec['source_profile'], 'capture_hashes': {p.name: sha(p) for p in sorted(captures.glob('*.json.gz'))}, 'scope': 'Only supplied retained r4 frames; no live production mutation or source asset alteration.'})
    if args.mode != 'build':
        evaluate(captures, spec, output)
    write(output/'SHA256SUMS.json', {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    print(json.dumps({'candidate_sha256': sha(output/'candidate.json'), 'output': str(output), 'mode': args.mode}))


if __name__ == '__main__':
    main()
