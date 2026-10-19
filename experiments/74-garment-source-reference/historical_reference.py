"""Compare authenticated retained MPFB static output. Does not execute Blender."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/70-b1-garment-defect'))
from diagnose import area, component_error, sha


def require(ok, message):
    if not ok:
        raise ValueError(message)


def y_up(p):
    return [p[0], p[2], -p[1]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    require(not a.out.exists(), 'output already exists')
    summary_path = ROOT / 'experiments/53-character-comparison/reference/reference-summary.json'
    public_summary = json.loads(summary_path.read_text())
    retained_summary = json.loads((a.reference / 'summary.json').read_text())
    require(public_summary == retained_summary, 'retained/public summary differs')
    require(sha((ROOT / 'experiments/53-character-comparison/reference/core_smoke.py').read_bytes()) == public_summary['driver_sha256'], 'retained original-tool driver identity differs')
    entry = next(x for x in public_summary['cases'] if x['case_id'] == 'body-positive')
    raw = (a.reference / entry['path']).read_bytes()
    require(sha(raw) == entry['sha256'], 'retained original-tool result hash differs')
    ref = json.loads(raw)
    require(ref['case_id'] == 'body-positive' and ref['recipe'] == {'torso_length': 1., 'jaw_drop': 0.}, 'historical recipe differs')
    require(ref['garment_executed'] is True and len(ref['positions']) == 19158 and len(ref['garment_positions']) == 1797, 'reference geometry incomplete')
    identity = [[float(i == j) for j in range(4)] for i in range(4)]
    require(all(ref[k] == identity for k in ('body_world', 'rig_world', 'garment_world')), 'unexpected reference placement')
    require(sha(a.prepared.read_bytes()) == json.loads(a.prepared.with_name('preparation.json').read_text())['prepared_input_sha256'], 'prepared inputs changed')
    prepared = json.loads(a.prepared.read_text())
    actual = next(c for c in prepared['cases'] if c['case'] == 'arm0')
    cage = [y_up(p) for p in ref['positions']]
    cloth = [y_up(p) for p in ref['garment_positions']]
    cage_error = max(component_error(p, actual['cage'][str(i)]) for i, p in enumerate(cage))
    require(cage_error < 1e-5, 'original/current complete cage differs beyond original numeric tolerance')
    core = (246, 244, 182)
    original_area = area([cloth[i] for i in core])
    actual_area = area([actual['garment_rest'][str(i)] for i in core])
    report = dict(schema_version=1, scope='Historical actual MPFB static reference versus historical actual Nvwa arm0 fitted rest; no new Blender execution or posed equivalence',
        original_reference_sha256=entry['sha256'], public_summary_sha256=sha(summary_path.read_bytes()),
        original_blender_version=public_summary['blender_version'], original_mpfb_version=public_summary['mpfb_version'],
        body_recipe=ref['recipe'], author_recipe='UNKNOWN', source_triangle=list(core),
        helper_cage_max_component_error_m=cage_error,
        all1797_garment_max_component_error_m=max(component_error(p, actual['garment_rest'][str(i)]) for i, p in enumerate(cloth)),
        selected_reference_fitted_rest_area_m2=original_area, selected_nvwa_fitted_rest_area_m2=actual_area,
        selected_reference_over_nvwa_rest_area=original_area / actual_area,
        selected_points=[dict(source_id=i, original_reference_fitted_rest_m=cloth[i], historical_nvwa_fitted_rest_m=actual['garment_rest'][str(i)]) for i in core],
        posed_original_tool_reference='NOT-RUN', original_armature_policy_effect='UNKNOWN', minimum_justified_fix='NONE', quality='HOLD')
    a.out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in report.items() if 'area' in k or 'error' in k}))


if __name__ == '__main__':
    main()
