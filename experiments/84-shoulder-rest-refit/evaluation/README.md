# Rest-source position evaluation

The original experiment81 historical input authenticator remains unchanged in `authenticate_inputs`. It still requires the missing original compressed bytes and cannot accept recaptures.

The `authenticate_hybrid` seam has two explicit, separately authenticated cohort kinds. Native `current18-plus-original-anchor-v1` maps to `collect.py` and manifest `hybrid-current18-original-anchor`. Wasm `current18-wasm-plus-original-anchor-v1` maps to lazy-loaded `collect_wasm.py` and manifest `hybrid-current18-wasm-original-anchor`. Each contains eighteen current production CPU captures of the original recipes on its declared target, plus the unchanged original fresh default anchor. The Wasm authenticator owns its completed `wasm32-unknown-unknown` build/target receipt checks. Missing Wasm support, cross-labeled cohort manifests and authenticator failure have no native fallback. The failed native corpus and its exact anchor gate stay unchanged. It reruns source, complete bone and influence checks. It verifies current source bytes against the capture source inventory. Exact historical replay stays `MISSING / NOT-RUN`.

Before candidate bytes are read, `baseline_preflight` reconstructs every original body and garment rest row, including all render duplicates. The shared original/candidate path constructs raw neutral base and raw case shape, stores `f32(shape-base)`, then reconstructs `f32(base+delta)` exactly where production reads its morph. Garment shape fitting uses raw authenticated case helpers. This source reconstruction must be within **1e-7 m per component**. Each of all19 slots, including the original anchor with its own actual recipe/schema, separately checks scalar-f32 PreparedSkin matrix blending and independent source-weight/FK/binary64 LBS against the original posed arrays. Both use the frozen **1e-5 m per component** bound. Reports retain each method's maxima, component totals and exact/nonexact counts. These are independent baseline checks; copying unaffected candidate rows cannot hide a failed reconstruction.

A root receipt must pin the policy SHA, cohort kind, cohort manifest SHA, source inventory SHA and analytical execution closure. `verify_execution(freeze)` requires `execution_files`, a sorted unique list of `{path,bytes,sha256}`, and `execution_files_sha256`, the SHA256 of that list encoded as JSON with `sort_keys=True,separators=(",",":")`. File paths are safe repository-relative paths; bytes and SHA must match current disk files. The inventory must cover every `.py` file under experiments60/70/79/81/84 (full names in `EXECUTION_DIRECTORIES`); additional imported helpers may also be included. This guard runs before input admission and is callable by generator admission. Baseline/scoring receipts pin its digest. The policy uses `thresholds` exactly as `THRESHOLDS` in `evaluate_rest.py`, historical `input_hashes_sha256`, `baseline_rest_bound_m=1e-7`, `baseline_posed_bound_m=1e-5`, and the same new cohort fields. Preflight accepts `FROZEN_BASELINE_PREFLIGHT`; scoring accepts only `FROZEN_FOR_SCORING` and requires the frozen `candidate_sha256`.

```sh
python3 -B experiments/84-shoulder-rest-refit/evaluation/evaluate_rest.py \
  --freeze ROOT_RECEIPT.json --policy FROZEN_POLICY.json \
  --corpus CURRENT18_DIRECTORY --fresh ORIGINAL_ANCHOR.json \
  --preflight-only --out UNIQUE_BASELINE_REPORT.json
```

Scoring additionally requires `--candidate NEW.mhclo --retained ORIGINAL_RETAINED_DIRECTORY`, without `--preflight-only`. The policy declares exact `position_source_ids`, `incident_triangles0`, `normal_source_ids`, `normal_accumulation_triangles0`, `max_displacement_m=0.020` and `support_radius_m=0.070`. The evaluator reconstructs closure membership and connectivity from unchanged runtime source topology. Only declared MHCLO offset token spans 6/7/8 may change. The validator masks those exact spans and compares every other byte, including whitespace and line endings on supported rows. The original OBJ stays exact. Both fitted rest and posed case displacement must remain within 20 mm.

The scorer uses the unchanged experiment81 proper crossing and ray kernels, source body7941/7983 probes, degenerate threshold, winding check and strict original-default ROI benefit. The original rejected source847 witness must still produce its known new pair through the same crossing function used by scoring.

This is **position-only analytical evaluation**. Copied baseline normal/tangent fields are placeholders, not claimed new rest-source output. Source-fitter generated normals/tangents, actual candidate upload, Web/CLI, GPU, visual adoption, global collision and between-sample behavior remain NOT-RUN. The rest asset intentionally changes neutral/knee/end-arm geometry inside support; the old corrective zero-activation tests stay intact and are not new-asset requirements.

Short controls:

```sh
NVWA_SHOULDER_RETAINED=ORIGINAL_RETAINED_DIRECTORY \
  python3 -B -m unittest discover \
  -s experiments/84-shoulder-rest-refit/evaluation -p 'test_*.py' -v
```

Repeat with `-O` to check optimized Python. Without the retained directory, the actual old-witness test is explicitly skipped. Synthetic cohort controls test admission failures only; they are not capture or geometry evidence. Root owns scheduling runs over five minutes and all resource cleanup.

Wasm adapter controls currently verify wrong cohort/target routing, unavailable module, preserved authenticator failures and exact frozen hash forwarding. The target/tamper/source delegation controls use a mocked Wasm API until its separately owned collector is finalized. They are interface evidence, not actual Wasm build/corpus admission. The shared original exact53-bone anchor comparison, all19 baseline reconstruction and all numerical/geometry gates remain unchanged.
