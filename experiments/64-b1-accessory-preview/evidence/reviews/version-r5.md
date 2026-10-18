# Version delta review r5 — CLEAR

R0 targeted check against the previously CLEAR candidate-v2. No material finding in the assigned version-gate delta. This review does not review the Python sink repair itself or admit runtime/visual quality.

VERIFIED — candidate manifest `000f9e41e801780039b493b1051ae2caa370809037687f892b96abbff021b957` and every member SHA/byte count match; the eight integrated verification files are byte-identical to the candidate. Prior reviewed manifest remains `19b0adf8efcdccbb6b05424e79f501a04c74f88356eb486ca6604814f7527a4f`.

All nine checker function ASTs are identical to reviewed v2, including the source-gate function. Numerical reference and test source are byte-identical. Checker changes only update its version docstring, canonical map constant and bundled map filename; required-field sets and CLI are unchanged.

The old/new maps have identical 13-key sets. Exactly `experiments/64-b1-accessory-preview/build/serve.py` and `build/test_serve.py` have new digests. All remaining mapped Rust, HTML, Cargo lock/manifest, README/contract and build.py hashes are unchanged. The current gate independently passes against actual repository files, all 12 source payloads and stable53 weights. Current canonical map SHA256 is `549ba3161723a92db3065fa79edd2d869dc06ea4c809558a8a2c6ef1f71303d4`; raw map SHA256 is `ba0b0f262859abb90aa7cf0a80432f968371125f83e81e1cf83c21cdffd6d7a9`. Replacing the expected canonical identity with old r4 in memory is rejected.

Metadata accurately distinguishes r4 compiled renderer/schema from the repaired r5 Python capture sink. Historical 44-control results are retained with an explicit `whole_44_suite_replayed: false`; the new targeted version gate is recorded separately. No new runtime result is attributed to this reviewer/helper. Same-producer/world/GPU/normal limits remain unchanged. These byte comparisons establish unchanged mapped compiled inputs, not a fresh binary-build attestation.

Checks actually run: candidate and integrated-package hashes; full checker AST and text delta; numerical/test byte comparison; old/new source-map key and digest delta; actual integrated `verify_freeze`; old expected-pin rejection. Evidence: `review-scratch/version-r5-results.json`.

NOT-RUN — full 44-control replay (unchanged logic, intentionally omitted), actual Web/native captures, binary/build provenance, sink implementation review, UI/GPU, visual acceptance, independent current-world or smoothing/tangent proof. Root reports actual capture collection separately; no actual capture was inspected or copied for this version review. No source changes were made.

## Candidate identities

- `check_capture.py`: `d75a9faf032e926a75ac5b5a8d867cb53a7924f834361874b18c375238b661c2`
- `TEST-RESULTS.json`: `642c17a6ff49a3bed7ef4ed1a9976ade55d222153a6e904d7f9e602ddbbea208`
- `source_reference.py`: `46d0e909b8f08822941e24e20d7fffdd47105b7ef86e0046da9f2a4fe225c572`
- `equivalence.json`: `f367c4dd4eb2edc3fffd23d23aa9b471a36416c89766978c7e4570ccaede32e9`
- `test_candidate.py`: `80f8ff4da3d7c6dec1edd2093fc36174218ecc02f5be471d98d33d3131532ade`
- `README.md`: `d7de73320704b735b7c4231c655847975c03db98219c87c493f730fc4c354da5`
- `source-freeze-r5.json`: `ba0b0f262859abb90aa7cf0a80432f968371125f83e81e1cf83c21cdffd6d7a9`
- `MANIFEST.json`: `000f9e41e801780039b493b1051ae2caa370809037687f892b96abbff021b957`
