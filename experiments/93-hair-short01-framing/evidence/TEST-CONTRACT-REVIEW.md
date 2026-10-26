# Targeted independent R2 — native protocol contract repair

**PASS for root to release one new offline native all27-test attempt.** Standards findings0; Spec findings0; no open P0/P1/P2/P3 findings. This verdict reviews the test-only correction, not native02 execution. The native01 gate remains FAIL26/1. Web/build/capture advancement still requires the new native gate to pass and root's explicit next-stage release.

Reviewed55-file freeze SHA256: `b21af4755aab185ecb54e0e8401b0d6faa4b11c969f4330f347f483fb76db973`. All55 current file hashes independently match. Compared against the preserved failed native01 freeze `ec154de8cec066038b336576ccf69582b74d39b969b7491e14b4e02370f4a4d0`, exactly three files changed: `src/protocol_tests.rs`, `test_isolation.py`, `README.md`; remaining52files match. Runtime candidate/controller/camera, geometry, source/import tests, Work/reference fixtures, Cargo dependencies, raw-transfer contract, source/math tolerances and request-uniqueness repair are unchanged. Root's scope readback also records old91source45 and92source8 unchanged.

## Failure classification

Confirmed from retained log/source: native01 executed27tests,26PASS/1FAIL, exit101, no timeout. In `steady_actual_controller_a_b_a_preserves_image_policy_and_restores_exact_a`, the test selected real BShort01, passed its held readiness checks, checked image policy and different image bytes, then required every hair array equal original short04 A under an alpha-only expectation. The failed assertion at old line405 describes the wrong asset contract. A source-distinct short01 mesh correctly has its own geometry, topology and UVs. The failure stopped before `capture_variant(...steady-a2...)`, so this test's subsequent exact A2 restoration remains NOT-PROVEN by native01.

Five actual source tests and both framing/controller-camera-predicate tests passed in native01. Those results support the classification, but never convert the entire native gate or unexecuted A2 tail to PASS. `CLASSIFICATION.md` preserves the earlier finding.

## Repair meaning and narrowness

The patch removes only the obsolete B==A-array expectation and adds a positive short01 upload contract:

- Actual B arrays are retained immediately after controller capture. Three further held-ready updates must preserve those exact arrays.
- POSITION and NORMAL deserialize into f32three-component rows; each has3177entries, all finite, and each array differs from A. This adds structural checks beyond merely asserting inequality.
- The exact short01 source-map bytes are authenticated against SHA256 `218b454cd9100c9dcbb725f1aba0bf1a21ad97817b3ef4eb453b2f291de1432c`.
- Actual and expected UVs deserialize in the existing exact typed-f32 domain, while corner indices compare exactly as u32. Published candidate source/UV corner pairs match the same authenticated map. The unchanged source tests bind that map to the actual short01 importer.
- Existing A1/B/A2 ready checks, image policy equality, distinct B pixel bytes, and exact A2original image plus all original mesh arrays remain byte-for-byte in place. No error is caught, test skipped, tolerance widened or state mutated to accommodate the assertion.

These checks are appropriate to the steady-controller test. They establish positive asset structure/mapping and stability while leaving full source-fit arithmetic to existing source tests/raw validators. They do not independently prove new-frame geometry, rendering or continuous motion. Actual execution of this corrected A2 tail remains mandatory.

The isolation guard no longer demands protocol_tests.rs be wholly identical to91. Instead it requires exactly one occurrence each of the old steady-B block and old B assertion, then demands full-file equality after precisely those two literal replacements. The rest of the protocol file cannot silently drift. This is a narrow documented test-contract exception to the preserved runtime copy rule, not a generic waiver. README accurately records the native failure and keeps A2success NOT-RUN until the new run.

## Verification and preservation

Read both complete updated control logs and independently checked their receipt/log hashes and binding to b21freeze:

| Mode | Result | Receipt elapsed | Limit |
| --- | --- | --- | --- |
| Normal |9/9PASS, exit0;55source files unchanged|36.776049708s|240s; no timeout|
| Optimized (-O) |9/9PASS, exit0;55source files unchanged|35.712941916s|240s; no timeout|

These are author Python3.9.5 executions. They validate the textual/capture guards, not Rust compilation or execution of the new assertions. Reviewer ran no tests/replay/build.

Independently authenticated native01 raw Cargo log and receipt against NATIVE-RESULT.json. Retained exact executed binary SHA256 is `d5437537209787aec862dd2e6211898df988ba3b066113bc435bf2d02d9753ef`; its bytes match. All55 source files copied under `failed-native01-preserved/source` match the failed freeze, and all files listed in its preservation manifest match their hashes. The failed log/receipt/gate and original source remain recoverable. No old failure is rewritten or discarded.

## Release limits

Root may issue the separate native02gate for all27tests under existing offline/cache/budget restrictions. No test selection, skip or result substitution may omit the corrected steady-controller path. Require27/27PASS with current freeze identity, new exact executable/run receipt and actual A2tail reached before treating native gate as passed. Preserve native01 alongside it.

The exact full93camera, actual12distinct captures,8original A/Bimages and independent visual review remain unrun. The one predetermined target1.60 is still the only framing. Any incomplete required frontal hairline/crown, missing material improvement or new defect invokes the existing stop rule. No new downloads/models/resources, extra framing, source tuning or added playing observation is authorized by this report. Phase1 remains PARTIAL; formal identity/CLI/shared product changes stay gated. Existing M2/#80 HOLD,112 original FAIL,#3 blocked and #4 gaps remain.

VERIFIED — failure classification, bounded meaningful test repair,55current/55failed source hashes, preserved failure log/receipt/executed binary, and both9/9control receipts. NOT-RUN — native02, corrected A2restoration execution, Web build/capture, visual or phase1 acceptance. Only files in code-review/native-fix were written by reviewer.
