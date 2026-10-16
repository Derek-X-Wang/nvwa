# Path A — offline compiled character package experiment

This is an isolated CPU experiment. The actual approved MakeHuman source-compiled
comparison is in [REPORT.md](REPORT.md); body/joint-endpoint/garment numeric parity
passes while rig/skin/graphics acceptance remains incomplete.
The package consists of the **existing pinned original GLB**, the existing character profile,
and a small explicit sidecar binding each parameter to `(node, mesh, primitive, target)`.
No model is copied into this experiment. No preset mesh switching is used.

From the repository root, rerun with one command:

```sh
experiments/54-compiled-character-package/run.sh
```

The script uses `cargo build --locked --offline -j 1`, its own lockfile and target,
then runs the independent Python process controls and the separate handwritten
signed/helper/proxy controls. It prints case and rejection-control
counts. A fresh private directory under `.work/` retains build/control logs, recipes,
complete JSON receipts and `cases/summary.json`. Existing output is never overwritten.
An optional first argument names an **absolute, absent** private run directory.
No external source or asset is fetched. Python uses only its installed standard library.

Direct experimental CLI:

```sh
experiments/54-compiled-character-package/target/debug/compiled-character-probe \
  experiments/54-compiled-character-package/fixture-package.json \
  /absolute/path/to/recipe.json /absolute/path/to/new-result.json
```

A recipe contains `schema_version: 1`, a nonempty `case_id`, the exact `profile_id`
and `profile_sha256`, and all four parameter IDs in `values`. Ranges come from the
hashed profile. The result names all inputs, the actual command, the evaluated
recipe, primitive-local position fingerprints/bounds/witnesses, and unsupported
fields. Fingerprints serialize all evaluated coordinates as little-endian f64.

The independent oracle decodes the original GLB in Python, evaluates every POSITION
entry and compares its full fingerprint, bounds and original node/primitive identity
with the **actual Rust process output**. Cases are neutral, `.25/.5/1` for each of
four controls and one combination. Rejection controls invoke the same binary and
check both absent-output and existing-output preservation. Deliberately corrupted
input copies are temporary and are removed after the control run.

## Existing GLB binary support boundary

The original `compiled-character-probe` admits only `nvwa-existing-fixture-control`. The separate `compiled-numeric-probe` executes the approved common MakeHuman sample
with the same frozen manifest and case IDs as path B. Its actual supported operators and missing rig/skin/graphics gates are listed in
[ADAPTATION.md](ADAPTATION.md). A profile is not a general Blender/MPFB rule engine.

The bounded decoder accepts one embedded GLB buffer and finite f32 VEC3 POSITION /
morph accessors, including byte offsets and strides. It rejects sparse accessors,
required extensions, unsupported/nonzero default morph weights, missing bindings,
invalid hashes, invalid ranges and non-finite geometry/bounds. It is not a general
glTF validator. Other attributes remain referenced in preserved primitive metadata;
normal/tangent morphs are not evaluated. The source GLB is never written.

Positions stay in each mesh's original glTF local basis. No global vertex index is
used across primitives. All source node transforms/hierarchy and skin metadata plus
inverse-bind matrices are retained in the private receipt; they are **not evaluated**.
The experiment does not skin, animate, relocate joints, fit clothing, render, save a
Work, run desktop/Web or assess character quality. Garment state remains `null`.

See [REPORT.md](REPORT.md) and compact [control evidence](evidence/control-summary.json).
The full receipts are private `.work/` evidence; the summary records their hashes.

Approved-sample continuation and current numeric operator scope are in
[ADAPTATION.md](ADAPTATION.md). This does not upgrade the old fixture evidence.
