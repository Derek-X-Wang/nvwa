# Compiled source rules and exact supported scope

The user approved the exact assets and local validation. Root owns the common
manifest and Blender 5.2.2 / MPFB 2.0.18 reference. A owns only this experiment and
runs CPU Rust execution. The actual common comparison is recorded in REPORT.md.

## Implemented compiled operators

- Signed sparse target pairs: zero selects neither branch, negative selects decr,
  positive selects incr; each sparse delta keeps its original source vertex ID.
- Explicit `(topology_id, node, mesh, primitive)` identity; no ambiguous global
  overwrite across primitive domains.
- Helper point rules: explicit source vertex index sets averaged after deformation.
  Bone endpoint rules retain name/parent/roll and point to those evaluated centroids.
- Garment proxy: source triples and unmodified source weights plus componentwise
  offsets scaled by explicit vertex-pair axis distances. Rounded source weights are
  not silently renormalized. All coordinate mapping is compiled explicitly.
- Whole-package/common-manifest hashes pinned in each recipe. All branches, including
  an unselected negative branch, are validated before evaluation/output creation.

`compile_common.py` reads the frozen manifest's source_paths/parameters/case recipes.
It checks the source allowlist and extraction receipts. It does not read full-sample
reference geometry to compile output. `compare_common.py` subsequently reads reference
geometry and verifies its frozen hashes. Both processes remain separate.

## Audited source semantics

Source: `.work/character-approved-20261016/mpfb-addon/`, MPFB 2.0.18; data audited
against `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. No plugin execution by A.

- `services/targetservice.py:415–437`: raw target `(x,y,z)` → `(x,-z,y)`;
  `358–379`: apply the declared scale_factor.
- `entities/rig.py:864–939`: average evaluated vertices in joint groups;
  `272–300`: CUBE centroids or MEAN source indices select endpoints.
- Actual GameEngine data: 53 bones, 105 CUBE endpoints, one MEAN endpoint, no endpoint
  offsets. This finding is not rig or animation quality admission.
- `services/clothesservice.py:181–183,229–234`: source-axis distance ratios and weighted
  body triples plus scaled offsets. `entities/clothes/mhclo.py:129`: offset conversion.
- Selected audited MHCLO and OBJ both have 1,797 garment vertex entries.

The original GLB probe remains a distinct existing-fixture lane. The new
`compiled-numeric-probe` is called by actual shared-sample execution and by clearly
labeled handwritten controls. Bone rest matrices, inverse binds, skinning, graphics,
materials and Work exchange are not implemented or inferred from endpoint parity.
