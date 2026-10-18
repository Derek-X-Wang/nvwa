# Contract and source review — prepared controls

Status: **NOT-RUN — actual Rust compatibility/mutation execution awaits root's
independent review and scheduled build.** Cheap tooling controls do not discharge
the product requirements below.

## Accepted authority

The accepted #85 `parameters-design.md` (SHA256
`6b5ebb78bedb169e5cef49907b31c168d8fe7d0598e8227d01c18bbb6c99a347`),
line109 states:

> 全零new与old实际CPU geometry、indices、UV及53bone rest/posed/IBM/gauge相同（忽略entity/generation/serial等身份字段）。旧8个reference recipe的新六项为0，再与旧profile按原数值门比较；原40组姿态门仍运行，不改阈值。所有零值若非逐float相同必须先保留失败并解释，不直接降为宽松近似。

Line110 states:

> 生产调用处的真实target遗漏/错号/错符号/二次×0.1/未用新增字段 mutation应red；源独立f64叠加与实际helper/骨架/上传差异检验分开。

The parent-designated `review89/admission-gap-audit.md` classifies these as
remaining CPU acceptance evidence gaps, not an established implementation defect.
Its retained original57 full40 and current sampled40 CI are distinct evidence;
neither is silently reassigned to the new profile.

## Production seams and actual observations

All production links below refer to the pinned581 source; [pins.json](pins.json)
authenticates the relevant bytes.

- [b1.rs](../../crates/nvwa-runtime/src/b1.rs): `motion_app`1985 installs actual
  runtime/playback systems and the admitted in-memory authenticated asset reader;
  `fill_v2`2993 supplies the actual selected manifest and25 fixed payloads;
  `open_ready`3006 uses ordinary `EditorState.request_open` and publication.
- `b1::install`53 schedules the actual production `appearance::update` after B1
  publication. New tests select normal canonical Work appearance through
  `CharacterAppearance::b1_cc0_for`, then ordinary Open. They never insert a UV
  attribute manually, call a reconstruction oracle to fake an upload, replace an
  actual frame with fixture arrays, or add a production API.
- `b1_frame_snapshot`3720 checks current Work/transport/generation/mesh bindings,
  reads actual display POSITION/indices/normals/tangents and all53 bone frames,
  and verifies uploaded buffers against the actual complete-positive skin frame.
  The test fragment reads UV0 directly from that same bound `Assets<Mesh>` handle.
- Production display creation858–870 has no UV0. The exact-zero test therefore
  covers **two** ordinary states: untextured (both body/garment UV0 absent), and
  skin-on (actual body UV0 required present, nonempty and exactly equal). Garment
  display UV0 remains absent on both profiles and its absence is an explicit
  equality, not a claim that a nonexistent uploaded array was measured. No source
  UV or manually manufactured UV substitutes for that observation.
- [BoneFrame](../../crates/nvwa-b1-adapter/src/lib.rs)20 has name, parent and nine
  matrix fields: rest, posed, inverse_bind, local_rest, local_posed, skin,
  canonical_rest, canonical_posed, frame_gauge. Every field on all53 actual bones
  is covered, in preserved source order; name/parent identities cannot be ignored.
- Existing endpoint test3019 is unchanged, including its independent original
  target-text sparse delta/0.1 unit witness and actual uploaded POSITION check.
  Only the copied production mapping599–611 is faulted; expectations are intact.

Legacy profile/backend/base and new profile/backend/base retain their distinct
correct identities in compact comparison receipts. Only entity/mesh handles,
generation, frame serial and other transport identity bookkeeping are excluded
from geometry comparison. Work parameters, diagnostic pose, full source-ID and
bone order, hierarchy, topology and complete positive influence rows are covered.
Actual display/model transforms and fitted rest arrays are also compared under
the original matrix/geometry bounds, with exact transforms at zero. Normal and
tangent arrays have recorded hashes and the original per-frame validity gates;
no new cross-profile normal-angle tolerance is invented. No profile ID is
rewritten to manufacture equality. Compact actual observations are written before
numeric assertions to retain failure hashes, Work values and source identities.

## Original40 coverage and numeric gates

[cases.json](cases.json) is copied exactly from the recipe/pose entries of
[56 frozen manifest](../56-b1-pose-reference/reference/frozen/manifest.json),
SHA256 `98ffb4b7947101bdd2107055beed866d7f040b33f699fb859c090c4c03242636`.
The pinned [five authored poses](../56-b1-pose-reference/poses.json) have SHA256
`8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2`.

Eight `(torso_length, jaw_drop)` recipes: neutral(0,0), body-negative(-1,0),
body-half(.5,0), body-positive(1,0), face-negative(0,-1), face-half(0,.5),
face-positive(0,1), combined(.5,.5). Each uses neutral, shoulder, elbow, knee,
combined. Old and new canonical Works clear the motion timeline and select that
same original diagnostic pose; all six added new fields remain exactly0.
Both parts retain all actual render rows, triangles and complete positive joint
rows, including body rows with more than four weights. POSITION, fitted rest,
full influence rows and source IDs must have matching render-row counts. The
unique source-ID domains must equal exactly `0..19158` for body and `0..1797` for
garment. Render rows are never deduplicated or constrained to these unique counts:
UV seams repeat source IDs. Parent's retained R4 observations report22077 body
render rows /19158 unique IDs and1986 garment rows /1797 unique IDs. Those actual
counts informed the R2 correction; this source pass does not itself execute Rust.
The complete old/new render arrays still compare row-for-row.

The actual zero comparison requires exact POSITION, indices, UV0 and complete
BoneFrame equality, plus matching serialized hashes for positions and bones.
The40 old/new comparisons use the original
[57 compare.py](../57-b1-pose-runtime/compare.py) and
[57 validation.py](../57-b1-pose-runtime/validation.py) bounds:

| Gate | Unchanged bound |
| --- | --- |
| Body / garment maximum position component | 1e-3m / 3e-3m |
| All bone matrix components / canonical posed joint heads | 1e-4 / 1e-5m |
| Independent scalar LBS from actual complete raw rows and posed×IBM | 1e-5m |
| Rest×IBM, stored skin, canonical/gauge physical identities | 1e-5 |
| Affine bottom row / rigid orthonormality and determinant | 1e-5 / 1e-4 |
| Nonzero normal/tangent unit length / tangent handedness | 1e-4 / 1e-6 |

Indices, source IDs, source/bone order, parent names, full influence rows and
present/absent UV0 remain exact discrete correspondence checks for every pair.
All numerics reject nonfinite values and incomplete/vacuous arrays before maxima.
The scalar LBS check is independently accumulated f64 from actual fitted rest,
actual matrices and all actual raw positive influences. It is not an independent
MakeHuman source-target or Blender reference oracle. Its scope is distinct from
71's independent original-text shape computation and actual cohort checks.

This40-case run binds **current production legacy/new numeric equivalence** to the
original full40 coverage/limits. It does not claim the external historical source
arrays were freshly recomputed by Blender or that sampled CI became full40.
Original full-reference evidence is retained at
[57 final-current40.json](../57-b1-pose-runtime/evidence/final-current40.json).

## Five real faults, separately compiled/executed when authorized

Each targets only `head_width` at the real mapping, leaving source authentication,
original expectations and all other parameters intact:

| Fault | Actual source change | Required existing assertion |
| --- | --- | --- |
| Omit new target | Skip only head decrease target; negative sign first | head_width -1 must reach actual Mesh POSITION |
| Wrong name/ID | Route head pair to existing nose pair names | head_width -1 selected signed target/units must reach fitted body |
| Wrong sign | Negate head parameter before signed pair | same signed-target assertion |
| Second×0.1 | Scale head field by an extra0.1 | same signed-target assertion |
| Ignore field | Force head value0 | actual POSITION assertion |

Faults have exact single-occurrence text anchors and distinct mutant hashes.
Wrong-name uses another authenticated existing target, so a missing-asset error
cannot satisfy the gate. Each red must run the named endpoint test, exit101 and
hit the specified head-negative semantic witness, with zero passed/one failed.
Each fault restores exact source bytes and reruns green before continuing. Any
unexpected/compile/error result is retained as a failed attempt, followed by
restoration; it is never relabeled a red proof or skipped. No lowered thresholds,
four-weight path, clipped influences, substitute oracle mutation or body deletion
is permitted.

## Preparation limits and resources

No Cargo, GUI/GPU, app, server, network, renderer capture or commit was performed
in this preparation. The only authored scope is this new72 directory. Actual
source/target/log/archive outputs are created only by a later explicit
`run.py --execute` under its fresh output. Root owns their scheduling and cleanup.
The author checkout, integration581 source and active71 channels are untouched.
Historical failed R1/R2 cache paths were inspected read-only and were absent;
no cache seed, cleanup or reuse was performed or claimed.
