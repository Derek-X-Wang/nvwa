# Feature-direction v4: one attempt rejected, no garment generated

**#80 remains HOLD.** The reviewed v4 direction rule completed all30 source
points and581 logical samples, retaining623 nearest-face inequalities. Its one
frozen authoring attempt then rejected an infeasible fixed/zero-slope sample.
No candidate MHCLO or asset manifest exists. This is a constraint-feasibility
result, not a measured garment-quality failure or improvement.

The [original baseline and v3 rejection](RESULTS.md) remain unchanged. The
[implementation contract](FEATURE-POLICY-V4.md), [fixed policy](feature-policy-v4.json)
and [machine-readable outcome](evidence/feature-v4-outcome.json) identify this
separate attempt. Both actual rejection receipts and source capsules remain in
the local work-product archive. The summary does not replace raw records.

## What changed and what stayed fixed

V3 could not choose a unique normal where several nearest triangles shared a
source feature. V4 derives directions from source-ID keyed, area-weighted vertex
normals and their normalized barycentric interpolation. Every nearest face keeps
its own geometric normal and inequality. No easiest-face selection or unrelated
surface averaging is allowed.

V4 uses the same original30-source connected patch,70mm radius,1/.75/.25 feather
weights,20mm displacement cap,581 logical samples,1mm ideal margin and0.9999mm
saved-f32/text residual floor. Original topology, helper coefficients, full skin
weights, materials, body deletion mask, source assets and quality gates stay fixed.
A separate v4 source closure, policy and authorization prevent reuse of v3 identity.

Independent pre-freeze review found and resolved two issues: final receipt
publication now remains inside the guarded lifecycle; evaluation independently
rebuilds directions, slopes, the complete interval and actual saved offsets instead
of trusting receipt numbers. Original reviews and repaired-source reviews are
retained. Technical freeze approval did not predict candidate feasibility.

## Actual execution and independent audit

The one actual run used the existing current19 corpus. Admission authenticated
that corpus and reran all19 original baseline checks before consuming the new
attempt directory. No runtime build, new capture, asset download or model run was
needed. The frozen309-file execution closure did not change during the process.

| Observation | Actual result |
| --- | --- |
| Bounded process |163.119873166s; exit1; no timeout |
| Completed source directions |30/30 |
| Retained logical samples / face inequalities |581 /623 |
| Author receipt |`REJECT_AUTHORING_SINGLE_ATTEMPT` |
| Error |`infeasible fixed/zero-slope sample` |
| Candidate / manifest files |0 /0 |
| Fixed inequalities below1mm |30, across27 logical samples and16 body faces |
| These fixed slopes |All exactly0; active garment sources outside the30-source patch |
| Quality scoring / candidate Web A/B / CLI exchange |NOT-RUN; no candidate |

The independent outcome auditor checked all retained logical memberships and
claimed face coverage, counted blockers, verified source/capsule identities and
reconstructed the first original garment point from source OBJ/MHCLO inputs.
It performed **one** nearest query against the same frozen displayed-body mesh.
It did not independently repeat the other580 nearest queries, the full30-direction
traversal or the19-case baseline arithmetic. Full baseline arithmetic ran in
actual author admission; its earlier independent audit remains separately pinned.

## Why the first fixed inequality is impossible

Logical sample198 is the source258 vertex of garment triangle420, with
barycentric weights `[0,0,1]`. Source258 is outside the frozen patch. Its
movement direction and inequality slope are therefore exactly zero.
The independently reproduced nearest displayed-body face is13665, with source
IDs `[8318,8308,8309]`. The signed distance to that face's infinite supporting
plane is `-0.008151335683567537 m`.

The required inequality is:

```text
-0.008151335683567537 + amplitude * 0 >= 0.001
```

No amplitude can satisfy it. Changing the movement amplitude or choosing a
convenient tied face would not be a valid repair under this frozen contract.
No amplitude was selected, and no parameter sweep or second attempt ran.

## What the distance does not establish

The actual nearest point is on edge8308–8309, about **73.078609383mm** away from
the garment point. This is a boundary of the displayed, masked body: one adjacent
original OBJ polygon is removed by the unchanged garment body-deletion mask;
the other is retained. The displayed body is not a closed collision surface.

Thus the negative8.151mm **supporting-plane projection is not8.151mm of physical
penetration**. Neither this one query nor the counted retained blockers proves
that the source garment is defective, that all blockers arise from mask boundaries,
or that widening the patch would fix the visible shoulder gap.

Before another fitting attempt, resolve which body surface and local clearance
rule can represent garment contact at masked boundaries. Keep the current
rejections, original crossing witness and19-case quality requirements. This
report proposes that investigation; it does not authorize another authoring run,
a larger patch, changed margin, body-mask edit or alternate collision mesh.

## Checks, reproduction and limits

From the repository root:

```sh
python3 -B scripts/check-portable.py current19-shoulder-refit
```

The complete old+new group passed **239 tests in each Python mode** locally
(normal16.688s; optimized15.501s). The102 new controls include directions and
refusals, complete face coverage, signed-slope intervals, realized residuals,
source and artifact admission, forged provenance, and receipt-publication failure.
Independent source-mutation controls turn real failure cases red. The unchanged
portable catalog already discovers these tests in CI; no test or gate was removed.

```sh
python3 -B experiments/85-current19-shoulder-refit/feature_author.py --help
python3 -B experiments/85-current19-shoulder-refit/feature_evaluate.py --help
```

Actual execution also needs the locally retained corpus, original source files,
independent audit, exact execution closure and a separately approved parent freeze.
The consumed attempt directory must not be reused. These interface commands are
not permission to repeat authoring. Candidate evaluation requires a candidate and
its separate scoring freeze; neither exists from this run.

Product assets, runtime code, dependencies, Cargo.lock, historical117 protected
files, old298 execution sources and original CI/check bodies remain unchanged.
The current19 baseline is a new cohort, not recovery of the missing historical18
raw arrays. GPU/shading parity, candidate quality, Web A/B and CLI candidate
save/reload are NOT-RUN. Ordinary desktop UI remains deferred by policy. #79 and
M2 are not expanded; #3 remains blocked; #4 retains its measurement gaps.

**PARTIAL — direction and constraint implementation verified; one actual attempt
rejected and independently localized; garment-quality improvement unverified.**
