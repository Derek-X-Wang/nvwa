# Feature direction and all-nearest-face policy v4

Implementation contract for #80. This is not authoring authorization. The parent
must review and freeze the completed implementation before one actual attempt.

## Fixed scope

- Candidate ID: `nvwa-current19-shoulder-feature-refit-v4`.
- Authoring policy version: `4`; a separate policy JSON and execution freeze.
- Keep the consumed v3 rejection, its source capsules, current19 raw corpus,
  original experiment84 policy/support, all existing137 controls and quality gates.
- Reuse the admitted actual current19 corpus and independent audit. Reauthenticate
  and rerun all19 baseline gates before authoring, and before candidate reads.
- Original30 connected source offsets,70mm radius, feather weights1/.75/.25,
 20mm cap,581 logical samples,1mm ideal margin,0.9999mm saved-f32/text floor,
  original topology/helpers/full weights/materials/body mask and scorer limits.
- No full actual30-direction/581-sample traversal, authoring, candidate score,
  runtime build, download or model run during implementation. Small declared
  fixtures and the retained real source213 witness are permitted controls.

## Geometry semantics

Accumulate oriented source-triangle area vectors in frozen source order and
normalize each source vertex sum. At the closest source feature, normalize the
source-ID keyed barycentric interpolation of those vertex normals. Only then
apply the original feather weight. This is source geometry, not a claim about
production shading-normal parity.

Keep exhaustive nearest-face enumeration with the original squared-distance tie
bound `1e-12 m^2`. Exact zero barycentric weights identify the active source
feature. Selected direction ties must have the same source feature, exact point
and source-keyed weights. Otherwise refuse. Equivalent face interpolations must
agree within the existing1e-9 vector limit. Refuse invalid source topology,
nonfinite/zero normals, local disconnected/nonmanifold fans, relevant degenerate
faces, inconsistent winding or nonpositive applicable face orientation. A
connected open boundary fan is allowed. Never choose the first/easiest face,
average unrelated surfaces or alter tolerances after seeing an outcome.

For each original logical sample retain every nearest face's own projected point
and oriented geometric normal. Impose all inequalities on the same amplitude:
`d + amplitude*a >= .001`. Preserve the original interval rules: positive slope
above1e-12 raises L, negative slope below-1e-12 lowers U, near-zero slope refuses
only if the fixed distance misses the margin. Empty/nonpositive intervals refuse;
choose the single original lower endpoint, without sweep or retry.

Count581 logical samples separately from K nearest-face inequalities. Preserve
duplicate logical samples. Each inequality has stable `(logical_sample0,
body_triangle0)` identity. Complete nearest-face coverage and every realized
saved-f32/text residual >=.0009999m are mandatory; an ideal-only result cannot pass.

## Shared interface and ownership

All new modules live beside the old experiment85 modules. Do not edit old Python
files or share their module-global authorization by monkeypatching.

- Primary worker owns `feature_policy.py`, `feature-policy-v4.json`,
  `feature_author.py`, `test_feature_policy.py`, `test_feature_author.py`.
- Parallel helper owns `feature_execution.py`, `feature_evaluate.py`,
  `test_feature_execution.py`, `test_feature_evaluate.py`.
- Parent owns this contract, final docs/evidence, Git/PR/CI and actual execution.
  No overlapping writer. Coordinate material interface changes through parent.
- `feature_execution` provides `KIND`, `CANDIDATE_ID`, `AUTHORING`, `SCORING`,
  `required_execution_paths()`, `execution_files()`, `reference_policy()` and
  `load_context(freeze_path, corpus, allowed_statuses)`. Its Context keeps old
  `freeze/records/loaded/baseline/mapping/policy/support`; add `feature_policy`.
  Here `policy` remains the unchanged original geometry/scoring policy.
- Policy path is `feature-policy-v4.json`. Its JSON is version4 and binds the
  original policy/support hashes and complete accepted semantics above. The
  helper validates that JSON through primary's public validation seam; agree
  ordinary function names through parent before depending on them.
- Public policy seam: `validate_policy(policy) -> policy`. Geometry seams:
  `source_normals(body, triangles)` returns a normalized source-ID mapping with
  body/triangle identity and incidence metadata; `nearest_faces(point, body,
  triangles, smooth, diagnostic=None)` returns all per-face records sorted by
  `body_triangle0`. Reuse the same body/triangle objects for that normal mapping.
- Freeze KIND is `nvwa85-current19-feature-author-score-freeze-v4`; stages are
  `FROZEN_FOR_CURRENT19_FEATURE_AUTHORING_V4` and
  `FROZEN_FOR_CURRENT19_FEATURE_SCORING_V4`. Receipt kind is
  `nvwa85-current19-feature-authoring-receipt-v4`; manifest kind is
  `nvwa85-current19-feature-offset-asset-manifest-v4`.
- Freeze identity extends old fields with `authoring_policy_version:4`,
  `feature_policy_sha256` and a parent-bound `previous_rejection` file row.
  Execution source closure includes old code, all new Python files, new policy
  JSON and this contract. Capture284/compiled237 identities stay separate.
- New author receipt/asset manifest use distinct v4 kinds and carry the above
  policy identities. Keep old artifact/hash crosslinks, exclusive attempt path,
 19-case displacement checks and unscored-single-candidate states.
- Author receipt exposes `logical_samples` (581 complete source/sample records,
  each with `logical_sample0`, `triangle0`, `sample0`, `barycentric`, `sources`,
  `nearest_face_ids`) and `planes` (K records with those sample identities,
  original `d_m/slope/plane` fields and realized residuals). Every plane's
  `body_triangle0` identifies the actual retained body face. Successful receipts
  include `logical_sample_count:581` and `face_constraint_count:K`. Both count
  fields are mandatory in the asset manifest too and must match the receipt.
- Each inequality has matching top-level `body_triangle0` and nested
  `plane.body_triangle0`. The coverage validator accepts independently rebuilt
  `expected_samples` with the same logical metadata and nearest-face IDs; it
  must reject jointly omitted claimed face IDs and inequalities. Evaluation
  rebuilds actual expected sets and plane geometry from original neutral inputs,
  not only from claims in the author receipt.
- Evaluator authenticates all new policy/artifact/count identities and complete
 581/K coverage. Reuse unchanged position/scoring pure helpers and explicit
  strict default-arm2 ROI check. No weakening of the old crossing witness.
- Evaluation independently rebuilds the original30 feature directions and ring
  weights, every sampled slope, the complete signed-slope/capped interval and
  its unique positive lower endpoint. The receipt's source planes, slopes,
  amplitude/lower/upper and interval metadata must agree. Each actual parsed
  candidate offset must equal the declared original offset plus that amplitude's
  direction/scale change after the original f32 round trip; do not trust the
  receipt's numeric claims merely because its bytes were frozen.
- Final success receipt publication belongs inside the guarded publication
  lifecycle. A one-shot final receipt-write failure must retain a truthful
  rejected receipt reflecting any actual candidate bytes, and propagate error.

## Acceptance before actual attempt

Both Python modes must cover source213's three faces and eight logical sample
memberships; old v3 still rejects that witness. Test face/edge/vertex continuity,
source identity and triangle-order behavior; disconnected/distinct/degenerate/
reversed/zero/nonfinite refusals; signed-slope interval semantics; contradictory
face inequalities; omitted-face rejection; and an ideal-pass/one-realized-face-
fail case through a production-called seam. Also test wrong/missing/changed
freeze, previous-rejection identity, source closure, artifact identities,
baseline-before-candidate order, count/coverage refusal and consumed attempt.

Independent implementation review precedes parent freeze. One exclusive new
attempt directory is then consumed. Any rejection is retained and stops this
attempt. A created asset still requires unchanged all19 offline quality checks.
Only an offline pass allows actual Web A/B and CLI save/reload/exchange. Routine
desktop GUI remains deferred; #79/M2 unchanged, #3 blocked, #4 gaps retained.
