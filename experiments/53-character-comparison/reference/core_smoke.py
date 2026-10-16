"""Run approved MPFB APIs in an isolated Blender background scene.

Original experiment driver; it calls MPFB rather than copying its implementation.
This reference evaluates geometry. It does not admit rendering or animation.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
import bpy
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addon", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--garment", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.out.mkdir(parents=True, exist_ok=False)
    assert bpy.app.version == (5, 2, 2), bpy.app.version_string
    assert bpy.app.background and not bpy.app.online_access
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
    mpfb = importlib.import_module("bl_ext.user_default.mpfb")
    assert mpfb.VERSION == (2, 0, 18) and mpfb.BUILD_INFO == "20261010"
    assert Path(mpfb.__file__).resolve() == (args.addon / "__init__.py").resolve()
    services = importlib.import_module("bl_ext.user_default.mpfb.services")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # Explicit raw hm08 baseline; no phenotype/macro defaults or grounding shift.
    body = services.ObjectService.load_base_mesh(scale_factor=0.1)
    source = args.addon / "data/3dobjs/base.obj"
    raw = np.array([[float(x) for x in line.split()[1:4]]
                    for line in source.read_text().splitlines() if line.startswith("v ")])
    baseline = np.array([list(v.co) for v in body.data.vertices])
    assert len(raw) == len(baseline)
    fit, _, rank, _ = np.linalg.lstsq(np.c_[raw, np.ones(len(raw))], baseline, rcond=None)
    assert rank == 4
    transform = np.eye(4)
    transform[:3, :] = fit.T
    fit_error = float(np.max(np.abs(np.c_[raw, np.ones(len(raw))] @ fit - baseline)))
    # The declared format conversion is tested against every imported vertex.
    declared = np.array([[.1, 0, 0, 0], [0, 0, -.1, 0], [0, .1, 0, 0], [0, 0, 0, 1.]])
    declared_error = float(np.max(np.abs(np.c_[raw, np.ones(len(raw))] @ declared.T[:, :3] - baseline)))
    assert fit_error < 1e-6 and declared_error < 1e-6, (fit_error, declared_error)
    targets = {
        "body_decr": "torso/torso-scale-vert-decr.target.gz",
        "body_incr": "torso/torso-scale-vert-incr.target.gz",
        "face_decr": "chin/chin-jaw-drop-decr.target.gz",
        "face_incr": "chin/chin-jaw-drop-incr.target.gz",
    }
    keys = {name: services.TargetService.load_target(body, str(args.addon / "data/targets" / rel),
                                                    name="nvwa_" + name)
            for name, rel in targets.items()}
    rig = services.HumanService.add_builtin_rig(body, "game_engine")
    assert rig and len(rig.data.bones) == 53
    garment = None
    if args.garment:
        assert args.garment.is_file()
        # MPFB refit resolves asset_source through its user asset search path.
        # Install only these already-audited six files in this process's isolated
        # BLENDER_USER_RESOURCES, without touching the user's real preferences.
        asset_root = Path(services.LocationService.get_user_data("clothes"))
        isolated_root = Path(__import__("os").environ["BLENDER_USER_RESOURCES"]).resolve()
        assert asset_root.resolve().is_relative_to(isolated_root)
        registered = asset_root / args.garment.parent.name
        registered.mkdir(parents=True, exist_ok=True)
        for source_file in args.garment.parent.iterdir():
            assert source_file.is_file() and not source_file.is_symlink()
            destination = registered / source_file.name
            if destination.exists():
                assert sha(destination) == sha(source_file), destination
            else:
                shutil.copy2(source_file, destination)
        assert services.AssetService.find_asset_absolute_path(
            args.garment.parent.name + "/" + args.garment.name, "clothes")
        garment = services.HumanService.add_mhclo_asset(
            str(args.garment), body, subdiv_levels=0, material_type="NONE",
            set_up_rigging=True, interpolate_weights=True, import_subrig=False,
            import_weights=False)
        assert garment and garment.type == "MESH"
    cases = [
        ("neutral", 0.0, 0.0), ("body-negative", -1., 0.0), ("body-half", .5, 0.0),
        ("body-positive", 1., 0.0), ("face-negative", 0.0, -1.),
        ("face-half", 0.0, .5), ("face-positive", 0.0, 1.), ("combined", .5, .5),
    ]
    receipts = []
    for case_id, body_value, face_value in cases:
        for name, key in keys.items():
            value = body_value if name.startswith("body_") else face_value
            key.value = max(0., -value if name.endswith("decr") else value)
        bpy.context.view_layer.update()
        services.HumanService.refit(body)
        bpy.context.view_layer.update()
        # Clothing adds visibility masks for covered body faces. Compare the
        # complete source cage (including joint helpers) before visibility masks,
        # keeping stable OBJ vertex IDs. Restore masks before garment evaluation.
        masks = [m for m in body.modifiers if m.type == "MASK" and m.show_viewport]
        for modifier in masks:
            modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            positions = [list(v.co) for v in mesh.vertices]
        finally:
            evaluated.to_mesh_clear()
            for modifier in masks:
                modifier.show_viewport = True
            bpy.context.view_layer.update()
        assert len(positions) == len(raw)
        bones = [{"name": b.name, "parent": b.parent.name if b.parent else None,
                  "head": list(b.head_local), "tail": list(b.tail_local),
                  "matrix_local": [list(row) for row in b.matrix_local]} for b in rig.data.bones]
        data = {"case_id": case_id, "recipe": {"torso_length": body_value, "jaw_drop": face_value},
                "basis": "Blender mesh-local Z-up, raw OBJ transformed by declared matrix",
                "body_capture": "complete evaluated cage before clothing visibility MASK modifiers",
                "visibility_masks": [{"name": m.name, "vertex_group": m.vertex_group,
                                      "invert_vertex_group": m.invert_vertex_group} for m in masks],
                "positions": positions, "bones": bones, "body_world": [list(row) for row in body.matrix_world],
                "rig_world": [list(row) for row in rig.matrix_world], "garment_executed": garment is not None}
        if garment:
            cloth_eval = garment.evaluated_get(bpy.context.evaluated_depsgraph_get())
            cloth_mesh = cloth_eval.to_mesh()
            try:
                data["garment_positions"] = [list(v.co) for v in cloth_mesh.vertices]
            finally:
                cloth_eval.to_mesh_clear()
            data["garment_world"] = [list(row) for row in garment.matrix_world]
        path = args.out / (case_id + ".json")
        path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n")
        receipts.append({"case_id": case_id, "path": path.name, "sha256": sha(path),
                         "vertices": len(positions), "bones": len(bones)})
    summary = {"schema_version": 1, "status": "reference_geometry_passed" if garment else "core_smoke_passed", "full_sample_status": "reference_geometry_only" if garment else "not_run",
               "blender_version": bpy.app.version_string, "mpfb_version": list(mpfb.VERSION),
               "mpfb_build": mpfb.BUILD_INFO, "base_sha256": sha(source),
               "baseline": "raw hm08, scale .1, no macros, no grounding, all helpers retained",
               "raw_obj_to_reference": declared.tolist(), "fitted_transform": transform.tolist(),
               "basis_fit_max_abs": fit_error, "declared_transform_max_abs": declared_error,
               "parameter_semantics": "signed pair: negative selects decr, positive selects incr, zero is raw basis",
               "driver_sha256": sha(Path(__file__)),
               "garment_mhclo_sha256": sha(args.garment) if args.garment else None,
               "garment_material_policy": "neutral geometry comparison; legacy shader/material parity NOT-RUN",
               "cases": receipts, "garment_executed": garment is not None, "graphics_executed": False,
               "reference_pipeline_executed": True}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print("NVWA_MPFB_CORE=" + json.dumps({"cases": len(receipts), "vertices": len(raw), "bones": 53,
                                          "max_basis_error": declared_error}))


if __name__ == "__main__":
    main()
