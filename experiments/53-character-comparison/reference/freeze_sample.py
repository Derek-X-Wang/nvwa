"""Freeze the approved common inputs and executed reference; no downloads."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(staging, reference, output):
    staging = staging.resolve()
    root = Path(__file__).resolve().parents[3]
    delivery = root / 'experiments/53-character-comparison/delivery'
    receipts = ['mpfb-extraction-receipt.json', 'system-garment-extraction-receipt.json']
    approved = {}
    for name in receipts:
        receipt = json.loads((delivery / name).read_text())
        for entry in receipt['files']:
            approved[Path(entry['path']).relative_to('.work/character-approved-20261016').as_posix()] = entry['sha256']
    summary_path = staging / reference / 'summary.json'
    summary = json.loads(summary_path.read_text())
    assert summary['status'] == 'reference_geometry_passed'
    assert summary['garment_executed'] and summary['reference_pipeline_executed']
    assert not summary['graphics_executed']
    assert summary['driver_sha256'] == sha(Path(__file__).with_name('core_smoke.py'))
    files = []
    def add(role, relative, license_name, source_url, expected=None):
        path = staging / relative
        assert path.resolve().is_relative_to(staging) and path.is_file()
        digest = sha(path)
        if expected is not None:
            assert digest == expected, relative
        files.append(dict(role=role, path=relative, sha256=digest, bytes=path.stat().st_size,
                          license=license_name, source_url=source_url))
    tag = 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e'
    targets = {
        'torso_length': {'decr': 'torso/torso-scale-vert-decr.target.gz',
                         'incr': 'torso/torso-scale-vert-incr.target.gz'},
        'jaw_drop': {'decr': 'chin/chin-jaw-drop-decr.target.gz',
                     'incr': 'chin/chin-jaw-drop-incr.target.gz'}}
    source_paths = {'basemesh': 'mpfb-addon/data/3dobjs/base.obj',
                    'vertex_groups': 'mpfb-addon/data/mesh_metadata/basemesh_vertex_groups.json',
                    'rig': 'mpfb-addon/data/rigs/standard/rig.game_engine.json',
                    'weights': 'mpfb-addon/data/rigs/standard/weights.game_engine.json'}
    for role, relative in source_paths.items():
        add(role, relative, 'CC0-1.0',
            f'https://github.com/makehumancommunity/mpfb2/blob/{tag}/src/mpfb/{relative.removeprefix("mpfb-addon/")}',
            approved[relative])
    parameters = {}
    for name, pair in targets.items():
        parameters[name] = dict(default=0.0, min=-1.0, max=1.0, targets={})
        for sign, source in pair.items():
            relative = 'mpfb-addon/data/targets/' + source
            add('target', relative, 'CC0-1.0',
                f'https://github.com/makehumancommunity/mpfb2/blob/{tag}/src/mpfb/data/targets/{source}',
                approved[relative])
            parameters[name]['targets'][sign] = relative
    garment = staging / 'system-assets/clothes/female_sportsuit01'
    source_paths['garment_mhclo'] = (garment / 'female_sportsuit01.mhclo').relative_to(staging).as_posix()
    source_paths['garment_obj'] = (garment / 'female_sportsuit01.obj').relative_to(staging).as_posix()
    for path in sorted(garment.iterdir()):
        relative = path.relative_to(staging).as_posix()
        add('garment', relative, 'CC0-1.0',
            'https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip',
            approved[relative])
    cases = []
    for entry in summary['cases']:
        relative = (Path(reference) / entry['path']).as_posix()
        add('reference', relative, 'CC0-1.0', 'local:executed-mpfb-reference', entry['sha256'])
        data = json.loads((staging / relative).read_text())
        assert len(data['positions']) == 19158 and len(data['bones']) == 53
        assert len(data['garment_positions']) == 1797
        case_id = entry['case_id']
        kind = 'body' if case_id.startswith('body-') else 'face' if case_id.startswith('face-') else case_id
        cases.append(dict(case_id=case_id, kind=kind, recipe=data['recipe'], reference_path=relative))
    add('reference', summary_path.relative_to(staging).as_posix(), 'CC0-1.0', 'local:executed-mpfb-reference')
    manifest = dict(schema_version=1, parameter_schema='paired-local-targets-v1',
        sample_class='makehuman-approved-sample', approved=True,
        authorization_manifest_sha256='234584fae55334e4a7a20f76e4aecd88e604200789b75d0e7ac7d4c67328b4ce',
        reference_manifest_sha256=sha(summary_path), reference_directory=reference,
        reference_driver_sha256=summary['driver_sha256'],
        basis='Blender mesh-local Z-up', units='metres',
        transforms={'raw_obj_to_reference': summary['raw_obj_to_reference']},
        baseline=summary['baseline'], all_helper_vertices_retained=True,
        body_capture='complete evaluated cage before clothing visibility MASK modifiers',
        material_policy=summary['garment_material_policy'],
        parameters=parameters, source_paths=source_paths, files=files, cases=cases,
        tolerances={'body_max_component':1e-5, 'joint_endpoint_max_component':1e-5,
                    'garment_max_component':1e-5,
                    'scope':'metre component numeric parity only; not rest/skin/visual-quality acceptance'},
        adoption_status='not_selected', graphics_executed=False)
    with output.open('x') as stream:
        stream.write(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'manifest_sha256':sha(output), 'source_and_reference_files':len(files), 'cases':len(cases)}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--staging', type=Path, required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    freeze(args.staging, args.reference, args.out)
