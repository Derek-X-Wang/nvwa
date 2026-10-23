#!/usr/bin/env python3
"""Read-only v4 blocker requery. No author, candidate, fitting-policy or runtime API.

Required inputs are pinned by the existing public v4 outcome. The old corpus is
authenticated against its preserved capture capsule, not today's source tree.
Only source rest geometry is re-queried. No posed body/candidate is synthesized.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import time

from geometry import need, interpolate, nearest, feature, norm, sub

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'experiments/85-current19-shoulder-refit'))
import current19
import provenance


def load(path):
    return current19.strict_load(path.read_bytes())


def identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pinned(path, expected):
    value = identity(path)
    need(all(value[k] == expected[k] for k in ('bytes', 'sha256')), 'input identity differs: '+str(path))
    return value


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def sum32(values):
    value = 0.
    for item in values:
        value = f32(value+item)
    return value


def read_obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'v':
            vertices.append([f32(float(v)) for v in words[1:4]])
        elif words[0] == 'f':
            face = [int(v.split('/')[0])-1 for v in words[1:]]
            need(len(face) >= 3 and all(0 <= s < len(vertices) for s in face), 'unsupported OBJ face')
            faces.append(face)
    return vertices, faces


def read_mapping(path):
    axes, rows, section = {}, [], False
    text = path.read_text()
    for line in text.splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        if words[0] in ('x_scale', 'y_scale', 'z_scale'):
            need(words[0][0] not in axes and len(words) == 4, 'invalid mapping scale')
            axes[words[0][0]] = (int(words[1]), int(words[2]), f32(float(words[3])))
        if words == ['verts', '0']:
            section = True
            continue
        if words[0] == 'delete_verts':
            break
        if section:
            need(len(words) in (1, 9), 'unsupported mapping row')
            if len(words) == 1:
                rows.append({'helpers': [int(words[0])], 'weights': [1.], 'offset': [0.]*3})
            else:
                weights = [f32(float(x)) for x in words[3:6]]
                total = sum32(weights)
                if abs(total) > 2**-23:
                    weights = [f32(x/total) for x in weights]
                rows.append({'helpers': list(map(int, words[:3])), 'weights': weights,
                             'offset': [f32(float(x)) for x in words[6:9]]})
    need(set(axes) == set('xyz') and rows, 'missing mapping scales/rows')
    deleted = set()
    for match in re.finditer(r'(\d+)(?:\s*-\s*(\d+))?', text.split('delete_verts', 1)[1]):
        lo, hi = int(match[1]), int(match[2] or match[1])
        need(lo <= hi, 'reversed mask range')
        deleted.update(range(lo, hi+1))
    return axes, rows, deleted


def fit(cage, axes, rows):
    scales = [f32(f32(cage[axes[key][1]][axis]-cage[axes[key][0]][axis])/axes[key][2])
              for axis, key in enumerate('xyz')]
    points = [[f32(sum32(f32(cage[s][axis]*w) for s, w in zip(row['helpers'], row['weights']))+
                   f32(scales[axis]*row['offset'][axis])) for axis in range(3)] for row in rows]
    return points, scales


def positive_aggregates(row, bone_names, weights):
    """Signed helper transfer, then positive final aggregates; no top-four limit."""
    result = []
    for joint, name in enumerate(bone_names):
        source = weights.get(name, {})
        weight = 0.
        for sid, coefficient in zip(row['helpers'], row['weights']):
            w = source.get(sid, 0.)
            if w > 0:
                weight = f32(weight+f32(w*coefficient))
        if weight > 0:
            result.append([joint, weight])
    return result


def read_face_groups(path):
    group, groups = '', []
    for line in path.read_text().splitlines():
        words = line.split()
        if words and words[0] == 'g':
            group = ' '.join(words[1:])
        elif words and words[0] == 'f':
            groups.append(group)
    return groups


def surfaces(faces, deleted, groups=None):
    full, displayed, ownership = [], [], []
    for fi, sources in enumerate(faces):
        helper = any(s >= 13380 for s in sources)
        masked = all(s in deleted for s in sources)
        group = groups[fi] if groups is not None else 'synthetic'
        ownership.append({'obj_face0': fi, 'obj_group': group, 'sources': sources, 'helper_excluded': helper,
                          'garment_delete_all_vertices': masked, 'displayed': not (helper or masked)})
        if helper:
            continue
        for fan in range(1, len(sources)-1):
            row = {'obj_face0': fi, 'obj_group': group, 'fan_triangle0': fan-1,
                   'sources': [sources[0], sources[fan], sources[fan+1]]}
            full.append(row)
            if not masked:
                displayed.append(row)
    return full, displayed, ownership


def topology(triangles):
    edges = defaultdict(list)
    vertices = defaultdict(list)
    for ti, tri in enumerate(triangles):
        sources = tri['sources']
        for s in sources:
            vertices[s].append(ti)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((sources[i], sources[j])))].append((ti, sources[i], sources[j]))
    counts = Counter(len(v) for v in edges.values())
    flips = [edge for edge, rows in edges.items()
             if len(rows) == 2 and rows[0][1:] == rows[1][1:]]
    return edges, vertices, {'triangles': len(triangles), 'vertices_used': len(vertices),
                             'edges_by_incidence': dict(sorted(counts.items())),
                             'inconsistent_directed_edge_pairs': len(flips),
                             'closed_two_manifold_edge_test': set(counts) == {2} and not flips}


def classify(hit, edges, vertices, ownership):
    found = feature(hit)
    sources = found['sources']
    if found['kind'] == 'interior':
        incident = [hit['triangle0']]
        boundary_edges = []
    elif found['kind'] == 'edge':
        incident = [r[0] for r in edges[tuple(sources)]]
        boundary_edges = [sources] if len(incident) == 1 else []
    else:
        incident = vertices[sources[0]]
        boundary_edges = [list(edge) for edge, rows in edges.items() if sources[0] in edge and len(rows) == 1]
    adjacent = [row for row in ownership if set(sources).issubset(row['sources'])]
    mask_boundary = any(not row['helper_excluded'] and row['garment_delete_all_vertices'] for row in adjacent)
    return {**found, 'incident_triangle_ids': incident, 'boundary_edges': boundary_edges,
            'is_mask_boundary_feature': bool(boundary_edges and mask_boundary),
            'original_obj_polygon_ownership': adjacent}


def run(archive, out):
    started = time.monotonic()
    audit_source = identity(Path(__file__))
    geometry_source = identity(Path(__file__).with_name('geometry.py'))
    public_path = ROOT/'experiments/85-current19-shoulder-refit/evidence/feature-v4-outcome.json'
    public = load(public_path)
    v4 = archive/'2026-10-22-shoulder-feature-v4'
    old = archive/'2026-10-21-current19-baseline'
    corpus = old/'current19-baseline-v2'
    capsule = old/'capture-source-capsule-v2'
    receipt_path = v4/'one-feature-refit-v4/authoring-receipt.json'
    inputs = {'public_v4_summary': identity(public_path),
              'v4_rejected_receipt': pinned(receipt_path, public['authoring_receipt']),
              'v4_freeze': pinned(v4/'AUTHORING-FREEZE-v4.json', public['freeze'])}
    freeze, receipt = load(v4/'AUTHORING-FREEZE-v4.json'), load(receipt_path)
    need(receipt['status'] == 'REJECT_AUTHORING_SINGLE_ATTEMPT' and receipt['candidate_created'] is False,
         'not original rejected v4 receipt')
    need(len(freeze['execution_files']) == 309 and
         provenance.inventory_digest(freeze['execution_files']) == public['source_identity']['execution_files_sha256'],
         'old v4 source closure identity differs')
    for row in freeze['execution_files']:
        pinned(ROOT/row['path'], row)
        pinned(v4/'reviewed-source-v2'/row['path'], row)
    records = provenance._authenticate(corpus, public['baseline']['manifest_sha256'],
                                       public['source_identity']['capture_source_sha256'], capsule)
    anchor = records[-1]['snapshot']
    need(len(records) == 19, 'incomplete corpus')
    inputs['corpus_manifest'] = identity(corpus/'manifest.json')
    inputs['capture_source_inventory'] = identity(corpus/'source-before.json')
    inputs['original_v3_rejection'] = pinned(Path(freeze['previous_rejection']['path']), freeze['previous_rejection'])
    inputs['previous_all19_independent_audit'] = pinned(Path(freeze['independent_audit']['path']), freeze['independent_audit'])
    need(inputs['previous_all19_independent_audit']['sha256'] == public['baseline']['independent_audit_sha256'],
         'prior audit public binding differs')
    # Preserve the known proper-crossing failure and all its original source/input bytes.
    cross_path = old/'data-audit/old-rejection-red-control.json'
    crossing = load(cross_path)
    need(crossing['status'] == 'PASS_REAL_OLD_REJECTION_RED_CONTROL', 'old crossing evidence absent')
    inputs['old_crossing_red_evidence'] = identity(cross_path)
    for row in crossing['source_closure']+list(crossing['known_inputs'].values()):
        pinned(Path(row['path']), row)
    # No import of old authoring/evaluation geometry; only provenance admission above.
    source = ROOT/'assets/characters/mpfb-b1-v1'
    source_files = ('base.obj', 'body.mhclo', 'garment/female_sportsuit01.obj',
                    'garment/female_sportsuit01.mhclo', 'weights.game_engine.json', 'rig.game_engine.json')
    capture = load(corpus/'source-before.json')
    source_rows = {r['path']: r for r in capture['files']}
    for name in source_files:
        relative = 'assets/characters/mpfb-b1-v1/'+name
        inputs[name] = pinned(source/name, source_rows[relative])
        need((source/name).read_bytes() == (capsule/relative).read_bytes(), 'source/capsule mismatch')
    cage, faces = read_obj(source/'base.obj')
    need(len(cage) == 19158 and {str(i): p for i, p in enumerate(cage)} ==
         receipt['neutral_inputs']['raw_neutral_helper_cage'], 'neutral helper cage differs')
    axes, mapping, deleted = read_mapping(source/'garment/female_sportsuit01.mhclo')
    fitted, scales = fit(cage, axes, mapping)
    need(len(mapping) == 1797, 'garment source count differs')
    groups = read_face_groups(source/'base.obj')
    need(len(groups) == len(faces), 'OBJ group/face coverage differs')
    full, displayed, ownership = surfaces(faces, deleted, groups)
    need(all(row['obj_group'] == 'body' for row in full), 'nonbody group entered real-body comparison')
    need(all(row['helper_excluded'] == (row['obj_group'] != 'body') for row in ownership),
         'real-body group and production source-ID exclusion disagree')
    group_counts = {}
    for group in sorted(set(groups)):
        own = [row for row in ownership if row['obj_group'] == group]
        group_counts[group] = {'polygons': len(own),
                               'excluded_source_id_ge13380': sum(row['helper_excluded'] for row in own),
                               'displayed_polygons': sum(row['displayed'] for row in own),
                               'garment_deleted_real_polygons': sum(not row['helper_excluded'] and
                                  row['garment_delete_all_vertices'] for row in own)}
    parts = {p['name']: p for p in anchor['parts']}
    for name, part in parts.items():
        need(set(part['source_ids']) == set(range(19158 if name == 'body' else 1797)), 'raw source coverage differs')
        need(len(part['full_joint_influences']) == len(part['source_ids']), 'raw influence coverage differs')
        need(all(row and all(type(j) is int and type(w) in (int, float) and w > 0 for j, w in row)
                 for row in part['full_joint_influences']), 'nonpositive/empty raw full influence row')
    body_map = [line.split() for line in (source/'body.mhclo').read_text().split('verts 0', 1)[1].splitlines()
                if line.split()]
    need(body_map == [[str(i)] for i in range(19158)], 'body mapping is not complete source identity')
    weight_source = load(source/'weights.game_engine.json')['weights']
    weight_source = {name: {sid: f32(w) for sid, w in rows} for name, rows in weight_source.items()}
    bone_names = [b['name'] for b in anchor['bones']]
    weight_counts = {}
    for name, part in parts.items():
        source_mapping = (mapping if name == 'garment' else
                          [{'helpers': [sid], 'weights': [1.]} for sid in range(19158)])
        aggregate_rows = [positive_aggregates(row, bone_names, weight_source) for row in source_mapping]
        need([aggregate_rows[sid] for sid in part['source_ids']] == part['full_joint_influences'],
             'source complete positive aggregate rows differ: '+name)
        weight_counts[name] = {'source_rows': len(aggregate_rows), 'render_rows': len(part['source_ids']),
                               'max_positive_influences': max(map(len, aggregate_rows)),
                               'rows_above_four_influences': sum(len(row) > 4 for row in aggregate_rows),
                               'source_to_raw_exact_match': True}
    part = parts['body']
    actual = [[part['source_ids'][i] for i in part['indices'][k:k+3]] for k in range(0, len(part['indices']), 3)]
    need(actual == [r['sources'] for r in displayed], 'display topology differs from actual corpus')
    cloth = parts['garment']
    cloth_triangles = [[cloth['source_ids'][i] for i in cloth['indices'][k:k+3]]
                       for k in range(0, len(cloth['indices']), 3)]
    _, obj_cloth_faces = read_obj(source/'garment/female_sportsuit01.obj')
    need(cloth_triangles == [[face[0], face[j], face[j+1]] for face in obj_cloth_faces
                            for j in range(1, len(face)-1)], 'garment source face order differs')
    support_path = ROOT/'experiments/84-shoulder-rest-refit/authoring/support-proposal.json'
    support = load(support_path)
    need(identity(support_path)['sha256'] == public['source_identity']['support_sha256'], 'support hash differs')
    need(len(receipt['logical_samples']) == 581 and len(receipt['planes']) == 623, 'old counts differ')
    blockers = [r for r in receipt['planes'] if abs(r['slope']) <= 1e-12 and r['d_m'] < .001]
    need(len(blockers) == 30 and len({r['logical_sample0'] for r in blockers}) == 27 and
         len({r['body_triangle0'] for r in blockers}) == 16, 'blocker set differs')
    need(all(r['slope'] == 0 for r in blockers), 'fixed blocker slope differs')
    indices = [v['logical_sample0'] for v in blockers]
    maps = {name: topology(tris) for name, tris in (('displayed', displayed), ('unmasked_real_body', full))}
    logical_results = {}
    query_count = Counter()
    for i in sorted(set(indices)):
        sample = receipt['logical_samples'][i]
        need(sample['logical_sample0'] == i and sample['sources'] == cloth_triangles[sample['triangle0']],
             'blocker logical/source identity differs')
        point = interpolate([fitted[s] for s in sample['sources']], sample['barycentric'])
        active = [s for s, w in zip(sample['sources'], sample['barycentric']) if w != 0]
        need(all(s not in support['position_source_ids'] for s in active), 'blocker active source has support')
        queries = {}
        for name, triangles in (('displayed', displayed), ('unmasked_real_body', full)):
            hits = nearest(point, cage, triangles)
            query_count[name] += 1
            edges, vertices, _ = maps[name]
            queries[name] = [{**hit, 'feature': classify(hit, edges, vertices, ownership)} for hit in hits]
        need([r['triangle0'] for r in queries['displayed']] == sample['nearest_face_ids'],
             'independent displayed nearest face set differs')
        logical_results[i] = {'logical_sample0': i, 'garment_triangle0': sample['triangle0'],
                              'garment_sources': sample['sources'], 'barycentric': sample['barycentric'],
                              'active_sources_outside_patch': active, 'source_neutral_point': point, **queries}
    rows = []
    for old_row in blockers:
        i, ti = old_row['logical_sample0'], old_row['body_triangle0']
        result = logical_results[i]
        hit = next(h for h in result['displayed'] if h['triangle0'] == ti)
        need(abs(hit['supporting_plane_projection_m']-old_row['d_m']) <= 1e-12 and
             abs(hit['distance_squared_m2']-old_row['plane']['distance_squared_m2']) <= 1e-12 and
             norm(sub(hit['point'], old_row['plane']['point'])) <= 1e-10,
             'independent retained inequality differs')
        rows.append({'logical_sample0': i, 'body_triangle0': ti, 'retained_d_m': old_row['d_m'],
                     'retained_slope': old_row['slope'], 'reconstructed_zero_direction': [0., 0., 0.],
                     'displayed': hit, 'unmasked_real_body': result['unmasked_real_body']})
    # Original117 bytes remain exact in the new checkout too; inspect no historical gate body.
    protected = load(old/'HISTORICAL-PROTECTION.json')
    need(len(protected['files']) == 117, 'historical protected count differs')
    for row in protected['files']:
        pinned(ROOT/row['path'], row)
    report = {'schema_version': 1, 'kind': 'nvwa86-local-clearance-diagnostic-v1',
              'status': 'PASS_BOUNDED_BLOCKER_REQUERY_NOT_CONTACT_POLICY',
              'inputs': inputs, 'audit_source': audit_source,
              'geometry_source': geometry_source,
              'corpus': {'authenticated_raw_records': 20, 'authenticated_gzip_cases': 19,
                         'full19_geometry_rerun': 'NOT-RUN; original hash-bound audit retained',
                         'capture_capsule': str(capsule), 'body_vertices': len(cage),
                         'garment_mapping_rows': len(mapping), 'signed_mapping_rows':
                         sum(any(w < 0 for w in row['weights']) for row in mapping),
                         'f32_offset_scales': scales, 'full_positive_weights': weight_counts,
                         'posed_skin_arithmetic': 'NOT-RUN; raw anchor aggregate weights only'},
              'surfaces': {name: info[2] for name, info in maps.items()},
              'source_obj_groups': group_counts,
              'body_mask': {'owner': 'garment/female_sportsuit01.mhclo:delete_verts',
                            'deleted_source_ids': len(deleted),
                            'predicate': 'omit polygon if any ID >=13380 OR all IDs in garment delete_verts',
                            'unmasked_comparison_change': 'omit only the all-IDs-in-delete_verts predicate'},
              'queries': dict(query_count), 'retained_fixed_inequalities': len(rows),
              'unique_blocker_logical_samples': len(logical_results),
              'unique_blocker_body_faces': len(set(r['body_triangle0'] for r in rows)),
              'displayed_features_by_inequality': dict(Counter(r['displayed']['feature']['kind'] for r in rows)),
              'displayed_mask_boundary_inequalities': sum(r['displayed']['feature']['is_mask_boundary_feature'] for r in rows),
              'displayed_distance_m_range': [min(r['displayed']['bounded_distance_m'] for r in rows),
                                             max(r['displayed']['bounded_distance_m'] for r in rows)],
              'unmasked_distance_m_range': [min(h['bounded_distance_m'] for r in rows for h in r['unmasked_real_body']),
                                            max(h['bounded_distance_m'] for r in rows for h in r['unmasked_real_body'])],
              'surface_only_change_under_original_fixed_margin_model': {
                  'zero_direction_logical_samples': len(logical_results),
                  'unmasked_inequalities': sum(len(row['unmasked_real_body']) for row in logical_results.values()),
                  'unmasked_below_1mm_inequalities': sum(h['supporting_plane_projection_m'] < .001
                      for row in logical_results.values() for h in row['unmasked_real_body']),
                  'unmasked_below_1mm_logical_samples': sum(any(h['supporting_plane_projection_m'] < .001
                      for h in row['unmasked_real_body']) for row in logical_results.values()),
                  'unmasked_negative_projection_inequalities': sum(h['supporting_plane_projection_m'] < 0
                      for row in logical_results.values() for h in row['unmasked_real_body']),
                  'interpretation': 'Still infeasible with unchanged patch/1mm supporting-plane model. No inside/outside conclusion.'},
              'rows': rows, 'logical_samples': list(logical_results.values()),
              'preserved': {'historical117_exact_bytes': True, 'old_v3_rejection': True,
                            'old_v4_rejection': True, 'old_crossing_source_and_inputs': True,
                            'v4_309_source_files_and_capsule_exact_bytes': True},
              'not_run': ['other554 logical nearest queries', 'full30 source-direction reconstruction',
                          'new contact predicate or inside/outside classification', 'posed full body reconstruction',
                          'old crossing algorithm replay', 'new authoring/refit/candidate/scoring',
                          'build/capture/download/model/GPU/UI', 'Web A/B and CLI candidate exchange'],
              'elapsed_seconds': time.monotonic()-started}
    # Fail if any consulted immutable evidence/source changed during the queries.
    for row in inputs.values():
        pinned(Path(row['path']), row)
    pinned(Path(__file__), audit_source)
    pinned(Path(__file__).with_name('geometry.py'), geometry_source)
    need(not out.exists(), 'diagnostic output exists; choose a new output path')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('inputs', 'rows', 'logical_samples')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.archive.resolve(), args.out.resolve())
