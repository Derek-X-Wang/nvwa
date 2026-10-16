# Independent R2 targeted re-review — 55 evidence binding

**PASS within reviewed scope. The accepted P2 is resolved. No remaining actionable findings.**

Frozen review packet SHA256: `15c340feedac80d77866cf2dcdb5208f77b92db38f4f36a7338c6fa842ecb083` (`experiments/55-source-character-runtime/ready-inventory-v2.json`).
Comparator SHA256: `1e516a14793f387d1d7c457ea82b28deccaf72b1057f9c434146982b1478a29c`.
Controls SHA256: `d7284ffa3a63840dcdde46f6e6935694272682c8f1ec0e6f8478e908e5d60e3d`.

## Fix and counterexample

The comparator now validates run schema/route/sample/common-manifest/status, complete unique eight-case identity, per-case successful exit and actual execution, and each candidate output hash before loading geometry. It also binds binary, command binary, adapter source, successful build manifest/lock and B1 patch. These checks raise explicit failures rather than relying on Python assertions.

The unchanged ORIGINAL reviewer counterexample from the first review now rejects with exit 2 and `execution output SHA256 mismatch: neutral`. No comparison receipt is created. All its geometry replacements remain private review counterexamples, not experiment outputs.

Missing variant is not generically interpreted as B0. The historical original B0 summary is admitted only when its exact summary hash and binary hash match the checkpoint recorded before B1. An independently tested missing-variant B1 copy rejects.

## Executed verification

```sh
python3 -B .work/character-actual-independent-review/verify_55_fix.py
```

Evidence: `.work/character-actual-independent-review/55-fix-rerun/55-fix-verification.json`.

- Independently reproduced all ten implementation control classes on copied real B1 results: changed output bytes, failed summary, changed output hash, missing case, nonzero exit, false execution flag, wrong common manifest, wrong variant, wrong binary and wrong adapter. All exit 2, create no receipt and preserve copied inputs.
- Added duplicate-case and missing-variant rejection checks, plus the original reference-coordinate replacement counterexample: **13 negative controls passed**.
- Reran the same fixed comparator on untouched B0 and B1 outputs. Generated receipts match the final bound receipts exactly. B0 exits 3 with `numeric_parity_failed` / `candidate_algorithms_changed: false`; B1 exits 0 with `within_numeric_tolerance` / `candidate_algorithms_changed: true`.
- Verified every frozen review-file, retained-artifact and retained-output hash/size before and after controls: 119 entries, 238 checks. Verified both complete derived source trees, both adapter trees, sample data tree, config tree and common manifest identity. Both original binaries, raw runs and locks remain unchanged.
- Rechecked hashes from the prior 53/54 review. All previously reviewed 54 files and 53 reference/contract sources are unchanged. Observed 53 changes are the already accepted downloader repair and two README updates; read the updates. Read final 55 REPORT, ACTUAL and REVIEW-PACKET plus root 53 RESULTS synthesis.

The verification script's initial run completed the negative and positive checks but stopped on a final reviewer allowlist that omitted the announced delivery README update. After inspecting that README, a fresh-output rerun passed. This was review scaffolding, not a product or comparator failure. Prior negative evidence was retained.

## Conclusions and limits

The bounded synthesis is consistent with evidence: A passes source geometry/endpoints/proxy metrics; unchanged B0 executes but fails body and garment numeric parity; the isolated one-line B1 change passes the same eight cases and fixed tolerances. Prioritizing B1 for the next pose/rest/graphics experiment while retaining A as an independent control is a supported next experiment, not a production selection.

B1's maximum garment error remains `7.581710815385279e-6 m` under the declared `1e-5 m` threshold. Its maximum body/helper error is `4.0531158440604287e-7 m`; joint heads `3.4570693963065224e-7 m`. These do not verify rest-frame/IBM equivalence, joint tails, posed skinning, graphics, browser, full Work exchange, style or production performance. Candidate execution/build and numerical parity remain distinct claims. No production character/dependency is admitted.

VERIFIED — Both review P2 findings are corrected and independently retested at the frozen hashes. Current 53/54/55 numerical evidence and limited synthesis remain consistent. NOT-RUN — fresh Cargo/Rust/Blender execution, graphics/GPU, browser, poses, rest/IBM-frame parity, tails, performance/adoption acceptance. No real network or downloads performed. Reviewed files untouched; no owned processes remain. Reviewer-created copies and reports are intentionally retained under `.work/character-actual-independent-review` for root publication/cleanup.
