"""Call retained MPFB and Blender CPU APIs. No rendering or imported/fabricated rig."""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
import bpy
from mathutils import Matrix, Vector


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def error(a, b):
    return max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def mat(column_major):
    return Matrix([[column_major[c * 4 + r] for c in range(4)] for r in range(4)])


def area(p):
    return (Vector(p[1]) - Vector(p[0])).cross(Vector(p[2]) - Vector(p[0])).length / 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--addon', type=Path, required=True)
    p.add_argument('--garment', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    a.out.mkdir(parents=True, exist_ok=False)
    require(bpy.app.background and not bpy.app.online_access, 'background/offline required')
    require(digest(a.inputs) == json.loads(a.inputs.with_name('preparation.json').read_text())['prepared_input_sha256'], 'prepared inputs changed')
    inputs = json.loads(a.inputs.read_text())
    for rel, expected in inputs['source_hashes'].items():
        require(digest(a.addon.parent / rel) == expected, 'prepared source drift: ' + rel)
    bpy.ops.preferences.addon_enable(module='bl_ext.user_default.mpfb')
    mpfb = importlib.import_module('bl_ext.user_default.mpfb')
    require(mpfb.VERSION == (2, 0, 18), 'unexpected MPFB version')
    require(Path(mpfb.__file__).resolve() == (a.addon / '__init__.py').resolve(), 'wrong addon source')
    services = importlib.import_module('bl_ext.user_default.mpfb.services')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    body = services.ObjectService.load_base_mesh(scale_factor=.1)
    require(len(body.data.vertices) == 19158, 'official body source IDs changed')
    key = services.TargetService.load_target(body, str(a.addon / 'data/targets/torso/torso-scale-vert-incr.target.gz'), name='nvwa_torso')
    rig = services.HumanService.add_builtin_rig(body, 'game_engine')
    require(len(rig.data.bones) == 53, 'official rig is not53 bones')
    asset_root = Path(services.LocationService.get_user_data('clothes'))
    require(asset_root.resolve().is_relative_to(Path(os.environ['BLENDER_USER_RESOURCES']).resolve()), 'asset path escapes isolated resources')
    registered = asset_root / a.garment.parent.name
    registered.mkdir(parents=True, exist_ok=False)
    for source in a.garment.parent.iterdir():
        require(source.is_file() and not source.is_symlink(), 'unexpected garment dependency')
        shutil.copy2(source, registered / source.name)
    garment = services.HumanService.add_mhclo_asset(str(a.garment), body, subdiv_levels=0,
        material_type='NONE', set_up_rigging=True, interpolate_weights=True,
        import_subrig=False, import_weights=False)
    require(garment is not None and len(garment.data.vertices) == 1797, 'original garment import failed')
    triangles = []
    for face in garment.data.polygons:
        ids = list(face.vertices)
        triangles.extend([[ids[0], ids[j], ids[j + 1]] for j in range(1, len(ids) - 1)])
    require(triangles == inputs['triangles'], 'original OBJ import topology/source IDs differ')
    key.value = 1.
    bpy.context.view_layer.update()
    services.HumanService.refit(body)
    bpy.context.view_layer.update()
    # Source Y-up metre frame -> Blender Z-up metre frame. No scale here.
    c = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    ci = c.inverted()
    mixed = body.shape_key_add(name='nvwa_reference_cage', from_mix=True)
    cage = [list(ci.to_3x3() @ v.co) for v in mixed.data]
    body.shape_key_remove(mixed)
    cases = []
    for case in inputs['cases']:
        for pb in rig.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        byname = {b['name']: b for b in case['bones']}
        require(set(byname) == set(rig.data.bones.keys()), 'source bone names differ')
        require({b.name: b.parent.name if b.parent else None for b in rig.data.bones} ==
                {n: b['parent'] for n, b in byname.items()}, 'official rig hierarchy differs')
        cage_error = max(abs(x - y) for i, v in enumerate(cage) for x, y in zip(v, case['cage'][str(i)]))
        require(cage_error < 1e-5, f'official/current helper cage mismatch: {cage_error}')
        rest_error = max(error(ci @ b.matrix_local, mat(byname[b.name]['canonical_rest'])) for b in rig.data.bones)
        require(rest_error < 1e-4, f'official/canonical rest mismatch: {rest_error}')
        if case['case'] == 'arm2':
            rig.pose.bones['upperarm_l'].matrix_basis = Matrix.Rotation(math.radians(45), 4, 'Z')
            rig.pose.bones['lowerarm_l'].matrix_basis = Matrix.Rotation(math.radians(75), 4, 'Z')
        elif case['case'] == 'knee2':
            rig.pose.bones['calf_l'].matrix_basis = Matrix.Rotation(math.radians(65), 4, 'X')
            foot = rig.data.bones['foot_l'].matrix_local.to_3x3()
            calf = rig.data.bones['calf_l'].matrix_local.to_3x3()
            axis = foot.transposed() @ calf.col[0]
            rig.pose.bones['foot_l'].matrix_basis = Matrix.Rotation(math.radians(-65), 4, axis.normalized())
        bpy.context.view_layer.update()
        skin_error = max(error(ci @ pb.matrix @ pb.bone.matrix_local.inverted() @ c, mat(byname[pb.name]['skin'])) for pb in rig.pose.bones)
        require(skin_error < 1e-4, f'original armature/source skin mismatch: {skin_error}')
        evaluated = garment.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            require(len(mesh.vertices) == 1797, 'evaluated source IDs changed')
            posed = [list(ci.to_3x3() @ v.co) for v in mesh.vertices]
        finally:
            evaluated.to_mesh_clear()
        rest = [list(ci.to_3x3() @ v.co) for v in garment.data.vertices]
        selected = (246, 244, 182)
        ratio = area([posed[i] for i in selected]) / area([rest[i] for i in selected])
        rows = {g.index: g.name for g in garment.vertex_groups}
        weights = [{rows[g.group]: g.weight for g in v.groups if rows[g.group] in byname} for v in garment.data.vertices]
        result = dict(case=case['case'], cage_max_component_error_m=cage_error,
            rest_max_matrix_component_error=rest_error,
            skin_max_matrix_component_error=skin_error, posed_over_rest_area=ratio,
            historical_input_sha256=case['sha256'], positions=posed, rest_positions=rest,
            weights=weights, bones=[dict(name=pb.name, matrix_local=[list(r) for r in pb.bone.matrix_local], matrix=[list(r) for r in pb.matrix]) for pb in rig.pose.bones],
            modifiers=[dict(name=m.name, type=m.type, show_viewport=m.show_viewport,
                preserve_volume=getattr(m, 'use_deform_preserve_volume', None)) for m in garment.modifiers])
        (a.out / (case['case'] + '.json')).write_text(json.dumps(result, allow_nan=False))
        cases.append({k: v for k, v in result.items() if k not in ('positions', 'rest_positions', 'weights', 'bones')})
    summary = dict(schema_version=1, blender_version=bpy.app.version_string,
        mpfb_version=list(mpfb.VERSION), input_sha256=digest(a.inputs), driver_sha256=digest(Path(__file__)),
        cases=cases, original_tool_reference_executed=True, rendering_executed=False,
        author_recipe='UNKNOWN', quality='HOLD', candidate='NONE')
    (a.out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print('NVWA_GARMENT74=' + json.dumps(summary))


if __name__ == '__main__':
    main()
