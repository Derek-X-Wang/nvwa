# Independent targeted R1 re-review, round 2 — CLEAR

The prior P2 is resolved in the exact eight-file candidate whose manifest SHA256 is `19b0adf8efcdccbb6b05424e79f501a04c74f88356eb486ca6604814f7527a4f`. No remaining actionable P1/P2 finding in the assigned targeted scope. This clears the public verification package review; it does not establish runtime acceptance.

## Resolution verified

`check_capture.py:11-30` defines exact frozen runtime/accessory/material field sets and requires nonempty entity, mesh, material and image handles, finite metadata arrays and a 64-character lowercase hexadecimal upload digest. `protocol` requires full/compact runtime fields. `check_record:118,133-134` validates both full and compact accessory observations before comparing every expected compact field. Missing fields can no longer remove their own comparisons. Valid-shaped full/compact upload digests must agree.

Direct diff against preserved candidate-v1 confines checker behavior changes to the intended validators and protocol/observation checks. `source_reference.py` remains byte-identical (`46d0e909b8f08822941e24e20d7fffdd47105b7ef86e0046da9f2a4fe225c572`); direct AST comparison confirms all ten numerical/helper functions still equal the private original. Four unchanged historical parser/projector functions remain AST-identical; protocol/check_record changes and the two added validators are accurately recorded in equivalence.json and README. Original private reference/adapter file hashes remain unchanged. Arithmetic, tolerances and complete positive influences are preserved.

## Checks actually run

- Updated `test_candidate.py` against reviewer-owned relocated public inputs: all 44 rejection controls pass, valid ARTIFICIAL fixture passes, source gate and missing/changed frozen source reject correctly.
- Both public CLI coherent-negative tests pass: name-only compact accessories and malformed upload hash return nonzero at the intended parser guard and create no success output.
- Independent 78-case omission/malformed-value sweep: delete every full accessory field, every compact accessory field, every nested material field, every full runtime field and every compact runtime field; malformed/uppercase/short/long/newline/nonstring upload hashes; full/compact valid-shaped hash mismatch; name-only compact; blank identity handles. All 78 reject. Report and receipt are coherently regenerated from separate JSON-derived objects so rejection cannot be explained by accidentally inconsistent copies.
- Valid unchanged ARTIFICIAL fixture still passes `PASS_WITH_LIMITS`. All eight files moved into another directory with spaces and invoked from `/` with Python `-S`, against a separately relocated public-input repository: PASS_WITH_LIMITS. No retained private captures or installed packages needed.
- Manifest identity, all seven member hashes/byte counts, original reference/adapter hashes, source-reference hash, and 13-file source-freeze gate verified. Candidate files rehashed unchanged at report creation.

Evidence: `review-scratch/rereview-r2-independent-results.json` (78 independent controls and hashes), `review-scratch/rereview-r2-suite/test-results.json` (44 controls and two CLI negatives), `review-scratch/rereview-r2-suite.log`, and `review-scratch/ARTIFICIAL-rereview-r2-moved-result.json`.

The README still explicitly limits protocol binding to the same producer, upload digest validation to syntax/equality rather than Rust JSON digest recomputation, CPU observations rather than GPU readback, and normals to finite/unit checks. No independent-world, visual, smoothing or tangent proof is asserted. Coherently stale whole-bundle acceptance remains a disclosed limitation.

NOT-RUN — actual native/Web captures, runtime build, UI/GPU, visual acceptance, independent current-world freshness, MPFB/Blender oracle, smoothing/tangent parity and the original six actual captures. No candidate, historical original or runtime source was mutated; no actual private raw capture was copied. Reviewer-generated scratch fixtures remain for root-owned retention/cleanup.

## Reviewed identities

- `MANIFEST.json`: `19b0adf8efcdccbb6b05424e79f501a04c74f88356eb486ca6604814f7527a4f`
- `README.md`: `d36a3bec8ed31129e3a5115e0bb75e8f09eefa6499ad48b7c48dacf2faaac662`
- `TEST-RESULTS.json`: `da9996cbea2efd68630988b80cf0f63506450d03dd733a402c6ce78ce70c3c27`
- `check_capture.py`: `37080426fee1d4c3f24fdddfd7e2f300f409ff73df5359a08114624897360c5f`
- `equivalence.json`: `fe41943fee5be0fb0bfa861a5383eee6f27ee6e47871c9dd2a5c3538bde15b2c`
- `source-freeze-r4.json`: `099e50f48496c7e9b139c1579c9e91ad4b7e648b809af94811f8f4c04576a51f`
- `source_reference.py`: `46d0e909b8f08822941e24e20d7fffdd47105b7ef86e0046da9f2a4fe225c572`
- `test_candidate.py`: `80f8ff4da3d7c6dec1edd2093fc36174218ecc02f5be471d98d33d3131532ade`
