# Independent R1 review — experiment63 offline accessory preparation

Reviewer: Codex Astra/high. Checkout: `/Users/derekxwang/.codex/worktrees/b1-appearance-preview/nvwa`. Scope is only `experiments/63-b1-accessory-fit/` and its declared local inputs. This is separate from experiment62, PR81/#78, CI, and #79 admission.

**Verdict: no P1/P2 findings in this bounded offline preparation. Accept its declared offline result. Do not treat this review as runtime, appearance-quality, independent MPFB-reference, or mainline acceptance.**

## Source and policy review

Read all of `fit.py`, `test_controls.py`, `CONTRACT.md`, `README.md`, public `RESULTS.json`, and the retained full summary. Compared the relevant formulas directly with current vendored Humentity `shape_mesh_from_helpers_mhclo`, the loader's coefficient normalization and `get_offset_scale_mhclo`, and adapter `full_proxy_influences`/`PreparedSkin::evaluate`.

- Complete cage recovery requires the exact source domain 0..19157. Repeated render entries must have exactly equal rest positions for a source ID. No duplicate is silently allowed to replace a conflicting coordinate. This establishes full fitted rest coverage, not body UV values.
- Accessory face-corner `(v,vt)` mapping is preserved separately from cage source IDs. The original UV and one V flip are recorded separately. The code does not flatten a seam to one UV per source vertex. It correctly avoids claiming Bevy triangulation/normal/tangent parity.
- The fitted position uses normalized signed helper coefficients, plus the declared signed axis difference divided by its reference length and multiplied by the offset. Both accessory offset and reference lengths use 0.1 metres conversion, with no axis swap or absolute-value replacement. Existing garment uses unit1. Single-helper rows copy their helper.
- Weight transfer accumulates signed helper contributions per bone, then retains every strictly positive final aggregate and normalizes all of them. Negative input coefficients are not clipped, and positive influences are not truncated to four. Source bone order comes from the actual 53-bone snapshot and is checked against source weight names.
- LBS uses the actual `skin` matrices on fitted model-local rest points. Stage arrays apply `display_transform` once. `model_to_world` is recorded but not applied a second time. This matches the actual uploaded-position/frame convention used by the prior checker.
- The existing garment control reconstructs all1797 garment source vertices, checks repeated rows, compares normalized full weights, and compares render-order uploaded positions. Existing delete-mask text is recorded only; new accessory delete masks reject. This is useful current-path reproduction, not an independent oracle for accessory fit quality.

No numerical threshold or formula change is needed for the retained inputs. The parser is a bounded parser for pinned assets, not a general replacement for the production loader. No broader hostile-input or arbitrary-format guarantee follows from this review.

## Independent identity and numerical checks

Independently rehashed all **15 declared source identities**, all **six original capture files** in the separate character-foundation worktree, and all **12 gzip mesh sidecars**. Capture SHA/length/request/revision/generation/sample match. Public compact frame fields and source/input identities agree with the full retained summary. All12 prepared experiment62 output files match the pinned decoded manifest's SHA and size. No image decoding was rerun.

Selected one actual case for independent arithmetic: `resume17_r4_tm1_b1_arm_rehearsal_v1_2.json`, torso−1/jaw0/arm source2. I wrote a separate in-memory parser and arithmetic calculation from the original MHCLO/source weights and raw snapshot; I did not call `fit.py`'s fitting, transfer, LBS, or garment-control implementation for this calculation.

The selected body contains22077 render entries, all19158 source IDs, and2919 exact duplicate rest entries. Results:

| Selected calculation | Independent result |
|---|---|
| Eyes rest and normalized weights | Exact equality with retained arrays |
| Eyes posed/model and stage arrays | Exact equality |
| Hair rest and normalized weights | Exact equality |
| Hair posed/model maximum component difference | 1.1102230246251565e−16 m |
| Hair stage maximum component difference | 2.220446049250313e−16 m |
| Eyes influences | All96 vertices have one head influence |
| Hair influences | Maximum5; two vertices exceed4;242 vertices have >1% nonhead weight |
| Existing garment rest maximum error | 8.465882606056852e−08 m |
| Existing garment normalized-weight maximum L1 | 7.264952478491793e−08 |
| Existing garment uploaded-position maximum error | 1.4805545911489304e−07 m |

The hair differences are floating-point summation-order differences in my independent expression, many orders below the existing arithmetic guard. My initial exact-equality assertion rejected this ~1e−16 difference; I inspected the cause and reported the measured difference rather than claiming bit equality. No reviewed source or retained result was changed. The garment errors reproduce the selected recorded control and remain below its declared1e−5 guards.

Ran the **six purely in-memory control tests**, normally and with Python `-O`: complete/duplicate cage, invalid/missing source IDs, signed offset/reference units, signed final aggregation, full five-influence LBS/invalid rows, and once-only placement. All12 executions pass. I inspected but did not rerun the two temporary-file parser/OBJ tests, to honor the single-report-write restriction. Therefore this review does not claim a fresh8/8 full-suite run. The original eight-test result remains separately recorded.

## Interpretation and unverified scope

The documents accurately describe six actual cages/bone frames and twelve offline outputs, with a current garment reproduction control. The tiny accessory motion in these two clips is correctly explained: neither clip specifically exercises the head chain. It does not establish rigid hair, natural hair dynamics, eye/eyelid contact, gaze, or arbitrary motion suitability.

Only the selected case received my fresh independent fitting/LBS arithmetic; all six capture identities and all twelve output identities were checked, but I did not rerun the six-case production script or a larger matrix. No independent MPFB/Blender oracle, current Humentity accessory runtime construction, Bevy upload, actual runtime UV/triangulation/normal/tangent parity, native/Web rendering, alpha material policy, eye/hair fit quality, collision, jaw variants, or performance was established. Cloth and M2 HOLD remain. The f64 computation and garment reproduction do not substitute for these gates.

## Reviewed identities

- `fit.py`: `59ba5b28d3468c6d13d737af6fdc4a6a9e2bb5de06f5027496fa5cc41f296a5f`
- `test_controls.py`: `c2bd9e56f3b31246f2423a2ef9bdd0c9d2e5cf223e91ab139761ab137922612e`
- `CONTRACT.md`: `33f4ffa5f26c5e39963287e57c3c6172f14e271f4db05f9f0f14ea810573729b`
- `README.md`: `c757b3a5325d9bd5d8a310feadf6699f2fa0aa635b9b61c95a523c404b271e2e`
- `RESULTS.json`: `566da74d5e4f6ef9c44d8d372d6ce6a67fd650d13a52667c518dde2f9c2030c9`
- `.work/final/summary.json`: `23425f72c79d7b397c5335c0a46a6a047e6f96d8be264367990d70529eedb483`

Only this report was written. No download, build, GUI/GPU action, source change, or external write occurred.

**VERIFIED — bounded source-policy review, all declared identities, one independently calculated real case plus garment control, six in-memory controls normal/−O. NOT-RUN — runtime/independent MPFB oracle/rendering/quality and #79 admission.**
