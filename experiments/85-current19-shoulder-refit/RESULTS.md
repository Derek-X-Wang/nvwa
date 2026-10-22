# Current nineteen-case baseline and one static shoulder attempt

**The complete new baseline passed. The one authoring attempt was rejected before
creating an asset. #80 remains HOLD.**

## What actually ran

One locked, offline native build produced an 81,264,880-byte executable. The build
and captures used the same Apple Silicon Mac, Rust toolchain, production runtime,
source assets, and compiled source closure. No window or renderer was installed.
This is actual CPU runtime evidence, not desktop UI or GPU acceptance.

One process collected the eighteen legacy profile recipes and separately opened
the original v2 rear-arm2 Work for the nineteenth sample. All twenty raw records
(nineteen samples plus completion), nineteen gzip records, and build/source
receipts are retained locally. An independent auditor reread those actual bytes
and repeated the source-table, full53-bone, full-positive-weight, topology, rest,
and posed reconstruction checks for every case.

| Check | Maximum error | Unchanged limit |
| --- | ---: | ---: |
| Ordered scalar-f32 source fit and morph round trip | 0 m | 1e-7 m |
| Scalar-f32 prepared skin | 0 m | 1e-5 m |
| Source weights / FK / binary64 skin | 4.86193e-7 m | 1e-5 m |
| Separate binary64 signed-helper rest fit | 1.09593e-7 m | 1e-6 m |
| Normalized original source weights | 3.63248e-8 | 1e-6 |

The independent FK reconstruction still uses captured `canonical_rest` and
`frame_gauge`. It is not a new source-only anatomical frame reconstruction.
The [baseline report](evidence/baseline-v2.json) contains per-case results and
hashes. A report does not replace the locally retained raw corpus.

The first complete capture remains REJECT. Its extra binary64 check had a Python
dictionary-axis iteration bug. The original data and 284-file source capsule were
preserved. A source-grounded test caught the old failure, and a fresh capture with
the repaired checker passed. The executable, arithmetic, and limits did not change.

## Why the single attempt stopped

The reference v3 policy permits only MHCLO offset changes on one fixed connected
30-source shoulder panel. Topology, helper coefficients, full skin weights,
materials, body deletion, and the original OBJ remain unchanged. The author
reserves one exclusive output directory before computing directions. It does not
choose another direction or amplitude after a rejection.

At garment source point **213**, three body triangles (**13494, 13495, 13524**)
have the same nearest point and squared distance. Their face normals differ. The
frozen policy requires tied normals to agree within `1e-9`, so the unchanged
`nearest_plane` rule rejects with `ambiguous nearest normal tie`.

The actual run stopped after 21 completed source directions. It completed **0 of
581 sample-plane constraints**, chose no amplitude, and created **zero candidate
files**. The 298-file prospective source closure remained unchanged.
See [the retained rejection summary](evidence/authoring-rejection.json).

This establishes that the fixed nearest-face-normal policy cannot define a unique
direction for this source point. It does **not** establish that a generated garment
would pass or fail the nineteen-case quality comparison. No garment was generated.
A future bounded policy must define how edges and vertices select a direction
before another attempt; this run did not try such a policy.

## Checks and boundaries

From the repository root:

```sh
python3 -B scripts/check-portable.py current19-shoulder-refit
```

The actual old rejected crossing `[240, 13661]` was also checked. It is detected
normally; disabling the real crossing predicate in an isolated control makes the
same check fail; restoring the predicate passes again. This proves that known
old rejection seam. It is not a new candidate-quality result.

The original eighteen historical raw arrays remain missing. Their exact checks,
fixtures, authenticator, and 117 protected historical files are unchanged. The new
cohort has its own identity and is not recovered historical evidence. All original
portable check bodies and CI gates remain in place.

Candidate quality scoring, generated shading/upload parity, Web A/B, and CLI
candidate save/reload are **NOT-RUN** because an offline candidate pass is required
first. No product asset was replaced. #79 and M2 are not expanded, #3 remains
blocked, and #4 retains its measurement gaps.
