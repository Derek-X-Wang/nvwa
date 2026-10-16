# Common MPFB reference

This original driver calls the approved MPFB 2.0.18 APIs in **system Blender 5.2.2 LTS**, with background mode, offline mode and task-local extension resources. It creates no user project and changes no user preference file. Blender was upgraded from 3.3.1 with explicit human authorization; the historical standalone 4.2.23 DMG request was superseded and that DMG was not downloaded. See [installation receipt](../delivery/blender-homebrew-upgrade.json).

## Exact sample and measurement

- Raw `hm08` base OBJ at scale `.1`, without phenotype/macro defaults or grounding. All **19,158** vertices and helper IDs remain available.
- The torso vertical-scale and chin jaw-drop target pairs expose signed values `[-1, 1]`. Negative selects the `decr` source, positive selects `incr`, and zero is the raw basis. This is a narrow parameter probe, not the complete MakeHuman macro system.
- Official `game_engine` rig, **53** bones; reference records parents, endpoints and `matrix_local`.
- The same approved `female_sportsuit01` MHCLO/OBJ, **1,797** evaluated garment vertices. MPFB performs actual garment fitting and weight interpolation. Neutral material isolates geometry; legacy MakeHuman GLSL/material appearance is unverified.
- MPFB's OBJ conversion is checked against every imported base vertex: source `(x,y,z)` becomes reference `(.1*x,-.1*z,.1*y)` metres. Maximum measured component error is `2.72274017332208e-7` metres.
- Clothing installs a body visibility mask. Body measurement temporarily disables **only active MASK modifiers**, records them, captures the complete evaluated source cage, and restores the masks before garment evaluation. This preserves source IDs for geometric comparison. It does not claim visible-face topology or clothing occlusion parity.
- Eight cases: neutral; torso `-1`, `.5`, `1`; jaw `-1`, `.5`, `1`; and both `.5`. Per-component tolerance was declared as **1e-5 metres** for body, joint endpoints and garment before the full A/B measurements. This is numeric parity, not an anatomical, skinning or visual quality threshold.

Full arrays remain in ignored task data. Public manifests and summaries identify them by hash. Neither Rust path may use reference vertices or matrices to produce its own character results. Reference files are comparison outputs only.

## Reproduce on the retained local inputs

From the research checkout root (the commands do not fetch or install anything):

```sh
export NVWA_SAMPLE_ROOT="$PWD/.work/character-approved-20261016"
BLENDER_USER_RESOURCES="$NVWA_SAMPLE_ROOT/blender-user" \
  /opt/homebrew/bin/blender --background --factory-startup --offline-mode \
  --python-exit-code 7 --python experiments/53-character-comparison/reference/core_smoke.py -- \
  --addon "$NVWA_SAMPLE_ROOT/mpfb-addon" \
  --garment "$NVWA_SAMPLE_ROOT/system-assets/clothes/female_sportsuit01/female_sportsuit01.mhclo" \
  --out "$NVWA_SAMPLE_ROOT/reference-reproduction"
python3 experiments/53-character-comparison/reference/freeze_sample.py \
  --staging "$NVWA_SAMPLE_ROOT" --reference reference-reproduction \
  --out "$NVWA_SAMPLE_ROOT/common-sample-reproduction.json"
```

Output directories/files must be new. The isolated extension environment contains `blender-user/extensions/user_default/mpfb`, linked to the audited `mpfb-addon` directory. The driver registers the six audited garment files in this isolated user's asset search path. It does not install MPFB in the human's Blender preferences. Both Rust paths bind the **same frozen manifest hash**; reproducing into another directory changes path identities and requires binding that new manifest for both paths.

## Observed failures retained

1. `reference-full-run1`: absolute garment import succeeded, subsequent MPFB refit could not resolve its asset-source fragment. Fixed the task-local search configuration; no fitting operation was bypassed.
2. `reference-full-run2`: refit succeeded, but the newly added clothing visibility mask changed evaluated body vertex count. The full-cage assertion failed. Fixed the explicit capture policy above; did not remove the assertion or conceal the failure.
3. `reference-full-run3`: eight cases passed with body, rig and garment outputs. No render or animation ran.

**PARTIAL — Offline MPFB geometry reference executed. Native/Web graphics, pose skinning, inverse-bind comparison, whole-Work exchange, performance and character aesthetics are separate unverified gates.**
