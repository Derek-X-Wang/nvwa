"""Original offline MPFB pose reference, evaluated by Blender's CPU depsgraph.

No output from this script is an input to the candidate character computation.
The original approved addon and assets are opened read-only; task-local Blender
resources hold registration/configuration, never human Blender preferences.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

COMMON_SHA = "2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7"
POSE_SHA = "8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data, *, compact=False):
    with path.open("x") as stream:
        json.dump(data, stream, allow_nan=False, indent=None if compact else 2,
                  separators=(",", ":") if compact else None)
        stream.write("\n")


def mat(value):
    return [list(row) for row in value]


def modifiers(obj):
    result = []
    for modifier in obj.modifiers:
        entry = {"name": modifier.name, "type": modifier.type,
                 "show_viewport": modifier.show_viewport, "show_render": modifier.show_render}
        if modifier.type == "ARMATURE":
            entry.update(object=modifier.object.name if modifier.object else None,
                         use_deform_preserve_volume=modifier.use_deform_preserve_volume,
                         use_multi_modifier=modifier.use_multi_modifier,
                         vertex_group=modifier.vertex_group,
                         invert_vertex_group=modifier.invert_vertex_group,
                         use_vertex_groups=modifier.use_vertex_groups,
                         use_bone_envelopes=modifier.use_bone_envelopes)
        elif modifier.type == "MASK":
            entry.update(vertex_group=modifier.vertex_group,
                         invert_vertex_group=modifier.invert_vertex_group)
        result.append(entry)
    return result


def capture(obj, *, before_masks=False):
    disabled = [m for m in obj.modifiers if before_masks and m.type == "MASK" and m.show_viewport]
    for modifier in disabled:
        modifier.show_viewport = False
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        assert len(mesh.vertices) == len(obj.data.vertices), (obj.name, len(mesh.vertices))
        positions = [list(vertex.co) for vertex in mesh.vertices]
        normals = [list(vertex.normal) for vertex in mesh.vertices]
        assert np.isfinite(positions).all() and np.isfinite(normals).all()
        # OBJ vertex order survives the shape-key + armature stack. Require
        # original topology as well, rather than assuming equal counts imply IDs.
        loop_ids = [loop.vertex_index for loop in mesh.loops]
        assert loop_ids == [loop.vertex_index for loop in obj.data.loops]
        assert [list(poly.vertices) for poly in mesh.polygons] == [list(poly.vertices) for poly in obj.data.polygons]
        tangents = []
        if mesh.uv_layers.active:
            mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
            tangents = [[*loop.tangent, loop.bitangent_sign] for loop in mesh.loops]
            assert np.isfinite(tangents).all()
        return {"positions": positions, "normals": normals,
                "source_ids": list(range(len(positions))), "loop_source_ids": loop_ids,
                "tangents": tangents, "uv_map": mesh.uv_layers.active.name if mesh.uv_layers.active else None,
                "normal_space": "evaluated mesh-local; world inverse-transpose(matrix_world[:3,:3]) then normalize",
                "tangent_space": "evaluated mesh-local corner tangent xyz + bitangent sign; world linear transform then normalize",
                "disabled_masks": [modifier.name for modifier in disabled]}
    finally:
        evaluated.to_mesh_clear()
        for modifier in disabled:
            modifier.show_viewport = True
        bpy.context.view_layer.update()


def full_weights(obj, rig):
    bone_ids = {bone.name: index for index, bone in enumerate(rig.data.bones) if bone.use_deform}
    groups = {group.index: bone_ids[group.name] for group in obj.vertex_groups if group.name in bone_ids}
    result = [[[groups[group.group], group.weight] for group in vertex.groups
               if group.group in groups and group.weight != 0.0] for vertex in obj.data.vertices]
    assert all(weight >= 0 and math.isfinite(weight) for row in result for _, weight in row)
    sums = [sum(weight for _, weight in row) for row in result]
    return result, {"vertices": len(result), "influences": sum(map(len, result)),
                    "max_influences": max(map(len, result)), "unweighted_vertices": sum(not row for row in result),
                    "nonzero_sum_min": min(value for value in sums if value), "sum_max": max(sums),
                    "max_abs_sum_minus_one_weighted": max(abs(value - 1) for value in sums if value),
                    "truncated": False, "renormalized": False,
                    "excluded_groups": [group.name for group in obj.vertex_groups if group.name not in bone_ids]}


def bones_capture(rig):
    return [{"name": bone.name, "parent": bone.parent.name if bone.parent else None,
             "use_deform": bone.use_deform, "use_connect": bone.use_connect,
             "inherit_scale": bone.inherit_scale, "use_inherit_rotation": bone.use_inherit_rotation,
             "head": list(bone.head_local), "tail": list(bone.tail_local),
             "matrix_local": mat(bone.matrix_local), "matrix_pose": mat(rig.pose.bones[bone.name].matrix),
             "matrix_basis": mat(rig.pose.bones[bone.name].matrix_basis),
             "posed_head": list(rig.pose.bones[bone.name].head), "posed_tail": list(rig.pose.bones[bone.name].tail),
             "skin_matrix": mat(rig.pose.bones[bone.name].matrix @ bone.matrix_local.inverted())}
            for bone in rig.data.bones]


def set_pose(rig, pose):
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
        bone.rotation_mode = "QUATERNION"
    for rotation in pose["rotations"]:
        bone = rig.pose.bones[rotation["bone"]]
        assert not bone.constraints
        bone.rotation_quaternion = Quaternion(Vector(rotation["axis"]), math.radians(rotation["degrees"]))
    bpy.context.view_layer.update()


def convention_metrics(rig, pose):
    requested = {rotation["bone"]: Quaternion(Vector(rotation["axis"]), math.radians(rotation["degrees"])).to_matrix().to_4x4()
                 for rotation in pose["rotations"]}
    basis_error = pose_error = 0.0
    for bone in rig.data.bones:
        basis = requested.get(bone.name, Matrix.Identity(4))
        actual = rig.pose.bones[bone.name]
        basis_error = max(basis_error, float(np.max(np.abs(np.array(actual.matrix_basis) - np.array(basis)))))
        expected = (rig.pose.bones[bone.parent.name].matrix @ bone.parent.matrix_local.inverted() @ bone.matrix_local @ basis
                    if bone.parent else bone.matrix_local @ basis)
        pose_error = max(pose_error, float(np.max(np.abs(np.array(actual.matrix) - np.array(expected)))))
    assert basis_error <= 1e-6 and pose_error <= 1e-5, (basis_error, pose_error)
    planes = []
    for rotation in pose["rotations"]:
        bone = rig.data.bones[rotation["bone"]]
        axis = bone.matrix_local.to_3x3() @ Vector(rotation["axis"])
        planes.append({"bone": bone.name, "local_axis": rotation["axis"],
                       "axis_in_rig_rest": list(axis), "degrees": rotation["degrees"],
                       "head_rest": list(bone.head_local), "tail_rest": list(bone.tail_local),
                       "head_posed": list(rig.pose.bones[bone.name].head),
                       "tail_posed": list(rig.pose.bones[bone.name].tail)})
    return {"basis_max_component": basis_error, "pose_recurrence_max_component": pose_error, "authored_axes": planes}


def full_lbs_check(rest_positions, posed_positions, weights, bones, obj, rig):
    # Diagnostic only: full-weight LBS compared with Blender, never used to
    # replace evaluated geometry. Normalization matches Blender's group mixing.
    rest = np.c_[rest_positions, np.ones(len(rest_positions))]
    before = np.array(rig.matrix_world.inverted() @ obj.matrix_world)
    after = np.array(obj.matrix_world.inverted() @ rig.matrix_world)
    skin = np.array([after @ np.array(bone["skin_matrix"]) @ before for bone in bones])
    result = np.array(rest_positions, dtype=float)
    for index, row in enumerate(weights):
        total = sum(weight for _, weight in row)
        if total:
            result[index] = sum(weight * (skin[bone_id] @ rest[index])[:3] for bone_id, weight in row) / total
    delta = result - np.array(posed_positions)
    return {"max_component": float(np.max(np.abs(delta))), "rms_component": float(np.sqrt(np.mean(delta ** 2))),
            "source_ids": len(result), "weighted_source_ids": sum(bool(row) for row in weights)}


def verify_inputs(root, sample, poses_path):
    common_path = sample / "common-sample.json"
    assert sha(common_path) == COMMON_SHA and sha(poses_path) == POSE_SHA
    common = json.loads(common_path.read_text())
    identities = {}
    for entry in common["files"]:
        if entry["role"] != "reference":
            path = sample / entry["path"]
            assert sha(path) == entry["sha256"], entry["path"]
            identities[entry["path"]] = entry["sha256"]
    receipt_hashes = {}
    for name in ("mpfb-extraction-receipt.json", "system-garment-extraction-receipt.json"):
        receipt_path = root / "experiments/53-character-comparison/delivery" / name
        receipt_hashes[name] = sha(receipt_path)
        for entry in json.loads(receipt_path.read_text())["files"]:
            relative = Path(entry["path"]).relative_to(".work/character-approved-20261016")
            assert sha(sample / relative) == entry["sha256"], str(relative)
    return common, identities, receipt_hashes


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--recipes", nargs="*", help="Probe subset only; omitted runs every frozen recipe")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    root = Path(__file__).resolve().parents[3]
    sample = args.sample.resolve()
    poses_path = Path(__file__).resolve().parents[1] / "poses.json"
    common, source_ids, receipt_hashes = verify_inputs(root, sample, poses_path)
    driver_sha = sha(Path(__file__))
    args.out.mkdir(parents=True, exist_ok=False)
    assert bpy.app.version == (5, 2, 2) and bpy.app.background and not bpy.app.online_access
    resources = Path(os.environ["BLENDER_USER_RESOURCES"]).resolve()
    assert resources.is_relative_to(root / ".work/b1-pose-reference")
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
    mpfb = importlib.import_module("bl_ext.user_default.mpfb")
    assert mpfb.VERSION == (2, 0, 18) and mpfb.BUILD_INFO == "20261010"
    assert Path(mpfb.__file__).resolve() == sample / "mpfb-addon/__init__.py"
    services = importlib.import_module("bl_ext.user_default.mpfb.services")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    body = services.ObjectService.load_base_mesh(scale_factor=.1)
    assert len(body.data.vertices) == 19158
    targets = {"body_decr": "torso/torso-scale-vert-decr.target.gz", "body_incr": "torso/torso-scale-vert-incr.target.gz",
               "face_decr": "chin/chin-jaw-drop-decr.target.gz", "face_incr": "chin/chin-jaw-drop-incr.target.gz"}
    keys = {name: services.TargetService.load_target(body, str(sample / "mpfb-addon/data/targets" / relative), name="nvwa_" + name)
            for name, relative in targets.items()}
    rig = services.HumanService.add_builtin_rig(body, "game_engine")
    assert rig and len(rig.data.bones) == 53
    rig.data.pose_position = "POSE"
    garment_path = sample / common["source_paths"]["garment_mhclo"]
    asset_root = Path(services.LocationService.get_user_data("clothes"))
    assert asset_root.resolve().is_relative_to(resources)
    registered = asset_root / garment_path.parent.name
    registered.mkdir(parents=True, exist_ok=True)
    for source in garment_path.parent.iterdir():
        assert source.is_file() and not source.is_symlink()
        destination = registered / source.name
        if destination.exists():
            assert sha(destination) == sha(source)
        else:
            shutil.copy2(source, destination)
    garment = services.HumanService.add_mhclo_asset(str(garment_path), body, subdiv_levels=0, material_type="NONE",
                set_up_rigging=True, interpolate_weights=True, import_subrig=False, import_weights=False)
    assert garment and len(garment.data.vertices) == 1797
    body_weights, body_weight_summary = full_weights(body, rig)
    garment_weights, garment_weight_summary = full_weights(garment, rig)
    poses = json.loads(poses_path.read_text())["poses"]
    assert poses[0] == {"pose_id": "neutral", "rotations": []}
    cases = common["cases"]
    if args.recipes:
        assert set(args.recipes) <= {case["case_id"] for case in cases}
        cases = [case for case in cases if case["case_id"] in args.recipes]
    command = {"executable": bpy.app.binary_path, "argv": sys.argv, "BLENDER_USER_RESOURCES": str(resources)}
    entries = []
    for recipe_case in cases:
        recipe_id, recipe = recipe_case["case_id"], recipe_case["recipe"]
        set_pose(rig, poses[0])
        for name, key in keys.items():
            value = recipe["torso_length" if name.startswith("body_") else "jaw_drop"]
            key.value = max(0., -value if name.endswith("decr") else value)
        bpy.context.view_layer.update()
        services.HumanService.refit(body)
        bpy.context.view_layer.update()
        body_rest, garment_rest = capture(body, before_masks=True), capture(garment)
        old = json.loads((sample / recipe_case["reference_path"]).read_text())
        old_errors = {"body": float(np.max(np.abs(np.array(body_rest["positions"]) - old["positions"]))),
                      "garment": float(np.max(np.abs(np.array(garment_rest["positions"]) - old["garment_positions"])))}
        assert max(old_errors.values()) <= 1e-5, old_errors
        for pose in poses:
            set_pose(rig, pose)
            body_pose, garment_pose = capture(body, before_masks=True), capture(garment)
            bones = bones_capture(rig)
            conventions = convention_metrics(rig, pose)
            case_id = recipe_id + "__" + pose["pose_id"]
            result = {"schema_version": 1, "case_id": case_id, "recipe_id": recipe_id,
                      "recipe": recipe, "pose_id": pose["pose_id"], "pose": pose,
                      "common_sha256": COMMON_SHA, "pose_sha256": POSE_SHA, "driver_sha256": driver_sha,
                      "source_sha256s": source_ids, "command": command, "bones": bones,
                      "body_world": mat(body.matrix_world), "rig_world": mat(rig.matrix_world),
                      "garment_world": mat(garment.matrix_world), "basis": common["basis"], "units": "metres",
                      "body_weights": body_weights, "garment_weights": garment_weights,
                      "body_weight_summary": body_weight_summary, "garment_weight_summary": garment_weight_summary,
                      "body_modifiers": modifiers(body), "garment_modifiers": modifiers(garment),
                      "rest_positions": body_rest["positions"], "rest_normals": body_rest["normals"],
                      "garment_rest_positions": garment_rest["positions"], "garment_rest_normals": garment_rest["normals"],
                      "rest_reproduction_max_component": old_errors, "convention_metrics": conventions,
                      "evaluation": {"pipeline": "actual MPFB plus Blender CPU evaluated depsgraph", "graphics_executed": False,
                                     "body_capture": "complete evaluated source cage before active visibility MASK modifiers; restored afterwards",
                                     "pose_position": rig.data.pose_position, "garment_fit_executed": True,
                                     "garment_interpolated_weights": True, "source_order_topology_checked": True,
                                     "normal_policy": body_pose["normal_space"], "tangent_policy": body_pose["tangent_space"]}}
            for name in ("positions", "normals", "source_ids", "loop_source_ids", "tangents", "uv_map", "disabled_masks"):
                result[name] = body_pose[name]
                result["garment_" + name] = garment_pose[name]
            diagnostics = {"body": full_lbs_check(body_rest["positions"], body_pose["positions"], body_weights, bones, body, rig),
                           "garment": full_lbs_check(garment_rest["positions"], garment_pose["positions"], garment_weights, bones, garment, rig)}
            result["diagnostic_full_weight_lbs_vs_evaluated"] = diagnostics
            path = args.out / (case_id + ".json")
            write_json(path, result, compact=True)
            entry = {"case_id": case_id, "recipe_id": recipe_id, "pose_id": pose["pose_id"], "path": path.name,
                     "sha256": sha(path), "bytes": path.stat().st_size, "body_vertices": len(body_pose["positions"]),
                     "garment_vertices": len(garment_pose["positions"]), "bones": len(bones),
                     "body_tangent_corners": len(body_pose["tangents"]), "garment_tangent_corners": len(garment_pose["tangents"]),
                     "convention_metrics": conventions, "full_weight_lbs_vs_evaluated": diagnostics,
                     "rest_reproduction_max_component": old_errors}
            entries.append(entry)
            print("NVWA_POSE_CASE=" + json.dumps(entry), flush=True)
    summary = {"schema_version": 1, "status": "actual_mpfb_pose_reference_complete" if len(entries) == 40 else "actual_mpfb_pose_probe_complete",
               "common_sha256": COMMON_SHA, "pose_sha256": POSE_SHA, "driver_sha256": driver_sha,
               "source_sha256s": source_ids, "audited_source_receipt_sha256s": receipt_hashes,
               "blender_version": bpy.app.version_string, "mpfb_version": list(mpfb.VERSION), "mpfb_build": mpfb.BUILD_INFO,
               "command": command, "body_weight_summary": body_weight_summary, "garment_weight_summary": garment_weight_summary,
               "body_modifiers": modifiers(body), "garment_modifiers": modifiers(garment),
               "graphics_executed": False, "candidate_comparison_executed": False, "cases": entries,
               "elapsed_seconds": time.monotonic() - start}
    write_json(args.out / "summary.json", summary)
    print("NVWA_POSE_DONE=" + json.dumps({"cases": len(entries), "elapsed_seconds": summary["elapsed_seconds"],
                                          "summary_sha256": sha(args.out / "summary.json")}), flush=True)


if __name__ == "__main__":
    main()
