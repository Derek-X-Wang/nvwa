# #80 body-surface and local-clearance investigation

**Changing the query surface alone cannot make the unchanged fixed-patch,
1mm supporting-plane model feasible. This does not establish19 physical garment
penetrations. #80 remains HOLD. No refit or candidate was created.**

This isolated diagnostic reconstructs all27 logical blocker points from source
OBJ/MHCLO bytes and independently re-queries all30 retained fixed inequalities.
It uses the existing current19 corpus. It changes no production surface, asset,
mask, patch, margin, v3/v4 policy, historical gate, Cargo file, workflow or lockfile.
The [derived evidence](evidence/blocker-summary.json) contains all30 rows, original
OBJ polygon/fan identities, closest points, feature ownership and source hashes.
It is a summary, not a substitute for locally retained raw records.

## Surface ownership and source semantics

The production [upload path](../../crates/nvwa-runtime/src/b1.rs) evaluates both
parts before publication. `visible_body_indices` removes a source quad when **any
source ID is >=13380**, or **all four source IDs are in the garment's
`delete_verts` set**. It does not remove a polygon merely because one vertex is
masked. The mask owner is `garment/female_sportsuit01.mhclo`, not `body.mhclo`.
The mask contains4678 source IDs and removes1932 real-body polygons.

Independent source/group enumeration proves that the unchanged >=13380 test
excludes exactly the non-body OBJ groups in these admitted bytes:

| Original OBJ role | Polygons | Admitted for unmasked body query |
| --- | ---: | --- |
| `g body` |13378 |all13378 |
| `helper-*` |4358 |0 |
| `joint-*` |750 |0 |

All18486 source faces are quads. The excluded groups include `helper-tights`,
skirt, hair, genital, tongue, teeth, eyelash and eye helpers, and joint cages,
including eye joints/targets. They are fitting/rig data, not substitute physical
body surfaces. The comparison retains exactly the same real-body groups and
source winding; it removes only the garment-deletion filtering step.

| Query surface | Polygons / fan triangles | Source vertices used | Boundary edges |
| --- | ---: | ---: | ---: |
| Actual displayed, masked body |11446 /22892 |11574 |246 |
| Same `g body` before garment deletion |13378 /26756 |13380 |0 |

The unmasked real-body mesh has40134 edges, all with two incident faces, and no
inconsistent directed edge pair. This is an edge-closure/orientation observation.
It does not prove outward orientation, vertex manifoldness, lack of
self-intersection, anatomical correctness, or physical inside/outside.

The source **fitting cage** has19158 vertices, including helpers. `body.mhclo`
maps all19158 to themselves. Current19 retains all body source vertices and full
influence rows, even though its uploaded body indices are masked. Thus existing
raw coordinates can carry removed real-body polygons without inventing geometry.
This diagnostic queries neutral source-f32 coordinates only; it does not claim a
new posed-body or rendering result.

Garment source positions are set by [signed MHCLO mapping](../../vendor/humentity/src/assets.rs),
not the garment OBJ's authored positions. The [loader](../../vendor/humentity/src/loaders/mhclo.rs)
parses three signed f32 helper coefficients, normalizes by their signed f32 sum
when its absolute value exceeds f32 epsilon, and applies axis-scaled offsets.
The independent parser reproduces that operation order and keeps all30 rows with
negative helper coefficients. It adds no extra coordinate scale.

The production [full-weight transfer and PreparedSkin path](../../crates/nvwa-b1-adapter/src/lib.rs)
multiplies original positive helper-bone weights by those **signed** coefficients,
keeps each positive final bone aggregate, then normalizes for skinning. It does
not truncate to four influences. Independent reconstruction exactly matches every
anchor source/render influence row:

| Part | Source / render rows | Maximum influences | Source rows above four |
| --- | ---: | ---: | ---: |
| Body |19158 /22077 |7 |981 |
| Garment |1797 /1986 |6 |283 |

This verifies aggregate weight identity for the anchor. It does not rerun posed
skinning or establish source-only anatomical frames. The prior all19 audit remains
hash-bound; its FK reconstruction uses captured `canonical_rest` and `frame_gauge`.

## Complete blocker comparison

The new closest-point implementation minimizes over the bounded triangle
interior and its three closed segments. It imports no old authoring/evaluation
geometry. The unchanged provenance reader authenticates raw20/gzip19 against the
preserved capture capsule; it does not rerun the all19 geometry arithmetic.

The v4 receipt remains623 inequalities on581 logical samples and30 directions.
The fixed subset remains30 inequalities across27 logical samples and16 displayed
body triangles. Every active garment source of this subset is outside the fixed
30-source patch; every retained slope is exactly0. Independent re-query reproduces
every displayed nearest-face set, closest point, distance and signed projection
(projection/distance-squared differences <=1e-12; closest-point difference <=1e-10m).
Ties retain every face. Duplicate logical queries are evaluated once each.

| Classification of the original30 inequalities | Count | Meaning |
| --- | ---: | --- |
| Nearest retained triangle interior |15 |Local plane projection; not mask-boundary evidence |
| Nearest edge |13 |9 mask-boundary;4 internal-edge inequalities |
| Nearest vertex |2 |Both mask-boundary; same logical point, two tied faces |
| Total mask-boundary inequalities |11 on10 logical points |Surface filtering changes these nearest features |
| Total other inequalities |19 on17 logical points |Mask removal does not eliminate their fixed failure |

The11 mask-boundary inequalities have displayed bounded distances51.180–77.393mm,
although their supporting-plane projections are negative. On the unmasked real
body their nearest points are on previously removed polygon interiors, with
positive projections/bounded distances1.927–4.801mm. This demonstrates a false
distant-plane interpretation for this subset; it is not a reason to suppress all
negative values.

For example, logical198/source258 retains displayed triangle13665, original OBJ
polygon7943/fan1, edge8308–8309. Its bounded distance is73.078609383mm and its
supporting-plane projection is-8.151335684mm. The unmasked nearest triangle is
15807, original polygon7903/fan1, sources8276/8235/8236, with an interior closest
point2.762174672mm away and positive2.762174672mm projection. These two triangle
indices belong to explicitly different surfaces; the OBJ polygon IDs preserve
the shared source identity.

The other19 inequalities keep their original source feature after mask removal:

- Fifteen interior inequalities retain negative projections from-0.628567mm
  through-8.799205mm. Their bounded distances equal the projection magnitudes.
  Independent inside/outside and anatomical-frame proof are NOT-RUN, so they are
  not labeled physical penetrations.
- Four inequalities cover two logical points at an internal edge. They retain
  two adjacent faces each, with positive projections0.973085mm and0.882493mm
  (bounded distance0.973293mm, approximately). Both projections remain below1mm.

On the unmasked surface the27 points produce29 nearest-face inequalities:
25 interior and4 edge. Nineteen inequalities across17 logical points remain
below the unchanged1mm ideal margin. All27 points still have zero movement
direction under the fixed patch. Therefore the existing scalar model still has
constant constraints `d + amplitude * 0 >= .001` with `d < .001`; no amplitude
can satisfy them. No new authoring run is needed to prove this infeasibility.

## Smallest next contract for review

Use the same unmasked **real-body** polygons as the candidate contact domain;
keep helper/joint/eye-helper exclusions and displayed mask ownership separate.
This is a recommended domain for further diagnostics, not an adopted collision
mesh or permission to alter production upload indices.

Define clearance from a **bounded closest point on that domain**, with every tied
feature retained. An unsigned closest distance cannot reject a point inside a
body. A face's signed plane projection cannot establish global inside/outside.
Before using signed bounded distance, independently establish orientation and a
side classification on the admitted surface, with explicit refusals for open,
degenerate, non-manifold, disconnected/ambiguous, flipped or self-intersecting
input relevant to that sign. Keep numerical uncertainty explicit. Edge/vertex
sign rules need source adjacency and a demonstrated geometric basis.

Do not choose a locality radius from these27 failure distances. The bounded
closest point already removes the infinite-plane distance error. If a future
optimization uses a local linear plane, separately justify its trust region from
feature stability and geometry, and re-query saved-f32 positions after movement.
An unsigned radius-only rule must never turn an inside point into a pass.

Preserve the1mm/0.9999mm floors,20mm cap,70mm patch radius, original30-source
connected patch and feather weights. Changing the surface or distance meaning
requires reviewed geometry evidence; it cannot be justified by making these
rows pass. The19 surviving fixed constraints require an explicit disposition
under the reviewed metric before a feasible authoring contract can exist.
This investigation does not authorize a larger patch or changed margin.

Required failure controls for that future contract:

1. Actual distant masked-boundary points must not be called penetration merely
   because a distant face plane has a negative projection. Check every original
   blocker and every tied face, not just logical198.
2. A truly inside point and a strict garment/body triangle crossing must reject.
   Keep the original historical pair `[240,13661]` and its exact input hashes as
   a distinct real rejection control. Disable the production-called predicate
   in isolation and require that control to turn red, then restore it.
3. A segment/triangle crossing can have endpoints farther than1mm from the body.
   Clearance samples cannot replace the unchanged intersection gate. Preserve
   tangency/coplanarity semantics and tolerance witnesses separately.
4. Planted wrong source IDs, helper sign removal, top-four truncation, wrong
   normalization, mismatched body/garment coordinates, faulty canonical/frame
   transforms, stale provenance, omitted ties and reversed winding must fail at
   the production-consumed diagnostic/evaluation seam. Geometry must not excuse
   an invalid frame. Source-only anatomical frame proof remains a distinct gap.
5. Freeze identities and coverage first. Run the reviewed predicate on existing
   current19 raw data before any candidate, retain all current/historical gates,
   and keep ambiguous sign/geometry as a refusal. A changed query feature after
   saved-f32/text movement requires a fresh bounded query, not a trusted receipt.

The next useful action is independent review of this surface/metric evidence and
its failure contract. No new refit is authorized by this report. Better contact
semantics alone would not establish shoulder quality or justify another known
infeasible fixed-patch run.

## Reproduction, identities and limits

From the repository root:

```sh
python3 -B -m unittest discover -s experiments/86-local-clearance -p 'test_*.py' -v
python3 -B -O -m unittest discover -s experiments/86-local-clearance -p 'test_*.py' -v
python3 -B experiments/86-local-clearance/audit.py --archive "$ARCHIVE" --out "$NEW_REPORT"
```

`ARCHIVE` is the existing task-owned Nvwa work-product archive; `NEW_REPORT` must
not already exist. No network, runtime build, new capture, GPU or model is used.
The CLI does not call authoring or publish a candidate. The new tests are isolated
and are not added to the root portable catalog in this investigation.

The source-stable actual diagnostic performed27 displayed and27 unmasked queries,
37.649180833s total, including provenance/weights/topology checks. The preceding
45.236216125s pass was exploratory: the audit source was extended while it ran,
so its recorded source hash is not an executed-source attestation. It remains
retained locally, superseded by the source-stable receipt. No fitting attempt ran
in either pass. Twenty-five isolated tests pass in normal and optimized modes;
the tests include actual patched-seam red controls for unbounded-plane distance
and disabled strict crossing. These analytical controls do not replace the old
historical crossing witness, whose source/input bytes were checked but whose
algorithm was not replayed this time.

The stable raw diagnostic is263465 bytes,
SHA256 `50ccf0c75a6a762dae1b6642411edfdb7f10d70a2e5ba09c0000b936c0a2baff`.
The v4 receipt is still3103250 bytes,
SHA256 `e2950b175f7a84ae15062d5a29b68492cf2ee73a91eef95594bdc89438ee832d`.
The corpus manifest remains
`bd3d5763bc15eadc258327e2bbefb625788663daa0ed8b8d20dcefd99726e7e6`.
The original309-file v4 execution closure and preserved capsule both match
`b61b7241b99a556f0b9cc50ffa3aad8b387df1a2c5e27e7506ec7cb209ef3d25`;
all117 protected historical files remain byte-identical. Exact source asset and
prior audit/rejection identities are in the derived evidence.

The remaining554 logical nearest queries and full30 direction reconstruction are
NOT-RUN. Full19 posed arithmetic, independent inside/outside, source-only
anatomical frames, complete collision freedom, new candidate quality,
GPU/shading/upload parity, Web A/B and CLI candidate exchange are NOT-RUN.
Ordinary desktop UI remains deferred by policy. Historical18 raw arrays remain
missing; current19 is a separate cohort. Original capture rejection, v3/v4
rejections, crossing witness, old298 sources, capture284 closure and all original
assertions/gates remain unchanged. #112 remains FAIL, #3 remains blocked, #4
retains measurement gaps, and #79/M2 are not expanded.

**PARTIAL — all30 fixed inequalities independently re-queried; surface-only
infeasibility proved; physical sign and garment-quality improvement unverified.**
