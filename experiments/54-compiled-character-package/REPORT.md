# Path A preparation checkpoint — 2026-10-16

**PARTIAL — the offline Rust package probe executes continuous morph evaluation on
Nvwa's real existing fixture. It does not establish MakeHuman compatibility or select
a character foundation.** The approved common MakeHuman/MPFB sample is unavailable.

## Actual scope and evidence

Only `experiments/54-compiled-character-package/` was changed. Product code, root
Cargo/lock, old experiments, original assets and the shared comparison contract were
not changed by this worker. There were no downloads, installs, new libraries, GPU/UI
tasks, commits, pushes or external writes.

The probe reads `assets/fixtures/nvwa-humanoid.glb` with SHA-256
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6` and the existing
hashed character profile. Its sidecar explicitly binds four parameters to node 22,
mesh 4, primitives 0–4. Four eye primitives remain separate and unchanged.

The actual Rust process passed **14 cases**: neutral; `.25`, `.5`, `1` for jaw width,
nose width, smile and shoulder width; and one mixed recipe. For each case, an
independent Python GLB decoder compared all **24,736 primitive vertex entries**
(including duplicated topology entries) through the complete little-endian f64
POSITION fingerprint, local bounds and source node/primitive identities. Intermediate
maximum displacements scale by `.25` and `.5` within `1e-12` local units.

| Control | Maximum local displacement at weight 1 |
| --- | ---: |
| jaw_width | 0.0688607394695282 |
| nose_width | 0.06944765770627767 |
| smile | 0.03925796059651317 |
| shoulder_width | 0.08988398313522339 |

These are mesh-local geometric distances, not world-space body measurements or
visual quality scores. No rest/skin/world transform was applied.

**16 failure controls passed.** They cover wrong profile hash/ID, asset hash,
manifest hash, wrong node binding, missing/duplicate primitive bindings, missing/
unknown/out-of-range values, inverted profile bounds, non-finite recipe JSON,
non-finite real POSITION data, sparse accessors, non-finite accessor bounds and
valid input with an existing output. Invalid cases returned exit 2, created no new
result, and preserved a pre-existing result sentinel. Original asset, profile,
package and manifest hashes were unchanged after the suite. The non-finite geometry,
sparse-accessor and bound controls assert the specific rejection diagnostic, so an
earlier unrelated hash failure cannot satisfy those controls.

The first independent run caught a source node JSON float-rounding difference in
serde_json defaults. Enabling its cached `float_roundtrip` feature fixed this; the
final suite compares the preserved node metadata exactly. This was a numeric
serialization issue, not proof of skeletal evaluation.

## Reproduction and retained evidence

From repository root:

```sh
experiments/54-compiled-character-package/run.sh
```

The script forces network-offline locked Cargo and one compilation job. Rust 1.95.0
and Python 3.14.7 were used. The first cold build took 12.94 seconds with cached
sources; subsequent bounded builds took seconds. End-to-end control duration is
recorded in [control-summary.json](evidence/control-summary.json). This is control
wall time, not an engine/runtime performance benchmark. Peak memory was not measured.

The final exact run and all full receipts are retained under
`.work/final-receipts/`; the compact summary records the absolute private evidence
path and each result hash. Earlier failed/green debug runs are also private under
`.work/`. No per-vertex arrays or duplicate GLBs are retained. The isolated target
cache is intentionally retained for offline reproduction; no processes or servers
remain owned by this experiment. Integration owner controls later cache cleanup.

## Not run and comparison limits

- **NOT-RUN — approved MakeHuman/MPFB common sample, its actual source rules, exporter
  and shared offline reference.** `evidence/approved-sample.not-run.json` is a blocked
  receipt with no fabricated recipe or measured positions.
- **NOT-RUN — body-proportion joint relocation, inverse-bind recomputation, skinning,
  garment fitting, shoulder/elbow/knee poses, normals/tangents and style suitability.**
  Source nodes, skin joint metadata and inverse-bind matrices are preserved only.
- **NOT-RUN — desktop/Web, actual rendering, full-Work save exchange, performance
  acceptance and production integration.** No character or Rust library is adopted.

This proves a bounded explicit-binding position evaluator and its failure preservation
boundary. Existing M2 quality HOLD and #3/#4 boundaries remain unchanged.
