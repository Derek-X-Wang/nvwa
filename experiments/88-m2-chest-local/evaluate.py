#!/usr/bin/env python3
"""Bounded old50 identity, derivative preservation and fixed-source observations."""
import argparse
import json
import math
from pathlib import Path
import signal
import sys
import time
import candidate as c

KEYS = [0, 15, 30, 45, 60, 75, 89]
NAMED_EDGES = [(6497, 6508), (8998, 9001)]


def old_evaluator(candidate50):
    # The unchanged old file imports `candidate` by name. Bind it only while
    # importing, preserving the caller's module and old50's exact gate.
    previous = sys.modules.get('candidate')
    sys.modules['candidate'] = candidate50
    try:
        return c.module('evaluate50_unchanged_for88', 'experiments/50-upper-arm-neutral-ab/evaluate.py')
    finally:
        if previous is None:
            sys.modules.pop('candidate', None)
        else:
            sys.modules['candidate'] = previous


def mechanism_gate(samples):
    c.require([s['key_index'] for s in samples] == KEYS, 'fixed seven edge samples')
    last = samples[-1]
    c.require(len(last['edges']) == 39, 'same39 edge mechanism scope')
    by_edge = {tuple(r['edge']): r for r in last['edges']}
    failures = []
    for edge in NAMED_EDGES:
        c.require(edge in by_edge, 'named original edge present')
        row = by_edge[edge]
        if not row['candidate_length_m'] < row['control_length_m']:
            failures.append('key89 named edge '+str(edge)+' did not shorten')
    if not last['candidate_maximum_length_m'] < last['control_maximum_length_m']:
        failures.append('key89 maximum over same39 edges did not decrease')
    return {'status': 'PASS' if not failures else 'FAIL', 'failures': failures,
            'named_edges': [list(e) for e in NAMED_EDGES],
            'same_edge_count': len(last['edges']), 'key_index': 89}


def partitions(asset, surface):
    node = asset.nodes[22]
    skin = asset.doc['skins'][node['skin']]
    result = {name: [] for name in surface.GROUPS}
    for pi, primitive in enumerate(asset.doc['meshes'][node['mesh']]['primitives']):
        attrs = primitive['attributes']
        js, ws = asset.accessor(attrs['JOINTS_0']), asset.accessor(attrs['WEIGHTS_0'])
        indices = [r[0] for r in asset.accessor(primitive['indices'])]
        c.require(primitive.get('mode', 4) == 4 and len(indices) % 3 == 0, 'original triangle primitives')
        for name, nodes in surface.GROUPS.items():
            flags = [sum(w for slot, w in zip(j, weights) if skin['joints'][slot] in nodes) >= surface.MASS
                     for j, weights in zip(js, ws)]
            result[name] += [[pi, i//3] for i in range(0, len(indices), 3)
                             if all(flags[v] for v in indices[i:i+3])]
    return result


def fixed_geometry(before, after, region):
    edges, faces = region['boundary_edge_indices'], region['incident_face_indices']
    c.require(len(edges) == 39 and len(faces) == 259, 'same39 edges259 faces')
    primitive = before.doc['meshes'][before.nodes[22]['mesh']]['primitives'][1]
    indices = [r[0] for r in before.accessor(primitive['indices'])]
    selected = set(region['vertex_indices'])
    actual_incident = [i//3 for i in range(0, len(indices), 3) if any(v in selected for v in indices[i:i+3])]
    c.require(actual_incident == faces, 'original259 incident source-face IDs')
    samples = []
    for key in KEYS:
        control = before.skin_vertices(key, 22, 1)
        candidate = after.skin_vertices(key, 22, 1)
        edge_rows = []
        for edge in edges:
            row = {'edge': edge}
            for label, points in [('control', control), ('candidate', candidate)]:
                endpoints = [points[v] for v in edge]
                row[label+'_endpoints_m'] = endpoints
                row[label+'_length_m'] = math.dist(*endpoints)
            edge_rows.append(row)
        face_rows = []
        for face in faces:
            vertices = indices[3*face:3*face+3]
            face_rows.append({'source_face_index': face, 'vertex_indices': vertices,
                              'control_points_m': [control[v] for v in vertices],
                              'candidate_points_m': [candidate[v] for v in vertices]})
        samples.append({'key_index': key, 'time_seconds': before.times[key], 'edges': edge_rows,
                        'control_maximum_length_m': max(r['control_length_m'] for r in edge_rows),
                        'candidate_maximum_length_m': max(r['candidate_length_m'] for r in edge_rows),
                        'fixed259_source_faces': face_rows})
    return samples


def run(output):
    old_c, before, region, attrs, positions, names, eligible, pins = c.load_control()
    construction = json.loads((output/'construction.json').read_text())
    c.require(construction['status'] == 'CONSTRUCTED_PENDING_OFFLINE' and construction['real_constructor_calls'] == 1,
              'one successful frozen construction receipt')
    raw = c.ASSET.read_bytes()
    c.require(c.sha(raw) == construction['glb_sha256'], 'constructed derivative hash')
    c.require(c.sha(c.OUT_WORK.read_bytes()) == construction['work_sha256'], 'constructed Work hash')
    new_work = json.loads(c.OUT_WORK.read_text())
    expected_work = json.loads(c.WORK.read_text())
    expected_work['profile']['id'] = 'nvwa-experiment88-chest-local'
    expected_work['character']['profile_id'] = expected_work['profile']['id']
    expected_work['profile']['asset_path'] = 'generated/genuine44-chest-local88.glb'
    expected_work['profile']['asset_sha256'] = c.sha(raw)
    c.require(new_work == expected_work, 'only authorized Work identity fields')
    doc, binary = old_c.export48.decode_glb(raw)
    preservation = c.validate_binary(before.doc, before.binary, doc, binary, attrs, eligible, positions, names)
    original = c.CONTROL.read_bytes()
    c.require(len(raw) == len(original) and raw[:-len(binary)] == original[:-len(before.binary)], 'exact GLB framing and JSON bytes')
    (output/'preservation.json').write_text(json.dumps(preservation, indent=2, allow_nan=False)+'\n')

    old = old_evaluator(old_c)
    # This invocation retains the old complete exact-frozen-rotation-byte check
    # and applies it to saved old50 only. No derivative is passed to old.gate.
    identity = old.gate(c.CONTROL)
    (output/'old50-unchanged-gate.json').write_text(json.dumps(identity, indent=2, allow_nan=False)+'\n')
    after = old_c.candidate_asset(c.ASSET)
    contract = json.loads((c.ROOT/'experiments/50-upper-arm-neutral-ab/CONTRACT.json').read_text())
    direction_rows = []
    for key in range(90):
        bl, bg = before.pose(key)
        al, ag = after.pose(key)
        c.require(al == bl and ag == bg, 'all90 local poses and global transforms exact to old50')
        arms = {}
        for target, node, child in [('upper_arm.R', 7, 6), ('upper_arm.L', 4, 3)]:
            expected = identity['samples'][key]['arms'][target]['source_chest_relative']
            actual = old.direction(ag, node, child)
            component = max(abs(x-y) for x, y in zip(expected, actual))
            angle = old.D.angle(expected, actual)
            c.require(component <= contract['direction_component_tolerance'], 'unchanged source-direction component gate')
            c.require(angle <= contract['direction_angle_tolerance_deg'], 'unchanged source-direction angle gate')
            arms[target] = {'component_error': component, 'angle_error_deg': angle}
        direction_rows.append({'key_index': key, 'arms': arms})
    (output/'motion-preservation.json').write_text(json.dumps({'status': 'PASS', 'keys': 90,
        'all_local_and_global_poses_exact': True, 'source_direction_samples': direction_rows,
        'limits': 'skeleton/source direction preservation; changed surface quality remains HOLD'}, indent=2)+'\n')

    samples = fixed_geometry(before, after, region)
    mechanism = mechanism_gate(samples)
    (output/'fixed-geometry.json').write_text(json.dumps({'source_vertex_ids': region['vertex_indices'],
        'source_edge_ids': region['boundary_edge_indices'], 'source_face_ids': region['incident_face_indices'],
        'samples': samples, 'mechanism': mechanism}, indent=2, allow_nan=False)+'\n')

    # Preserve the unchanged analyzer and its own budget/partition criteria.
    # Counts are supplemental, even when the necessary mechanism has failed.
    sys.path.insert(0, str(c.ROOT/'experiments/49-runtime-pose-parity/offline'))
    surface = c.module('surface49_unchanged_for88', 'experiments/49-runtime-pose-parity/offline/surface.py')
    membership = {}
    for label, asset in [('control', before), ('candidate', after)]:
        surface.Asset = lambda asset=asset: asset
        measured = surface.analyze(keys=KEYS, budget_seconds=60)
        membership[label] = partitions(asset, surface)
        c.require(measured['partition_triangle_counts'] == {k: len(v) for k, v in membership[label].items()},
                  'original surface partition coverage readback')
        (output/(label+'-surface.json')).write_text(json.dumps(measured, indent=2, allow_nan=False)+'\n')
    changes = {}
    for name in surface.GROUPS:
        a, b = set(map(tuple, membership['control'][name])), set(map(tuple, membership['candidate'][name]))
        changes[name] = {'removed_source_faces': sorted(a-b), 'added_source_faces': sorted(b-a),
                         'control_count': len(a), 'candidate_count': len(b)}
    (output/'surface-membership.json').write_text(json.dumps({'source_face_ids_by_partition': membership,
        'changes': changes, 'comparison_limit': 'Count decreases after changed membership are noncomparable coverage, not penetration improvement. Original surface failures remain.'}, indent=2)+'\n')
    result = {'status': 'OFFLINE_PASS' if mechanism['status'] == 'PASS' else 'STOP', 'quality': 'HOLD',
        'glb_sha256': c.sha(raw), 'input_sha256': pins, 'preservation': 'PASS', 'old50_exact_gate': 'PASS',
        'all90_motion_and_source_direction': 'PASS', 'mechanism': mechanism,
        'surface': 'SUPPLEMENTAL_MEASURED', 'real_constructor_calls_in_evaluator': c.REAL_CONSTRUCTOR_CALLS,
        'cli_web_released': False, 'retry_authorized': False,
        'limits': ['offline PASS only permits root to consider CLI/Web release',
                   'normal/shading, between-key surface, roll, contact, hidden surfaces and visible benefit unproved']}
    c.require(c.REAL_CONSTRUCTOR_CALLS == 0, 'evaluator never calls candidate constructor')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    c.require(args.output.is_dir() and not (args.output/'offline.json').exists(), 'existing construction directory / fresh offline receipt')
    started = time.monotonic()
    c.hard_stop(240)
    try:
        result = run(args.output)
        code = 0 if result['status'] == 'OFFLINE_PASS' else 1
    except Exception as error:
        result = {'status': 'STOP', 'quality': 'HOLD', 'error': str(error),
                  'real_constructor_calls_in_evaluator': c.REAL_CONSTRUCTOR_CALLS,
                  'cli_web_released': False, 'retry_authorized': False}
        code = 1
    signal.alarm(0)
    result['elapsed_seconds'] = time.monotonic()-started
    (args.output/'offline.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
