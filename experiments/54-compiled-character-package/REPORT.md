# Path A — actual shared MakeHuman numeric comparison

**PARTIAL — the source-compiled Rust package matches the independent MPFB reference
for body positions, helper-derived joint endpoints and the selected garment across
all eight frozen cases. Rest matrices, skinning, poses and graphical acceptance are
not verified. No character foundation or production dependency is selected.**

## Frozen inputs and execution

Common manifest SHA-256:
`2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`.

Root owns `.work/character-approved-20261016/common-sample.json`, the approved source
files and `reference-full-run3/`. Its Blender 5.2.2 / MPFB 2.0.18 reference retains all
19,158 hm08 vertex IDs/helpers and captures body geometry before clothing visibility
MASK modifiers. Baseline: raw hm08, scale .1, no macro defaults or grounding. The
measured raw-to-reference mapping is `.1*x, -.1*z, .1*y`, in Blender mesh-local metres.

The A compiler reads **source paths and parameters from that manifest**, checks their
byte counts/SHA-256/license and independently checks MPFB/garment extraction receipts.
It compiles raw OBJ basis positions, four sparse source targets, GameEngine helper
index rules and MHCLO weighted proxy/scaling rules. In full-sample mode it never
opens reference geometry to construct the package or recipes. Reference files are
opened only by the independent comparison step and checked against frozen hashes.

The actual Rust binary evaluates signed `torso_length` and `jaw_drop` continuously.
It recomputes joint CUBE/MEAN centroids from deformed vertices and refits all 1,797
`female_sportsuit01` vertices from proxy triples plus dynamic source-axis scales.
It does not interpolate endpoint skeletons/garments or switch preset meshes.

| Compared channel, all 8 cases | Entries per case | Maximum absolute component error |
| --- | ---: | ---: |
| Body positions | 19,158 vertices | `3.807830809554602e-7 m` |
| Joint heads/tails | 53 bone pairs | `2.539825438852006e-7 m` |
| Garment positions | 1,797 vertices | `3.0110187632104157e-7 m` |

All are below the root's **predeclared `1e-5 m` component tolerance**. Cases are
neutral, each parameter's negative/positive endpoints and positive midpoint, plus a
midpoint combination. All seven non-neutral cases change real body vertices. Positive
body strength 1 moves 12,865 body entries, 81 joint endpoints and 913 garment entries;
maximum displacements are .1028 m, .1028 m and .102801028 m respectively. Positive jaw
strength 1 moves 42 body entries by up to .005632051 m; this local target does not move
the selected rig's endpoints or garment. Half-strength linearity error across the
measured channels is at most `2.220446049250313e-16 m`.

## Failure preservation and retained controls

Eight corrupt-real-package controls passed: wrong recipe package/common digest,
out-of-domain value, invalid unselected target index, invalid helper index, unknown
bone parent, garment proxy index and zero garment scale denominator. Every case
returned exit 2, created no new result, preserved an existing result sentinel and
left the real package/recipe/common manifest unchanged. Diagnostics are asserted.

Separate retained controls remain green: existing original GLB 14 cases + 16 rejection
controls; handwritten numeric 7 cases + 6 rejection controls; 10 analytic unit controls.
Those are separate sample classes. Strict offline Clippy, formatting and changed-file
whitespace checks pass. No checks lasted five minutes; no wefty execution was needed.

## Reproduce and inspect

From repository root, one command reruns the actual full comparison:

```sh
experiments/54-compiled-character-package/run-common.sh \
  "$PWD/.work/character-approved-20261016/common-sample.json" \
  "$PWD/.work/character-approved-20261016/reference-full-run3" \
  "$PWD/.work/character-approved-20261016/system-assets/clothes/female_sportsuit01/female_sportsuit01.mhclo"
```

The script builds with `--locked --offline -j 1` and uses only this experiment's
Cargo/lock/target. Rust/Cargo 1.95.0 and Python 3.14.7 were used. Final receipts are
private under `.work/full-common-run1/`: compiled package, exact recipes, Rust outputs,
comparison, preservation controls and logs. Compact summaries plus result hashes are
in `evidence/common-{comparison,failure,continuity}-summary.json`.

The package is **2,117,964 bytes** uncompressed JSON, SHA-256
`dcdc82b42a86d9b8ffd6e57803171eae73df4a564bcec04cc4d13d30183ef022`.
Eight evaluation/comparison cases took 3.529 seconds including process launch and
Python comparison; this is not an engine performance benchmark. Peak memory was not
measured. No duplicate GLB or large generated arrays are tracked.

## Limits and ownership

- **NOT-RUN:** bone rest matrices, inverse-bind recomputation, weight transfer, posed
  skinning, shoulder/elbow/knee poses and animation quality. Output preserves endpoint
  parent/roll identity, but emits no fabricated matrices or inverse binds.
- **NOT-RUN:** native/Web graphics, materials, clothing intersections, style suitability,
  full-Work save exchange, production integration and performance acceptance.
- Only `experiments/54-compiled-character-package/` changed. No product/root Cargo,
  source asset, old experiment or shared contract edits; no additional downloads,
  installs, GPU tasks, commits, pushes or external writes by this worker.
- Private receipts and isolated target cache are retained for root review/reproduction.
  No owned checks/processes or servers remain active. Root owns later cache cleanup.

Existing M2 quality HOLD and #3/#4 boundaries remain unchanged.
