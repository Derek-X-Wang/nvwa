"""Authenticate actual MPFB modifier outputs and compare historical Nvwa captures.

Independent stdlib matrix/geometry replay is diagnostic, never original-tool output.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/70-b1-garment-defect'))
from diagnose import Source, area, component_error, delta, lbs, norm, point, require, transfer, vector

DRIVER_SHA = '16b65d928bfa8c5988d144ecdf462a8322c40ab7becdd4c7811e560452b53087'
INPUT_SHA = '95678a63e88288a10ad0e9a71e5aadf889f7d3033cdddb35c0f425fb9c303099'
CAPTURE_SHAS = {
    'arm0': '1a310480d1a9e3934bce23678c4a74c05d0e110eaf68f2674b172dee1b5009d3',
    'arm2': '5df0c97e5c51b3e71741e115ca4040d441189dd5853a505c1076d9ed0a53ae5e',
    'knee2': 'e99893c5cf5c7b24890f10f35d22bd01da3ea32e880e7ecf4533e3b8c285364b',
}
CORE = (246, 244, 182)
C = [[1,0,0,0], [0,0,-1,0], [0,1,0,0], [0,0,0,1]]
CI = [list(row) for row in zip(*C)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mm(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def inverse(a):
    rows = [list(row) + [float(r == c) for c in range(4)] for r, row in enumerate(a)]
    for c in range(4):
        pivot = max(range(c, 4), key=lambda r: abs(rows[r][c]))
        require(abs(rows[pivot][c]) > 1e-12, 'singular reference matrix')
        rows[c], rows[pivot] = rows[pivot], rows[c]
        denominator = rows[c][c]
        rows[c] = [x / denominator for x in rows[c]]
        for r in range(4):
            if r != c:
                factor = rows[r][c]
                rows[r] = [x - factor * y for x, y in zip(rows[r], rows[c])]
    return [row[4:] for row in rows]


def column(a):
    return [a[r][c] for c in range(4) for r in range(4)]


def matrix(value):
    require(isinstance(value, list) and len(value) == 4, 'reference matrix rows')
    require(all(isinstance(row, list) and len(row) == 4 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in row) for row in value), 'reference matrix shape/finite')
    return value


def geometry(positions):
    points = [positions[i] for i in CORE]
    edges = [norm(delta(points[i], points[j])) for i, j in ((0,1), (1,2), (2,0))]
    a = area(points)
    return dict(area_m2=a, edge_lengths_m=edges, height_to_longest_edge_m=2*a/max(edges))


def compare_case(case, reference, source):
    label = case['case']
    require(reference['case'] == label and reference['historical_input_sha256'] == CAPTURE_SHAS[label] == case['sha256'], 'case/capture identity mismatch')
    require(len(reference['positions']) == len(reference['rest_positions']) == len(reference['weights']) == 1797, 'reference source mesh coverage')
    for key in ('positions', 'rest_positions'):
        for v in reference[key]:
            vector(v)
    names = [b['name'] for b in case['bones']]
    original_names = [b['name'] for b in reference['bones']]
    require(len(names) == len(set(names)) == 53 and len(original_names) == len(set(original_names)) == 53 and set(names) == set(original_names), 'reference53-bone identity mismatch')
    byname = {b['name']: b for b in reference['bones']}
    original_skin, rest_error, skin_error = [], 0., 0.
    for b in case['bones']:
        rb = byname[b['name']]
        r, p = matrix(rb['matrix_local']), matrix(rb['matrix'])
        canonical = column(mm(CI, r))
        skin = column(mm(mm(mm(CI, p), inverse(r)), C))
        rest_error = max(rest_error, component_error(canonical, b['canonical_rest']))
        skin_error = max(skin_error, component_error(skin, b['skin']))
        original_skin.append(dict(skin=skin))
    require(rest_error < 1e-4, 'reference canonical rest mismatch')
    require(skin_error < 1e-4, 'reference authored skin mismatch')
    require(reference['modifiers'] == [dict(name='Armature', type='ARMATURE', show_viewport=True, preserve_volume=False)], 'reference modifier policy mismatch')
    original_rows = []
    for weights in reference['weights']:
        require(bool(weights) and set(weights).issubset(names) and all(math.isfinite(w) and w > .001 for w in weights.values()), 'reference bone weight policy/identity mismatch')
        original_rows.append([(names.index(n), w) for n, w in weights.items()])
    replay = [lbs(rest, row, original_skin) for rest, row in zip(reference['rest_positions'], original_rows)]
    replay_error = max(component_error(a,b) for a,b in zip(replay,reference['positions']))
    require(replay_error < 1e-5, 'reference modifier/LBS reconstruction mismatch')
    rust_rest = [case['garment_rest'][str(i)] for i in range(1797)]
    rust_posed = [case['garment_posed'][str(i)] for i in range(1797)]
    rest_difference = max(component_error(a,b) for a,b in zip(rust_rest,reference['rest_positions']))
    require(rest_difference < 1e-5, 'reference fitted rest/source ID mismatch')
    rust_rows = [transfer(row, names, source.weights) for row in source.mapping]
    # Same historical Nvwa skin matrices in all four analytical combinations.
    swaps = {}
    for label_rest, rests in [('rust', rust_rest), ('mpfb', reference['rest_positions'])]:
        for label_weights, rows in [('rust', rust_rows), ('mpfb', original_rows)]:
            posed = [lbs(rests[i], rows[i], case['bones']) for i in CORE]
            swaps[label_rest + '_rest_' + label_weights + '_weights'] = area(posed) / area([rests[i] for i in CORE])
    metrics = dict(rust_rest=geometry(rust_rest), rust_posed=geometry(rust_posed), original_rest=geometry(reference['rest_positions']), original_modifier_posed=geometry(reference['positions']))
    ratios = dict(rust=metrics['rust_posed']['area_m2']/metrics['rust_rest']['area_m2'],
                  original_modifier=metrics['original_modifier_posed']['area_m2']/metrics['original_rest']['area_m2'],
                  original_driver_float=reference['posed_over_rest_area'])
    require((ratios['original_modifier'] > 10) == (case['case'] == 'arm2'), 'reference witness/control signal mismatch')
    selected=[]
    for i in CORE:
        selected.append(dict(source_id=i, rust_normalized_weights={names[j]:w for j,w in rust_rows[i]},
            original_raw_weights=reference['weights'][i],
            original_normalized_weights={names[j]:w/sum(reference['weights'][i].values()) for j,w in original_rows[i]},
            rust_displacement_m=delta(rust_posed[i],rust_rest[i]),
            original_displacement_m=delta(reference['positions'][i],reference['rest_positions'][i])))
    return dict(case=case['case'], historical_capture_sha256=case['sha256'], ratios=ratios, geometry=metrics,
        all1797_rest_max_component_difference_m=rest_difference,
        all1797_posed_max_component_difference_m=max(component_error(a,b) for a,b in zip(rust_posed,reference['positions'])),
        canonical_rest_matrix_max_component_error=rest_error, authored_skin_matrix_max_component_error=skin_error,
        actual_original_modifier_lbs_max_component_error_m=replay_error, selected=selected,
        analytical_same_historical_skin_swaps=swaps,
        analytical_swaps_scope='Counterfactual arithmetic on actual frozen rest/weights; not Blender execution or a product candidate')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--freeze', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a=p.parse_args()
    require(not a.out.exists(), 'output must be new')
    require(digest(a.prepared) == INPUT_SHA, 'prepared input frozen hash mismatch')
    freeze=json.loads(a.freeze.read_text())
    require(freeze['prepared_input_sha256'] == INPUT_SHA and freeze['driver_sha256'] == DRIVER_SHA, 'freeze source identity mismatch')
    for rel, expected in freeze['run_files'].items():
        require(digest(a.run/rel) == expected, 'original run frozen hash mismatch: '+rel)
    execution=json.loads((a.run/'execution.json').read_text())
    require(execution['exit_code'] == 0 and not execution['timed_out'] and execution['declared_threads'] == 1 and execution['no_render_requested'], 'reference execution failed')
    summary=json.loads((a.run/'reference/summary.json').read_text())
    require(summary['input_sha256'] == INPUT_SHA and summary['driver_sha256'] == DRIVER_SHA and summary['mpfb_version'] == [2,0,18] and summary['original_tool_reference_executed'] and not summary['rendering_executed'], 'original reference source identity')
    require([c['case'] for c in summary['cases']] == ['arm0','arm2','knee2'], 'original case coverage')
    inputs=json.loads(a.prepared.read_text())
    require([c['case'] for c in inputs['cases']] == ['arm0','arm2','knee2'], 'prepared case coverage')
    source=Source(ROOT/'assets/characters/mpfb-b1-v1')
    require(inputs['triangles'] == source.triangles and source.triangles[200] == list(CORE), 'source triangle identity mismatch')
    cases=[compare_case(c,json.loads((a.run/'reference'/ (c['case']+'.json')).read_text()),source) for c in inputs['cases']]
    result=dict(schema_version=1, scope='Actual new offline Blender/MPFB modifier outputs versus authenticated historical Nvwa CPU captures',
        blender_version=summary['blender_version'], mpfb_version=summary['mpfb_version'], original_execution_seconds=execution['elapsed_seconds'],
        driver_sha256=DRIVER_SHA, prepared_input_sha256=INPUT_SHA, original_run_freeze_sha256=digest(a.freeze),
        source_triangle=list(CORE), body_recipe=dict(torso_length=1.,jaw_drop=0.), original_author_recipe='UNKNOWN',
        cases=cases, candidate='NONE', product_policy='UNCHANGED: all positive aggregate influences', quality='HOLD',
        limitations=['No original author body recipe authentication','Historical Nvwa CPU captures; no fresh product capture','No rendering, visual acceptance, GPU or performance evidence','Analytical swaps isolate numerical effects only; no new correction candidate'])
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({c['case']:c['ratios'] for c in cases}))


if __name__ == '__main__':
    main()
